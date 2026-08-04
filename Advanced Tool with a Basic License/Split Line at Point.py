import arcpy

########################################################################################
## Esri Documentation:
##  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/data-management/split-line-at-point.htm
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/functions/getparameterastext.html
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/data-access/describe.html
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/functions/listfields.html
##  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/analysis/generate-near-table.html?tabs=python
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/data-access/searchcursor-class.html
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/classes/pointgeometry.html
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/classes/point.html
##  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/data-management/create-feature-class.html?tabs=python
##  https://doc.esri.com/en/arcgis-pro/latest/help/analysis/geoprocessing/basics/the-in-memory-workspace.html
##  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/data-management/add-field.html?tabs=python
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/data-access/insertcursor-class.html
##  https://pro.arcgis.com/en/pro-app/latest/tool-reference/conversion/export-features.htm
##  https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/delete.htm
##
## Original tool syntax:
##      arcpy.management.SplitLineAtPoint(in_features, point_features, out_feature_class, {search_radius})
##
########################################################################################

## 🤗 Support content creation 👉 https://buymeacoffee.com/glenbambrick

########################################################################################
## USER INPUTS #########################################################################

## Linear feature class to split
in_features = arcpy.GetParameterAsText(0)

## the point feature class to split the lines by
point_features = arcpy.GetParameterAsText(1)

## output workspace; gdb or folder for shapefile
out_feature_class = arcpy.GetParameterAsText(2)

## snap points within distance to closest point on the line
search_radius = arcpy.GetParameterAsText(3)

########################################################################################
## TOOL OBJECT REQUIREMENTS ############################################################

## srs id of the in_features to assign the same to the output
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

## insert the oid field name at the start of the in_fld_names list
in_fld_names.insert(0, oid_fld)

## this will hold information for all line segments to create
## it will be a list of lists containing attributes and geometry
segments_lst = []

## dictionary to hold the key: OID, value: vertice points for each line.
points_dict = {}

########################################################################################
## NEAR TABLE ##########################################################################

## if no search_radius set we are interested in only one point, that is the point
## that is closest to the line
if not search_radius:
    near_tbl = arcpy.analysis.GenerateNearTable(
        in_features = in_features,
        near_features = point_features,
        out_table = "memory\\near_tbl",
        location = "LOCATION",
        closest="CLOSEST"
    )

## otherwise we want all points found within the search_radius for each line.
else:
    near_tbl = arcpy.analysis.GenerateNearTable(
        in_features = in_features,
        near_features = point_features,
        out_table = "memory\\near_tbl",
        search_radius = search_radius,
        location = "LOCATION",
        closest="ALL"
    )

## for each near table entry
with arcpy.da.SearchCursor(
    in_table = near_tbl,
    field_names = ["IN_FID", "FROM_X", "FROM_Y"]
) as cursor:
    for row in cursor:
        ## if the IN_FID (linear) not in the dictionary add it with a list
        if row[0] not in points_dict:
            points_dict[row[0]] = [arcpy.PointGeometry(arcpy.Point(X = row[1], Y = row[2]))]

        ## if it is in the dictionary add to the list of points asscoiated to the line
        else:
            points_dict[row[0]] = points_dict[row[0]] + [arcpy.PointGeometry(arcpy.Point(X = row[1], Y = row[2]))]

########################################################################################
## SPLIT LINES #########################################################################

## search through each linear record
with arcpy.da.SearchCursor(in_features, in_fld_names) as ln_cursor:
    for ln in ln_cursor:

        ## get the start point of the line
        first_ln_xy = (ln[-1].firstPoint.X, ln[-1].firstPoint.Y)

        ## some lines may not have a closest point
        try:
            pt_sel = points_dict[ln[0]]

            ## will hold a list of distances points are along a line to help
            ## chop up a line in order
            distances = []

            ## for each PointGeometry in the list
            for pt in pt_sel:
                ## get the X,Y of the point
                pt_xy = (pt.centroid.X, pt.centroid.Y)

                ## if the point is a start; do nothing
                if  pt_xy == first_ln_xy:
                    pass

                ## otherwise, lets get the distance along the line for each point
                ## and append the distance to the list.
                else:
                    distance = ln[-1].queryPointAndDistance(pt)[1]
                    distances.append(distance)

            ## acount that we need the last segment to the end point
            end_pt = arcpy.PointGeometry(
                X = arcpy.Point(ln[-1].lastPoint.X,
                Y = ln[-1].lastPoint.Y)
            )

            ## distance to end point
            distance = ln[-1].queryPointAndDistance(end_pt)[1]

            ## append to distance list
            distances.append(distance)

            ## 0.0 is the start of the line
            start_dist = 0.0

            ## sequence number per split segment of each line
            ## the sequence number is added to the output as per Esri documentation
            seq_num = 1

            ## iterate through a sorted list of distances
            ## and cut the line at each distance from the start distance
            ## the start distance becomes the current distance for each iteration
            for distance in sorted(distances):
                segment = ln[-1].segmentAlongLine(start_dist, distance)
                ## if segment has no length move on to the next line, we have hit the end
                if segment.getLength('PLANAR', 'METERS') == 0.0:
                    continue
                else:
                    start_dist = distance
                    ## the attributes from the original line
                    segment_attributes = list(ln[0:-1])
                    ## the segment geometry
                    segment_attributes.append(segment)
                    ## the sequence number of the segment for this line
                    segment_attributes.append(seq_num)
                    ## append the info above into our segments list
                    segments_lst.append(segment_attributes)
                    ## increase the sequence number for the next segment
                    seq_num += 1

        ## handle with a KeyError rexception
        except KeyError:
            ## get the attributes/shape for the entire line
            segment_attributes = list(ln)
            ## it will have an ORIG_SEQ of 1
            segment_attributes.append(1)
            ## apend the information to the segments list.
            segments_lst.append(segment_attributes)

########################################################################################
## CREATE OUPUT FEATURE CLASS ##########################################################

## create a linear feature class based from a template of teh original input
temp_fc = arcpy.management.CreateFeatureclass(
    out_path = "memory",
    out_name = "temp_lines",
    geometry_type = "POLYLINE",
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
    field_type = "LONG",
    field_is_nullable = "NULLABLE"
)

## add the ORIG_SEQ field
arcpy.management.AddField(
    in_table = temp_fc,
    field_name = "ORIG_SEQ",
    field_type = "LONG",
    field_is_nullable = "NULLABLE"
)

## adjust our in_fld_names list to account for the added fields.
## and remove the OID field.
in_fld_names.remove(oid_fld)
in_fld_names.insert(0, "ORIG_FID")
in_fld_names.append("ORIG_SEQ")

########################################################################################
## INSERT THE DATA #####################################################################

with arcpy.da.InsertCursor(
    in_table = temp_fc,
    field_names = in_fld_names
) as i_cursor:
    for attributes in segments_lst:
        i_cursor.insertRow(attributes)

########################################################################################
## WRITE TO DISK #######################################################################

arcpy.conversion.ExportFeatures(
    in_features = temp_fc,
    out_features = out_feature_class
)

########################################################################################
## CLEAN UP ############################################################################

arcpy.management.Delete(
    in_data = [temp_fc, near_tbl]
)

########################################################################################
