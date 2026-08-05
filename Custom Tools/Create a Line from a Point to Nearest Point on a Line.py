import arcpy

################################################################################
## Esri Documentation
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/functions/getparameterastext.html
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/data-access/describe.html
##  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/analysis/generate-near-table.html?tabs=python
##  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/data-management/xy-to-line.html?tabs=python
##  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/data-management/delete.html?tabs=python
##  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/conversion/export-features.html?tabs=python
##  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/data-management/append.html?tabs=python
##
########################################################################################

## Watch the video: https://youtu.be/aUkBugB5LS8

## 🤗 Support content creation 👉 https://buymeacoffee.com/glenbambrick

########################################################################################
## USER INPUTS

## input point feature class
pt_features = arcpy.GetParameterAsText(0)

## input linear feature class
ln_features = arcpy.GetParameterAsText(1)

## maximum distance to consider
max_distance = arcpy.GetParameterAsText(2)

## Create a new linear feature class or not
create_new_fc = arcpy.GetParameterAsText(3)

## the output feature class if creating a new one
out_feature_class = arcpy.GetParameterAsText(4)

########################################################################################
## REQUIRED OBJECTS ####################################################################

## srs id of the in_features so we can assign the output the same
srs_id = arcpy.da.Describe(ln_features)["spatialReference"].factoryCode

########################################################################################
## GENERATE NEAR TABLE #################################################################

near_tbl = arcpy.analysis.GenerateNearTable(
    in_features = pt_features,
    near_features = ln_features,
    out_table = "memory\\near_tbl",
    search_radius = max_distance,
    location = "LOCATION",
    angle = "NO_ANGLE",
    closest = "CLOSEST",
    closest_count = 0,
    method = "PLANAR"
)

########################################################################################
## CREATE LINES ########################################################################

near_lines = arcpy.management.XYToLine(
    in_table = near_tbl,
    out_featureclass = "memory\\near_lines",
    startx_field = "FROM_X",
    starty_field = "FROM_Y",
    endx_field = "NEAR_X",
    endy_field = "NEAR_Y",
    line_type = "GEODESIC",
    id_field = "NEAR_FID",
    spatial_reference = srs_id,
    attributes="NO_ATTRIBUTES"
)

########################################################################################
## CLEANUP MEMORY ######################################################################

arcpy.management.Delete(
    in_data = near_tbl
)

########################################################################################
## CREATE OUPUT FEATURE CLASS ##########################################################

if create_new_fc == "true":
    arcpy.conversion.ExportFeatures(
        in_features = near_lines,
        out_features = out_feature_class
    )

########################################################################################
## OR APPEND TO ORIGINAL LINEAR FEATURE CLASS ##########################################

else:
    arcpy.management.Append(
        inputs=near_lines,
        target=ln_features,
        schema_type="NO_TEST"
    )

########################################################################################
## CLEANUP MEMORY ######################################################################

arcpy.management.Delete(
    in_data = near_lines
)

########################################################################################