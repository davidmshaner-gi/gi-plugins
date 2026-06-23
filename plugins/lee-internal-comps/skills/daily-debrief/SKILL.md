---
name: lee-daily-debrief
description: Walks Will through yesterday's broker requests one-by-one — both plugin sessions AND off-plugin asks. For each, captures completion outcome, broker request source, and (for off-plugin asks) why the plugin wasn't used (plugin_broke / known_gap / new_opportunity). Writes back to lee-raleigh-mcp; feeds the Friday rollup. Run daily.
---

# /lee-daily-debrief

Interview-style daily review of yesterday's broker requests. The goal is to end up with a complete picture of (a) what brokers asked Will for yesterday, (b) which requests went through the plugin, (c) which didn't and why, and (d) what new patterns suggest plugin work to do next.

## Why this matters

Will is Lee's analyst. He's the funnel for broker requests. Some land in the plugin; some he handles manually. A debrief that only counts plugin sessions misses the entire off-plugin pipeline — which is where the roadmap signal lives. Every off-plugin ask is one of three things:

- **plugin_broke** — Will tried the plugin and it didn't work (bug to fix).
- **known_gap** — Will didn't try the plugin because we both know the feature isn't built yet (already on the roadmap somewhere).
- **new_opportunity** — Will didn't try the plugin because the feature isn't on anyone's radar yet (net new ask, worth adding to the roadmap).

These three categories drive different next steps. The debrief is how that signal reaches David and Bonner.

## When to run

Daily, first thing in the morning, covering yesterday's activity. Idempotent — re-running replaces previous answers for the same session (UPSERT on session_id).

## How to run this interview (read this before Step 1)

This skill is for Will, who is busy and not technical. The whole reason it exists is to get a clean daily signal **without making him do work** — so the interview has to be effortless and impossible to lose. Follow these rules on every run:

- **One question per turn. Never batch.** Ask a single thing, wait for Will's reply, then ask the next. Do not present numbered lists of questions or multi-part prompts — that is exactly what caused him to lose his place and abandon the skill before.
- **Make answers one word where possible.** Offer the keyword options and ask him to "just reply with the word" (e.g. `plugin_only`). Short answers can't be mangled by a stray chat edit.
- **Save as you go, and say so.** After each session or ask is captured, write it immediately and confirm out loud ("Saved ✅ — next:"). Will should always know his progress is banked.
- **It is always safe to stop or restart.** If Will gets confused, interrupted, or thinks he answered wrong, tell him: *"No problem — just run `/lee-daily-debrief` again. Anything we already saved gets updated, never duplicated, so you can't break it."* Re-running is the recovery path; never ask him to re-paste or reconstruct lost text.
- **You drive, he reacts.** Summarize what the data already shows and ask him to confirm or correct it. Don't make him compose from a blank page.

## Flow

### Step 0 — Open with a one-line orientation

Before fetching anything, set expectations in a single sentence so Will knows what he's in for:

> "Morning — quick daily debrief. I'll go one question at a time and save as we go, so it's fast and you can stop anytime. Ready?"

Then proceed to Step 1.

### Step 1 — Pull yesterday's plugin sessions

Call `lee_debrief_fetch_yesterday`. You'll get back a list of sessions Will ran through the plugin yesterday. Each has a `sessionId` and one or more `toolCalls`.

Tell Will how many there are so the interview has a known length ("You ran {N} plugin sessions yesterday — let's tag each one, then I'll ask about anything that happened off the plugin.").

If zero sessions came back, say so and skip directly to Step 3.

### Step 2 — Walk through each plugin session, one question at a time

For each session, first summarize what happened in one line, then ask **one question, wait, then the next.** Do not stack them.

**2a — Outcome.** Ask:

> "Yesterday at {timestamp of first tool call} you ran `{first tool name}`{add ', plus N more steps' if toolCalls.length > 1}{if query_text is available, add a short plain-English summary, e.g. 'looking up sale comps' or 'rendering a comp set PDF'}. How did the broker end up getting what they needed? Just reply with one word:
>
> - `plugin_only` — got the answer entirely from the plugin
> - `plugin_with_manual_fix` — plugin got you started but you fixed/added something by hand
> - `manual_only` — you set the plugin output aside and finished it manually
> - `unable` — broker didn't get a usable answer"

