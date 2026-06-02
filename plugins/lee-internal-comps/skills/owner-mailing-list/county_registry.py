"""County -> ArcGIS parcel service + field map.

Wake is live-confirmed (the 100 Walnut run, Task 10). The remaining entries were
pre-researched per county: every field name below was read from the service's live
`?f=json` layer metadata (not guessed). What still needs a live confirmation run per
county (Task 11) is the VACANT_FILTER value and the result count — many counties do not
publish a decoded land-class string, so the vacant filter falls back to a building-value
proxy (`bldg_val = 0`), which is reliable but coarser than Wake's `LAND_CLASS_DECODE='Vacant'`.

Counties with no usable public REST parcel service are intentionally ABSENT here, so
`resolve_county` returns None and the skill graceful-halts ("not covered yet"). Today that
is Nash (county server 403s; ConnectGIS times out). See QA_MATRIX.md for per-county status.

Some small counties have no county-run server; they route through the NC OneMap statewide
service (`services.nconemap.gov/.../NC1Map_Parcels`), which needs a `cntyname = '<County>'`
clause — that scoping is baked into their `vacant_filter`.

`mail_concat` (when present) lists the fields to join for a full mailing address; the skill
concatenates them at extract time (same as Wake's ADDR1/ADDR2/ADDR3).
"""

