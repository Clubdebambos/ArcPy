import arcpy

########################################################################################
## ESRI Documentation:
##  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/editing/erase-point.html
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/functions/getparameter.html
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/functions/getparameterastext.html
##  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/data-management/select-layer-by-location.html
##  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/data-management/delete-features.html
##
## Original tool syntax:
##     arcpy.edit.ErasePoint(in_features, remove_features, {operation_type})
##
########################################################################################

## 🤗 Support content creation 👉 https://buymeacoffee.com/glenbambrick

########################################################################################
## USER INPUTS #########################################################################

## input feature class (point)
in_features = arcpy.GetParameter(0)

## othe polygon features
remove_features = arcpy.GetParameter(1)

## delete INSIDE or OUTSIDE of the polygons
operation_type = arcpy.GetParameterAsText(2)

########################################################################################
## TOOL OBJECT REQUIREMENTS ############################################################

## set the invert_spatial_relationship parameter in SelectLayerByLocation based on input
operation_dict = {
    "INSIDE" : "NOT_INVERT",
    "OUTSIDE" : "INVERT"
}

########################################################################################
## DELETE FEATURES #####################################################################

## select the points to delete
arcpy.management.SelectLayerByLocation(
    in_layer = in_features,
    overlap_type = "INTERSECT",
    select_features = remove_features,
    invert_spatial_relationship = operation_dict[operation_type]

)

## delete the points
arcpy.management.DeleteFeatures(
    in_features = in_features
)

########################################################################################