// plugins/lee-internal-comps/tests/test_arcgis_query.mjs
import assert from "node:assert";
import {
  fetchAllParcels, isExemptOwner, buildRows, dedupeByMailingAddress, toCsv,
  buildOwnerMailingCsv,
} from "../skills/owner-mailing-list/arcgis_query.js";

// --- pagination: 1500 rows, page size 1000 -> must page twice ----------------
{
  let calls = 0;
  const fakeFetch = async (url) => {
    calls++;
    const offset = Number(new URL(url).searchParams.get("resultOffset") || 0);
    const remaining = 1500 - offset;
    const n = Math.min(1000, remaining);
    const features = Array.from({ length: n }, (_, i) => ({ attributes: { id: offset + i } }));
    return { json: async () => ({ features, exceededTransferLimit: offset + n < 1500 }) };
  };
  const rows = await fetchAllParcels("https://x/MapServer/0", { where: "1=1" }, fakeFetch);
  assert.strictEqual(rows.length, 1500, "must retrieve ALL rows across pages");
  assert.strictEqual(calls, 2, "must page exactly twice");
}

// --- isExemptOwner: government / HOA / cemetery / utility dropped; private kept
{
  for (const n of ["ONSLOW COUNTY", "CITY OF JACKSONVILLE", "NC DEPARTMENT OF TRANSPORTATION",
    "ONSLOW COUNTY BOARD OF EDUCATION", "WILMINGTON HOUSING AUTHORITY", "BELLEVUE CEMETERY",
    "CAPE FEAR MARINA HOA", "TROLLEY PATH CONDOMINIUM ASSN", "NORTH CAROLINA STATE PORTS AUTHORITY",
    "CAROLINA POWER & LIGHT CO", "SEABOARD COAST LINE R/R", "STATE OF NORTH CAROLINA", "", "   "]) {
    assert.strictEqual(isExemptOwner(n), true, `should be exempt/dropped: ${JSON.stringify(n)}`);
  }
  for (const n of ["WAKE STONE CORP", "MATTHEWS, JOE", "REEDY CREEK INVESTMENTS LLC",
    "HOWARD & SONS RENTALS", "DORA HIGHSMITH MARKHAM REVOCABLE LIVING TRUST", "SAS INSTITUTE INC",
    // false-positive guards — private LLCs that bare-keyword patterns would wrongly drop:
    "USA PARK INVESTMENTS LLC", "RAILROAD AVENUE LLC", "UTILITY SYSTEMS LLC",
    "SMITH PROPERTY OWNERS LLC", "STATEWIDE HOLDINGS LLC"]) {
    assert.strictEqual(isExemptOwner(n), false, `should be KEPT (private): ${n}`);
  }
}

// --- buildRows: mail_concat joins split address; site_concat; empty site ------
{
  const cfg = {
    fieldMap: { acreage: "AC", land_class: "LC", bldg_val: "BV", owner: "OWN", mail_addr: "M1", site_addr: "SITE" },
    mailConcat: ["M1", "M2", "CITY", "ST", "ZIP"],
  };
  const raw = [{ OWN: "ACME LLC", M1: "PO BOX 5", M2: "", CITY: "CARY", ST: "NC", ZIP: "27513", SITE: "0 MAPLE", AC: 3.1, LC: "Vacant" }];
  const out = buildRows(raw, cfg);
  assert.deepStrictEqual(out, [{ owner: "ACME LLC", mail_addr: "PO BOX 5 CARY NC 27513", site_addr: "0 MAPLE", acreage: 3.1, land_class: "Vacant" }]);

  // empty site_addr field -> "" not crash (Orange County case)
  const cfg2 = { fieldMap: { acreage: "AC", land_class: "LC", bldg_val: "BV", owner: "OWN", mail_addr: "A1", site_addr: "" }, mailConcat: ["A1", "A2"] };
  const out2 = buildRows([{ OWN: "X", A1: "123 Rd", A2: "Durham NC", AC: 2, LC: "v" }], cfg2);
  assert.strictEqual(out2[0].site_addr, "");
  assert.strictEqual(out2[0].mail_addr, "123 Rd Durham NC");
}

