#!/usr/bin/env python3
"""Deterministically give seeds/support_tickets.csv a response clock: four new
columns appended at the end of every row --

    first_response_at, resolved_at, first_response_hours, resolution_hours

ADDITIVE, BYTE-PRESERVING: the file is read as text and every existing line
keeps its original bytes (CRLF included); only ",<4 fields>" is inserted
before each line terminator. csv is used only to *read* the values the clock
is computed from, never to re-serialise the existing fields (the body carries
embedded commas and ~~NL~~-escaped newlines and must stay byte-identical).
Refuses to run twice: reset with `git checkout -- seeds/support_tickets.csv`.

Column semantics:
  * first_response_at    -- never null; every ticket got a first human reply.
  * resolved_at          -- set iff status == 'resolved' ('pending' and 'open'
                            are both unresolved), empty otherwise.
  * first_response_hours -- (first_response_at - opened_at) in hours, 2 dp.
  * resolution_hours     -- (resolved_at - opened_at) in hours, 2 dp, empty when
                            unresolved; always >= first_response_hours + 0.25.

Clock model:
  * Desk hours 08:00-19:00 local, seven days a week. Phone and chat have an
    overnight on-call cover (slower); email and portal wait for the desk to
    open (the overnight inbox is cleared first thing); a reply that would go out
    after the late shift wraps up (22:00) slips to the next morning.
  * Channel base (median hours of desk time): phone < chat < portal < email.
  * Priority proxy, derived from the body for generation only (no column):
      high (faster): "second time", "unacceptable", "furious", "escalate",
                     "i need answers today", "zero communication"
      low  (slower): "no rush", "when you have a moment",
                     "i understand there may be delays"
  * 2023-2024 are quiet: answered within hours, nothing day-scale.
  * 2025 is strained, but only in two places: Jaffle Werke (CLI-0042) gets a
    right-skewed (log-normal) multiplier that pushes a real share of its
    tickets into days; tickets whose shipment originates at the busiest hub,
    Paris (HUB-PAR), get a milder one. CLI-0042 tickets out of HUB-PAR take the
    worse of the two. Every other 2025 ticket is only mildly slower.
  * Resolution = first response + a positive right-skewed working time
    (same-shift for quick tickets, longer for the strained 2025 ones).
  * Nothing after the dataset's present (2025-12-31T23:59:59): timestamps that
    would run past it are clamped, keeping first_response_at >= opened_at + 1
    minute and resolved_at comfortably after first_response_at.
"""
import csv, os, sys, random, datetime, collections, statistics

SEED = 20251231
HERE = os.path.dirname(os.path.abspath(__file__))
SEEDS = os.path.join(HERE, "..", "seeds")
TICKETS = os.path.join(SEEDS, "support_tickets.csv")
SHIPMENTS = os.path.join(SEEDS, "shipments.csv")

FMT = "%Y-%m-%dT%H:%M:%S"
NEW_COLS = ["first_response_at", "resolved_at", "first_response_hours", "resolution_hours"]
PRESENT = datetime.datetime(2025, 12, 31, 23, 59, 59)
DESK_OPEN, DESK_CLOSE = 8, 19
MINUTE = datetime.timedelta(minutes=1)

STRAINED_CLIENT = "CLI-0042"      # Jaffle Werke -- Equipment
BUSIEST_HUB = "HUB-PAR"           # Paris

# Median hours of desk time to a first reply, phone fastest -> email slowest.
CHANNEL_BASE = {"phone": 1.2, "chat": 1.8, "portal": 2.8, "email": 3.8}
OVERNIGHT_CHANNELS = {"phone", "chat"}       # on-call cover after hours
OVERNIGHT_SLOWDOWN = 1.6
MORNING_TRIAGE = 0.35                        # overnight email/portal cleared at 08:00
LATE_SHIFT_START, LATE_SHIFT_END = 7, 22     # a reply drafted in-shift may go out 07:00-22:00

HIGH_PRIORITY = ["second time", "unacceptable", "furious", "escalate",
                 "i need answers today", "zero communication"]
LOW_PRIORITY = ["no rush", "when you have a moment", "i understand there may be delays"]
PRIORITY_FACTOR = {"high": 0.6, "normal": 1.0, "low": 1.5}


def priority(body):
    text = body.lower()
    if any(k in text for k in HIGH_PRIORITY):
        return "high"
    if any(k in text for k in LOW_PRIORITY):
        return "low"
    return "normal"


def in_desk_hours(ts):
    return DESK_OPEN <= ts.hour < DESK_CLOSE


