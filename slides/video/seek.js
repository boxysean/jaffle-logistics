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
    count:  { at: 0.9, dur: 1.1 }
  };

  try {
    var cues = JSON.parse(params.get('cues') || '[]');
    cues.forEach(function (c) {
      if (c.anim === 'panels-in') cfg.panels.at = c.at;
      else if (c.anim === 'charts' || c.anim === 'draw-charts' || c.anim === 'bars-in') cfg.charts.at = c.at;
      else if (c.anim === 'count-up') cfg.count.at = c.at;
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