COUNTY_REGISTRY = {
    # --- Live-confirmed (Task 10) -------------------------------------------------
    "WAKE COUNTY": {
        # Confirmed live from the 100 Walnut St run. Host is maps.wakegov.com, NOT maps.wake.gov.
        "service_url": "https://maps.wakegov.com/arcgis/rest/services/Property/Parcels/MapServer/0",
        "field_map": {
            "acreage": "DEED_ACRES",
            "land_class": "LAND_CLASS_DECODE",
            "bldg_val": "BLDG_VAL",
            "owner": "OWNER",
            "mail_addr": "ADDR1",
            "site_addr": "SITE_ADDRESS",
        },
        "mail_concat": ["ADDR1", "ADDR2", "ADDR3"],
        "vacant_filter": "LAND_CLASS_DECODE = 'Vacant'",
    },

    # --- Triangle -----------------------------------------------------------------
    "DURHAM COUNTY": {
        "service_url": "https://webgis.durhamnc.gov/server/rest/services/PublicServices/Property/MapServer/4",
        "field_map": {
            "acreage": "ACREAGE",
            "land_class": "LAND_CLASS",
            "bldg_val": "TOTAL_BLDG_VALUE_ASSESSED",
            "owner": "PROPERTY_OWNER",
            "mail_addr": "OWNER_MAIL_1",
            "site_addr": "LOCATION_ADDR",
        },
        "mail_concat": ["OWNER_MAIL_1", "OWNER_MAIL_2", "OWNER_MAIL_3"],
        # LAND_CLASS holds short codes (vacant likely 'VL', unconfirmed). bldg=0 is reliable.
        "vacant_filter": "TOTAL_BLDG_VALUE_ASSESSED = 0",
    },
    "ORANGE COUNTY": {
        "service_url": "https://gis.orangecountync.gov/arcgis/rest/services/WebParcelService/MapServer/0",
        "field_map": {
            "acreage": "CALC_ACRES",
            "land_class": "RATECODE",
            "bldg_val": "BLDGVALUE",
            "owner": "OWNER1",
            "mail_addr": "ADDRESS1",
            "site_addr": "",  # parcel layer has NO situs/site address field (gap vs Wake)
        },
        "mail_concat": ["ADDRESS1", "ADDRESS2"],
        "vacant_filter": "BLDGVALUE = 0",
    },
    "JOHNSTON COUNTY": {
        # No county-run server; NC OneMap statewide service, scoped to Johnston.
        "service_url": "https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer/1",
        "field_map": {
            "acreage": "gisacres",
            "land_class": "parusedesc",
            "bldg_val": "improvval",
            "owner": "ownname",
            "mail_addr": "mailadd",
            "site_addr": "siteadd",
        },
        "vacant_filter": "parusedesc = 'Vacant Land' AND cntyname = 'Johnston'",
    },
    "CHATHAM COUNTY": {
        "service_url": "https://gisservices.chathamcountync.gov/opendataagol/rest/services/Cadastral/Chatham_CamaParcels/MapServer/0",
        "field_map": {
            "acreage": "gross_current_acres",
            "land_class": "land_use",
            "bldg_val": "jan1_bldg_ASV",
            "owner": "current_owners",
            "mail_addr": "address1",
            "site_addr": "physical_street_address",
        },
        "mail_concat": ["address1", "address2"],
        # land_use = 'Vacant' likely but unconfirmed; bldg ASV = 0 is reliable.
        "vacant_filter": "jan1_bldg_ASV = 0",
    },

    # --- Sandhills ----------------------------------------------------------------
    "LEE COUNTY": {
        "service_url": "https://lee-arcgis.leecountync.gov/arcgis/rest/services/ParcelsPictometryTyler/MapServer/0",
        "field_map": {
            "acreage": "ACRES",
            "land_class": "ob_DESCRIB",  # unreliable: blank on vacant parcels; use APRBLDG=0
            "bldg_val": "APRBLDG",
            "owner": "Owner1",
            "mail_addr": "MailADRNO",
            "site_addr": "PropAddr",
        },
        "mail_concat": ["MailADRNO", "MailADRSTR", "MailCity", "MailState", "MailZip"],
        "vacant_filter": "APRBLDG = 0",
    },
    "MOORE COUNTY": {
        "service_url": "https://gis.moorecountync.gov/server/rest/services/TemplateSite/Planning/MapServer/6",
        "field_map": {
            "acreage": "DEED_ACRES",
            "land_class": "CLASS",
            "bldg_val": "BUILD_VAL",
            "owner": "NAME",
            "mail_addr": "ADDRESS",
            "site_addr": "PROPST",  # composite: PROPNUM + PROPDIR + PROPST (no single field)
        },
        "site_concat": ["PROPNUM", "PROPDIR", "PROPST"],
        # CLASS 2-letter codes; FV/RV/CV = vacant (farm/res/commercial). FA/CA/RA = agricultural.
        "vacant_filter": "CLASS IN ('FV', 'RV', 'CV')",
    },
    "CUMBERLAND COUNTY": {
        "service_url": "https://gis.co.cumberland.nc.us/server/rest/services/Tax/Parcels/MapServer/0",
        "field_map": {
            "acreage": "ACREAGE",
            "land_class": "LAND_CLASS",
            "bldg_val": "TOTAL_BLDG_VALUE_ASSESSED",
            "owner": "OWNER",
            "mail_addr": "ADDRESS",
            "site_addr": "LOCATION_ADDR",  # quality gaps ("0 N/A DR") on some records
        },
        # LAND_CLASS LIKE 'F%' = rural/undeveloped; bldg=0 is the broader reliable proxy.
        "vacant_filter": "TOTAL_BLDG_VALUE_ASSESSED = 0",
    },
    "HARNETT COUNTY": {
        "service_url": "https://gis.harnett.org/arcgis/rest/services/Tax/Parcels/MapServer/0",
        "field_map": {
            "acreage": "CalculatedLandArea",
            "land_class": "UseCode",  # no public legend; Class field is null everywhere
            "bldg_val": "ParcelBuildingValue",
            "owner": "Owner1",
            "mail_addr": "MailingAddress",
            "site_addr": "PhysicalAddress",
        },
        "vacant_filter": "ParcelBuildingValue = 0",
    },

    # --- Wilmington / coast -------------------------------------------------------
    "NEW HANOVER COUNTY": {
        # Native NHC layer lacks bldg_val + mailing address; route through NC OneMap.
        "service_url": "https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/MapServer/1",
        "field_map": {
            "acreage": "gisacres",
            "land_class": "parusedesc",
            "bldg_val": "improvval",
            "owner": "ownname",
            "mail_addr": "mailadd",
            "site_addr": "siteadd",
        },
        "vacant_filter": "improvval = 0 AND cntyname = 'New Hanover'",
    },
    "BRUNSWICK COUNTY": {
        # Native TaxParcels has no bldg_val; route through NC OneMap.
        "service_url": "https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/MapServer/1",
        "field_map": {
            "acreage": "gisacres",
            "land_class": "parusedesc",
            "bldg_val": "improvval",
            "owner": "ownname",
            "mail_addr": "mailadd",
            "site_addr": "siteadd",
        },
        "vacant_filter": "improvval = 0 AND cntyname = 'Brunswick'",
    },
    "PENDER COUNTY": {
        # NC OneMap is empty for Pender; native service is the only option.
        "service_url": "https://gis.pendercountync.gov/arcgis/rest/services/Layers/MapServer/4",
        "field_map": {
            "acreage": "ACRES",
            "land_class": "PCL_CLASS",  # sparse (~60% null)
            "bldg_val": "HEAT_SQ_FT",   # heated sq ft, NOT a dollar value; presence proxy only
            "owner": "NAME",
            "mail_addr": "ADDR",        # single unstructured string (may be a c/o name)
            "site_addr": "PROPERTY_ADDRESS",  # null on many rural parcels
        },
        "vacant_filter": "HEAT_SQ_FT IS NULL",
    },

    # --- Triad --------------------------------------------------------------------
    "GUILFORD COUNTY": {
        "service_url": "https://gcgis.guilfordcountync.gov/arcgis/rest/services/GC_Cadastral_Current/Parcels_Ownership/FeatureServer/0",
        "field_map": {
            "acreage": "ACREAGE",
            "land_class": "LAND_CLASS",
            "bldg_val": "TOTAL_BLDG_VALUE_ASSESSED",
            "owner": "PROPERTY_OWNER",
            "mail_addr": "OWNER_MAIL_1",
            "site_addr": "LOCATION_ADDR",
        },
        "mail_concat": ["OWNER_MAIL_1", "OWNER_MAIL_2", "OWNER_MAIL_3"],
        "vacant_filter": "LAND_CLASS = 'VACANT'",  # confirmed exact string
    },
    "ALAMANCE COUNTY": {
        "service_url": "https://apps.alamance-nc.com/arcgis/rest/services/Tax/AlamanceParcels/FeatureServer/0",
        "field_map": {
            "acreage": "ACRES",
            "land_class": "AMVICD",  # Vacant/Improved code: 'V' = vacant, 'I' = improved
            "bldg_val": "AKICFM",
            "owner": "OWNAM1",
            "mail_addr": "OWADR1",
            "site_addr": "CAKPSAD",
        },
        "mail_concat": ["OWADR1", "OWADR2", "OWADR3", "OWADR4"],
        "vacant_filter": "AMVICD = 'V'",
    },

    # --- Eastern NC ---------------------------------------------------------------
    "WILSON COUNTY": {
        "service_url": "https://gis.wilson-co.com/arcgis/rest/services/Tax/Taxparcels/MapServer/0",
        "field_map": {
            "acreage": "CACRES",
            "land_class": "LandCurrentUsageCode",  # empty across live data; use bldg proxy
            "bldg_val": "ImproveASVCur",
            "owner": "Name1",
            "mail_addr": "TaxpayerAddress1",
            "site_addr": "PhysicalStreetAddress",
        },
        "mail_concat": ["TaxpayerAddress1", "TaxpayerAddress2", "TaxpayerAddress3", "TaxpayerAddress4"],
        "vacant_filter": "ImproveASVCur = 0",
    },
    "WAYNE COUNTY": {
        "service_url": "https://services5.arcgis.com/q2nSlChj7QgGTANO/arcgis/rest/services/Parcels/FeatureServer/14",
        "field_map": {
            "acreage": "GIS_Acres",
            "land_class": "PropUse",  # text use-codes, no dedicated vacant entry
            "bldg_val": "ParcelBuildingValue",
            "owner": "Name1",
            "mail_addr": "Address1",
            "site_addr": "PropertyAddress",
        },
        "mail_concat": ["Address1", "Address2", "Address3"],
        "vacant_filter": "ParcelBuildingValue = 0",
    },
    "CRAVEN COUNTY": {
        "service_url": "https://gis.cravencountync.gov/arcgis/rest/services/JustParcels/MapServer/0",
        "field_map": {
            "acreage": "PACREA",
            "land_class": "LUDESC",  # rich 127-value taxonomy incl. 18 vacant categories
            "bldg_val": "totbld",
            "owner": "PANAME",
            "mail_addr": "TMADDR",
            "site_addr": "FULLADD",
        },
        # LUDESC has explicit vacant categories, but bldg=0 is the simplest reliable filter.
        "vacant_filter": "totbld = 0",
    },
    "ONSLOW COUNTY": {
        "service_url": "https://gismaps.onslowcountync.gov/arcgis/rest/services/WEB_PUBLICATIONS/County_Map_Layers/MapServer/0",
        "field_map": {
            "acreage": "ACRES",
            "land_class": "LANDUSEDESCR",  # null across live data; use bldg proxy
            "bldg_val": "FINALFULLBUILDINGVALUE",
            "owner": "OWNER1",
            "mail_addr": "ADDRLINE1",
            "site_addr": "PHYSICALADDRESS",
        },
        "mail_concat": ["ADDRLINE1", "ADDRLINE2", "ADDRLINE3"],
        # parenthesized so it ANDs cleanly with the acreage range in the skill's WHERE builder.
        "vacant_filter": "(FINALFULLBUILDINGVALUE = 0 OR FINALFULLBUILDINGVALUE IS NULL)",
    },
}

# Counties intentionally NOT covered (resolve_county -> None -> skill graceful-halts):
#   Nash — county ArcGIS server returns 403; ConnectGIS portal times out; NC OneMap
#          population for Nash unverified. Promote to a registry entry once a live
#          NC OneMap (cntyname='Nash') pull is confirmed in Task 11.


def resolve_county(county_name):
    if not county_name:
        return None
    key = county_name.strip().upper()
    if not key.endswith(" COUNTY"):
        key = key + " COUNTY"
    return COUNTY_REGISTRY.get(key)
