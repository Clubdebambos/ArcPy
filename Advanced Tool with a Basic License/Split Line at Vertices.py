import arcpy

########################################################################################
## ESRI Documentation:
##  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/data-management/split-line-at-vertices.html?tabs=dialog
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/functions/getparameterastext.html
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/data-access/describe.html
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/functions/listfields.html
##  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/data-management/get-count.html?tabs=python
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/data-access/searchcursor-class.html
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/classes/polyline.html
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/classes/pointgeometry.html
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/classes/point.html
##  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/data-management/create-feature-class.html?tabs=python
##  https://doc.esri.com/en/arcgis-pro/latest/help/analysis/geoprocessing/basics/the-in-memory-workspace.html
##  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/data-management/add-field.html?tabs=python
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/data-access/insertcursor-class.html
##  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/conversion/export-features.html?tabs=python
##  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/data-management/delete.html?tabs=python
##
## Original tool syntax:
##     arcpy.management.SplitLine(in_features, out_feature_class)
##
########################################################################################

## Watch the video: https://youtu.be/RpgOv5iZQmo

## 🤗 Support content creation 👉 https://buymeacoffee.com/glenbambrick

########################################################################################
## USER INPUTS #########################################################################

## input feature class (linear)
in_features = arcpy.GetParameterAsText(0)

## output feature class filepath
out_feature_class = arcpy.GetParameterAsText(1)

########################################################################################
## TOOL OBJECT REQUIREMENTS ############################################################

## srs id of the in_features so we can assign the output the same
srs_id = arcpy.da.Describe(in_features)["spatialReference"].factoryCode

## the geometry type of the input features
shape_type = arcpy.da.Describe(in_features)["shapeType"]

## this list will hold the names of the input fields in order
in_fld_names = [
    fld.name for fld
    in arcpy.ListFields(
        dataset=in_features
    ) if fld.type not in ("Blob","Geometry","GlobalID","Guid","OID","Raster")
]

## add field for accessing geometry
in_fld_names.append("SHAPE@")

## remove Shape_Length
if "Shape_Length" in in_fld_names:
    in_fld_names.remove("Shape_Length")

if "Shape_Area" in in_fld_names:
    in_fld_names.remove("Shape_Area")

## we need the OID field for the ORIG_ID output_field
oid_fld = [
    fld.name for fld
    in arcpy.ListFields(
    dataset = in_features
    ) if fld.type=="OID"
][0]

## insert the oid field name at the start of the in_fld_names list
in_fld_names.insert(0, oid_fld)

## create a copy of the in_fld_name for the out_feature_class
out_fld_names = list(in_fld_names)

## adjust our out_fld_names list to account for the added fields.
## and remove the OID field.
out_fld_names.remove(oid_fld)
out_fld_names.insert(0, "ORIG_FID")
out_fld_names.append("ORIG_SEQ")

## this will hold information for all line segments to create
## it will be a list of lists containing attributes and geometry
segments_lst = []

## dictionary to hold the key: OID, value: vertice points for each line.
vertices_dict = {}

## used for the tool progressor label
feature_count = int(arcpy.GetCount_management(in_rows=in_features).getOutput(0))

########################################################################################
## CREATE OUPUT FEATURE CLASS ##########################################################

## create a linear feature class in memory using the in_features as a template.
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

########################################################################################
## GET VERTICES ########################################################################

## use the Insert Cursor to insert one segment at a time as a record
with arcpy.da.InsertCursor(
    in_table=temp_fc,
    field_names=out_fld_names
) as i_cursor:
    ## iterate through each record in the in_features feature class.
    ## we are only interested in the OID field and the SHAPE@ for accessing geometry.
    with arcpy.da.SearchCursor(
            in_table=in_features,
            field_names=in_fld_names
    ) as s_cursor:
        ## for each feature/record
        for row in s_cursor:
            ## sequence number per split segment of each line
            ## the sequence number is added to the output as per Esri documentation
            seq_num = 1

            ## for each polyline in the geometry
            for part in row[-1]:
                arcpy.AddMessage(part)
                ## 0.0 is the start of the line
                start_dist = 0.0

                ## Step through each vertex in the feature
                for point_num, pnt in enumerate(part):
                    ## start point so do nothing
                    if point_num == 0:
                        pass
                    else:
                        ## create a Point object
                        point = arcpy.Point(
                            X=pnt.X,
                            Y=pnt.Y,
                            Z=pnt.Z,
                            M=pnt.M
                        )
                        ## create a PointGeometry object
                        point_geom = arcpy.PointGeometry(
                            inputs=point
                        )

                        polyline = arcpy.Polyline(part)

                        distance = polyline.queryPointAndDistance(
                            in_point=point_geom
                        )[1]

                        segment = polyline.segmentAlongLine(
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
                            segment_attributes = list(row[0:-1])
                            ## the segment geometry
                            segment_attributes.append(segment)
                            ## the sequence number of the segment for this line
                            segment_attributes.append(seq_num)
                            ## append the info above into our segments list
                            segments_lst.append(segment_attributes)
                            ## increase the sequence number for the next segment
                            seq_num += 1

                            i_cursor.insertRow(segment_attributes)

########################################################################################
## WRITE TO DISK #######################################################################

arcpy.conversion.ExportFeatures(
    in_features=temp_fc,
    out_features=out_feature_class
)

########################################################################################
## CLEAN UP ############################################################################

arcpy.management.Delete(
    in_data = temp_fc
)

########################################################################################