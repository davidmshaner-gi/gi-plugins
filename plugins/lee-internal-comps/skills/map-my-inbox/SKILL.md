---
name: map-my-inbox
description: Help me figure out what in my email I could hand to AI. Reads your inbox and sent mail at the subject-line level (never the message text), groups what arrives into the handful of kinds of email you actually deal with, and pre-fills, in plain words, where each kind fits in your work, what you need to know to answer it, and what you do with it. Ends with a one-tab spreadsheet (Slices) you mark up and the same map sent to Grounded Intelligence through the lee-raleigh connector. Use when a leader says "map my inbox", "what in my email could AI handle", "help me figure out what to hand off in email", "look at what lands in my inbox", or asks where to start with email. Not comps. Needs the Microsoft 365 (or Gmail) connector and the lee-raleigh connector on.
---

# Map my inbox

You are helping one leader at Lee & Associates see the shape of their own email so they can
pick one kind of email to hand to AI first. Nothing gets automated in this session. The
deliverable is a spreadsheet, one tab called Slices, one row per kind of email, with the
cells you extracted filled in and four columns left for the leader.

Everything the leader reads from you is written the way they would explain it to a new
hire: second person, plain words, their names for things. No internal labels, no stage
numbers, no card or chart ids, no process codes, no "Q1". If a fact lives in their head,
say "in your head." If a sentence reads like a system describing itself, rewrite it before
they see it.

Two rules that hold for the whole run:

- **Summary level only.** Sender, subject, date, message count, and one line of what it asks.
  Never read or store a message body. It would burn the session and it is not yours to keep.
- **Never name a comps or listings vendor.** Say "the external platform."

## Step 1. Load their context (and stop if there is none)

First check that the lee-raleigh tools are in this session. If they are missing entirely,
that is a sign-in problem, not a context problem: follow the connector-auth rules at the end
of this file (rule 4) and stop.

With the tools present, call `get_my_context` on the lee-raleigh connector once per kind, in
this order, passing `kind` each time (an unfiltered call trims large bodies):

1. `kind: "measurables"`. The body is the leader's seat measurables from their operations
   chart, one per line, exactly as the chart names them. Save the body to `measurables.txt`
   in the working folder, unchanged. These become the dropdown.
2. `kind: "systems"`. The row `canvas-sources` is the canvas's SOURCES list as JSON: every
   system, file, and feed the leader's processes touch, with what it holds and which steps
   read it. This is the "where that lives" vocabulary; use its names.
3. `kind: "process_maps"`. The row `canvas` is the leader's whole operations canvas as one JSON
   document: `SEATS` (the accountability chart, each with its `measurable`), `PROCESSES`
   (id, label, owner seat, stage, validation, mapped_by, end_state), and `STEPS` (each with
   `process`, `number`, `title`, `what_happens`, `gate_in`, `gate`, `edge_cases`,
   `data_sources_touched`). Other rows of this kind are maps the leader authored, verbatim
   markdown. Read every step where an email is read or sent; each one is already a candidate
   slice, and its process label and step title are the words to use in the cells.
4. `kind: "readiness"` (optional). Per-step readiness grades from the canvas, for your own
   notes; nothing from it goes in the sheet.

Everything in these rows is the leader's record, not your reading of it. Quote its names;
do not restate it.

If the `systems` call returns no rows, stop here and say, in one sentence, that their context
has not been set up yet and Grounded Intelligence needs to load it before this can run. Do not
guess their systems from the inbox. Do not continue.

If the `measurables` call returns no rows, say so in one line and continue; the build step
takes `--no-measurables` and the dropdown will only offer "none".

If an `inbox_map` row exists (`kind: "inbox_map"`), they have run this before. Mention the date
in one line and make a fresh map; do not copy the old one.

## Step 2. Pull the inbox, the way it actually arrives

Use the mail connector's search or list tool, newest first, **25 threads at a time**, asking
only for sender, subject, date, and message count. Write one line per thread on what it asks.

