import arcpy

########################################################################################
## Esri Documentation
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/functions/getparameter.html
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/functions/getparameterastext.html
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/functions/listfields.html
##  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/data-management/create-feature-class.html?tabs=python
##  https://doc.esri.com/en/arcgis-pro/latest/help/analysis/geoprocessing/basics/the-in-memory-workspace.html
##  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/data-management/add-field.html?tabs=python
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/data-access/searchcursor-class.html
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/data-access/insertcursor-class.html
##  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/conversion/export-features.html?tabs=python
##  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/data-management/delete-field.html?tabs=python
##  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/data-management/delete.html?tabs=python
##
########################################################################################

## Watch the video: https://youtu.be/P5hBuO6rp24

## 🤗 Support content creation 👉 https://buymeacoffee.com/glenbambrick

########################################################################################
## USER INPUTS #########################################################################

## the point features to create the rectangle buffers from
input_point_features = arcpy.GetParameterAsText(0)

## the output polygon feature class
output_feature_class = arcpy.GetParameterAsText(1)

## boolean, if true use field attributes
use_fields = arcpy.GetParameter(2)

## the width of the buffer
buffer_width = arcpy.GetParameter(3)

## the height of the buffer
buffer_height = arcpy.GetParameter(4)

## the field name that contains the width values
width_field = arcpy.GetParameterAsText(5)

## the field name that contains the height values
heigth_field = arcpy.GetParameterAsText(6)

## Boolean whether to transfer attributes to the rectangle
transfer_attributes = arcpy.GetParameter(7)

## the fields to transfer
fields = arcpy.GetParameterAsText(8)

########################################################################################
## REQUIRED OBJECTS ####################################################################

## spatial Reference for output same as input points
srs = arcpy.da.Describe(input_point_features)["spatialReference"]

## the oid name from the input points feature class
oid_fld = [fld.name for fld in arcpy.ListFields(dataset=input_point_features) if fld.type=="OID"][0]

## if the user is using field attributes for width and height we need this
## dictionary of oid : (width, height)
if width_field and heigth_field:
    wh_dict = {
        row[0] : (row[1], row[2])
        for row in arcpy.da.SearchCursor(
            in_table = input_point_features,
            field_names = [oid_fld, width_field, heigth_field]
        )
    }

## the fields to transfer to the output from the input
in_field_list = [oid_fld] + fields.split(";") + ["SHAPE@XY"]

## the fields for the insert cursor
out_field_list = ["ORIG_FID"] + fields.split(";") + ["SHAPE@"]

########################################################################################
## CREATE MEMORY FEATURE CLASS #########################################################

## if the user is transferring fields
if fields:
    temp_ply_fc = arcpy.management.CreateFeatureclass(
        out_path = "memory",
        out_name = "temp_ply_fc",
        geometry_type = "POLYGON",
        template = input_point_features,
        spatial_reference = srs
    )

    arcpy.management.DeleteField(
        in_table = temp_ply_fc,
        drop_field = fields.split(";"),
        method = "KEEP_FIELDS"
    )

## otherwise
else:
    temp_ply_fc = arcpy.management.CreateFeatureclass(
        out_path = "memory",
        out_name = "temp_ply_fc",
        geometry_type = "POLYGON",
        spatial_reference = srs
    )

    in_field_list.remove("")
    out_field_list.remove("")

########################################################################################
## ADD THE ORIG_FID FIELD ##############################################################

arcpy.management.AddField(
    in_table = temp_ply_fc,
    field_name = "ORIG_FID",
    field_type = "LONG",
    field_is_nullable = "NULLABLE"
)

########################################################################################
## CREATE POLYGONS #####################################################################

## use a SearchCursor to iterate over the point features
with arcpy.da.SearchCursor(
    in_table = input_point_features,
    field_names = in_field_list
) as s_cursor:
    ## use an InsertCursor to insert records to the memory feature class
     with arcpy.da.InsertCursor(
        in_table = temp_ply_fc,
        field_names = out_field_list
     ) as i_cursor:
        ## for each row (point) in the SearchCursor
        for row in s_cursor:
            ## get the X and Y coord values
            x,y = row[-1]

            ## half dimensions (easier for calculations)
            if buffer_width and buffer_height:
                half_width = buffer_width / 2.0
                half_height = buffer_height / 2.0

            else:
                half_width = wh_dict[row[0]][0] / 2.0
                half_height = wh_dict[row[0]][1] / 2.0

            ## contstruct the Array of Points that represent the rectangle
            rectangle = arcpy.Array([
                arcpy.Point(x - half_width, y - half_height), # xmin ymin
                arcpy.Point(x - half_width, y + half_height), # xmin ymax
                arcpy.Point(x + half_width, y + half_height), # xmax ymax
                arcpy.Point(x + half_width, y - half_height), # xmax ymin
                arcpy.Point(x - half_width, y - half_height)  # closed polygon
            ])

            ## create the Polygon geometry object
            polygon = arcpy.Polygon(
                inputs = rectangle,
                spatial_reference = srs
            )

            insert_feature = list(row[0:-1]) + [polygon]

            ## insert the row into the polygon feature class
            i_cursor.insertRow(insert_feature)

########################################################################################
## SAVE TO DISK ########################################################################

arcpy.conversion.ExportFeatures(
    in_features = temp_ply_fc,
    out_features = output_feature_class
)

########################################################################################
## CLEANUP MEMORY WORKSPACE ############################################################

arcpy.management.Delete(
    in_data = temp_ply_fc
)

########################################################################################