Wait for his reply.

**2b — Source.** Then ask:

> "Got it. How did the broker ask you for this one? Reply with one word: `inbox` / `text` / `slack` / `in_person` / `unknown`."

Wait for his reply.

**2c — Optional note.** Then ask:

> "Anything else worth noting on this one? (Optional — just say `skip` if not.)"

**2d — Save and confirm.** Now call `lee_debrief_write` using the real `sessionId` from `fetch_yesterday`, with `completion_status` from 2a, `broker_request_source` from 2b, and `notes` set to his 2c answer (omit `notes` if he said `skip`). Then confirm and move on:

> "Saved ✅. {if more sessions: 'Next session —' / else: 'That's all your plugin sessions. Now the off-plugin part.'}"

### Step 3 — Cover off-plugin asks (this is the most important step)

Ask Will, as a single question:

> "Now the part that matters most: what did brokers ask you for yesterday that did NOT go through the plugin? How many were there? (A number is fine — `0` if none.)"

If zero, skip to Step 4. Otherwise walk them **one ask at a time, one question per turn** — never present the five questions below as a list. For off-plugin ask #{N} of {total}, ask them in sequence, waiting after each:

> **3a —** "Off-plugin ask #{N}: what did the broker actually want? (Be specific — 'Sandy wanted an owner mailing for 123 Main St' beats 'a mailing'.)"

> **3b —** "How did they ask? One word: `inbox` / `text` / `slack` / `in_person` / `unknown`."

> **3c —** "Were you able to get it done? Reply `manual_only` (yes, by hand) or `unable` (no)."

> **3d —** "Why didn't this go through the plugin? One word:
> - `plugin_broke` — you tried the plugin and it didn't work
> - `known_gap` — didn't try; we both know the feature isn't built yet
> - `new_opportunity` — didn't try; this isn't on our radar yet"

> **3e —** (only if `plugin_broke` or `new_opportunity`) "What would have made the plugin handle this? (One line.)"

After 3e (or 3d if skipped), generate a fresh session_id prefixed `manual-` (e.g., `manual-<uuid>`) and call `lee_debrief_write` with:

- `completion_status`: `manual_only` or `unable` (from 3c)
- `broker_request_source`: from 3b
- `notes`: combine 3a, 3d, 3e into a structured free-text block, prefixed with the category. Format:

```
[CATEGORY: plugin_broke|known_gap|new_opportunity]
Request: <answer to 3a — what the broker wanted>
Why off-plugin: <answer to 3d>
What would have helped: <answer to 3e, or "n/a">
```

(The category prefix is a forward-compatibility hack until the `off_plugin_reason` enum column ships in a future migration. For now we encode it in notes so the Friday rollup can grep it.)

Then **confirm and move on before the next ask** so Will sees progress banked each time:

> "Saved ✅. {if more off-plugin asks: 'Next one —' / else: 'That's everything.'}"

### Step 4 — Confirm and close

Summarize back to Will:

> "All done — nothing else needed from you. Logged {N} plugin sessions and {M} off-plugin asks.
> Off-plugin breakdown: {plugin_broke count} plugin bugs, {known_gap count} known gaps, {new_opportunity count} new opportunities.
> Total broker requests yesterday: {N + M}.
> If anything looks off, just run `/lee-daily-debrief` again — re-running updates by session, never duplicates, so corrections are easy and you can't break it."

## Required tools

- `lee_debrief_fetch_yesterday` (read)
- `lee_debrief_write` (write — gated by the LEE_DEBRIEF_WRITERS allowlist on lee-raleigh-mcp)

## Notes

- The `sessionId` Will sees for plugin sessions comes from `audit_log.session_id`; legacy rows without one show up as `legacy-<id>`. Treat each legacy row as its own session.
- Off-plugin asks always get a synthetic `manual-<uuid>` session_id so they're distinguishable from plugin sessions in the rollup.
- If `lee_debrief_write` returns `forbidden`, the calling email is not on the LEE_DEBRIEF_WRITERS allowlist — escalate to David.
- The Friday rollup at 12:00 UTC (8am ET winter / 7am ET summer) reads everything written through this skill plus the upload page's coverage_log, and posts to the Lee plugin feed channel.
- Total broker requests yesterday = plugin sessions + off-plugin asks. Do not collapse the two.
