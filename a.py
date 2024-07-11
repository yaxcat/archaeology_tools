import arcpy
import math
import kd_tree

def inOrderTraversal(rootNode):
    if not rootNode:
        return
    inOrderTraversal(rootNode.left_child)
    arcpy.AddMessage(str(rootNode.id) + " - " + str(rootNode.point))
    inOrderTraversal(rootNode.right_child)

def get_pts(point_lyr, fields):
    point_list = []
    with arcpy.da.SearchCursor(point_lyr, fields) as cur:
        for pt in cur:
            id = pt[0]
            coords = (pt[1], pt[2])
            point_list.append([id, coords])
    return point_list


def pts_to_kd_tree(point_lyr, fields):
    desc = arcpy.Describe(points)
    if desc.shapeType not in ('Point', 'MultiPoint'):
        arcpy.AddWarning("The process was aborted because the input data were not points.  Please seclect a point dataset to use with this tool.")
        return
    point_list = get_pts(point_lyr, fields)
    tree = kd_tree.build_tree(point_list)
    
    return tree

def get_perimeter_pts(point_lyr, fields):
    pt_lyr = arcpy.MakeFeatureLayer_management(points, 'points_layer')
    bounding_poly = arcpy.MinimumBoundingGeometry_management(pt_lyr, 'Prc_01_bounding_poly', 'CONVEX_HULL')
    selection = arcpy.SelectLayerByLocation_management(point_lyr, 'BOUNDARY_TOUCHES', bounding_poly)
    arcpy.ExportFeatures_conversion(selection, 'Prc_02_perimeter_points')

    perimeter_pts = get_pts(selection, fields)
    return perimeter_pts

# Maps two non-negative integers into a single non-negative integer.  Used to keep track of point
# pairs and prevent duplication of work
def cantor_pairing(oid1, oid2):
    if oid1 == oid2:
        arcpy.AddWarning("Two or more points have the same ID.  Point IDs must be unique to use this tool.")
        return
    # Make sure the pairwise function always consumes the IDs in the same order so that return value is
    # consistent.  For example (3,5) and (5,3) should both return 41.
    if oid1 < oid2:
        k1 = oid1
        k2 = oid2
    else:
        k1 = oid2
        k2 = oid1
    pair_id = (k1 + k2) * (k1 + k2 + 1)/2 + k2
    return int(pair_id)

def gen_transects(perimeter_pts):
    pair_ids = set()
    transects = {}
    num_pts = len(perimeter_pts)
    for pt_1 in range(0, num_pts):
        for pt_2 in range(pt_1+1, num_pts):
            oid1 = perimeter_pts[pt_1][0]
            oid2 = perimeter_pts[pt_2][0]
            pair_id = cantor_pairing(oid1, oid2)
            arcpy.AddMessage(str(oid1) + ", " + str(oid2) + " - " + str(pair_id))
            if pair_id not in pair_ids:
                pair_ids.add(pair_id)
                transects[pair_id] = [perimeter_pts[pt_1], perimeter_pts[pt_2]]

    return transects

# Generates a list representing the station points along the transect line
def gen_station_points(start_pt, end_pt, spacing):
    x1 = start_pt[0]
    x2 = end_pt[0]
    y1 = start_pt[1]
    y2 = end_pt[1]

    line_len = math.sqrt((x2-x1)**2 + (y2-y1)**2) 
    station_points = [start_pt]
    inc = spacing

    while inc < line_len:
        v = (x2-x1, y2-y1) # direction of the vector
        vlen = math.sqrt((x2-x1)**2 + (y2-y1)**2) # length
        norm = ((x2-x1)/vlen, (y2-y1)/vlen) # Compute the fractional X & Y
        station = (round(x1 + spacing * norm[0], 2), round(y1 + spacing * norm[1], 2)) # Compute the station point
        station_points.append(station)
        x1, y1 = station[0], station[1] # Update the starting point to move along the line
        inc += spacing
    station_points.append(end_pt)

    return station_points

pts = gen_station_points((0,0), (7,7), 1)

 
"""
if __name__ == "__main__":
    points = arcpy.GetParameterAsText(0)
    arcpy.AddMessage(points)
    id = arcpy.GetParameterAsText(1)
    x = arcpy.GetParameterAsText(2)
    y = arcpy.GetParameterAsText(3)
    fields = [id, x, y]

    point_lyr = arcpy.MakeFeatureLayer_management(points, 'points_layer')

    tree = pts_to_kd_tree(point_lyr, fields)
    perimeter_pts = get_perimeter_pts(point_lyr, fields)
    transects = gen_transects(perimeter_pts)

    #inOrderTraversal(tree)

    arcpy.AddMessage(len(transects)) 

    #

    #for transect in transects:
    #    arcpy.AddMessage(str(transect))
"""
