# Owner Mailing List — Per-County QA Matrix (ship gate)

Each covered county needs its ArcGIS parcel service confirmed, its `field_map` validated,
a known test query run, full-row extraction verified (no truncation), and dedupe checked
before the skill ships for that county. A county with no usable public REST service is
marked **NOT COVERED** — the skill graceful-halts for it (no silent gaps).

Coverage footprint mirrors external comps (`/upload` page): Triangle, Sandhills,
Wilmington-coast, Triad, eastern NC. **QA-0 (open):** confirm the authoritative
covered-county list with David (= counties present in the external-comps D1 set).

| County | Region | Service confirmed | field_map | Test query | Full extraction | Result | Status |
|---|---|---|---|---|---|---|---|
| Wake | Triangle | ✅ `maps.wakegov.com/.../Property/Parcels/MapServer/0` | ✅ DEED_ACRES / LAND_CLASS_DECODE / BLDG_VAL / OWNER / ADDR1-3 / SITE_ADDRESS | 2–5 ac vacant within 3 mi of 100 Walnut St, Cary | ✅ paged past `exceededTransferLimit` | **69 parcels** | **PASS** |
| Durham | Triangle | — | — | — | — | — | TODO |
| Orange | Triangle | — | — | — | — | — | TODO |
| Johnston | Triangle | — | — | — | — | — | TODO |
| Chatham | Triangle | — | — | — | — | — | TODO |
| Lee | Sandhills | — | — | — | — | — | TODO |
| Moore | Sandhills | — | — | — | — | — | TODO |
| Cumberland | Sandhills | — | — | — | — | — | TODO |
| Harnett | Sandhills | — | — | — | — | — | TODO |
| New Hanover | Wilmington-coast | — | — | — | — | — | TODO |
| Brunswick | Wilmington-coast | — | — | — | — | — | TODO |
| Pender | Wilmington-coast | — | — | — | — | — | TODO |
| Guilford | Triad | — | — | — | — | — | TODO |
| Alamance | Triad | — | — | — | — | — | TODO |
| Wilson | eastern NC | — | — | — | — | — | TODO |
| Wayne | eastern NC | — | — | — | — | — | TODO |
| Nash | eastern NC | — | — | — | — | — | TODO |
| Craven | eastern NC | — | — | — | — | — | TODO |
| Onslow | eastern NC | — | — | — | — | — | TODO |

## Wake — PASS detail
- **Source of truth:** the recorded 100 Walnut St, Cary NC run (Claude Desktop + chrome-control), reproduced here.
- **Service:** `https://maps.wakegov.com/arcgis/rest/services/Property/Parcels/MapServer/0` (the registry seed `maps.wake.gov` was wrong; corrected to `maps.wakegov.com`).
- **Filters that produced the known-good set:** `LAND_CLASS_DECODE = 'Vacant'` + `DEED_ACRES` between 2 and 5, point + 3-statute-mile buffer of the geocoded subject.
- **Truncation:** the run paged past `exceededTransferLimit` to retrieve the full set (the partial-result trap was hit and handled).
- **Result:** 69 vacant parcels — matches the known-good count.

## Ship gate
The skill is releasable (Task 12) once every county in the authoritative covered list is
either **PASS** or explicitly **NOT COVERED** here. Today only Wake is PASS; the rest are
TODO and require a live Claude Desktop + chrome-control session per county.
