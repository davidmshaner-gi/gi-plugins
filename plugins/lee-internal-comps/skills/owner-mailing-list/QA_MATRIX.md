# Owner Mailing List — Per-County QA Matrix (ship gate)

Each covered county needs its ArcGIS parcel service confirmed, its `field_map` validated,
a known test query run, full-row extraction verified (no truncation), and dedupe checked
before the skill ships for that county. A county with no usable public REST service is
marked **NOT COVERED** — the skill graceful-halts for it (no silent gaps).

Coverage footprint mirrors external comps (`/upload` page): Triangle, Sandhills,
Wilmington-coast, Triad, eastern NC.

## Status legend
- **PASS (live)** — confirmed live: real query run, count verified, no truncation.
- **RESEARCHED** — service URL + every field name read from the live `?f=json` metadata
  (Task 11 pre-research). Still needs a live confirmation run: validate the vacant filter
  and eyeball a result count. The registry entry is populated and ready to test.
- **NOT COVERED** — no usable public REST parcel service; skill graceful-halts.

## Matrix

| County | Region | Service | Fields verified | Vacant filter | Status |
|---|---|---|---|---|---|
| Wake | Triangle | maps.wakegov.com/.../Property/Parcels/0 | ✅ | `LAND_CLASS_DECODE='Vacant'` | **PASS (live)** — 100 Walnut → 69 |
| Durham | Triangle | webgis.durhamnc.gov/.../Property/4 | ✅ (live ?f=json) | `TOTAL_BLDG_VALUE_ASSESSED = 0` (LAND_CLASS code 'VL' unconfirmed) | RESEARCHED |
| Orange | Triangle | gis.orangecountync.gov/.../WebParcelService/0 | ✅ | `BLDGVALUE = 0` | RESEARCHED — no site-address field (gap) |
| Johnston | Triangle | NC OneMap (no county server) | ✅ | `improvval=0 AND cntyname='Johnston'` | RESEARCHED |
| Chatham | Triangle | gisservices.chathamcountync.gov/.../Chatham_CamaParcels/0 | ✅ | `jan1_bldg_ASV = 0` (land_use='Vacant' unconfirmed) | RESEARCHED |
| Lee | Sandhills | lee-arcgis.leecountync.gov/.../ParcelsPictometryTyler/0 | ✅ | `APRBLDG = 0` (no land-class vacant code) | RESEARCHED |
| Moore | Sandhills | gis.moorecountync.gov/.../Planning/6 | ✅ | `CLASS IN ('FV','RV','CV')` | RESEARCHED — site addr composite |
| Cumberland | Sandhills | gis.co.cumberland.nc.us/.../Tax/Parcels/0 | ✅ | `TOTAL_BLDG_VALUE_ASSESSED = 0` | RESEARCHED |
| Harnett | Sandhills | gis.harnett.org/.../Tax/Parcels/0 | ✅ | `ParcelBuildingValue = 0` | RESEARCHED |
| New Hanover | Wilmington-coast | NC OneMap (native lacks value/mail) | ✅ | `improvval=0 AND cntyname='New Hanover'` | RESEARCHED |
| Brunswick | Wilmington-coast | NC OneMap (native lacks value) | ✅ | `improvval=0 AND cntyname='Brunswick'` | RESEARCHED |
| Pender | Wilmington-coast | gis.pendercountync.gov/.../Layers/4 | ✅ | `HEAT_SQ_FT IS NULL` (no $ value field) | RESEARCHED |
| Guilford | Triad | gcgis.guilfordcountync.gov/.../Parcels_Ownership/0 | ✅ | `LAND_CLASS = 'VACANT'` (confirmed string) | RESEARCHED |
| Alamance | Triad | apps.alamance-nc.com/.../AlamanceParcels/0 | ✅ | `AMVICD = 'V'` (confirmed code) | RESEARCHED |
| Wilson | eastern NC | gis.wilson-co.com/.../Tax/Taxparcels/0 | ✅ | `ImproveASVCur = 0` | RESEARCHED |
| Wayne | eastern NC | services5.arcgis.com/.../Parcels/14 | ✅ | `ParcelBuildingValue = 0` | RESEARCHED |
| Nash | eastern NC | NC OneMap (county server dead) | ✅ directly confirmed | `improvval=0 AND cntyname='Nash'` | RESEARCHED — 55,717 parcels (15,305 vacant), owner/mail/acres populated |
| Craven | eastern NC | gis.cravencountync.gov/.../JustParcels/0 | ✅ | `totbld = 0` (rich LUDESC taxonomy available) | RESEARCHED |
| Onslow | eastern NC | gismaps.onslowcountync.gov/.../County_Map_Layers/0 | ✅ | `(FINALFULLBUILDINGVALUE = 0 OR ... IS NULL)` | RESEARCHED |

