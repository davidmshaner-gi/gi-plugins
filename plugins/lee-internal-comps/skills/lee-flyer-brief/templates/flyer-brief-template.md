---
# Flyer Brief — canonical schema (v0.1)
property_address: ""
property_name: ""            # listing/marketing name if any
deal_type: ""                # lease | sale | investment-sale | sublease
sublease_expiration: ""      # only when sublease
asset_class: []              # retail | office | industrial | flex | land | medical — multiple allowed (mixed-use)
date_prepared: ""            # YYYY-MM-DD
prepared_with: lee-flyer-brief v0.1
broker_team: []              # [{name, title, phone, email}]
comps_db_writeback:          # filled in Phase 5
  broker_comps_written: 0
  subject_listing_written: false
---

# Flyer Brief — {property_name or address}

## 1. The Ask (headline block)

| Field | Value | Source |
|---|---|---|
| Offering | {SF available / total, suites} | broker |
| Max contiguous / min divisible | {SF / SF — multi-suite only} | broker |
| Asking | {rate + structure, or price} | broker |
| NOI / Cap rate | {investment sale only} | broker |
| Availability | {date / immediate} | broker |

## 2. Property Story

{2–4 broker highlights, in the broker's confirmed wording. This seeds the
flyer's headline and intro copy.}

### Location description

{4–6 sentence trade-area narrative in broker-confirmed wording: the corridor
and what it connects, nearby anchors, surrounding uses, why the trade area is
proven. Suggest-first from pulled data + web context.}

## 3. Property Facts (selected)

| Fact | Value | Source |
|---|---|---|
| Owner of record | | county record |
| Year built | | county record / broker |
| Lot / building SF | | county record |
| Zoning | | county record |
{only rows the broker confirmed for display}

## 4. Comp Set (broker-selected)

| # | Property | Date | SF | Rate / Price | $/SF | Source |
|---|---|---|---|---|---|---|
{selected comps only — internal DB / external (CoStar cache) / broker-provided}

### Comp narrative

{2–4 sentences positioning the subject against the selected set, in broker-
confirmed wording. Every figure traceable to a row above.}

## 5. Market Data (broker-selected components)

### Business key facts
{only the items the broker selected, each with geography + source}

### Demographics
{only the fields/radii the broker selected, each with source}

## 6. Photos & Assets

{filenames collected, or "broker will attach in Design"; note the hero image}

## 7. Contact & Call to Action

{broker contact block — registry-resolved or web-sourced-and-confirmed}
CTA label: {e.g. "Schedule a Tour"}
CTA destination (digital): {mailto:...?subject=Tour Request — {property} | tel:... | scheduling URL}
Distribution mode(s): {print | digital eblast | both}

---

## Appendix A — Provenance & exclusions

- Full pulled comp list with included/excluded flags and the broker's
  selection date.
- Key facts / demographic items pulled but not selected.
- Any field marked `[broker to confirm]` or `[data service unavailable]`.

## Appendix B — Write-back record

- Broker-provided comps written to comps DB: {ids / none}, attribution
  {broker, date}.
- Subject listing written as on-market record: {yes/no}.
