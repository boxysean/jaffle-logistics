/* Video seek hook.
 *
 * The renderer opens the built deck as
 *
 *     presentation-video.html?slide=<n>&t=<seconds>&cues=<json>
 *
 * and, per frame, calls window.__vseek(t) to hold the page at an exact time. No ?t
 * means the page is being viewed normally: this script returns immediately and the
 * deck is untouched.
 *
 * Everything is computed from t and written as inline styles, so a screenshot at
 * t=1.5 is always the same pixels - no dependence on the wall clock.
 *
 * The animation, over a clip's local time:
 *   - panels fade + rise in reading order, stepped to match the 16-bit skin;
 *   - chart bars grow from their baseline, chart lines draw left to right;
 *   - numbers on screen count up to their final value.
 */
(function () {
  var params = new URLSearchParams(window.location.search);
  if (!params.has('t')) return;                       // normal viewing: do nothing

  var slideIndex = parseInt(params.get('slide') || '0', 10) || 0;
  document.documentElement.classList.add('vseek');

  // default timeline, in seconds local to the clip; cues from script.json override the starts
  var cfg = {
    panels: { at: 0.0, step: 0.16, dur: 0.34, rise: 16, steps: 4 },
    charts: { at: 0.7, dur: 1.2, stagger: 0.05 },
    count:  { at: 0.9, dur: 1.1 },
    truck:  { at: 0.3 },
    robot:  { at: 4.0 }
  };

  try {
    var cues = JSON.parse(params.get('cues') || '[]');
    cues.forEach(function (c) {
      if (c.anim === 'panels-in') cfg.panels.at = c.at;
      else if (c.anim === 'charts' || c.anim === 'draw-charts' || c.anim === 'bars-in') cfg.charts.at = c.at;
      else if (c.anim === 'count-up') cfg.count.at = c.at;
      else if (c.anim === 'truck') cfg.truck.at = c.at;
      else if (c.anim === 'robot') cfg.robot.at = c.at;
    });
  } catch (e) {}

  var clamp = function (x, a, b) { return x < a ? a : (x > b ? b : x); };
  var quant = function (p, n) { return Math.round(p * n) / n; };

  /* ---- number formatting: keep the original prefix/suffix and separators ------ */
  function parseNumber(s) {
    var m = s.match(/-?[\d][\d.,]*/);
    if (!m) return null;
    var raw = m[0];
    var hasDot = raw.indexOf('.') >= 0, hasComma = raw.indexOf(',') >= 0;
    var decSep = null, thoSep = null, decimals = 0;
    if (hasDot && hasComma) {
      decSep = raw.lastIndexOf('.') > raw.lastIndexOf(',') ? '.' : ',';
      thoSep = decSep === '.' ? ',' : '.';
    } else if (hasComma) { thoSep = ','; }
    else if (hasDot) { decSep = '.'; }
    var digits = raw;
    if (thoSep) digits = digits.split(thoSep).join('');
    if (decSep === ',') digits = digits.replace(',', '.');
    var value = parseFloat(digits);
    if (isNaN(value)) return null;
    if (decSep) decimals = (digits.split('.')[1] || '').length;
    var at = s.indexOf(raw);
    return { value: value, decimals: decimals, thousands: thoSep, decimal: decSep || '.',
             prefix: s.slice(0, at), suffix: s.slice(at + raw.length) };
  }

  function formatNumber(spec, v) {
    var s = spec.decimals > 0 ? v.toFixed(spec.decimals) : String(Math.round(v));
    if (spec.thousands) {
      var parts = s.split('.');
      parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, spec.thousands);
      s = parts.join(spec.decimal);
    }
    return spec.prefix + s + spec.suffix;
  }

  var numberEls = [];

  function captureNumbers(slide) {
    numberEls = [];
    slide.querySelectorAll('text.val, .v, .num').forEach(function (el) {
      var txt = el.textContent.trim();
      if (/^(19|20)\d\d$/.test(txt)) return;                    // years don't count up
      var spec = parseNumber(txt);
      if (!spec) return;
      if (Math.abs(spec.value) < 1.5 && spec.decimals === 0) return;   // skip 0 / 1 badges
      numberEls.push({ el: el, spec: spec });
    });
  }

  function draw(slide, T) {
    // panels: stepped fade + rise, in reading order (panels sit at any depth under .frame)
    slide.querySelectorAll('.frame .panel:not(.status)').forEach(function (el, i) {
      var p = quant(clamp((T - cfg.panels.at - i * cfg.panels.step) / cfg.panels.dur, 0, 1), cfg.panels.steps);
      el.style.opacity = p <= 0 ? '0' : String(p);
      el.style.transform = 'translateY(' + ((1 - p) * cfg.panels.rise).toFixed(1) + 'px)';
    });
    // chart bars grow from the baseline
    slide.querySelectorAll('svg rect.b').forEach(function (el, i) {
      var p = clamp((T - cfg.charts.at - i * cfg.charts.stagger) / cfg.charts.dur, 0, 1);
      el.style.transform = 'scaleY(' + p + ')';
    });
    // chart lines draw left to right
    slide.querySelectorAll('svg line.ln, svg line.tg, svg polyline').forEach(function (el, i) {
      var p = clamp((T - cfg.charts.at - i * cfg.charts.stagger) / cfg.charts.dur, 0, 1);
      var len;
      try { len = el.getTotalLength(); } catch (e) { return; }
      if (!len) return;
      el.style.strokeDasharray = len + ' ' + len;
      el.style.strokeDashoffset = (len * (1 - p)).toFixed(2);
    });
    // numbers count up to their final value
    var n = clamp((T - cfg.count.at) / cfg.count.dur, 0, 1);
    numberEls.forEach(function (o) {
      o.el.textContent = formatNumber(o.spec, o.spec.value * n);
    });
    truck(slide, T);
    robot(slide, T);
  }

  /* the game-has-changed scene: a person stands waving; the robot walks in from the right,
     bumps them off to the left, takes their spot and waves; the caption fades in as it does.
     The cue is when the robot starts walking. */
  function robot(slide, T) {
    var human = slide.querySelector('svg.scene g.human'), bot = slide.querySelector('svg.scene g.robot');
    if (!human || !bot) return;
    var A = cfg.robot.at, PI2 = Math.PI * 2;
    var ease = function (p) { return 1 - Math.pow(1 - p, 3); };
    var easeIn = function (p) { return p * p; };
    // the robot: walk in (A to A+1.4), shove and keep going to the middle (to A+2.2)
    var walk = ease(clamp((T - A) / 1.4, 0, 1)), settle = ease(clamp((T - A - 1.4) / 0.8, 0, 1));
    var bx = 1260 + (664 - 1260) * walk + (532 - 664) * settle;
    var walking = T > A && T < A + 2.2;
    bot.setAttribute('transform', 'translate(' + bx.toFixed(1) + ' ' + (134 - (walking ? Math.abs(Math.sin(PI2 * 3 * T)) * 4 : 0)).toFixed(1) + ')');
    var step = walking ? Math.sin(PI2 * 3 * T) : 0;
    slide.querySelector('svg.scene g.legL').setAttribute('transform', 'translate(0 ' + (-8 * Math.max(0, step)).toFixed(1) + ')');
    slide.querySelector('svg.scene g.legR').setAttribute('transform', 'translate(0 ' + (-8 * Math.max(0, -step)).toFixed(1) + ')');
    var wave = T > A + 2.4 ? 16 * Math.sin(PI2 * 1.6 * (T - A - 2.4)) : 0;
    slide.querySelector('svg.scene g.arm').setAttribute('transform', 'rotate(' + wave.toFixed(2) + ' 204 184)');
    // the person: waves until the shove, then is knocked over and off to the left
    var shove = easeIn(clamp((T - A - 1.4) / 0.7, 0, 1));
    human.setAttribute('transform', 'translate(' + (532 - 760 * shove).toFixed(1) + ' 150) rotate(' + (-70 * shove).toFixed(1) + ' 68 320)');
    var hwave = shove > 0 ? 0 : 18 * Math.sin(PI2 * 1.6 * T);
    slide.querySelector('svg.scene g.harm').setAttribute('transform', 'rotate(' + hwave.toFixed(2) + ' 120 92)');
    var cap = slide.querySelector('.robo-cap');
    if (cap) cap.style.opacity = String(quant(clamp((T - A - 2.4) / 0.4, 0, 1), 4));
  }

  /* the storm slide's truck: it drives down the icy on-ramp with the cab straight ahead, then
     jackknifes, the cab swinging 90 degrees about the hitch into the drawn pose; the skid marks
     appear as it slides and the warning triangle flashes once it has stopped */
  var HITCH = '194 276';
  function truck(slide, T) {
    var cab = slide.querySelector('svg g.cab'), trailer = slide.querySelector('svg g.trailer');
    if (!cab || !trailer) return;
    var ease = function (p) { return 1 - Math.pow(1 - p, 3); };
    var A = cfg.truck.at;                                    // the cue: when the truck appears
    var drive = ease(clamp((T - A) / 1.3, 0, 1));            // A to A+1.3s: rolls in from above
    var fold = ease(clamp((T - A - 1.2) / 0.5, 0, 1));       // A+1.2 to A+1.7s: jackknifes
    var dy = (-520 * (1 - drive)).toFixed(1);
    var wobble = (Math.sin(clamp((T - A - 1.2) / 0.9, 0, 1) * Math.PI * 2) * 4 * (1 - fold * 0.6)).toFixed(2);
    trailer.setAttribute('transform', 'translate(0 ' + dy + ') rotate(' + (fold > 0 ? wobble : 0) + ' ' + HITCH + ')');
    cab.setAttribute('transform', 'translate(0 ' + dy + ') rotate(' + (-90 * (1 - fold)).toFixed(2) + ' ' + HITCH + ')');
    var skid = slide.querySelector('svg g.skid');
    if (skid) skid.style.opacity = String(quant(clamp((T - A - 1.2) / 0.4, 0, 1), 4));
    var warn = slide.querySelector('svg g.warn');
    var W = T - A - 1.8;
    if (warn) warn.style.opacity = W < 0 ? '0' : (W < 1.2 ? (Math.floor(W * 5) % 2 ? '0.25' : '1') : '1');
  }

  var ready = false;
  window.__vseekReady = false;

  function start() {
    if (ready) return;
    ready = true;
    try {
      Reveal.configure({ transition: 'none', backgroundTransition: 'none', controls: false, progress: false });
      Reveal.slide(slideIndex, 0);
    } catch (e) {}
    var slide = Reveal.getCurrentSlide();
    if (!slide) { window.__vseekReady = 'noslide'; return; }
    captureNumbers(slide);
    draw(slide, 0);
    window.__vseekReady = true;
  }

  /* highlight what the voice is talking about: every element in the current slide matching the
     selector gets .vhl (anim.css draws it); an empty selector clears the highlight */
  window.__vhl = function (sel) {
    var slide = Reveal.getCurrentSlide();
    if (!slide) return 0;
    slide.querySelectorAll('.vhl').forEach(function (e) { e.classList.remove('vhl'); });
    if (!sel) return 0;
    var hits = slide.querySelectorAll(sel);
    hits.forEach(function (e) { e.classList.add('vhl'); });
    return hits.length;
  };

  window.__vseek = function (t) {
    if (!ready) start();
    var slide = Reveal.getCurrentSlide();
    if (slide) draw(slide, t);
  };

  function boot() {
    if (!window.Reveal) { window.__vseekReady = 'noreveal'; return; }
    if (Reveal.isReady && Reveal.isReady()) start();
    else Reveal.on('ready', start);
  }

  if (document.readyState === 'complete') boot();
  else window.addEventListener('load', boot);
})();
