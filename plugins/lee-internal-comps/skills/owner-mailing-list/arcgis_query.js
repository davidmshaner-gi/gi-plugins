// plugins/lee-internal-comps/skills/owner-mailing-list/arcgis_query.js
//
// The owner-mailing-list pipeline. Runs ENTIRELY in the browser via Claude in Chrome's
// javascript_tool — the Cowork sandbox has no outbound network, so all data work happens
// here. SKILL.md injects this file's functions onto `window` (strip the `export` keywords)
// and calls `buildOwnerMailingCsv(cfg)` once; that returns the finished CSV + a report,
// so there is no per-row browser<->sandbox round-tripping.
//
// county_registry.py (Python, sandbox) remains the source of truth for service URLs,
// field maps, and vacant filters; the model resolves the entry there and passes the small
// `cfg` into this pipeline. The Python helpers (build_rows/dedupe) are kept as a tested
// parity reference; this JS is the runtime executor and is node-tested (test_arcgis_query.mjs).

// --- 1. Paginated fetch (loops past exceededTransferLimit) --------------------
export async function fetchAllParcels(serviceUrl, params, fetchImpl = fetch) {
  const all = [];
  let offset = 0;
  const pageSize = 1000;
  // eslint-disable-next-line no-constant-condition
  while (true) {
    const u = new URL(serviceUrl + "/query");
    u.searchParams.set("f", "json");
    u.searchParams.set("outFields", params.outFields || "*");
    u.searchParams.set("where", params.where || "1=1");
    if (params.geometry) {
      u.searchParams.set("geometry", params.geometry);
      u.searchParams.set("geometryType", "esriGeometryPoint");
      u.searchParams.set("distance", String(params.distance));
      u.searchParams.set("units", "esriSRUnit_StatuteMile");
      u.searchParams.set("spatialRel", "esriSpatialRelIntersects");
      u.searchParams.set("inSR", "4326");
    }
    u.searchParams.set("returnGeometry", "false");
    u.searchParams.set("resultOffset", String(offset));
    u.searchParams.set("resultRecordCount", String(pageSize));
    const resp = await fetchImpl(u.toString());
    const data = await resp.json();
    const feats = data.features || [];
    all.push(...feats.map((x) => x.attributes));
    if (!data.exceededTransferLimit || feats.length === 0) break;
    offset += feats.length;
  }
  return all;
}

// --- 2. Exempt / non-prospect owner filter -----------------------------------
// Brokers want privately-owned vacant LAND (prospects). Government, municipal, exempt,
// HOA/COA, cemetery, utility, and railroad parcels are noise — drop them. This is the
// generic, county-agnostic complement to the per-county vacant filter (most counties use
// a building-value=0 proxy, which catches every government/exempt parcel with no building).
export const EXEMPT_OWNER_PATTERNS = [
  /\bCOUNTY\s*$/i,                          // "ONSLOW COUNTY", "NEW HANOVER COUNTY"
  /\b(CITY|TOWN|COUNTY|STATE)\s+OF\b/i,     // "CITY OF JACKSONVILLE", "STATE OF NORTH CAROLINA"
  /BOARD OF EDUCATION|SCHOOL (BOARD|DISTRICT|ADMIN)/i,
  /HOUSING AUTHORITY/i,
  /\bDEPARTMENT OF\b|\bDEPT OF\b|DEPARTMENT OF TRANSPORTATION/i,
  /UNITED STATES|\bU\.?S\.? GOV|US GOVERNMENT|\bUSA\b/i,
  /PORTS? AUTHORITY|TRANSIT AUTHORITY|AIRPORT AUTHORITY/i,
  /HOMEOWNERS|\bHOA\b|\bCOA\b|OWNERS (ASSOCIATION|ASSN)|CONDOMINIUM (ASSN|ASSOCIATION)|PROPERTY OWNERS/i,
  /CEMET[AE]RY|MEMORIAL GARDENS/i,
  /POWER (&|AND) LIGHT|DUKE ENERGY|ELECTRIC MEMBERSHIP|\bUTILIT/i,
  /RAILROAD|RAILWAY|\bR\/R\b/i,
];

export function isExemptOwner(name) {
  const n = String(name || "").trim();
  if (!n) return true; // blank owner -> not mailable, drop
  return EXEMPT_OWNER_PATTERNS.some((re) => re.test(n));
}

// --- 3. Map raw ArcGIS rows through the county field map ----------------------
// Mirror of helpers.build_rows: honor mail_concat / site_concat so split mailing
// addresses (street + city + state + zip) are joined, not dropped.
function joinFields(row, fields) {
  return (fields || [])
    .map((f) => (row[f] == null ? "" : String(row[f]).trim()))
    .filter(Boolean)
    .join(" ");
}

export function buildRows(rawRows, cfg) {
  const fm = cfg.fieldMap;
  const mailFields = cfg.mailConcat && cfg.mailConcat.length ? cfg.mailConcat
    : (fm.mail_addr ? [fm.mail_addr] : []);
  const siteFields = cfg.siteConcat && cfg.siteConcat.length ? cfg.siteConcat
    : (fm.site_addr ? [fm.site_addr] : []);
  return rawRows.map((r) => ({
    owner: r[fm.owner] == null ? "" : String(r[fm.owner]).trim(),
    mail_addr: joinFields(r, mailFields),
    site_addr: joinFields(r, siteFields),
    acreage: r[fm.acreage] == null ? "" : r[fm.acreage],
    land_class: r[fm.land_class] == null ? "" : r[fm.land_class],
  }));
}

// --- 4. Dedupe by normalized mailing address (blank keys pass through) --------
function normAddr(s) {
  return String(s || "").replace(/\s+/g, " ").trim().toLowerCase();
}

export function dedupeByMailingAddress(rows) {
  const seen = new Set();
  const out = [];
  for (const r of rows) {
    const key = normAddr(r.mail_addr);
    if (key && seen.has(key)) continue;
    if (key) seen.add(key);
    out.push(r);
  }
  return { rows: out, input: rows.length, output: out.length, dropped: rows.length - out.length };
}

// --- 5. CSV serialization (RFC-4180 minimal quoting) -------------------------
const CSV_FIELDS = ["owner", "mail_addr", "site_addr", "acreage", "land_class"];

function csvCell(v) {
  const s = v == null ? "" : String(v);
  return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
}

export function toCsv(rows) {
  const lines = [CSV_FIELDS.join(",")];
  for (const r of rows) lines.push(CSV_FIELDS.map((f) => csvCell(r[f])).join(","));
  return lines.join("\n");
}

// --- 6. The one-shot pipeline ------------------------------------------------
// cfg: { serviceUrl, where, geometry, distance, fieldMap, mailConcat, siteConcat }
// Returns { csv, report }. SKILL.md stows `csv` on window and writes it to a file in
// deterministic line-batches (no base64, no ad-hoc slicing).
export async function buildOwnerMailingCsv(cfg, fetchImpl = fetch) {
  const raw = await fetchAllParcels(
    cfg.serviceUrl,
    { where: cfg.where, geometry: cfg.geometry, distance: cfg.distance, outFields: "*" },
    fetchImpl
  );
  const mapped = buildRows(raw, cfg);
  const kept = mapped.filter((r) => !isExemptOwner(r.owner));
  const exemptDropped = mapped.length - kept.length;
  const dd = dedupeByMailingAddress(kept);
  const csv = toCsv(dd.rows);
  return {
    csv,
    report: {
      parcels: raw.length,
      after_exempt_filter: kept.length,
      exempt_dropped: exemptDropped,
      unique_owners: dd.output,
      dedup_dropped: dd.dropped,
    },
  };
}
