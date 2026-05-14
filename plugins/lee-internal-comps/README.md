# lee-internal-comps

A Claude plugin for authorized Lee & Associates Raleigh brokers. Lets Claude pull internal Dealius lease and sale comps (Excel + Lee-branded PDF) plus external CoStar comps (Excel + Markdown table) via typed MCP tools, with broker-tour email drafts on every pull.

## Install

Install via the GI marketplace — see [parent README](../../README.md).

## What you get

- **Skill:** `internal-comps` — orchestrates a comp search against the firm's internal Dealius mirror, builds the Excel deliverable, and renders a Lee-branded PDF (broker chooses Excel / PDF / Both per request).
- **Skill:** `external-comps` — orchestrates a comp search against the external CoStar weekly snapshot, produces a Markdown table in chat plus an Excel deliverable, and drafts a tour-ready email. PDF deferred to v1.1.
- **MCP connector:** `lee-raleigh` — read-only access to your firm's internal Dealius mirror plus external CoStar comp tools, gated by OAuth + magic-link sign-in. Authorized brokers are pre-provisioned by Grounded Intelligence.

## External CoStar comps

The `external-comps` skill wraps three typed MCP tools (`search_external_sale_comps`, `search_external_lease_comps`, `get_external_comp_detail`) on the same `lee-raleigh` connector. The data lands weekly from Will's CoStar Excel export via the `external-comps-db` ingest pipeline. v1 produces Markdown + Excel; a Lee-branded PDF path is planned for v1.1.

## Sign-in

The first time the skill calls a tool, Cowork prompts an OAuth sign-in. You'll be redirected to a Lee Raleigh login page; enter your `@lee-associates.com` email, click the magic link in your inbox, and you're set. The session lasts 30 days; new magic link required after that.

## Help

Questions: `david@groundedintelligence.io`.
