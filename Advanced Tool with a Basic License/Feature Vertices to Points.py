import arcpy

########################################################################################
## ESRI Documentation:
##  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/data-management/feature-vertices-to-points.html?tabs=dialog
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/functions/getparameterastext.html
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/data-access/describe.html
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/functions/listfields.html
##  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/data-management/multipart-to-singlepart.html?tabs=python
##  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/data-management/calculate-geometry-attributes.html?tabs=python
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/data-access/searchcursor-class.html
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/classes/polyline.html
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/classes/pointgeometry.html
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/classes/point.html
##  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/data-management/create-feature-class.html?tabs=python
##  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/analysis/spatial-join.html?tabs=python
##  https://doc.esri.com/en/arcgis-pro/latest/help/analysis/geoprocessing/basics/the-in-memory-workspace.html
##  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/data-management/add-field.html?tabs=python
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/data-access/insertcursor-class.html
##  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/conversion/export-features.html?tabs=python
##  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/data-management/delete.html?tabs=python
##
## Original tool syntax:
##     arcpy.management.FeatureVerticesToPoints(in_features, out_feature_class, {point_location})
##
##
########################################################################################

## 🤗 Support content creation 👉 https://buymeacoffee.com/glenbambrick

########################################################################################
## USER INPUTS #########################################################################

## input fc (linear or polygon)
in_features = arcpy.GetParameterAsText(0)

## output point feature class
out_feature_class = arcpy.GetParameterAsText(1)

## ALL, MID, START, END, BOTH_ENDS, DANGLE (lines only)
point_location = arcpy.GetParameterAsText(2)

########################################################################################
## TOOL OBJECT REQUIREMENTS ############################################################

## ## srs id of the in_features so we can assign the output the same
srs_id = arcpy.da.Describe(in_features)["spatialReference"].factoryCode

## this list will hold the names of the input fields in order
in_fld_names = [
    fld.name for fld
    in arcpy.ListFields(
        dataset = in_features
    ) if fld.type not in ("Blob","Geometry","GlobalID","Guid","OID","Raster")
]

## add field for accessing geometry
in_fld_names.append("SHAPE@")

## remove Shape_Length
if "Shape_Length" in in_fld_names:
    in_fld_names.remove("Shape_Length")

## we need the OID field for the ORIG_ID output_field
oid_fld = [
    fld.name for fld
    in arcpy.ListFields(
        dataset = in_features
    ) if fld.type=="OID"
][0]

in_fld_names.insert(0, oid_fld)

## this list will hold the details for every point to be added to the
## output feature class for attributes and geometry
point_lst = []

########################################################################################
## FUNCTIONS ###########################################################################

def get_start_end_mid_points(record_atts, geometry, to_return):
    """
    Get the start, end, or mid point of a linear feature and return as a row
    containing the attributes of the original linear feature with a new point
    geometry.

    args:
        record      a row from a GeoDataFrame as a dictionary
        to_return   the point location to return, START, END, MID


    return:
        new_record  a dictionary containing attributes and geometry as keys
    """

    if to_return == "START":
        x, y = geometry.firstPoint.X, geometry.firstPoint.Y
        z, m = geometry.firstPoint.Z, geometry.firstPoint.M
        record_atts.append(arcpy.PointGeometry(arcpy.Point(x, y, z, m)))

    elif to_return == "END":
        x, y = geometry.lastPoint.X, geometry.lastPoint.Y
        z, m = geometry.lastPoint.Z, geometry.lastPoint.M
        record_atts.append(arcpy.PointGeometry(arcpy.Point(x, y, z, m)))

    elif to_return == "MID":
        midpoint = geometry.positionAlongLine(0.50,True)
        record_atts.append(midpoint)

    return record_atts

########################################################################################
## GET VERTICES ########################################################################

## if the point_location is not ALL, then we will explode multipart to singlepart
if point_location != "ALL":
    ## explode multipart to singlepart geometry
    single_lines_fc = arcpy.management.MultipartToSinglepart(
        in_features = in_features,
        out_feature_class = "memory\\single"
    )

    in_fld_names[0] = "ORIG_FID"

    if point_location == "DANGLE":
        single_lines_fc = arcpy.management.CalculateGeometryAttributes(
            in_features = single_lines_fc,
            geometry_property = "DANGLE_LEN LENGTH"
        )

## if the point_location is ALL ########################################################

if point_location == "ALL":
    ## interate through each record in the in_features
    with arcpy.da.SearchCursor(
        in_table = in_features,
        field_names = in_fld_names,
        explode_to_points = True
    ) as cursor:
        ## for each feature/record
        for row in cursor:
            ## append the row into the point_lst as a list
            point_lst.append(list(row))

