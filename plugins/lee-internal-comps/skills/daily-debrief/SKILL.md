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

## Flow

### Step 1 — Pull yesterday's plugin sessions

Call `lee_debrief_fetch_yesterday`. You'll get back a list of sessions Will ran through the plugin yesterday. Each has a `sessionId` and one or more `toolCalls`.

If zero sessions came back, skip directly to Step 3.

### Step 2 — Walk through each plugin session, one at a time

For each session, summarize what happened and ask Will to classify it:

> "Yesterday at {timestamp of first tool call} you ran `{first tool name}`{add ', followed by N more tool calls' if toolCalls.length > 1}. {If query_text is available, summarize: e.g., 'querying sale_comps_safe' or 'rendering a comp set PDF'.} How did the broker end up getting what they needed?
>
> - `plugin_only` — broker got the answer entirely from the plugin output
> - `plugin_with_manual_fix` — plugin gave you a starting point but you had to fix or supplement something by hand
> - `manual_only` — you abandoned the plugin output and finished it manually
> - `unable` — broker did not get a usable answer
>
> Also: how did the broker ask? `inbox` / `text` / `slack` / `in_person` / `unknown`
>
> Anything else worth capturing? (free text, can skip)"

After each session, call `lee_debrief_write` with the captured fields. Use the real `sessionId` from `fetch_yesterday`.

### Step 3 — Cover off-plugin asks (this is the most important step)

Ask Will:

> "Now the part that matters most: what did brokers ask you for yesterday that did NOT come through the plugin? Walk me through each one — I'll ask about them one at a time. How many off-plugin asks were there?"

If zero, skip to Step 4.

Otherwise, for **each** off-plugin ask, conduct a one-by-one interview:

> "Off-plugin ask #{N} of {total}:
>
> 1. What did the broker actually want? (Be specific — 'Sandy wanted an owner mailing for 123 Main St' is better than 'a mailing'.)
> 2. How did the broker ask? `inbox` / `text` / `slack` / `in_person` / `unknown`
> 3. Were you able to complete it? `manual_only` (yes, manually) or `unable` (no)
> 4. Why didn't this go through the plugin? Pick one:
>    - `plugin_broke` — you tried the plugin and it didn't work for this request (call out the specific failure)
>    - `known_gap` — you didn't try because the feature isn't built yet but we've already talked about it (it's on the roadmap)
>    - `new_opportunity` — you didn't try because the feature isn't on our radar — this is something we should consider building
> 5. If `plugin_broke` or `new_opportunity`, what would have made the plugin handle this?"

For each off-plugin ask, generate a fresh session_id prefixed `manual-` (e.g., `manual-<uuid>`) and call `lee_debrief_write` with:

- `completion_status`: `manual_only` or `unable` (from question 3)
- `broker_request_source`: from question 2
- `notes`: combine answers 1, 4, 5 into a structured free-text block, prefixed with the category. Format:

```
[CATEGORY: plugin_broke|known_gap|new_opportunity]
Request: <what the broker wanted>
Why off-plugin: <answer to question 4>
What would have helped: <answer to question 5, or "n/a">
```

(The category prefix is a forward-compatibility hack until the `off_plugin_reason` enum column ships in a future migration. For now we encode it in notes so the Friday rollup can grep it.)

### Step 4 — Confirm and close

Summarize back to Will:

> "Logged {N} plugin sessions and {M} off-plugin asks.
> Off-plugin breakdown: {plugin_broke count} plugin bugs, {known_gap count} known gaps, {new_opportunity count} new opportunities.
> Total broker requests yesterday: {N + M}.
> Want to revise any of these? Re-running this skill UPSERTs by session_id so corrections are easy."

## Required tools

- `lee_debrief_fetch_yesterday` (read)
- `lee_debrief_write` (write — gated by the LEE_DEBRIEF_WRITERS allowlist on lee-raleigh-mcp)

## Notes

- The `sessionId` Will sees for plugin sessions comes from `audit_log.session_id`; legacy rows without one show up as `legacy-<id>`. Treat each legacy row as its own session.
- Off-plugin asks always get a synthetic `manual-<uuid>` session_id so they're distinguishable from plugin sessions in the rollup.
- If `lee_debrief_write` returns `forbidden`, the calling email is not on the LEE_DEBRIEF_WRITERS allowlist — escalate to David.
- The Friday rollup at 12:00 UTC (8am ET winter / 7am ET summer) reads everything written through this skill plus the upload page's coverage_log, and posts to the Lee plugin feed channel.
- Total broker requests yesterday = plugin sessions + off-plugin asks. Do not collapse the two.
