// plugins/lee-internal-comps/skills/owner-mailing-list/arcgis_query.js
// Runs in the browser via Claude-for-Chrome execute_javascript.
// fetchAllParcels pages on exceededTransferLimit until the full set is retrieved.
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
