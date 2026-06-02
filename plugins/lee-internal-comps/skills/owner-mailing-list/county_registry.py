"""County -> ArcGIS parcel service + field map.

Wake is live-confirmed (the 100 Walnut run, Task 10). Every other entry was
pre-researched then live-validated 2026-06-02: the service URL, the field names,
the vacant filter (real vacant count + sane owner sample), the spatial radius
query, AND the full mailing address (street + city + state + zip) were all
exercised directly against the service. `mail_concat` lists the fields to join
for a complete mailing address — confirmed per county against live data, because
most counties hold city/state/zip in SEPARATE fields outside `mail_addr`. The
query MUST request `outFields="*"` so those fields are present; `helpers.build_rows`
does the join.

A county with no usable public REST parcel service would be intentionally ABSENT
here, so `resolve_county` returns None and the skill graceful-halts ("not covered
yet"). All 19 covered counties are present (none currently absent — Nash, which
lacks a county server, routes through NC OneMap). See QA_MATRIX.md for status.

Some small counties have no county-run server; they route through the NC OneMap
statewide service (`services.nconemap.gov/.../NC1Map_Parcels`), which needs a
`cntyname = '<County>'` clause baked into `vacant_filter`.
"""

COUNTY_REGISTRY = {
    # --- Live-confirmed (Task 10) -------------------------------------------------
    "WAKE COUNTY": {
        # Confirmed live from the 100 Walnut St run. Host is maps.wakegov.com, NOT maps.wake.gov.
        "service_url": "https://maps.wakegov.com/arcgis/rest/services/Property/Parcels/MapServer/0",
        "field_map": {
            "acreage": "DEED_ACRES", "land_class": "LAND_CLASS_DECODE", "bldg_val": "BLDG_VAL",
            "owner": "OWNER", "mail_addr": "ADDR1", "site_addr": "SITE_ADDRESS",
        },
        "mail_concat": ["ADDR1", "ADDR2", "ADDR3"],  # ADDR2 carries city/state/zip inline
        "vacant_filter": "LAND_CLASS_DECODE = 'Vacant'",
    },

    # --- Triangle -----------------------------------------------------------------
    "DURHAM COUNTY": {
        "service_url": "https://webgis.durhamnc.gov/server/rest/services/PublicServices/Property/MapServer/4",
        "field_map": {
            "acreage": "ACREAGE", "land_class": "LAND_CLASS", "bldg_val": "TOTAL_BLDG_VALUE_ASSESSED",
            "owner": "PROPERTY_OWNER", "mail_addr": "OWNER_MAIL_1", "site_addr": "LOCATION_ADDR",
        },
        "mail_concat": ["OWNER_MAIL_1", "OWNER_MAIL_2", "OWNER_MAIL_3",
                        "OWNER_MAIL_CITY", "OWNER_MAIL_STATE", "OWNER_MAIL_ZIP"],
        # LAND_CLASS holds short codes (vacant unconfirmed); bldg=0 is reliable.
        "vacant_filter": "TOTAL_BLDG_VALUE_ASSESSED = 0",
    },
    "ORANGE COUNTY": {
        "service_url": "https://gis.orangecountync.gov/arcgis/rest/services/WebParcelService/MapServer/0",
        "field_map": {
            "acreage": "CALC_ACRES", "land_class": "RATECODE", "bldg_val": "BLDGVALUE",
            "owner": "OWNER1", "mail_addr": "ADDRESS1",
            "site_addr": "",  # parcel layer has NO situs/site address field
        },
        "mail_concat": ["ADDRESS1", "ADDRESS2", "CITY", "STATE", "ZIPCODE"],
        "vacant_filter": "BLDGVALUE = 0",
    },
    "JOHNSTON COUNTY": {
        # No county-run server; NC OneMap statewide service, scoped to Johnston.
        "service_url": "https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1",
        "field_map": {
            "acreage": "gisacres", "land_class": "parusedesc", "bldg_val": "improvval",
            "owner": "ownname", "mail_addr": "mailadd", "site_addr": "siteadd",
        },
        "mail_concat": ["mailadd", "mcity", "mstate", "mzip"],
        # NC OneMap parusedesc is NOT standardized across counties; use the reliable bldg proxy.
        "vacant_filter": "improvval = 0 AND cntyname = 'Johnston'",
    },
    "CHATHAM COUNTY": {
        "service_url": "https://gisservices.chathamcountync.gov/opendataagol/rest/services/Cadastral/Chatham_CamaParcels/MapServer/0",
        "field_map": {
            "acreage": "gross_current_acres", "land_class": "land_use", "bldg_val": "jan1_bldg_ASV",
            "owner": "current_owners", "mail_addr": "address1", "site_addr": "physical_street_address",
        },
        "mail_concat": ["address1", "address2", "csz"],  # csz = "City, ST  ZIP"
        "vacant_filter": "jan1_bldg_ASV = 0",
    },

    # --- Sandhills ----------------------------------------------------------------
    "LEE COUNTY": {
        "service_url": "https://lee-arcgis.leecountync.gov/arcgis/rest/services/ParcelsPictometryTyler/MapServer/0",
        "field_map": {
            "acreage": "ACRES", "land_class": "ob_DESCRIB", "bldg_val": "APRBLDG",
            "owner": "Owner1", "mail_addr": "MailADRNO", "site_addr": "PropAddr",
        },
        "mail_concat": ["MailADRNO", "MailADRSTR", "MailCity", "MailState", "MailZip"],
        "vacant_filter": "APRBLDG = 0",  # ob_DESCRIB blank on vacant parcels
    },
    "MOORE COUNTY": {
        "service_url": "https://gis.moorecountync.gov/server/rest/services/TemplateSite/Planning/MapServer/6",
        "field_map": {
            "acreage": "DEED_ACRES", "land_class": "CLASS", "bldg_val": "BUILD_VAL",
            "owner": "NAME", "mail_addr": "ADDRESS", "site_addr": "PROPST",
        },
        "mail_concat": ["ADDRESS", "CITY", "STATE", "ZIP"],
        "site_concat": ["PROPNUM", "PROPDIR", "PROPST"],  # no single site field
        "vacant_filter": "CLASS IN ('FV', 'RV', 'CV')",
    },
    "CUMBERLAND COUNTY": {
        "service_url": "https://gis.co.cumberland.nc.us/server/rest/services/Tax/Parcels/MapServer/0",
        "field_map": {
            "acreage": "ACREAGE", "land_class": "LAND_CLASS", "bldg_val": "TOTAL_BLDG_VALUE_ASSESSED",
            "owner": "OWNER", "mail_addr": "ADDRESS", "site_addr": "LOCATION_ADDR",
        },
        "mail_concat": ["ADDRESS", "CITY", "STATE", "ZIP"],
        "vacant_filter": "TOTAL_BLDG_VALUE_ASSESSED = 0",
    },
    "HARNETT COUNTY": {
        "service_url": "https://gis.harnett.org/arcgis/rest/services/Tax/Parcels/MapServer/0",
        "field_map": {
            "acreage": "CalculatedLandArea", "land_class": "UseCode", "bldg_val": "ParcelBuildingValue",
            "owner": "Owner1", "mail_addr": "MailingAddress", "site_addr": "PhysicalAddress",
        },
        # MailingAddress is a single full string ("3303 WISTERIA DR  CLAYTON, NC 27527") — no concat.
        "vacant_filter": "ParcelBuildingValue = 0",
    },

    # --- Wilmington / coast -------------------------------------------------------
    "NEW HANOVER COUNTY": {
        # Native NHC layer lacks bldg_val + mailing address; route through NC OneMap.
        "service_url": "https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/MapServer/1",
        "field_map": {
            "acreage": "gisacres", "land_class": "parusedesc", "bldg_val": "improvval",
            "owner": "ownname", "mail_addr": "mailadd", "site_addr": "siteadd",
        },
        "mail_concat": ["mailadd", "mcity", "mstate", "mzip"],
        "vacant_filter": "improvval = 0 AND cntyname = 'New Hanover'",
    },
    "BRUNSWICK COUNTY": {
        # Native TaxParcels has no bldg_val; route through NC OneMap.
        "service_url": "https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/MapServer/1",
        "field_map": {
            "acreage": "gisacres", "land_class": "parusedesc", "bldg_val": "improvval",
            "owner": "ownname", "mail_addr": "mailadd", "site_addr": "siteadd",
        },
        "mail_concat": ["mailadd", "mcity", "mstate", "mzip"],
        "vacant_filter": "improvval = 0 AND cntyname = 'Brunswick'",
    },
    "PENDER COUNTY": {
        # NC OneMap is empty for Pender; native service is the only option.
        "service_url": "https://gis.pendercountync.gov/arcgis/rest/services/Layers/MapServer/4",
        "field_map": {
            "acreage": "ACRES", "land_class": "PCL_CLASS", "bldg_val": "HEAT_SQ_FT",
            "owner": "NAME", "mail_addr": "ADDR", "site_addr": "PROPERTY_ADDRESS",
        },
        "mail_concat": ["ADDR", "CITY", "STATE", "ZIP"],
        # NAME IS NOT NULL excludes ~300 attribute-less placeholder records.
        "vacant_filter": "NAME IS NOT NULL AND HEAT_SQ_FT IS NULL",
    },

    # --- Triad --------------------------------------------------------------------
    "GUILFORD COUNTY": {
        "service_url": "https://gcgis.guilfordcountync.gov/arcgis/rest/services/GC_Cadastral_Current/Parcels_Ownership/FeatureServer/0",
        "field_map": {
            "acreage": "ACREAGE", "land_class": "LAND_CLASS", "bldg_val": "TOTAL_BLDG_VALUE_ASSESSED",
            "owner": "PROPERTY_OWNER", "mail_addr": "OWNER_MAIL_1", "site_addr": "LOCATION_ADDR",
        },
        "mail_concat": ["OWNER_MAIL_1", "OWNER_MAIL_2", "OWNER_MAIL_3",
                        "OWNER_MAIL_CITY", "OWNER_MAIL_STATE", "OWNER_MAIL_ZIP"],
        # LAND_CLASS='VACANT' is a narrow subcategory (2,893); bldg=0 is inclusive (34,781).
        "vacant_filter": "TOTAL_BLDG_VALUE_ASSESSED = 0",
    },
    "ALAMANCE COUNTY": {
        "service_url": "https://apps.alamance-nc.com/arcgis/rest/services/Tax/AlamanceParcels/FeatureServer/0",
        "field_map": {
            "acreage": "ACRES", "land_class": "AMVICD", "bldg_val": "AKICFM",
            "owner": "OWNAM1", "mail_addr": "OWADR1", "site_addr": "CAKPSAD",
        },
        "mail_concat": ["OWADR1", "OWADR2", "OWADR3", "OWADR4", "OWCITY", "OWSTA", "OWZIPA"],
        # AMVICD='V' too sparse (161); improvement-value proxy gives 14,443.
        "vacant_filter": "(AKICFM = 0 OR AKICFM IS NULL)",
    },

    # --- Eastern NC ---------------------------------------------------------------
    "WILSON COUNTY": {
        "service_url": "https://gis.wilson-co.com/arcgis/rest/services/Tax/Taxparcels/MapServer/0",
        "field_map": {
            "acreage": "CACRES", "land_class": "LandCurrentUsageCode", "bldg_val": "ImproveASVCur",
            "owner": "Name1", "mail_addr": "TaxpayerAddress1", "site_addr": "PhysicalStreetAddress",
        },
        "mail_concat": ["TaxpayerAddress1", "TaxpayerAddress2", "TaxpayerAddress3",
                        "TaxpayerAddress4", "TaxpayerCity", "State", "ZIPCode"],
        "vacant_filter": "ImproveASVCur = 0",  # LandCurrentUsageCode empty in live data
    },
    "NASH COUNTY": {
        # County server is dead; NC OneMap has 55,717 Nash parcels (15,305 vacant).
        "service_url": "https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/MapServer/1",
        "field_map": {
            "acreage": "gisacres", "land_class": "parusedesc", "bldg_val": "improvval",
            "owner": "ownname", "mail_addr": "mailadd", "site_addr": "siteadd",
        },
        # Nash's mcity already carries the full "City ST ZIP" string, so mstate/mzip would duplicate.
        "mail_concat": ["mailadd", "mcity"],
        "vacant_filter": "improvval = 0 AND cntyname = 'Nash'",
    },
    "WAYNE COUNTY": {
        "service_url": "https://services5.arcgis.com/q2nSlChj7QgGTANO/arcgis/rest/services/Parcels/FeatureServer/14",
        "field_map": {
            "acreage": "GIS_Acres", "land_class": "PropUse", "bldg_val": "ParcelBuildingValue",
            "owner": "Name1", "mail_addr": "Address1", "site_addr": "PropertyAddress",
        },
        "mail_concat": ["Address1", "Address2", "Address3", "City", "State", "ZipCode"],
        "vacant_filter": "ParcelBuildingValue = 0",
    },
    "CRAVEN COUNTY": {
        "service_url": "https://gis.cravencountync.gov/arcgis/rest/services/JustParcels/MapServer/0",
        "field_map": {
            "acreage": "PACREA", "land_class": "LUDESC", "bldg_val": "totbld",
            "owner": "PANAME", "mail_addr": "TMADDR", "site_addr": "FULLADD",
        },
        "mail_concat": ["TMADDR", "CITYNM", "ZIP"],  # no state field on this layer
        "vacant_filter": "totbld = 0",
    },
    "ONSLOW COUNTY": {
        "service_url": "https://gismaps.onslowcountync.gov/arcgis/rest/services/WEB_PUBLICATIONS/County_Map_Layers/MapServer/0",
        "field_map": {
            "acreage": "ACRES", "land_class": "LANDUSEDESCR", "bldg_val": "FINALFULLBUILDINGVALUE",
            "owner": "OWNER1", "mail_addr": "ADDRLINE1", "site_addr": "PHYSICALADDRESS",
        },
        # MAILCITY/STATE/ZIP are the OWNER mailing fields; PHYSICALCITY/ZIP are the site (do not use).
        "mail_concat": ["ADDRLINE1", "ADDRLINE2", "ADDRLINE3", "MAILCITY", "MAILSTATE", "MAILZIP"],
        # parenthesized so it ANDs cleanly with the acreage range in the skill's WHERE builder.
        "vacant_filter": "(FINALFULLBUILDINGVALUE = 0 OR FINALFULLBUILDINGVALUE IS NULL)",
    },
}

# All 19 covered counties are present above. Any county not in this dict (e.g. one outside
# the Lee Raleigh footprint) resolves to None and the skill graceful-halts ("not covered yet").


def resolve_county(county_name):
    if not county_name:
        return None
    key = county_name.strip().upper()
    if not key.endswith(" COUNTY"):
        key = key + " COUNTY"
    return COUNTY_REGISTRY.get(key)