def next_desk_open(ts):
    """The next 08:00 at or after ts (ts itself if it already is inside desk hours)."""
    if in_desk_hours(ts):
        return ts
    day = ts.date() if ts.hour < DESK_OPEN else ts.date() + datetime.timedelta(days=1)
    return datetime.datetime.combine(day, datetime.time(DESK_OPEN))


def hours(a, b):
    return (b - a).total_seconds() / 3600.0


def floor_minute(ts):
    return ts.replace(second=0, microsecond=0)


def response_multiplier(rng, year, client, hub):
    """(first-response multiplier, working-time multiplier) for one ticket.
    Both draws are always made so the stream is identical regardless of branch."""
    werke = rng.lognormvariate(2.2, 0.95)        # median ~9x, long right tail
    paris = rng.lognormvariate(0.85, 0.45)       # median ~2.3x
    mild = rng.uniform(1.1, 1.5)
    if year < 2025:
        return 1.0, 1.0
    mults = [mild]
    work = [1.3]
    if client == STRAINED_CLIENT:
        mults.append(werke)
        work.append(6.0)
    if hub == BUSIEST_HUB:
        mults.append(paris)
        work.append(2.0)
    return max(mults), max(work)


def clock(rng, row, hub):
    opened = datetime.datetime.strptime(row["opened_at"], FMT)
    year = opened.year
    channel = row["channel"]
    prio = priority(row["body"])

    noise = rng.lognormvariate(0.0, 0.35)
    work_draw = rng.lognormvariate(1.3, 0.7)     # median ~3.7 h, same-shift-ish
    resp_mult, work_mult = response_multiplier(rng, year, row["client_id"], hub)
    jitter_min = rng.randint(0, 20)

    desk_hours = CHANNEL_BASE[channel] * PRIORITY_FACTOR[prio] * noise * resp_mult
    if channel in OVERNIGHT_CHANNELS:
        start = opened
        if not in_desk_hours(opened):
            desk_hours *= OVERNIGHT_SLOWDOWN
    elif not in_desk_hours(opened):
        # the overnight inbox is worked first thing in the morning
        start = next_desk_open(opened)
        desk_hours *= MORNING_TRIAGE
    else:
        start = opened
    desk_hours = min(desk_hours, 110.0)          # keep the worst tail under ~5 days
    first = start + datetime.timedelta(hours=desk_hours)
    if channel not in OVERNIGHT_CHANNELS and not (LATE_SHIFT_START <= first.hour < LATE_SHIFT_END):
        first = next_desk_open(first) + datetime.timedelta(minutes=jitter_min)
    first = floor_minute(first)
    first = max(first, opened + MINUTE)

    resolved = None
    if row["status"] == "resolved":
        work = min(max(work_draw * work_mult, 0.5), 190.0)
        resolved = floor_minute(first + datetime.timedelta(hours=work))

    # Nothing after the dataset's present.
    if resolved is not None and resolved > PRESENT:
        resolved = floor_minute(PRESENT)
        first = min(first, resolved - datetime.timedelta(minutes=30))
        first = max(first, opened + MINUTE)
    if first > PRESENT:
        first = max(floor_minute(PRESENT), opened + MINUTE)
    return opened, first, resolved


def load_hubs():
    with open(SHIPMENTS, newline="") as fh:
        return {r["shipment_id"]: r["origin_hub_id"] for r in csv.DictReader(fh)}


def split_lines(text):
    """Split into physical CRLF lines (terminator kept separately). The seed has
    no real newlines inside quoted fields (~~NL~~ escapes them), so one
    physical line is one record -- asserted against csv.reader below."""
    assert text.endswith("\r\n"), "expected a CRLF-terminated file"
    lines = text[:-2].split("\r\n")
    assert all("\n" not in l and "\r" not in l for l in lines), "stray bare CR/LF in seed"
    return lines


def fmt_h(x):
    return "%.2f" % x


