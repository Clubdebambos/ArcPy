import arcpy

########################################################################################
## Esri Documentation:
##  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/data-management/polygon-to-line.html?tabs=dialog
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/functions/getparameterastext.html
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/data-access/describe.html
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/functions/listfields.html
##  https://pro.arcgis.com/en/pro-app/latest/arcpy/data-access/searchcursor-class.htm
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/classes/array.html
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/classes/polyline.html
##  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/data-management/create-feature-class.html?tabs=python
##  https://doc.esri.com/en/arcgis-pro/latest/help/analysis/geoprocessing/basics/the-in-memory-workspace.html
##  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/data-management/add-field.html?tabs=python
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/data-access/insertcursor-class.html
##  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/conversion/export-features.html?tabs=python
##  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/data-management/delete.html?tabs=python
##
## Original tool syntax:
##     arcpy.management.PolygonToLine(in_features, out_feature_class, {neighbor_option})
##
##  neighbor_option not accounted for in this tool.
##
########################################################################################

########################################################################################
## USER INPUTS #########################################################################

## polygon featurer class to convert boundaries to lines
in_features = arcpy.GetParameterAsText(0)

## output feature class filepath
out_feature_class = arcpy.GetParameterAsText(1)

########################################################################################
## TOOL OBJECT REQUIREMENTS ############################################################

## srs id of the in_features, this will be the srs for the out_feature_class
srs_id = arcpy.da.Describe(in_features)["spatialReference"].factoryCode

## this list will hold the names of the input fields in order
in_fld_names = [
    fld.name for fld
    in arcpy.ListFields(
        dataset = in_features
    ) if fld.type != "OID"
]

## we need the OID field to be able to create the ORIG_FID field in the output
oid_fld = [
    fld.name for fld
    in arcpy.ListFields(
        dataset = in_features
    ) if fld.type=="OID"
][0]

in_fld_names.insert(0, oid_fld)

## remove Shape_Length
if "Shape_Length" in in_fld_names:
    in_fld_names.remove("Shape_Length")

## add field for accessing geometry
in_fld_names.append("SHAPE@")

## create a copy of the in_fld_name for the out_feature_class
out_fld_names = list(in_fld_names)
out_fld_names[0] = "ORIG_FID"

########################################################################################
## CREATE OUPUT FEATURE CLASS ##########################################################

## create a temporary linear feature class in the memory workspace.
temp_fc = arcpy.management.CreateFeatureclass(
    out_path = "memory",
    out_name = "temp_vertices",
    geometry_type = "POLYLINE",
    template = in_features,
    has_m = "SAME_AS_TEMPLATE",
    has_z = "SAME_AS_TEMPLATE",
    spatial_reference = srs_id
)

## add field for ORIG_FID
arcpy.management.AddField(
    in_table = temp_fc,
    field_name = "ORIG_FID",
    field_type = "LONG",
    field_is_nullable="NULLABLE"
)

########################################################################################
## PROCESS POLYGONS TO LINES ###########################################################

## use a search cursor to iterate through the polygons
with arcpy.da.SearchCursor(
    in_table = in_features,
    field_names = in_fld_names
) as s_cursor:
    ## use an insert cursor to insect the linear features into the temp_fc
    with arcpy.da.InsertCursor(
        in_table = temp_fc,
        field_names = out_fld_names
    ) as i_cursor:
        ## for each record in the polygon feature class
        for row in s_cursor:
            ## get all attributes, less the geometry as a list
            row_attributes = list(row[0:-1])

            ## create a list to hold all polylines that make up the
            ## polygon boundary
            polyline_list = []

            ## for each port in the polygon geometry
            for index, part in enumerate(row[-1]):
                ## at the part to the polyline_lst
                polyline_list.append(row[-1].getPart(index))

            ## create an arcpy Array from the polyline_lst
            pl_array = arcpy.Array(polyline_list)
            ## append the Polyline to the attributes
            row_attributes.append(arcpy.Polyline(pl_array))

            ## insert the record, attributes and linear geometry to the temp_fc
            i_cursor.insertRow(row_attributes)

########################################################################################
## WRITE TO DISK #######################################################################

## write the temp_fc to disk
arcpy.conversion.ExportFeatures(
    in_features = temp_fc,
    out_features = out_feature_class
)

########################################################################################
## CLEAN UP ############################################################################

## clean us the memory workspace
arcpy.Delete_management(
    in_data = temp_fc
)

########################################################################################