## What "RESEARCHED" means for the live confirmation pass (Task 11)
For each RESEARCHED county, the field NAMES are already live-verified (read from `?f=json`),
so the live pass is fast: run one known area+criteria query through the skill and confirm
(a) it returns a plausible, non-zero parcel set, (b) pagination retrieved everything (no
truncation), and (c) the vacant filter isolates vacant land. Where the vacant filter is a
`bldg_val = 0` proxy (Durham, Chatham, Lee, Cumberland, Harnett, Wilson, Wayne, Craven,
Onslow), confirm it matches broker intent; where it's a land-class value (Guilford, Alamance,
Moore, Johnston), it's already code-confirmed by research. Then flip the row to PASS (live).

## Per-county data gotchas (carry into the live pass)
- **Orange:** parcel layer has NO site-address field — `site_addr` is empty; join an address layer if needed.
- **Moore:** site address is composite (`PROPNUM+PROPDIR+PROPST`), no single field (`site_concat` in registry).
- **Pender:** `bldg_val` = `HEAT_SQ_FT` (a size proxy, not dollars); `mail_addr` is one unstructured string.
- **Cumberland:** `LOCATION_ADDR` has placeholder junk on some rows ("0 N/A DR").
- **Lee / Harnett / Wilson / Onslow:** land-class field unreliable/empty — vacant filter is a building-value proxy.
- **New Hanover / Brunswick / Johnston:** routed through NC OneMap (county server absent or value-less); `cntyname` scoping is baked into the vacant filter.

## Live data validation — 2026-06-02 (direct query, all 19 counties)
Every county's `service_url` + `field_map` + `vacant_filter` was exercised directly against
the live service: vacant-parcel count, a real owner-name sample, AND a 3-mile point+buffer
spatial query with `inSR=4326` (confirming radius search works across State Plane / Web
Mercator / NC OneMap projections). **All 19 returned real owner data and sane counts.**

Vacant counts (countywide): Wake 30,009 · Durham 20,591 · Orange 10,160 · Johnston 24,812 ·
Chatham 13,170 · Lee 10,276 · Moore 21,794 · Cumberland 23,068 · Harnett 26,885 ·
New Hanover 13,094 · Brunswick 58,902 · Pender 22,918 · Guilford 34,781 · Alamance 14,443 ·
Wilson 9,927 · Nash 15,305 · Wayne 26,556 · Craven 16,572 · Onslow 19,769.

Filter corrections made during validation: Guilford (`LAND_CLASS='VACANT'` 2,893 → `bldg=0`
34,781), Alamance (`AMVICD='V'` 161 → `bldg=0` 14,443), Pender (added `NAME IS NOT NULL` to
exclude empty placeholder records). Johnston/Nash standardized to `improvval=0` on NC OneMap.

## Ship gate
The skill is releasable (Task 12) once every county is confirmed or NOT COVERED.
- **Wake:** PASS (full live run, 100 Walnut → 69).
- **Other 18:** DATA-CONFIRMED — service + fields + vacant filter + spatial radius all verified
  by direct query (above). 0 NOT COVERED.
- **Remaining:** the only unrun step is an end-to-end pass through the *installed* skill inside
  a Cowork session (geocode → recipe → CSV), which requires the gi-plugins push first. The data
  risk — wrong URL / wrong field / broken filter / projection failure — is retired for all 19.

> Note: the research sweep initially mis-flagged Nash as NOT COVERED (it only checked the
> dead county server). Direct probing confirmed NC OneMap covers Nash fully. Treat every
> "NOT COVERED" verdict as needing a direct NC OneMap (`cntyname='<County>'`) check before
> it's accepted — the statewide service backstops most missing county servers.
