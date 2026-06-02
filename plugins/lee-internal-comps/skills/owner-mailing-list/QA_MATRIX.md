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

## Ship gate
The skill is releasable (Task 12) once every county here is PASS (live) or NOT COVERED.
Today: Wake = PASS, 18 covered counties RESEARCHED (registry-ready, awaiting a live
confirmation run), 0 NOT COVERED. David is holding the push until the full sweep is
PASS/NOT-COVERED.

> Note: the research sweep initially mis-flagged Nash as NOT COVERED (it only checked the
> dead county server). Direct probing confirmed NC OneMap covers Nash fully. Treat every
> "NOT COVERED" verdict as needing a direct NC OneMap (`cntyname='<County>'`) check before
> it's accepted — the statewide service backstops most missing county servers.