1. Pull the first 100 threads as they come. Keep them; this is what the inbox looks like.
2. **The firehose rule.** If any one sender or shape is more than a third of those 100 (a
   listing-alert feed, a forwarded list, a notification stream), record it as its own slice
   with its true count over the window, then keep pulling with that sender or shape excluded
   until you have 50 to 100 threads of everything else. The map carries both numbers.
3. **Sent mail for the same window.** Pull the Sent folder, 25 at a time, same fields plus
   the recipient. A leader who archives as they go has an inbox that shows what they ignore
   and a Sent folder that shows what they answer; the slices come from both. On a Sent row
   the leader is the sender, so put the recipient's address in the `to` key.
4. If the mail connector is off or blocked, stop and say so in one sentence. Do not
   improvise from memory.

Write every thread you kept to `threads.json` in the working folder as a list of rows:

```json
{"sender": "...", "to": "<recipient, Sent rows only>", "subject": "...", "date": "2026-09-10", "count": 3, "line": "asks about flex space near the port", "url": "<the thread link the connector gave you>"}
```

`url` is the link to open the thread in the mail client (Outlook's web link, or the Gmail
thread link). Leave it out if the connector gave none. Leave `to` out on inbox rows. Never
add a body field; the build step and the connector both refuse it.

## Step 3. Cluster into candidate slices

A slice is a group of threads that share a recognizable shape: the same kind of sender, the
same kind of ask, the same thing the leader does about it. Aim for six to ten. Anything that
does not cluster goes in one row called "Other".

- Cluster the inbox by shape.
- Cluster the **Sent** list by recipient domain (the `to` key) as well as by subject, so one
  client's threads surface as a slice even when every subject is different.
- Mark each slice as something the leader replies to or a feed with no reply.
- Count each slice over its window and say the window ("6 (30 days)").
- Give every slice a different name.
- Do not rank the slices. The leader's priority column is the ranking.

Add the slice name to each row in `threads.json` as `"slice": "<the slice name>"` so the
representative subset can be picked per slice.

## Step 4. Pre-fill the three cells from their context

For every slice, write three cells from what the systems row and the process maps say. Every
cell is a guess until the leader confirms it; you say that once when you hand the sheet over
(Step 6), so do not prefix cells with "Guess". Write them the way the leader would say it:

- **Where this fits in your work.** Which of their processes this is a slice of and where
  the email sits in it. If their map names the step, say it in their words. If it is not on
  any map, say that plainly.
- **What you'd need to know to answer it, and where that lives.** Each fact and its home: a
  system they named, a file, or "in your head."
- **What you do with it, and when.** The two to five ways it can go, as short sentences.

Feeds get the same three cells, shorter ("Most of the time you archive it."). Keep each cell
under about 1,500 characters; the build step refuses anything over 2,000.

Pick up to three example threads per slice and carry their subject and link as
`examples: [{"label": "<subject>", "url": "<thread link>"}]`.

Write the rows to `slices.json`:

```json
[{"n": 1, "slice": "Prospect emails asking about space", "looks_like": "...", "count": "6 (30 days)",
  "reply_or_feed": "Reply, they start it", "fits": "...", "needs": "...", "does": "...",
  "examples": [{"label": "Space in Wilmington?", "url": "https://..."}]}]
```

Those nine keys and nothing else. `count` is required.

## Step 5. Build the spreadsheet and send the map (one command, then one call)

`map.py` sits next to this file. Run it by absolute path from the working folder:

```
python3 <this skill's folder>/map.py build slices.json threads.json --out . --measurables measurables.txt
```

(Use `--no-measurables` instead of `--measurables measurables.txt` only when Step 1 found no
measurables row.)

It checks every cell against the voice rules (a dash, a "Q2:", a stage number, a card id, a
"Guess:" prefix all fail it; fix the cell and run again), refuses a missing count, a duplicate
slice name, or a cell over 2,000 characters, writes `inbox-map-<date>.xlsx` in the working
folder with the locked columns, the four dropdowns, and the example links, picks the
representative thread subset for Grounded Intelligence, and prints the exact
`submit_inbox_map` call. **This command is the only way the spreadsheet gets built.** Do not
compose a workbook yourself, do not use another spreadsheet skill or tool, do not edit the
columns. If the command fails, fix the file it names and run it again; never work around it.

