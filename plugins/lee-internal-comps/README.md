# lee-internal-comps

A Claude plugin for authorized Lee & Associates Raleigh brokers. Lets Claude pull internal Dealius lease and sale comps, plus query external CoStar comps via typed MCP tools. Internal comps generate Excel exports and broker-tour email drafts.

## Install

Install via the GI marketplace — see [parent README](../../README.md).

## What you get

- **Skill:** `internal-comps` — orchestrates a comp search, builds the Excel deliverable, and drafts a tour-ready email.
- **MCP connector:** `lee-raleigh` — read-only access to your firm's internal Dealius mirror plus external CoStar comp tools, gated by OAuth + magic-link sign-in. Authorized brokers are pre-provisioned by Grounded Intelligence.

## External CoStar comps

External CoStar comps are surfaced via three typed MCP tools (`search_external_sale_comps`, `search_external_lease_comps`, `get_external_comp_detail`). The data lands weekly from Will's CoStar Excel export via `sow_1_analyst_pilot/external-comps-db/`. A broker-facing skill wrapping the external tools is forthcoming (v1.5).

## Sign-in

The first time the skill calls a tool, Cowork prompts an OAuth sign-in. You'll be redirected to a Lee Raleigh login page; enter your `@lee-associates.com` email, click the magic link in your inbox, and you're set. The session lasts 30 days; new magic link required after that.

## Help

Questions: `david@groundedintelligence.io`.
