import arcpy

def pts_to_kd_tree(points, fields):
    desc = arcpy.Describe(points)
    if desc.shapeType not in ('Point', 'MultiPoint'):
        arcpy.AddWarning("The process was aborted because the input data were not points.  Please seclect a point dataset to use with this tool.")
        return
    
    
    point_list = []
    pt_lyr = arcpy.MakeFeatureLayer_management(points, 'points_layer')
    with arcpy.da.SearchCursor(pt_lyr, fields) as cur:
        for pt in cur:
            s = str(pt[0]) + " - " + "(" + str(pt[1]) + ", " + str(pt[2]) + ")"
            arcpy.AddMessage(s)
    



if __name__ == "__main__":
    points = arcpy.GetParameterAsText(0)
    arcpy.AddMessage(points)
    id = arcpy.GetParameterAsText(1)
    x = arcpy.GetParameterAsText(2)
    y = arcpy.GetParameterAsText(3)
    fields = [id, x, y]

    pts_to_kd_tree(points, fields)