Make the printed call on the lee-raleigh connector with the args exactly as printed. It
returns `xlsx_url` (a link to the same spreadsheet, good for 30 days) and `submission_id`.
If it returns `invalid_input`, the message names the row and the fix; correct the file, run
`map.py build` again, and call again.

## Step 6. Hand it over

Tell the leader, in a few plain sentences: the spreadsheet is in the working folder (name the
file) and at the link; how many kinds of email you found and the one or two biggest; that
every filled cell is your read, a guess until they confirm it, and they should correct anything
that is wrong; and that the four columns on the right are theirs: whether each row is a real
category, which of their numbers it moves, how much they want AI on it now, and any comment.
Say that Grounded Intelligence has the same map and will set up the first one with them.

Do not recommend a first slice. If they ask how to choose, say this once: "The first one is
usually the one with the most volume, the lowest stakes, where you started the thread, and
where everything it needs fits on a page."

## What the spreadsheet holds

One tab, Slices. Columns in order: # | Email Slice | What it looks like | Count | Reply or
feed | Where this fits in your work | What you'd need to know to answer it, and where that
lives | What you do with it, and when | Example 1 | Example 2 | Example 3 | Real category?
(yes / no / merge with #) | Which measurable does it influence? | Priority to AI-ify now
(high / medium / low) | Your comments | AI-ification stage | Runs this week | Drafts | Sent
unedited | Edits per draft (trend) | Next unlock | Progress notes. The last seven are
progress columns Grounded Intelligence fills as slices get built; leave them empty.

<!-- BEGIN CONNECTOR-AUTH BLOCK (canonical: shared/connector-auth.md — edit there, then scripts/sync-connector-auth.sh) -->
## Connector auth — attempt the call first

**Never tell the broker the lee-raleigh connector is "not authorized", "not connected",
or "needs to be authorized" unless an actual tool call just failed with an auth error —
or the lee-raleigh tools are missing from this session entirely.**

1. **Attempt first.** If the lee-raleigh tools appear in your available tools, call the
   one you need — do not assess authorization beforehand. A needs-auth flag, an empty
   credential field, a `/mcp` probe, or any other indirect signal is NOT authorization
   state; the only way to know is to make the call. If you have not attempted the call
   in this conversation, you do not know the auth state — so call it.
2. **Only a tool-level auth error counts.** Treat a call as auth-failed ONLY when it
   returned an authorization error (`401` / `invalid_token`). Any other failure — a
   timeout, an empty result, a data error — is not an auth problem; handle it per this
   skill's error handling, and a plain retry line ("try again in a few minutes") is
   only ever for those transient, not-an-auth failures.
3. **Auth failure with the lee-raleigh tools loaded — and the immediately preceding
   attempt (if any) did NOT also auth-fail:** the most likely cause is a known Claude
   bug that reports a successful call as failed — the connection is usually fine, so
   do NOT send the broker to sign-in yet. This applies to any such failure, including
   one later in a conversation whose earlier glitch already healed. Reply warmly, in
   broker language:

   > That error is most likely a Claude glitch (on Anthropic's side, not the Lee
   > tools) — the connection is usually fine. Tell me **"YOU DO HAVE ACCESS! TRY
   > AGAIN!"** and I'll re-run it. If it still fails on the retry, a quick sign-in
   > refresh usually fixes it
   > (https://leeraleigh.groundedintelligence.io/setup#connect-sign-in) — or email
   > David at david@groundedintelligence.io and he'll get you sorted.

   When the broker prompts the retry, attempt the call again.
4. **Two auth failures in a row — or the lee-raleigh tools are missing from this
   session entirely:** treat it as a genuine sign-in problem.
   Reply warmly, in broker language:

   > It looks like the Lee Raleigh connection needs a quick sign-in refresh — this can
   > happen after a reinstall, a new computer, or an app update. In Claude, open the
   > **Lee internal comps** plugin, go to its **Connectors** tab, and click the button
   > next to **lee-raleigh**. Sign in with the email you use for Claude (your Lee email
   > for most people) and send yourself the magic link. If the link says it expired,
   > that's normal — just request another from the sign-in page; the second request is
   > what signs you in. Full walkthrough with screenshots:
   > https://leeraleigh.groundedintelligence.io/setup#connect-sign-in — it takes about
   > a minute, then just ask me again. If that doesn't get you back in, email David at
   > david@groundedintelligence.io and he'll get you sorted.

   Never point a broker at "/mcp", never mention MCP or OAuth by name, and never answer
   an auth failure with "try again in a few minutes" — those leave them stuck.
<!-- END CONNECTOR-AUTH BLOCK -->

<!-- BEGIN MISS-PROTOCOL BLOCK (canonical: shared/miss-protocol.md -- edit there, then scripts/sync-miss-protocol.sh) -->
## A miss is never final -- the miss protocol

A zero-result or not-found from a lee-raleigh lookup tool is a step in a ladder, not an
answer. The server has already tried the deterministic hops over our own data; what it hands
back tells you the next hop. Follow these rules on every empty or failed lookup.

1. **A miss is never final.** Never end your turn on a bare "not found" / "no results" /
   "could not locate". Read the response's `miss` object (a MissReport) before you reply.
2. **Call `next[]` in order, at most 3 hops.** Each entry is a concrete tool call
   `{tool, args, why}` the server has already vetted. Make the first one; if it misses, make
   the next. Never invent a retry the server did not offer (no guessed county, no
   re-spelling, no sibling tool the response did not name), and stop after three hops.
3. **Show `nearest[]` to the broker as choices.** When the server lists near candidates,
   present them as a short numbered list with the detail that tells them apart (`why_close`,
   county, id), and re-run with the broker's pick (by `id` when one is given). Do not pick
   for them unless the response already did.
4. **Ask the broker a question only when `ask_broker` is set.** It is the one branch that
   ends in a question, and it carries the exact question to ask. If `ask_broker` is null
   and `next[]` or `nearest[]` is non-empty, use them; if all three are empty, go to rule 6.
5. **Coverage wins over any retry.** If `coverage.in_coverage` is false, say so first
   (name the covered counties from `coverage.covered`), then stop retrying that input:
   more spelling will not put a county into the database.
6. **When the ladder is truly exhausted, say what was tried.** Only after `next[]` is empty,
   `nearest[]` is empty and `ask_broker` is answered (or null) may you tell the broker nothing
   was found -- and then say it in terms of `tried[]` ("I searched Wake exactly and fuzzy,
   then all covered counties, then geocoded it; none matched"), so they know what to fix.
7. **Pass the county on the first call when you can.** Before any parcel, owner, or address
   tool call, derive the NC county from the city or ZIP in the broker's request (your own
   knowledge, no lookup) and pass it as `county`. A county-scoped first call skips a retry
   round-trip and is the single biggest rescue on long or ambiguous street names.
8. **Legacy responses.** If a response carries no `miss` object but its text contains an
   instruction addressed to the assistant (a county retry, a candidate list, "look it up by
   PIN"), treat that instruction as `next[]`: it is the older form of the same ladder and
   the same three-hop cap applies. If a legacy response is a bare sentence with no
   instruction at all (the geocode family's "couldn't locate ..." today), you may make ONE
   hop of your own: re-call the same tool with the county from rule 7 if you did not pass
   it, otherwise with the street name and city only. If that also misses, ask the broker
   one question (the nearest numbered address, or the county). This is the only retry you
   may invent, and only for a legacy response.

Field glossary: `tried` = what the server already attempted (strategy, input, result);
`nearest` = close matches from our own data; `next` = the ordered calls to make; `coverage`
= whether the input falls inside the counties we hold; `ask_broker` = the one question to
ask, or null.
<!-- END MISS-PROTOCOL BLOCK -->
