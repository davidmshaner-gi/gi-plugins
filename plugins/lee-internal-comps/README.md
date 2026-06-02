# lee-internal-comps

A Claude plugin for authorized Lee & Associates Raleigh brokers. Lets Claude pull internal Dealius lease and sale comps (Excel + Lee-branded PDF) plus external comps (Excel + Markdown table) via typed MCP tools, with broker-tour email drafts on every pull.

## Install

Install via the GI marketplace — see [parent README](../../README.md).

## What you get

- **Skill:** `internal-comps` — orchestrates a comp search against the firm's internal Dealius mirror, builds the Excel deliverable, and renders a Lee-branded PDF (broker chooses Excel / PDF / Both per request).
- **Skill:** `external-comps` — orchestrates a comp search against the external weekly snapshot, produces a Markdown table in chat plus an Excel deliverable, and drafts a tour-ready email. PDF deferred to v1.1.
- **Skill:** `internal-and-external-comps` — the **default** "all comps" skill: an unqualified comps request (broker didn't say internal or external) pulls **both** internal Dealius and external CoStar in parallel and returns one combined chat table, one Excel (All Comps sheet + per-source detail sheets), and one Lee-branded **unified PDF** with every row tagged by Source. No dedup; sale and lease. Explicit "internal comps" / "external comps" still route to the single-source skills.
- **Skill:** `demographic-summary` — single-page 1/3/5-mile demographic infographic for any NC address (JSON + Lee-branded PDF with a 1-hour signed link).
- **Skill:** `demographic-detail` — multi-page Demographic and Income Profile with inline SVG charts, race/income breakdowns, 2020/2025/2030 projections (gi_permit_adjusted + Census BPS add-back), Family HHs + Owner HUs trend bars, and four Esri-analog indices.
- **Skill:** `business-key-facts` — BAO-style Business Key Facts 3-page landscape PDF for any NC address: key statistics, households table, site map with 1/3/5-mile rings, education attainment + workforce charts, population/housing growth.
- **Skill:** `owner-lookup` — sub-second owner-of-record + mailing address + assessor facts for any property in Wake, Durham, New Hanover, or Lee NC. Backed by a ~2M-row D1 owner graph bulk-staged from each county's GIS endpoint (no live external calls on the request path).
- **Skill:** `daily-debrief` — Will-only interview-style classification of yesterday's plugin sessions; walks Will through each session, records his outcome classification (plugin_only / plugin_with_manual_fix / manual_only / unable) and broker request source, and feeds the Friday usage rollup in #all-groundedintelligence.
- **Skill:** `tenants-in-market` — scheduled Cowork ingest of Triangle Pairlist tenant-requirement emails. Screens each as a tenant requirement (broker seeking space/investment) vs a listing (broker marketing a property), extracts the requirement fields, and writes every screened email to a shared, queryable `tenant_requirements` store (audit-everything) via the `lee_tenant_requirement_write` tool. Analyst/automation skill, not broker-invoked.
- **Skill:** `owner-mailing-list` — deduplicated owner + mailing-address CSV for an area + criteria request ("owners of 2–5 acre vacant land within 3 miles of 100 Walnut St, Cary"). Drives Claude-for-Chrome against a county's public ArcGIS parcel service to find matching parcels, then returns a clean CSV of owner names + mailing + site addresses, deduped by mailing address. 19 NC counties (Triangle, Sandhills, Wilmington-coast, Triad, eastern NC). Requires the `chrome-control` extension; detects it and walks the broker through enabling it if absent.
- **MCP connector:** `lee-raleigh` — read-only access to your firm's internal Dealius mirror, external comp tools, demographic infographics, and the cross-county owner graph, gated by OAuth + magic-link sign-in. Authorized brokers are pre-provisioned by Grounded Intelligence.

## External comps

The `external-comps` skill wraps three typed MCP tools (`search_external_sale_comps`, `search_external_lease_comps`, `get_external_comp_detail`) on the same `lee-raleigh` connector. The data lands weekly from Will's Excel export via the `external-comps-db` ingest pipeline. v1 produces Markdown + Excel; a Lee-branded PDF path is planned for v1.1.

## Sign-in

The first time the skill calls a tool, Cowork prompts an OAuth sign-in. You'll be redirected to a Lee Raleigh login page; enter your `@lee-associates.com` email, click the magic link in your inbox, and you're set. The session lasts 30 days; new magic link required after that.

## Help

Questions: `david@groundedintelligence.io`.
