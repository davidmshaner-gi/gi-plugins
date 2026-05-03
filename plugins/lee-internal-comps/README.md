# lee-internal-comps

A Claude plugin for authorized Lee & Associates Raleigh brokers. Lets Claude pull internal Dealius lease and sale comps, then generates Excel exports and broker-tour email drafts.

## Install

Install via the GI marketplace — see [parent README](../../README.md).

## What you get

- **Skill:** `internal-comps` — orchestrates a comp search, builds the Excel deliverable, and drafts a tour-ready email.
- **MCP connector:** `lee-raleigh` — read-only access to your firm's internal Dealius mirror, gated by OAuth + magic-link sign-in. Authorized brokers are pre-provisioned by Grounded Intelligence.

## Sign-in

The first time the skill calls a tool, Cowork prompts an OAuth sign-in. You'll be redirected to a Lee Raleigh login page; enter your `@lee-associates.com` email, click the magic link in your inbox, and you're set. The session lasts 30 days; new magic link required after that.

## Help

Questions: `david@groundedintelligence.io`.