## if the point location is MID, START, END ############################################

elif point_location in ("MID", "START", "END"):
    ## interate through each record in the in_features
    with arcpy.da.SearchCursor(
        in_table = single_lines_fc,
        field_names = in_fld_names
    ) as cursor:
        ## for each feature/record
        for row in cursor:
            geom = row[-1]
            row_attributes = list(row[0:-1])
            row_attributes = get_start_end_mid_points(row_attributes, geom, point_location)
            point_lst.append(row_attributes)

## if the point location is BOTH_ENDS ##################################################

elif point_location == "BOTH_ENDS":
    ## interate through each record in the in_features
    with arcpy.da.SearchCursor(
        in_table = single_lines_fc,
        field_names = in_fld_names
    ) as cursor:
        ## for each feature/record
        for row in cursor:
            for end in ("START", "END"):
                geom = row[-1]
                row_attributes = list(row[0:-1])
                row_attributes = get_start_end_mid_points(row_attributes, geom, end)
                point_lst.append(row_attributes)

## if the point location is DANGLE #####################################################

elif point_location == "DANGLE":
    ## a dangle will only be a start or end point.
    possible_dangles = []

    ## interate through each record in the in_features
    with arcpy.da.SearchCursor(
        in_table = single_lines_fc,
        field_names = "SHAPE@"
    ) as cursor:
        ## for each feature/record
        for row in cursor:
            geom = row[0]

            ## get start and end points
            get_start_end_mid_points(possible_dangles, geom, "START")
            get_start_end_mid_points(possible_dangles, geom, "END")

    ## spatial join between points and lines
    sj = arcpy.analysis.SpatialJoin(
        target_features = possible_dangles,
        join_features = single_lines_fc,
        out_feature_class = "memory\\sj",
        join_operation = "JOIN_ONE_TO_ONE",
        join_type = "KEEP_ALL",
        match_option="INTERSECT",
        search_radius="0.01 Meters"
    )

    ## add the field name for DANGLE_LEN
    in_fld_names.append("DANGLE_LEN")

    ## iterate through the spatial join where Join_Count is equal to 1
    ## if count is greater than 1 the point connects to more than one line
    ## and is therefore not a dangle
    with arcpy.da.SearchCursor(
        in_table = sj, field_names = in_fld_names,
        where_clause = "Join_Count = 1"
    ) as cursor:
        for row in cursor:
            ## add list to the point_lst
            point_lst.append(list(row))

    ## delete the sj, it is no longer needed
    arcpy.management.Delete(sj)

########################################################################################
## CREATE OUPUT FEATURE CLASS ##########################################################

## create a temp point feature class in the memory workspace
temp_fc = arcpy.management.CreateFeatureclass(
    out_path = "memory",
    out_name = "temp_vertices",
    geometry_type = "POINT",
    template = in_features,
    has_m = "SAME_AS_TEMPLATE",
    has_z = "SAME_AS_TEMPLATE",
    spatial_reference = srs_id
)

########################################################################################
## CREATE OUPUT FEATURE CLASS SCHEMA ###################################################

## add the ORIG_FID field
arcpy.management.AddField(
    in_table = temp_fc,
    field_name = "ORIG_FID",
    field_type="LONG",
    field_is_nullable="NULLABLE"
)

if point_location == "DANGLE":
    ## replace TARTGET_FID
    in_fld_names[-1] = "DANGLE_LEN"
    arcpy.management.AddField(
        in_table = temp_fc,
        field_name = "DANGLE_LEN",
        field_type = "DOUBLE",
        field_is_nullable = "NULLABLE"
    )

if point_location == "ALL":
    ## remove the OID field from in_fld_names
    ## add in the ORIG_FID field name to the in_fld_names list
    in_fld_names[0] = "ORIG_FID"

########################################################################################
## INSERT THE DATA #####################################################################

## inject point record into the output feature class.
with arcpy.da.InsertCursor(
    in_table = temp_fc,
    field_names = in_fld_names
) as i_cursor:
    for attributes in point_lst:
        i_cursor.insertRow(attributes)

########################################################################################
## WRITE TO DISK #######################################################################

arcpy.conversion.ExportFeatures(
    in_features = temp_fc,
    out_features = out_feature_class
)

########################################################################################
## CLEAN UP ############################################################################

if point_location != "ALL":
    arcpy.management.Delete(
        in_data = single_lines_fc
    )

arcpy.management.Delete(
    in_data = temp_fc
)

########################################################################################