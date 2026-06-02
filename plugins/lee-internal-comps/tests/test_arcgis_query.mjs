// plugins/lee-internal-comps/tests/test_arcgis_query.mjs
import assert from "node:assert";
import { fetchAllParcels } from "../skills/owner-mailing-list/arcgis_query.js";

// mock: server has 1500 rows, page size 1000 -> must page twice
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
console.log("ok");
