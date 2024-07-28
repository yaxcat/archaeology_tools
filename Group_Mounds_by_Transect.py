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
            id = pt[1]
            coords = (pt[0][0], pt[0][1])
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


def get_perimeter_pts(point_lyr, fields, wsp):
    pt_lyr = arcpy.MakeFeatureLayer_management(points, 'points_layer')
    bounding_poly = arcpy.MinimumBoundingGeometry_management(pt_lyr, wsp + 'Prc_01_bounding_poly', 'CONVEX_HULL')
    selection = arcpy.SelectLayerByLocation_management(point_lyr, 'BOUNDARY_TOUCHES', bounding_poly)
    arcpy.ExportFeatures_conversion(selection, wsp + 'Prc_02_perimeter_points')

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
    transect_num = 0 # Cantor can produce very large integers, so use our key starting at 0
    for pt_1 in range(0, num_pts):
        for pt_2 in range(pt_1+1, num_pts):
            oid1 = perimeter_pts[pt_1][0]
            oid2 = perimeter_pts[pt_2][0]
            pair_id = cantor_pairing(oid1, oid2)
            if pair_id not in pair_ids:
                pair_ids.add(pair_id)
                transects[transect_num] = [perimeter_pts[pt_1], perimeter_pts[pt_2]]
            transect_num += 1
    return transects


# Generates a list representing the station points along the transect line
def gen_station_points(start_pt, end_pt, spacing):
    x1 = start_pt[0]
    x2 = end_pt[0]
    y1 = start_pt[1]
    y2 = end_pt[1]

    line_len = math.sqrt((x2-x1)**2 + (y2-y1)**2) # Overall line length
    station_points = [start_pt]
    inc = spacing

    while inc < line_len:
        vlen = math.sqrt((x2-x1)**2 + (y2-y1)**2) # segment length
        norm = ((x2-x1)/vlen, (y2-y1)/vlen) # Compute the fractional X & Y
        station = (round(x1 + spacing * norm[0], 2), round(y1 + spacing * norm[1], 2)) # Compute the station point
        station_points.append(station)
        x1, y1 = station[0], station[1] # Update the starting point to move along the line
        inc += spacing
    station_points.append(end_pt)
    return station_points


def get_distance(point_a, point_b):
    x1 = point_a[0]
    x2 = point_b[0]
    y1 = point_a[1]
    y2 = point_b[1]
    line_len = math.sqrt((x2-x1)**2 + (y2-y1)**2)
    return line_len


def group_nodes_by_transect(tree, transects, tolerance):
    groups = set()
    point_groups = {}
    station_groups = {}
    grp_id = 0
    for transect in transects:
        id = transect
        t_begin = transects[transect][0][1]
        t_end = transects[transect][1][1]
        t_stations = gen_station_points(t_begin, t_end, station_point_density)
        station_groups[id] = t_stations
        for station in t_stations:
            nn = kd_tree.nearest_neighbor(tree, station)
            dist = get_distance(station, nn.point)
            if dist < tolerance:
                if id not in groups:
                    point_groups[id] = [nn.point]
                    groups.add(id)
                else:
                    if point_groups[id][-1] != nn.point: # Possible to accidentally grab the same point more than once depending on the station density
                        point_groups[id].append(nn.point)
    return station_groups, point_groups


def write_geometry(point_lyr, point_groups, type, wsp):
    #aprx = arcpy.mp.ArcGISProject("CURRENT")
    #default_gdb = aprx.defaultGeodatabase
    spatial_ref = arcpy.Describe(point_lyr).spatialReference # Use the same CRS as the input points
    if type == 'neighbors':
        out_fc = arcpy.CreateFeatureclass_management(wsp, 'Res_01_point_groups', "POINT", "", "", "",  spatial_reference=spatial_ref)
    elif type == 'stations':
        out_fc = arcpy.CreateFeatureclass_management(wsp, 'Prc_03_station_groups', "POLYLINE", "", "", "",   spatial_reference=spatial_ref)
    else:
        arcpy.AddWarning("Incorrect type passed to write geometry function.  Please use one of the defined types.")
        return        
    arcpy.AddField_management(out_fc, "Group", "LONG")

    if type == 'stations':
        with arcpy.da.InsertCursor(out_fc, ["SHAPE@", "Group"]) as cursor:
            for group in point_groups:
                group_id = group
                array = arcpy.Array()
                points = point_groups[group]
                group_size = len(points)
                if group_size > 2:
                    for xy in points:
                        point = arcpy.Point(xy[0], xy[1])
                        array.add(point)
                    polyline = arcpy.Polyline(array)
                    cursor.insertRow([polyline, group_id])
        del cursor
    elif type == 'neighbors':
        with arcpy.da.InsertCursor(out_fc, ["SHAPE@XY", "Group"]) as cursor:
            for group in point_groups:
                group_id = group
                points = point_groups[group]
                group_size = len(points)
                if group_size > 1:
                    for xy in points:
                        cursor.insertRow([xy, group_id])
        del cursor


if __name__ == "__main__":
    points = arcpy.GetParameterAsText(0)
    id = arcpy.GetParameterAsText(1)
    station_point_density = int(arcpy.GetParameterAsText(2))
    tolerance = float(arcpy.GetParameterAsText(3))
    wsp = arcpy.GetParameterAsText(4) + "\\"
    fields = ["SHAPE@XY", id]

    point_lyr = arcpy.MakeFeatureLayer_management(points, 'points_layer')

    tree = pts_to_kd_tree(point_lyr, fields)
    perimeter_pts = get_perimeter_pts(point_lyr, fields, wsp)
    transects = gen_transects(perimeter_pts)
    
    station_groups, node_groups = group_nodes_by_transect(tree, transects, tolerance)
    write_geometry(point_lyr, station_groups, 'stations', wsp)
    write_geometry(point_lyr, node_groups, 'neighbors', wsp)
