# Canonical connector-auth guidance (gi-plugins#117, #135)

This file is the single source of truth for the connector-auth section embedded in
every lee-internal-comps SKILL.md that calls the lee-raleigh connector. **Edit the
block below (between the BEGIN/END markers), then run `scripts/sync-connector-auth.sh`
to propagate it** — never hand-edit the copy inside an individual SKILL.md.
`scripts/test/connector-auth-guidance.test.sh` fails the build on any drift.

Why this exists (three incidents, one fix surface — full detail on gi-plugins#117 and #135):

- **False refusal (2026-07-15):** an agent *reasoned about* auth state instead of
  *testing* it and twice told the user the connector "needs to be authorized via
  /mcp" — then the actual call worked first try. The connector was authorized the
  whole time.
- **Genuine grant drop (2026-07-08):** a broker's OAuth grant silently dropped
  (reinstall/new machine), and the improvised fallback copy ("authorize via /mcp or
  the connector settings") was too developer-y to self-serve, so the broker escalated
  instead of reconnecting.
- **False client-side auth error (2026-07-23):** the Claude app displayed two tool
  calls as auth-failed while the Worker's audit log shows both calls authorized and
  served (rows 2533/2534, 50 rows each) — so the model attempted first, was lied to
  about the result, and walked the user through a pointless sign-in. A fresh-turn
  retry on the same token succeeded immediately. Observed signature of the false
  case: tools loaded + call "fails", heals on the next turn. A genuine disconnect
  instead presents as the lee-raleigh tools missing from the session entirely.
  Hence the retry-first ladder in rules 3–4 below.

The reconnect steps must stay in sync with the real flow (`mcp-server/src/auth/oauth.ts`
and the /setup guide's `connect-sign-in` section) — in particular the "expired link →
just request another" behavior, which is deliberate (mail-scanner pre-fetch).

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
   > tools) — the connection is usually fine. Tell me **"you do have access — try
   > again"** and I'll re-run it. If it still fails on the retry, a quick sign-in
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