// --- dedupe: case/whitespace-insensitive; blank keys pass through ------------
{
  const dd = dedupeByMailingAddress([
    { mail_addr: "PO BOX 5, Cary NC" }, { mail_addr: "po box 5,  cary nc" }, { mail_addr: "1 Main St" },
    { mail_addr: "" }, { mail_addr: "  " },
  ]);
  assert.strictEqual(dd.output, 4, "two real dups collapse to one; blanks survive");
  assert.strictEqual(dd.dropped, 1);
}

// --- toCsv: header + RFC-4180 quoting of embedded commas ---------------------
{
  const csv = toCsv([{ owner: "MATTHEWS, JOE", mail_addr: "1 Main St Cary NC 27513", site_addr: "0 Oak", acreage: 2.1, land_class: "Vacant" }]);
  const lines = csv.split("\n");
  assert.strictEqual(lines[0], "owner,mail_addr,site_addr,acreage,land_class");
  assert.ok(lines[1].startsWith('"MATTHEWS, JOE",'), "owner with comma is quoted");
}

// --- end-to-end: buildOwnerMailingCsv filters exempt + dedupes + emits CSV ----
{
  const rawRows = [
    { OWNER: "WAKE STONE CORP", ADDR1: "PO BOX 190", ADDR2: "", ADDR3: "KNIGHTDALE NC 27545", SITE_ADDRESS: "0 OLD US 1", DEED_ACRES: 4.2, LAND_CLASS_DECODE: "Vacant" },
    { OWNER: "WAKE STONE CORP", ADDR1: "PO BOX 190", ADDR2: "", ADDR3: "KNIGHTDALE NC 27545", SITE_ADDRESS: "0 OTHER RD", DEED_ACRES: 3.0, LAND_CLASS_DECODE: "Vacant" }, // dup mail
    { OWNER: "CITY OF RALEIGH", ADDR1: "PO BOX 590", ADDR2: "", ADDR3: "RALEIGH NC 27602", SITE_ADDRESS: "0 GOV", DEED_ACRES: 9.0, LAND_CLASS_DECODE: "Vacant" }, // exempt
    { OWNER: "", ADDR1: "0", ADDR2: "", ADDR3: "", SITE_ADDRESS: "0", DEED_ACRES: 8.9, LAND_CLASS_DECODE: "Vacant" }, // blank owner
  ];
  const fakeFetch = async () => ({ json: async () => ({ features: rawRows.map((a) => ({ attributes: a })), exceededTransferLimit: false }) });
  const cfg = {
    serviceUrl: "https://maps.wakegov.com/arcgis/rest/services/Property/Parcels/MapServer/0",
    where: "LAND_CLASS_DECODE = 'Vacant'", geometry: JSON.stringify({ x: -78.78, y: 35.78 }), distance: 3,
    fieldMap: { acreage: "DEED_ACRES", land_class: "LAND_CLASS_DECODE", bldg_val: "BLDG_VAL", owner: "OWNER", mail_addr: "ADDR1", site_addr: "SITE_ADDRESS" },
    mailConcat: ["ADDR1", "ADDR2", "ADDR3"],
  };
  const { csv, report } = await buildOwnerMailingCsv(cfg, fakeFetch);
  assert.strictEqual(report.parcels, 4);
  assert.strictEqual(report.exempt_dropped, 2, "CITY OF RALEIGH + blank-owner dropped");
  assert.strictEqual(report.unique_owners, 1, "two WAKE STONE rows dedupe to one");
  const lines = csv.split("\n");
  assert.strictEqual(lines.length, 2, "header + 1 owner");
  assert.ok(lines[1].includes("PO BOX 190 KNIGHTDALE NC 27545"), "complete mailing address");
}

console.log("ok");
