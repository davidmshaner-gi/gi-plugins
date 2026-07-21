# Canonical connector-auth guidance (gi-plugins#117)

This file is the single source of truth for the connector-auth section embedded in
every lee-internal-comps SKILL.md that calls the lee-raleigh connector. **Edit the
block below (between the BEGIN/END markers), then run `scripts/sync-connector-auth.sh`
to propagate it** — never hand-edit the copy inside an individual SKILL.md.
`scripts/test/connector-auth-guidance.test.sh` fails the build on any drift.

Why this exists (two incidents, one fix surface):

- **False refusal (Bonner, 2026-07-15):** an agent *reasoned about* auth state instead
  of *testing* it, told the broker the connector "needs to be authorized via /mcp"
  twice — then the actual call worked first try. The connector was authorized the
  whole time.
- **Genuine grant drop (James Bailey, 2026-07-08):** a broker's OAuth grant silently
  dropped (reinstall/new machine), and the improvised fallback copy ("authorize via
  /mcp or the connector settings") was too developer-y to self-serve, so he escalated
  instead of reconnecting.

The reconnect steps must stay in sync with the real flow (`mcp-server/src/auth/oauth.ts`
and the /setup guide's `connect-sign-in` section) — in particular the "expired link →
just request another" behavior, which is deliberate (mail-scanner pre-fetch).

<!-- BEGIN CONNECTOR-AUTH BLOCK (canonical: shared/connector-auth.md — edit there, then scripts/sync-connector-auth.sh) -->
## Connector auth — attempt the call first

**Never tell the broker the lee-raleigh connector is "not authorized", "not connected",
or "needs to be authorized" unless an actual tool call just failed with an auth error.**

1. **Attempt first.** If the lee-raleigh tools appear in your available tools, call the
   one you need — do not assess authorization beforehand. A needs-auth flag, an empty
   credential field, a `/mcp` probe, or any other indirect signal is NOT authorization
   state; the only way to know is to make the call. If you have not attempted the call
   in this conversation, you do not know the auth state — so call it.
2. **Only a tool-level auth error counts.** Treat the connector as unauthorized ONLY
   when a call you just made returned an authorization error (`401` / `invalid_token`).
   Any other failure — a timeout, an empty result, a data error — is not an auth
   problem; handle it per this skill's error handling, and a plain retry line ("try
   again in a few minutes") is only ever for those transient, not-an-auth failures.
3. **On a genuine auth failure** — an attempted call returned `401`/`invalid_token`, or
   the lee-raleigh tools are missing from this session entirely — reply warmly, in
   broker language:

   > It looks like the Lee Raleigh connection needs a quick sign-in refresh — this can
   > happen after a reinstall, a new computer, or an app update. In Claude, open the
   > **Lee internal comps** plugin, go to its **Connectors** tab, and click the button
   > next to **lee-raleigh**. Sign in with the email you use for Claude (your Lee email
   > for most people) and send yourself the magic link. If the link says it expired,
   > that's normal — just request another from the sign-in page; the second request is
   > what signs you in. Full walkthrough with screenshots:
   > https://leeraleigh.groundedintelligence.io/setup#connect-sign-in — it takes about
   > a minute, then just ask me again.

   Never point a broker at "/mcp", never mention MCP or OAuth by name, and never answer
   an auth failure with "try again in a few minutes" — those leave them stuck.
<!-- END CONNECTOR-AUTH BLOCK -->