def pct(values, q):
    s = sorted(values)
    k = (len(s) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def print_table(title, groups):
    print("\n" + title)
    print("  %-22s %4s | %8s %8s %8s | %8s %8s %8s" % (
        "group", "n", "fr_med", "fr_p90", "fr_max", "res_med", "res_p90", "res_max"))
    for key in sorted(groups):
        fr = [r[0] for r in groups[key]]
        rs = [r[1] for r in groups[key] if r[1] is not None]
        res = ("%8.2f %8.2f %8.2f" % (statistics.median(rs), pct(rs, 0.9), max(rs))
               if rs else "%8s %8s %8s" % ("-", "-", "-"))
        print("  %-22s %4d | %8.2f %8.2f %8.2f | %s" % (
            " ".join(key), len(fr), statistics.median(fr), pct(fr, 0.9), max(fr), res))


def main():
    with open(TICKETS, "rb") as fh:
        text = fh.read().decode("utf-8")
    lines = split_lines(text)
    header = lines[0].split(",")
    if "first_response_at" in header:
        sys.exit("support_tickets.csv already has first_response_at; reset it first with "
                 "`git checkout -- seeds/support_tickets.csv` and re-run.")

    before = list(csv.reader(lines))
    assert len(before) == len(lines), "a record spans more than one physical line"
    orig_header, orig_rows = before[0], before[1:]
    rows = [dict(zip(orig_header, r)) for r in orig_rows]
    hubs = load_hubs()

    rng = random.Random(SEED)
    out = [lines[0] + "," + ",".join(NEW_COLS)]
    for line, row in zip(lines[1:], rows):
        opened, first, resolved = clock(rng, row, hubs.get(row["shipment_id"]))
        fields = [first.strftime(FMT),
                  resolved.strftime(FMT) if resolved else "",
                  fmt_h(hours(opened, first)),
                  fmt_h(hours(opened, resolved)) if resolved else ""]
        out.append(line + "," + ",".join(fields))
    with open(TICKETS, "wb") as fh:
        fh.write(("\r\n".join(out) + "\r\n").encode("utf-8"))

    # ------------------------------------------------------------ self-test
    with open(TICKETS, "rb") as fh:
        raw = fh.read()
    new_lines = raw.decode("utf-8")[:-2].split("\r\n")
    assert raw.count(b"\r\n") == raw.count(b"\n") == len(new_lines), "line terminators changed"
    for old, new in zip(lines[1:], new_lines[1:]):
        assert new.startswith(old + ","), "existing bytes changed"
    with open(TICKETS, newline="") as fh:
        after = list(csv.reader(fh))
    assert after[0] == orig_header + NEW_COLS, "header changed"
    assert len(after) - 1 == len(orig_rows) == 403, "row count changed: %d" % (len(after) - 1)
    unchanged = sum(1 for a, b in zip(after[1:], orig_rows) if a[:8] == b)
    assert unchanged == len(orig_rows), "existing columns changed"

    enriched = [dict(zip(after[0], r)) for r in after[1:]]
    stats_client = collections.defaultdict(list)
    stats_hub = collections.defaultdict(list)
    for r in enriched:
        opened = datetime.datetime.strptime(r["opened_at"], FMT)
        assert r["first_response_at"], r["ticket_id"]
        first = datetime.datetime.strptime(r["first_response_at"], FMT)
        assert first >= opened, r["ticket_id"]
        frh = float(r["first_response_hours"])
        assert frh >= 0, r["ticket_id"]
        assert first <= PRESENT, r["ticket_id"]
        is_resolved = r["status"] == "resolved"
        assert is_resolved == bool(r["resolved_at"]) == bool(r["resolution_hours"]), r["ticket_id"]
        rh = None
        if r["resolution_hours"]:
            resolved = datetime.datetime.strptime(r["resolved_at"], FMT)
            rh = float(r["resolution_hours"])
            assert frh < rh and rh - frh >= 0.25, r["ticket_id"]
            assert resolved >= first and resolved <= PRESENT, r["ticket_id"]
        year = r["opened_at"][:4]
        stats_client[(year, r["client_id"])].append((frh, rh))
        stats_hub[(year, hubs.get(r["shipment_id"], "-"))].append((frh, rh))

    def minmax(col):
        v = [r[col] for r in enriched if r[col]]
        return "%s .. %s (nulls %d)" % (min(v), max(v), len(enriched) - len(v))

    print("rows:", len(enriched))
    print("opened_at         min/max:", minmax("opened_at"))
    print("first_response_at min/max:", minmax("first_response_at"))
    print("resolved_at       min/max:", minmax("resolved_at"))
    print("existing columns unchanged: OK (%d/%d rows)" % (unchanged, len(orig_rows)))
    print_table("first_response_hours / resolution_hours by (year, client_id):", stats_client)
    print_table("first_response_hours / resolution_hours by (year, origin_hub_id):", stats_hub)
    werke = [fr for fr, _ in stats_client[("2025", STRAINED_CLIENT)]]
    slow = sum(1 for fr in werke if fr > 24)
    print("\n%s 2025 tickets with first_response_hours > 24: %d/%d = %.1f%%" % (
        STRAINED_CLIENT, slow, len(werke), 100.0 * slow / len(werke)))


if __name__ == "__main__":
    main()
