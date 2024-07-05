import arcpy
import kd_tree

def inOrderTraversal(rootNode):
    if not rootNode:
        return
    inOrderTraversal(rootNode.left_child)
    arcpy.AddMessage(str(rootNode.id) + " - " + str(rootNode.point))
    inOrderTraversal(rootNode.right_child)


def pts_to_kd_tree(points, fields):
    desc = arcpy.Describe(points)
    if desc.shapeType not in ('Point', 'MultiPoint'):
        arcpy.AddWarning("The process was aborted because the input data were not points.  Please seclect a point dataset to use with this tool.")
        return
    
    
    point_list = []
    pt_lyr = arcpy.MakeFeatureLayer_management(points, 'points_layer')
    with arcpy.da.SearchCursor(pt_lyr, fields) as cur:
        for pt in cur:
            id = pt[0]
            coords = (pt[1], pt[2])
            point_list.append([id, coords])
    tree = kd_tree.build_tree(point_list)
    
    return tree



if __name__ == "__main__":
    points = arcpy.GetParameterAsText(0)
    arcpy.AddMessage(points)
    id = arcpy.GetParameterAsText(1)
    x = arcpy.GetParameterAsText(2)
    y = arcpy.GetParameterAsText(3)
    fields = [id, x, y]

    tree = pts_to_kd_tree(points, fields)

    inOrderTraversal(tree)