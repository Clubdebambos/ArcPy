import arcpy

########################################################################################
## Esri Documentation
##  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/data-management/feature-envelope-to-polygon.html?tabs=dialog
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/functions/getparameterastext.html
##  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/data-management/minimum-bounding-geometry.html?tabs=python
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/functions/listfields.html
##  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/data-management/create-feature-class.html?tabs=python
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/data-access/describe.html
##  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/data-management/multipart-to-singlepart.html?tabs=python
##  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/data-management/add-field.html?tabs=python
##  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/data-management/calculate-field.html?tabs=python
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/data-access/searchcursor-class.html
##  https://doc.esri.com/en/arcgis-pro/latest/help/analysis/geoprocessing/basics/the-in-memory-workspace.html
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/classes/array.html
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/classes/polygon.html
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/data-access/updatecursor-class.html
##  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/conversion/export-features.html?tabs=python
##  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/data-management/delete-field.html?tabs=python
##  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/data-management/delete.html?tabs=python
##
## Original tool syntax:
##  arcpy.management.FeatureEnvelopeToPolygon(in_features, out_feature_class, {single_envelope})
##
########################################################################################

## 🤗 Support content creation 👉 https://buymeacoffee.com/glenbambrick

########################################################################################
## USER INPUTS / PARAMETERS

## the input features that can be multipoint, line, polygon
in_features = arcpy.GetParameterAsText(0)

## the output polygon feature class
out_feature_class = arcpy.GetParameterAsText(1)

## one envelope for entire multipart of sperate envelope for each part of the multipart.
single_envelope = arcpy.GetParameterAsText(2)

########################################################################################
## GET THE FEATURE CLASS SHAPE TYPE

## get the shape type of the in_features feature class
shape_type = arcpy.da.Describe(in_features)["shapeType"]

########################################################################################
## SINGLEPART and MULTIPOINT SELECTIONS

## Validation will only allow SINGLEPART to be chosen for Multipoint
if single_envelope == "SINGLEPART" or (shape_type == "Multipoint" and single_envelope == "MULTIPART"):
    ## we can simply use the MBG tool available for a Basic License to achieve
    ## desired output
    arcpy.management.MinimumBoundingGeometry(
        in_features = in_features,
        out_feature_class = out_feature_class,
        geometry_type = "ENVELOPE"
    )

########################################################################################
## MULTIPART POLYGON\POLYLINE

