import arcpy

########################################################################################
## Esri Documentation:
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/functions/getparameterastext.html
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/functions/getparameter.html
##  https://doc.esri.com/en/arcgis-pro/latest/tool-reference/conversion/export-table.html?tabs=python
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/classes/fieldmappings.html
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/classes/fieldmap.html
##
########################################################################################

## Watch the video: https://youtu.be/4O7rt138Uqo

## 🤗 Support content creation 👉 https://buymeacoffee.com/glenbambrick

########################################################################################
## USER INPUT

## the Feature CLass or Table to export to CSV
in_table = arcpy.GetParameterAsText(0)

## the fielpath for the CSV file to create
out_csv = arcpy.GetParameterAsText(1)

## to subset the output fields
out_fields = arcpy.GetParameter(2)

## to subset the output records
where_clause = arcpy.GetParameterAsText(3)

########################################################################################
## WORKFLOW
########################################################################################

if out_fields:
    ## create a FieldMappings object
    field_mappings = arcpy.FieldMappings()

    ## for each field name
    for field in out_fields:
        ## create a FieldMap object
        field_map = arcpy.FieldMap()

        ## add Field to the FieldMap
        field_map.addInputField(
            in_table, # table_dataset
            field.value # field_name
        )

        ## add the FieldMap object to the FieldMappings
        field_mappings.addFieldMap(
            field_map # field_name
        )
else:
    field_mappings = None

## Export Table to CSV
arcpy.conversion.ExportTable(
    in_table = in_table,
    out_table = out_csv,
    where_clause = where_clause,
    field_mapping = field_mappings
)

########################################################################################