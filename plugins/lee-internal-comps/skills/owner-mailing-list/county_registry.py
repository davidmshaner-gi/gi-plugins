"""County -> ArcGIS parcel service + field map. Seeded with Wake; grown via QA (Task 11)."""

COUNTY_REGISTRY = {
    "WAKE COUNTY": {
        # Confirmed live from the 100 Walnut St run (Task 10). Host is maps.wakegov.com, NOT maps.wake.gov.
        "service_url": "https://maps.wakegov.com/arcgis/rest/services/Property/Parcels/MapServer/0",
        "field_map": {
            "acreage": "DEED_ACRES",
            "land_class": "LAND_CLASS_DECODE",
            "bldg_val": "BLDG_VAL",
            "owner": "OWNER",
            "mail_addr": "ADDR1",      # ADDR1/ADDR2/ADDR3 concatenated at extract time
            "site_addr": "SITE_ADDRESS",
        },
        "vacant_filter": "LAND_CLASS_DECODE = 'Vacant'",
    },
}

def resolve_county(county_name):
    if not county_name:
        return None
    key = county_name.strip().upper()
    if not key.endswith(" COUNTY"):
        key = key + " COUNTY"
    return COUNTY_REGISTRY.get(key)
