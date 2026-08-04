import arcpy

########################################################################################
## Esri Documentation
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/functions/getparameterastext.html
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/data-access/describe.html
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/functions/listfields.html
##  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/data-management/add-field.html?tabs=python
##  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/data-management/create-feature-class.html?tabs=python
##  https://doc.esri.com/en/arcgis-pro/latest/help/analysis/geoprocessing/basics/the-in-memory-workspace.html
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/data-access/searchcursor-class.html
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/data-access/updatecursor-class.html
##  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/conversion/export-features.html?tabs=python
##  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/data-management/delete.html?tabs=python
##
#########################################################################################

## Watch the video: https://youtu.be/CU5gvV_Uc-w

## 🤗 Support content creation 👉 https://buymeacoffee.com/glenbambrick

#########################################################################################
## USER INPUTS

## input linear feature class
in_features = arcpy.GetParameterAsText(0)

## the output linear feature class to create
out_feature_class = arcpy.GetParameterAsText(1)

## how many line segments to chop the line up into
num_features = arcpy.GetParameter(2)

########################################################################################
## REQUIRED OBJECTS

## srs id of the in_features so we can assign the output the same
srs_id = arcpy.da.Describe(in_features)["spatialReference"].factoryCode

## we need the OID field for the ORIG_ID output_field
oid_fld = [
    fld.name for fld
    in arcpy.ListFields(
        dataset = in_features
    ) if fld.type=="OID"
][0]

## this list will hold the names of the input fields in order
in_fld_names = [
    fld.name for fld
    in arcpy.ListFields(
        dataset = in_features
    ) if fld.type not in ("Blob","Geometry","GlobalID","Guid","OID","Raster")
]

## remove Shape_Length
if "Shape_Length" in in_fld_names:
    in_fld_names.remove("Shape_Length")

## the field names for the output feature class
## this will be used in an InsertCursor as we create our output lines
out_fld_names = list(in_fld_names) + ["SHAPE@"]

## this will be used in a SearchCursor as we iterate over the
## original input lines
in_fld_names = [oid_fld] + in_fld_names + ["SHAPE@"]

########################################################################################
## CREATE TEMP POLYLINE FEATURE CLASS IN MEMORY ########################################

## in memory feature class to hold the split lines
temp_fc = arcpy.management.CreateFeatureclass(
    out_path = "memory",
    out_name = "temp_fc",
    geometry_type = "POLYLINE",
    template = in_features,
    has_m = "SAME_AS_TEMPLATE",
    has_z = "SAME_AS_TEMPLATE",
    spatial_reference = srs_id
)

## add the ORIG_FID field
arcpy.management.AddField(
    in_table = temp_fc,
    field_name = "ORIG_FID",
    field_type="LONG",
    field_is_nullable="NULLABLE"
)

## add the ORIG_SEQ field
arcpy.management.AddField(
    in_table = temp_fc,
    field_name = "ORIG_SEQ",
    field_type="LONG",
    field_is_nullable="NULLABLE"
)

## adjust our in_fld_names list to account for the added fields.
out_fld_names = ["ORIG_FID"] + out_fld_names + ["ORIG_SEQ"]

########################################################################################
## SEGMENT LINES #######################################################################

## insert records with an insert cursor
with arcpy.da.InsertCursor(
    in_table = temp_fc,
    field_names = out_fld_names
) as u_cursor:
    ## iterate over every line in the feature class
    with arcpy.da.SearchCursor(
        in_table = in_features,
        field_names = in_fld_names
    ) as s_cursor:
        ## for each line
        for row in s_cursor:
            ## get the line segments
            ## thanks to ArcPy Cafe for this line of code
            ## https://arcpy.wordpress.com/2014/10/30/split-into-equal-length-features/
            segments = [
                row[-1].segmentAlongLine(
                    start_measure = i/num_features,
                    end_measure = (i+1)/num_features,
                    use_percentage = True
                ) for i in range(0, num_features)
            ]

            ## for each segment
            for seq_id, segment in enumerate(segments, 1):
                ## get the original attributes and remove the geometry
                ## add in the new segment geometry and the ORIG_SEQ
                record = list(row[:-1]) + [segment, seq_id]
                ## add the record for that segment.
                u_cursor.insertRow(record)

########################################################################################
## SAVE TO DISK ########################################################################

arcpy.conversion.ExportFeatures(
    in_features = temp_fc,
    out_features = out_feature_class
)

########################################################################################
## CLEAN-UP MEMORY WORKSPACE ###########################################################

arcpy.management.Delete(
    in_data = temp_fc
)

########################################################################################