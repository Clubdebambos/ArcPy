import arcpy
from collections import Counter

########################################################################################
## Esri Documentation
##  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/analysis/pairwise-intersect.html?tabs=python
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/functions/getparameterastext.html
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/functions/listfields.html
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/data-access/searchcursor-class.html
##  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/data-management/select-layer-by-attribute.html?tabs=python
##  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/data-management/delete.html?tabs=python
##  https://doc.esri.com/en/arcgis-pro/latest/help/analysis/geoprocessing/basics/the-in-memory-workspace.html
##
########################################################################################

## Watch the video: https://youtu.be/iOl2Kbf-CEA

## 🤗 Support content creation 👉 https://buymeacoffee.com/glenbambrick

########################################################################################
## USER INPUT ##########################################################################

## the input points feature class
point_fc = arcpy.GetParameterAsText(0)

## the input polygon feature class
polygon_fc = arcpy.GetParameterAsText(1)

## the points must intersect this amount of polygons
num_or_more = arcpy.GetParameterAsText(2)

########################################################################################
## REQUIRED OBJECTS ####################################################################

## oid field for the point feature class
oid_field = [
    fld.name for fld
    in arcpy.ListFields(
        dataset = point_fc
    ) if fld.type == "OID"
][0]

########################################################################################
## PERFORM THE INTERSECTION ############################################################

## use the Analysis toolbox Pairwise Interset geoprocessing tool.
## use the memorey workspace.
intersect_fc = arcpy.analysis.PairwiseIntersect(
    in_features = [point_fc, polygon_fc],
    out_feature_class = "memory/intersect_fc",
    join_attributes = "ONLY_FID",
    cluster_tolerance = None,
    output_type = "POINT"
)

########################################################################################
## GET OIDS FOR SELECTION ##############################################################

## all OIDs that intersected polygons
oid_list = [
    row[2] for row
    in arcpy.da.SearchCursor(
        in_table = intersect_fc,
        field_names = "*")
    ]

## count multiple
counts = Counter(oid_list)

## if the count of the individual OID is equal to or greater than required
selection_oids = {oid for oid in oid_list if counts[oid] >= int(num_or_more)}

########################################################################################
## SELECT FEATURES IN THE MAP ##########################################################

if selection_oids:
    ## craete a where clause
    sql_exp = "{0} IN ({1})".format(oid_field, ",".join([str(oid) for oid in selection_oids]))

    ## select by attribute using where clause
    arcpy.management.SelectLayerByAttribute(
        in_layer_or_view = point_fc,
        selection_type = "NEW_SELECTION",
        where_clause = sql_exp
    )

else:
    arcpy.AddWarning("No point met the criteria")

########################################################################################
## MEMORY CLEANUP ######################################################################

arcpy.management.Delete(
    in_data = intersect_fc
)

########################################################################################