## if MULTIPART was selection for a Polygon or Polyline Feature Class
elif single_envelope == "MULTIPART" and shape_type in ("Polygon", "Polyline"):

    ####################################################################################
    ## REQUIRED OBJECTS

    ## we need the OID field to aid will matching original records with output records
    oid_fld = [
        fld.name for fld
        in arcpy.ListFields(
            dataset = in_features
        ) if fld.type=="OID"
    ][0]

    ## get a list of fields required for the output
    in_fld_names = [
        fld.name for fld
        in arcpy.ListFields(
            dataset=in_features
        ) if fld.type not in ("Blob","Geometry","GlobalID","Guid","OID","Raster")
    ]

    ## at the OID field as the first field name in the list
    in_fld_names.insert(0, oid_fld)

    ## get the SRS of the in_features feature class
    srs_id = arcpy.da.Describe(in_features)["spatialReference"].factoryCode

    ## dictionary to hold {oid:geometry} this will hold all the geometry we need to
    ## reapply to our memory_fc
    poly_dict = {}

    ####################################################################################
    ## CREATE TEMPORARY FEATURE CLASS IN MEMORY WORKSPACE

    ## create a Polygon feature class in the memory workspace
    memory_fc = arcpy.management.CreateFeatureclass(
        out_path = "memory",
        out_name = "memory_fc",
        geometry_type = "POLYGON",
        template = in_features,
        has_m = "SAME_AS_TEMPLATE",
        has_z ="SAME_AS_TEMPLATE",
        spatial_reference = srs_id
    )

    ## add the ORIG_OID field
    arcpy.management.AddField(
        in_table = memory_fc,
        field_name = "ORIG_OID",
        field_type = "LONG"
    )

    ## iterate through the in_features feature class and populate the
    ## attribute table for feature class in memorry
    with arcpy.da.SearchCursor(
        in_table = in_features,
        field_names = in_fld_names
    ) as cursor:
        in_fld_names[0] = "ORIG_OID"
        for row in cursor:
            with arcpy.da.InsertCursor(
                in_table = memory_fc,
                field_names = in_fld_names
            ) as i_cursor:
                i_cursor.insertRow(row)

    ####################################################################################
    ## MULTIPART TO SINGLEPART out-of-the-box BASIC TOOL

    ## Step 1. create singlepart from multipart
    singlepart = arcpy.management.MultipartToSinglepart(
        in_features = in_features,
        out_feature_class = "memory\\single_part"
    )

    ## add in a field to maintain the ORIG_FID field info generated from the
    ## MultipartToSinglepart tool. The MBG tool also uses ORIG_FID and it can
    ## cause confusion so we will be explicit and populate out own MP_HELPER field
    ## with the ORIG_FID
    arcpy.management.AddField(
        in_table = singlepart,
        field_name = "MP_HELPER",
        field_type = "LONG"
    )

    arcpy.management.CalculateField(
        in_table = singlepart,
        field = "MP_HELPER",
        expression = "!ORIG_FID!"
    )

    ####################################################################################
    ## MINIMUM BOUNDING GEOMETRY out-of-the-box BASIC TOOL

    ## Step 2. get MBG envelope for all features
    envelopes = arcpy.management.MinimumBoundingGeometry(
        in_features = singlepart,
        out_feature_class = "memory\\envelopes",
        geometry_type = "ENVELOPE"
    )

    ####################################################################################
    ## GET MULTIPART GEOMETRIES PER OID

    ## get a set of unique ORIG_FIDs from the MP_HELPER field
    unique_oid = set(sorted(row[0] for row in arcpy.da.SearchCursor(in_table = envelopes, field_names = "MP_HELPER")))

    ## for each oid
    for oid in unique_oid:
        ## create a list to hold the arrays for the geometry
        arrays = []
        ## iterate through each record that has the same MP_HELPER ID
        with arcpy.da.SearchCursor(
            in_table = envelopes,
            field_names = ["MP_HELPER", "SHAPE@"],
            where_clause = "MP_HELPER = {0}".format(oid)
        ) as cursor:
            for row in cursor:
                ## access the geometry
                geometry = row[1]
                ## create an Array object
                array = arcpy.Array()
                ## add all the points for each part to the array
                for part in geometry:
                    for point in part:
                        array.add(point)
                ## add that array to our array list
                arrays.append(array)

        ## create the dictionary entry for the oid, the value is the Polygon geometry
        ## that creates the multipart
        poly_dict[oid] = arcpy.Polygon(arcpy.Array(arrays))

    ####################################################################################
    ## APPLY THE MULTIPART GEOMETRIES TO THE RECORDS IN THE MEMORY FEATURE CLASS

    ## get the ORIG_OID field for the memory_fc
    ## this could differ from the in_features
    orig_fld = [fld.name for fld in arcpy.ListFields(dataset = memory_fc) if fld.name=="ORIG_OID"][0]

    ## use the UpdateCursor to update the geometry for each record
    with arcpy.da.UpdateCursor(
        in_table = memory_fc,
        field_names = [orig_fld, "SHAPE@"]
    ) as cursor:
        for row in cursor:
            row[1] = poly_dict[row[0]]
            cursor.updateRow(row)

    ## no need for our ORIG_OID field to remain...unless you want it to.
    arcpy.management.DeleteField(
        in_table = memory_fc,
        drop_field = "ORIG_OID"
    )

    ####################################################################################
    ## EXPORT FROM MEMORY TO DISK

    ## save to disk
    arcpy.conversion.ExportFeatures(
        in_features = memory_fc,
        out_features = out_feature_class
)
    ####################################################################################
    ## CLEAN-UP the MEMORY WORKSPACE

    ## clean up memory workspace.
    arcpy.management.Delete(
        in_data = memory_fc
    )

########################################################################################