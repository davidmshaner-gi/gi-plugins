#!/usr/bin/env python3
"""map.py: the one command behind the map-my-inbox deliverable (gi-plugins#176).

Stdlib only (the Cowork sandbox has no third-party packages and no outbound
HTTPS). Three commands:

  python3 map.py lint slices.json
      Check every cell the leader will read against the locked voice rules.
      Exit 1 with the offending cell on any hit. `build` runs this first.

  python3 map.py build slices.json threads.json [--out DIR] [--measurables FILE]
      Validate both files, write DIR/inbox-map-<date>.xlsx (one visible tab,
      Slices, the locked 22 columns, four dropdowns, example cells as links),
      and print the exact submit_inbox_map call to make on the lee-raleigh
      connector. This is the ONLY way the spreadsheet gets built; a session
      that hand-authors a sheet has skipped the gate.

  python3 map.py call slices.json threads.json
      Print the submit call only (no file).

slices.json: a list of rows with keys n, slice, looks_like, count,
reply_or_feed, fits, needs, does, examples (up to three {label, url}).
threads.json: summary rows with sender, subject, date, count, line and
optionally slice and url. Never a body.

The SLICE_COLUMNS literal below is byte-identical to the Worker's
(sow_1_analyst_pilot/mcp-server/src/tools/leader_context/inbox_map.ts);
the Worker's `npm run check:parity` compares the two against gi-plugins main.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys
import zipfile
from xml.sax.saxutils import escape

SLICE_COLUMNS = [
    "#",
    "Email Slice",
    "What it looks like",
    "Count",
    "Reply or feed",
    "Where this fits in your work",
    "What you'd need to know to answer it, and where that lives",
    "What you do with it, and when",
    "Example 1",
    "Example 2",
    "Example 3",
    "Real category? (yes / no / merge with #)",
    "Which measurable does it influence?",
    "Priority to AI-ify now (high / medium / low)",
    "Your comments",
    "AI-ification stage",
    "Runs this week",
    "Drafts",
    "Sent unedited",
    "Edits per draft (trend)",
    "Next unlock",
    "Progress notes",
]

STAGES = [
    "Triage",
    "Process mapping",
    "Context mapping",
    "I/O collection",
    "Agent impersonation",
    "Architecture spike",
    "Deployment",
    "Iterative loop",
    "Ongoing evaluation",
]
REAL_CATEGORY_OPTIONS = ["yes", "no", "merge with #"]
PRIORITY_OPTIONS = ["high", "medium", "low"]

MAX_SLICES = 40
MAX_THREADS = 200
MAX_LINE_CHARS = 240
THREADS_PER_SLICE = 10

SLICE_KEYS = {"n", "slice", "looks_like", "count", "reply_or_feed", "fits", "needs", "does", "examples"}
SLICE_TEXT_KEYS = ["slice", "looks_like", "count", "reply_or_feed", "fits", "needs", "does"]
THREAD_KEYS = {"sender", "subject", "date", "count", "line", "slice", "url"}

# Column widths, in Excel character units, one per SLICE_COLUMNS entry.
WIDTHS = [5, 30, 44, 12, 18, 48, 52, 48, 28, 28, 28, 18, 34, 18, 40, 20, 12, 10, 12, 16, 28, 36]
WRAP_COLS = {2, 3, 6, 7, 8, 15, 21, 22}


class MapError(Exception):
    pass


# ---------------------------------------------------------------------------
# Voice lint: what the leader reads is written the way he would explain it to
# a new hire. Nothing internal. (David, 2026-09-12; deviation log row 7.)
# ---------------------------------------------------------------------------

VOICE_RULES = [
    (re.compile("[–—]"), "an em dash or en dash (use a comma, a period, or parentheses)"),
    (re.compile(r"\bQ[1-3]\b"), "a Q1/Q2/Q3 label (the questions are headers, not cell text)"),
    (re.compile(r"\bstage\s*\d\b", re.I), "a stage number (name the thing, not the stage)"),
    (re.compile(r"(?<![\w/])#\d+\b"), "a card or issue number"),
    (re.compile(r"\b(lee|gi|gi-plugins)#\d*", re.I), "a repo card reference"),
    (re.compile(r"\bSOP\b"), "the word SOP (say what the process is)"),
    (re.compile(r"\b[LSPG]\d{1,2}\b"), "a chart process id (name the process in his words)"),
    (re.compile(r"\b(guess|GUESS):", re.I), "a 'Guess:' prefix (every cell is a guess; the sheet says so once)"),
]


def lint_text(text: str) -> str | None:
    for rx, why in VOICE_RULES:
        if rx.search(text or ""):
            return why
    return None


def lint_slices(rows: list[dict]) -> list[str]:
    """Lint the cells the session WROTE for the leader. Example labels are the
    threads' own subject lines (records; a sender's dash is not ours to fix) and
    are left alone, like the thread rows."""
    problems = []
    for i, r in enumerate(rows, 1):
        for k in SLICE_TEXT_KEYS:
            why = lint_text(str(r.get(k, "")))
            if why:
                problems.append(f"slice {i} ({r.get('slice', '?')}), {k}: {why}")
    return problems


# ---------------------------------------------------------------------------
# Validation (mirrors the Worker's validateSlices / validateThreads)
# ---------------------------------------------------------------------------

def _load(path: str):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def validate_slices(rows) -> list[dict]:
    if not isinstance(rows, list) or not rows:
        raise MapError("slices must be a non-empty list")
    if len(rows) > MAX_SLICES:
        raise MapError(f"slices has {len(rows)} rows; the cap is {MAX_SLICES}")
    out = []
    for i, raw in enumerate(rows, 1):
        if not isinstance(raw, dict):
            raise MapError(f"slice {i}: not an object")
        extra = set(raw) - SLICE_KEYS
        if extra:
            raise MapError(f"slice {i}: unknown key(s) {sorted(extra)}")
        row = {}
        for k in SLICE_TEXT_KEYS:
            v = raw.get(k, "")
            if v is None:
                v = ""
            if not isinstance(v, str):
                raise MapError(f"slice {i}: {k} must be a string")
            row[k] = v
        if not row["slice"].strip():
            raise MapError(f"slice {i}: slice name is required")
        n = raw.get("n")
        row["n"] = n if isinstance(n, int) else i
        ex = raw.get("examples") or []
        if not isinstance(ex, list) or len(ex) > 3:
            raise MapError(f"slice {i}: examples is a list of at most three {{label, url}}")
        examples = []
        for e in ex:
            if not isinstance(e, dict) or not str(e.get("label", "")).strip():
                raise MapError(f"slice {i}: each example needs a label")
            url = str(e.get("url", "") or "")
            if url and not url.startswith(("http://", "https://")):
                raise MapError(f"slice {i}: example url must start with http")
            examples.append({"label": str(e["label"])[:200], "url": url})
        row["examples"] = examples
        out.append(row)
    return out


def validate_threads(rows) -> list[dict]:
    if rows is None:
        return []
    if not isinstance(rows, list):
        raise MapError("threads must be a list")
    out = []
    for i, raw in enumerate(rows, 1):
        if not isinstance(raw, dict):
            raise MapError(f"thread {i}: not an object")
        extra = set(raw) - THREAD_KEYS
        if extra:
            raise MapError(
                f"thread {i}: unknown key(s) {sorted(extra)}; summary rows only "
                "(sender, subject, date, count, line, slice, url), never a body"
            )
        row = {}
        for k in ("sender", "subject", "date", "line"):
            v = raw.get(k, "") or ""
            if not isinstance(v, str):
                raise MapError(f"thread {i}: {k} must be a string")
            row[k] = v[:MAX_LINE_CHARS] if k == "line" else v[:300]
        c = raw.get("count", 1)
        row["count"] = max(0, int(c)) if isinstance(c, (int, float)) else 1
        if raw.get("slice") is not None:
            row["slice"] = str(raw["slice"])[:200]
        if raw.get("url"):
            url = str(raw["url"])
            if not url.startswith(("http://", "https://")):
                raise MapError(f"thread {i}: url must start with http")
            row["url"] = url
        out.append(row)
    return out


def select_threads(threads: list[dict], slices: list[dict]) -> list[dict]:
    """The representative subset GI gets: up to THREADS_PER_SLICE per slice, in the
    order given (the session lists newest first), then unassigned rows, capped at
    MAX_THREADS."""
    by_slice: dict[str, list[dict]] = {}
    loose: list[dict] = []
    for t in threads:
        s = t.get("slice")
        if s:
            by_slice.setdefault(s, []).append(t)
        else:
            loose.append(t)
    picked: list[dict] = []
    for sl in slices:
        picked.extend(by_slice.pop(sl["slice"], [])[:THREADS_PER_SLICE])
    for rest in by_slice.values():
        picked.extend(rest[:THREADS_PER_SLICE])
    picked.extend(loose)
    return picked[:MAX_THREADS]


def read_measurables(path: str | None) -> list[str]:
    seen, out = set(), []
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                t = line.strip()
                if not t or t.lower() == "none" or t in seen:
                    continue
                seen.add(t)
                out.append(t)
    out.append("none")
    return out


# ---------------------------------------------------------------------------
# xlsx writer (stdlib zipfile). One visible sheet, Slices; a hidden Lists sheet
# holds the dropdown sources (an inline list is capped at 255 characters and a
# measurable can be longer).
# ---------------------------------------------------------------------------

def _col(n: int) -> str:
    s = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def _c(ref: str, value, style: int = 0) -> str:
    if value is None or value == "":
        return f'<c r="{ref}" s="{style}"/>'
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f'<c r="{ref}" s="{style}"><v>{value}</v></c>'
    txt = escape(str(value))
    return f'<c r="{ref}" s="{style}" t="inlineStr"><is><t xml:space="preserve">{txt}</t></is></c>'


STYLES_XML = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
    '<fonts count="3">'
    '<font><sz val="10"/><name val="Calibri"/></font>'
    '<font><b/><sz val="10"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font>'
    '<font><u/><sz val="10"/><color rgb="FF0563C1"/><name val="Calibri"/></font>'
    "</fonts>"
    '<fills count="3">'
    '<fill><patternFill patternType="none"/></fill>'
    '<fill><patternFill patternType="gray125"/></fill>'
    '<fill><patternFill patternType="solid"><fgColor rgb="FFA6192E"/><bgColor indexed="64"/></patternFill></fill>'
    "</fills>"
    '<borders count="2">'
    "<border><left/><right/><top/><bottom/><diagonal/></border>"
    '<border><left/><right/><top/><bottom style="thin"><color rgb="FFD8D8D8"/></bottom><diagonal/></border>'
    "</borders>"
    '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
    '<cellXfs count="5">'
    '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
    '<xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf>'
    '<xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>'
    '<xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1" applyAlignment="1"><alignment vertical="top"/></xf>'
    '<xf numFmtId="0" fontId="2" fillId="0" borderId="1" xfId="0" applyFont="1" applyBorder="1" applyAlignment="1"><alignment vertical="top"/></xf>'
    "</cellXfs>"
    '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
    "</styleSheet>"
)


def build_xlsx(slices: list[dict], measurables: list[str], out_path: str) -> str:
    ncols = len(SLICE_COLUMNS)
    last_row = max(len(slices) + 1, 200)
    hyperlinks: list[tuple[str, str]] = []  # (cell ref, url)

    rows_xml = []
    header_cells = "".join(_c(f"{_col(i + 1)}1", h, 1) for i, h in enumerate(SLICE_COLUMNS))
    rows_xml.append(f'<row r="1" ht="42" customHeight="1">{header_cells}</row>')
    for r_off, s in enumerate(slices):
        r = r_off + 2
        vals = [s["n"], s["slice"], s["looks_like"], s["count"], s["reply_or_feed"], s["fits"], s["needs"], s["does"]]
        cells = []
        for c, v in enumerate(vals, 1):
            cells.append(_c(f"{_col(c)}{r}", v, 2 if c in WRAP_COLS else 3))
        for e in range(3):
            c = 9 + e
            ref = f"{_col(c)}{r}"
            ex = s["examples"][e] if e < len(s["examples"]) else None
            if ex and ex["url"]:
                hyperlinks.append((ref, ex["url"]))
                cells.append(_c(ref, ex["label"], 4))
            else:
                cells.append(_c(ref, ex["label"] if ex else None, 3))
        for c in range(12, ncols + 1):
            cells.append(_c(f"{_col(c)}{r}", None, 2 if c in WRAP_COLS else 3))
        rows_xml.append(f'<row r="{r}">{"".join(cells)}</row>')

    cols_xml = "".join(
        f'<col min="{i + 1}" max="{i + 1}" width="{w}" customWidth="1"/>' for i, w in enumerate(WIDTHS)
    )
    lists = [REAL_CATEGORY_OPTIONS, measurables, PRIORITY_OPTIONS, STAGES]
    dv = []
    for col, list_col in ((12, 1), (13, 2), (14, 3), (16, 4)):
        lc = _col(list_col)
        n = len(lists[list_col - 1])
        dv.append(
            f'<dataValidation type="list" allowBlank="1" showErrorMessage="0" sqref="{_col(col)}2:{_col(col)}{last_row}">'
            f"<formula1>Lists!${lc}$1:${lc}${n}</formula1></dataValidation>"
        )
    hl_xml = ""
    rels_xml = ""
    if hyperlinks:
        hl_xml = "<hyperlinks>" + "".join(
            f'<hyperlink ref="{ref}" r:id="rId{i + 1}"/>' for i, (ref, _) in enumerate(hyperlinks)
        ) + "</hyperlinks>"
        rels_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + "".join(
                f'<Relationship Id="rId{i + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" Target="{escape(url, {chr(34): "&quot;"})}" TargetMode="External"/>'
                for i, (_, url) in enumerate(hyperlinks)
            )
            + "</Relationships>"
        )

    sheet1 = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<dimension ref="A1:{_col(ncols)}{len(slices) + 1}"/>'
        '<sheetViews><sheetView workbookViewId="0" tabSelected="1">'
        '<pane xSplit="2" ySplit="1" topLeftCell="C2" activePane="bottomRight" state="frozen"/>'
        "</sheetView></sheetViews>"
        '<sheetFormatPr defaultRowHeight="15"/>'
        f"<cols>{cols_xml}</cols>"
        f"<sheetData>{''.join(rows_xml)}</sheetData>"
        f'<autoFilter ref="A1:{_col(ncols)}{max(len(slices) + 1, 2)}"/>'
        f'<dataValidations count="{len(dv)}">{"".join(dv)}</dataValidations>'
        f"{hl_xml}"
        '<pageMargins left="0.5" right="0.5" top="0.5" bottom="0.5" header="0.3" footer="0.3"/>'
        "</worksheet>"
    )
    list_rows = []
    height = max(len(x) for x in lists)
    for r in range(1, height + 1):
        cells = []
        for c, lst in enumerate(lists, 1):
            if r <= len(lst):
                cells.append(_c(f"{_col(c)}{r}", lst[r - 1]))
        list_rows.append(f'<row r="{r}">{"".join(cells)}</row>')
    sheet2 = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<dimension ref="A1:D{height}"/>'
        f"<sheetData>{''.join(list_rows)}</sheetData>"
        "</worksheet>"
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        "<sheets>"
        '<sheet name="Slices" sheetId="1" r:id="rId1"/>'
        '<sheet name="Lists" sheetId="2" state="hidden" r:id="rId2"/>'
        "</sheets></workbook>"
    )
    workbook_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>'
        '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
        "</Relationships>"
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        "</Relationships>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        "</Types>"
    )
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    # Overwrite in place: the sandbox cannot delete files, so a fixed name that
    # is rewritten each run is the rule (cowork-runtime-constraints Fact 16).
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", root_rels)
        z.writestr("xl/workbook.xml", workbook)
        z.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        z.writestr("xl/styles.xml", STYLES_XML)
        z.writestr("xl/worksheets/sheet1.xml", sheet1)
        z.writestr("xl/worksheets/sheet2.xml", sheet2)
        if rels_xml:
            z.writestr("xl/worksheets/_rels/sheet1.xml.rels", rels_xml)
    return out_path


# ---------------------------------------------------------------------------
# The submit call
# ---------------------------------------------------------------------------

def submit_call(slices: list[dict], threads: list[dict], note: str | None = None) -> dict:
    args = {"slices": slices, "threads": threads}
    if note:
        args["note"] = note
    return {"tool": "submit_inbox_map", "connector": "lee-raleigh", "args": args}


def _out_name(date: str | None = None) -> str:
    d = date or _dt.date.today().isoformat()
    return f"inbox-map-{d}.xlsx"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="map.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("lint")
    p.add_argument("slices")
    p = sub.add_parser("build")
    p.add_argument("slices")
    p.add_argument("threads")
    p.add_argument("--out", default=".")
    p.add_argument("--measurables", default=None, help="text file, one measurable per line (from get_my_context kind=measurables)")
    p.add_argument("--note", default=None)
    p.add_argument("--date", default=None)
    p = sub.add_parser("call")
    p.add_argument("slices")
    p.add_argument("threads")
    p.add_argument("--note", default=None)
    a = ap.parse_args(argv)

    try:
        if a.cmd == "lint":
            rows = validate_slices(_load(a.slices))
            probs = lint_slices(rows)
            if probs:
                print("VOICE LINT FAILED. Rewrite these cells the way the leader would say it, then run again:")
                for pr in probs:
                    print("  - " + pr)
                return 1
            print(f"voice lint OK: {len(rows)} slices")
            return 0
        slices = validate_slices(_load(a.slices))
        probs = lint_slices(slices)
        if probs:
            print("VOICE LINT FAILED. Rewrite these cells the way the leader would say it, then run again:")
            for pr in probs:
                print("  - " + pr)
            return 1
        threads = select_threads(validate_threads(_load(a.threads)), slices)
        if a.cmd == "build":
            out = os.path.join(a.out, _out_name(a.date))
            build_xlsx(slices, read_measurables(a.measurables), out)
            print(f"WROTE {os.path.abspath(out)}  ({len(slices)} slices, {len(threads)} thread summaries selected for GI)")
        print("Now make exactly this call on the lee-raleigh connector (copy the args as they are):")
        print(json.dumps(submit_call(slices, threads, a.note), indent=1, ensure_ascii=False))
        return 0
    except MapError as e:
        print(f"INVALID: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
