import arcpy

################################################################################
## ESRI Documentation:
##  https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/split-line-at-vertices.htm
##  https://pro.arcgis.com/en/pro-app/latest/arcpy/functions/getparameterastext.htm
##  https://pro.arcgis.com/en/pro-app/latest/arcpy/functions/describe.htm
##  https://pro.arcgis.com/en/pro-app/latest/arcpy/functions/listfields.htm
##  https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/get-count.htm
##  https://pro.arcgis.com/en/pro-app/latest/arcpy/data-access/searchcursor-class.htm
##  https://pro.arcgis.com/en/pro-app/latest/arcpy/classes/pointgeometry.htm
##  https://pro.arcgis.com/en/pro-app/latest/arcpy/classes/point.htm
##  https://pro.arcgis.com/en/pro-app/latest/arcpy/classes/polyline.htm
##  https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/create-feature-class.htm
##  https://pro.arcgis.com/en/pro-app/latest/help/analysis/geoprocessing/basics/the-in-memory-workspace.htm
##  https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/add-field.htm
##  https://pro.arcgis.com/en/pro-app/latest/arcpy/data-access/insertcursor-class.htm
##  https://pro.arcgis.com/en/pro-app/latest/tool-reference/conversion/export-features.htm
##  https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/delete.htm
##
## Syntax:
##     arcpy.management.SplitLine(in_features, out_feature_class)
##
################################################################################

################################################################################
## USER INPUTS #################################################################

## input feature class (linear)
in_features = arcpy.GetParameterAsText(0)

## output feature class filepath
out_feature_class = arcpy.GetParameterAsText(1)

################################################################################
## TOOL OBJECT REQUIREMENTS ####################################################

## srs id of the in_features so we can assign the output the same
srs_id = arcpy.Describe(
    value=in_features
).spatialReference.factoryCode

## this list will hold the names of the input fields in order
in_fld_names = [
    fld.name for fld in arcpy.ListFields(dataset=in_features)
    if fld.type not in ("Blob","Geometry","GlobalID","Guid","OID","Raster")
]

## add field for accessing geometry
in_fld_names.append("SHAPE@")

## remove Shape_Length
if "Shape_Length" in in_fld_names:
    in_fld_names.remove("Shape_Length")

## we need the OID field for the ORIG_ID output_field
oid_fld = [fld.name for fld in arcpy.ListFields(dataset=in_features) if fld.type=="OID"][0]
in_fld_names.insert(0, oid_fld)

## this will hold information for all line segments to create
## it will be a list of lists containing attributes and geometry
segments_lst = []

## dictionary to hold the key: OID, value: vertice points for each line.
vertices_dict = {}

################################################################################
## GET VERTICES ################################################################

arcpy.AddMessage("Getting vertices")

## iterate through each record in the in_features feature class.
## we are only interested in the OID field and the SHAPE@ for accessing geometry.
with arcpy.da.SearchCursor(
        in_table=in_features,
        field_names=[oid_fld, "SHAPE@"]
) as cursor:
    ## for each feature/record
    for row in cursor:
        ## this list will hold the point geometry for each vertex per OID
        points_list = []
        ## dig into each part of the geometry
        ## row[-1] is the SHAPE@ toke for accessing geometry
        for part in row[-1]:
            ## Step through each vertex in the feature
            for pnt in part:
                if pnt:
                    ## create a Point object
                    point = arcpy.Point(
                        X=pnt.X,
                        Y=pnt.Y,
                        Z=pnt.Z,
                        M=pnt.M
                    )
                    ## create a PointGeometry pbject
                    point_geom = arcpy.PointGeometry(
                        inputs=point
                    )
                    ## append the PointGeometry into the point_list for the OID
                    points_list.append(point_geom)
        ## add the OID as the key in the vertices_dict, and the list of points (vertices) as the dictionary value.
        vertices_dict[row[0]] = points_list

################################################################################
## SPLIT LINES #################################################################

arcpy.AddMessage("Splitting lines")

## iterate through each linear record from the in_features feature class.
with arcpy.da.SearchCursor(
    in_table=in_features, field_names=in_fld_names
) as ln_cursor:
    for ln in ln_cursor:
        ## get the start point of the line
        first_ln_xy = (ln[-1].firstPoint.X, ln[-1].firstPoint.Y)

        ## select points that belong to the line from the vertices dictionary
        pt_sel = vertices_dict[ln[0]]

        ## this list will hold the distances points are along a line to help
        ## chop up a line in order
        distances = []

        ## for each PointGeometry in the list
        for pt in pt_sel:
            ## get the X,Y of the point
            pt_xy = (pt.firstPoint.X, pt.firstPoint.Y)

            ## if the point is a start; do nothing
            if pt_xy == first_ln_xy:
                pass

            ## otherwise, lets get the distance along the line for each point (vertex)
            ## along the line.
            else:
                distance = ln[-1].queryPointAndDistance(
                    in_point=pt
                )[1]
                ## and append the distance to the list.
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
            segment = ln[-1].segmentAlongLine(
                start_measure=start_dist,
                end_measure=distance
            )
            ## if segment has no length move on to the next line, we have hit the end
            if segment.getLength(
                method='PLANAR',
                units='METERS'
            ) == 0.0:
                continue
            ## otherwise, lets get the attributes for the line segment.
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

################################################################################
## CREATE OUPUT FEATURE CLASS ##################################################

arcpy.AddMessage("Creating Feature Class")

## create a linear feature class in memory using the in_features as a template.
temp_fc = arcpy.management.CreateFeatureclass(
    out_path="memory",
    out_name="temp_lines",
    geometry_type="POLYLINE",
    template=in_features,
    has_m="SAME_AS_TEMPLATE",
    has_z="SAME_AS_TEMPLATE",
    spatial_reference=srs_id
)

################################################################################
## CREATE OUPUT FEATURE CLASS SCHEMA ###########################################

## add the ORIG_FID field
arcpy.management.AddField(
    in_table=temp_fc,
    field_name="ORIG_FID",
    field_type="LONG",
    field_is_nullable="NULLABLE"
)

## add the ORIG_SEQ field
arcpy.management.AddField(
    in_table=temp_fc,
    field_name="ORIG_SEQ",
    field_type="LONG",
    field_is_nullable="NULLABLE"
)

## adjust our in_fld_names list to account for the added fields.
## and remove the OID field.
in_fld_names.remove(oid_fld)
in_fld_names.insert(0, "ORIG_FID")
in_fld_names.append("ORIG_SEQ")

################################################################################
## INSERT THE DATA #############################################################

arcpy.AddMessage("Inserting data")

## use the Insert Cursor to insert one segment at a time as a record
with arcpy.da.InsertCursor(
    in_table=temp_fc,
    field_names=in_fld_names
) as i_cursor:
    for attributes in segments_lst:
        i_cursor.insertRow(attributes)

################################################################################
## WRITE TO DISK ###############################################################

arcpy.AddMessage("Writing Feature Class to disk")

arcpy.conversion.ExportFeatures(
    in_features=temp_fc,
    out_features=out_feature_class
)

################################################################################
## CLEAN UP ####################################################################

arcpy.management.Delete(in_data=temp_fc)

################################################################################
