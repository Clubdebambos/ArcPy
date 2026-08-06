import arcpy

########################################################################################
## ArcPy Reference Links:
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/functions/listfields.html
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/data-access/describe.html
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/functions/describe.html
##  https://doc.esri.com/en/arcgis-pro/latest/arcpy/functions/describe-object-properties.html
##
########################################################################################

## Watch the video: https://youtu.be/PvngX0z_usc

## 🤗 Support content creation 👉 https://buymeacoffee.com/glenbambrick

########################################################################################
## USER INPUT ##########################################################################

## the path to the feature class to get the OID field for
fc_path = r"C:\path\to\fc_or_table"

########################################################################################
## GET OID FIELD WITH LISTFILEDS #######################################################

oid_field = [fld.name for fld in arcpy.ListFields(fc_path) if fld.type=="OID"][0]

print(oid_field)

########################################################################################
## GET OID FIELD WITH DESCRIBE #########################################################

oid_field = arcpy.da.Describe(fc_path)["OIDFieldName"]
oid_field = arcpy.Describe(fc_path).OIDFieldName

print(oid_field)

########################################################################################
print("\nSCRIPT COMPLETE")