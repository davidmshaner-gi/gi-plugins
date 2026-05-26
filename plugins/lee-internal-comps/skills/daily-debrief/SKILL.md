---
name: lee-daily-debrief
description: Walks Will through yesterday's MCP tool calls interview-style and records his classification of each (plugin_only / plugin_with_manual_fix / manual_only / unable) plus the broker request source. Writes results back to lee-raleigh-mcp for the Friday rollup. Run daily.
---

# /lee-daily-debrief

Interview-style daily review of yesterday's plugin sessions. The skill fetches yesterday's audit_log rows via `lee_debrief_fetch_yesterday`, walks Will through each session, and writes his answers via `lee_debrief_write`.

## When to run

Daily, ideally first thing in the morning. Idempotent — re-running replaces previous answers (UPSERT on session_id).

## Flow

1. Generate a fresh UUID for this debrief session.
2. Call `lee_debrief_fetch_yesterday`. Receive a list of sessions, each with `sessionId` and `toolCalls`.
3. For each session, prompt Will:
   - "Yesterday at {first toolCall createdAt} you ran `{first tool}`{; followed by `{n}` more tool calls in this session if toolCalls.length > 1}. {Summarize query_text or row_count for context.} How did the broker end up getting what they needed? Pick one:
     - `plugin_only` — finished entirely with the plugin
     - `plugin_with_manual_fix` — used the plugin, had to fix something by hand
     - `manual_only` — abandoned the plugin and did it manually
     - `unable` — could not complete"
   - "How did the broker ask? `inbox` / `text` / `slack` / `in_person` / `unknown`"
   - "Anything else worth noting? (free text, can skip)"
4. After each session is answered, call `lee_debrief_write` with the captured fields.
5. After all sessions are covered, ask: "Anything brokers asked you for yesterday that did NOT touch the plugin? If so, log them as `manual_only` or `unable`." For each, generate a fresh UUID prefixed `manual-` and call `lee_debrief_write` with the user-provided source + notes.
6. Confirm completion: "Debrief logged: {N} plugin sessions, {M} off-plugin asks."

## Required tools

- `lee_debrief_fetch_yesterday` (read)
- `lee_debrief_write` (write — gated by the LEE_DEBRIEF_WRITERS allowlist on lee-raleigh-mcp)

## Notes

- The session_id Will sees comes from `audit_log.session_id`; legacy rows without one show up as `legacy-<id>`. Treat each legacy row as its own session.
- If `lee_debrief_write` returns `forbidden`, the calling email is not on the LEE_DEBRIEF_WRITERS allowlist — escalate to David.
- The Friday rollup at 12:00 UTC (8am ET winter / 7am ET summer) reads everything written through this skill plus the upload page's coverage_log, and posts to #all-groundedintelligence.
