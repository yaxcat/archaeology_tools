import arcpy
import math
import kd_tree

# Prints each K-D tree's node point property in order
def inOrderTraversal(rootNode):
    if not rootNode:
        return
    inOrderTraversal(rootNode.left_child)
    arcpy.AddMessage(str(rootNode.id) + " - " + str(rootNode.point))
    inOrderTraversal(rootNode.right_child)

# Retrieves coordinates and ID from the point layers specified in the tool UI
def get_pts(point_lyr, fields):
    point_list = []
    with arcpy.da.SearchCursor(point_lyr, fields) as cur:
        for pt in cur:
            id = pt[1]
            coords = (pt[0][0], pt[0][1])
            point_list.append([id, coords])
    return point_list

# Constructs a K-D from a point layer to make nodes searchable by distance
def pts_to_kd_tree(point_lyr, fields):
    desc = arcpy.Describe(points)
    if desc.shapeType not in ('Point', 'MultiPoint'):
        arcpy.AddWarning("The process was aborted because the input data were not points.  Please seclect a point dataset to use with this tool.")
        return
    point_list = get_pts(point_lyr, fields)
    tree = kd_tree.build_tree(point_list)
    return tree

# Gets the user-specified points we'll use to build transects
def get_perimeter_pts(perimeter_points, perim_fields):
    perimeter_pts = get_pts(perimeter_points, perim_fields)
    return perimeter_pts

# Organizes user-specified perimeter points into pairs for building transects
# TODO throw or warn of the number of points with the same ID != 2
def gen_transects(perimeter_pts):
    pair_ids = set()
    transects = {}
    num_pts = len(perimeter_pts)
    count = 0
    for pt in range(0, num_pts):
        pair_id = perimeter_pts[pt][0]
        if pair_id not in pair_ids:
            pair_ids.add(pair_id)
            transects[pair_id] = [perimeter_pts[pt]]
        else:
            transects[pair_id].append(perimeter_pts[pt])
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

# Computes the distance between two points
def get_distance(point_a, point_b):
    x1 = point_a[0]
    x2 = point_b[0]
    y1 = point_a[1]
    y2 = point_b[1]
    line_len = math.sqrt((x2-x1)**2 + (y2-y1)**2)
    return line_len

# Identifies the nearest K-D tree node to a given transect point and groups it with that transect if
# its closer to the transect point than the tolerance specified in the tool UI
def group_nodes_by_transect(tree, transects, tolerance):
    groups = set()
    point_groups = {}
    station_groups = {}
    grp_id = 0
    for transect in transects:
        arcpy.AddMessage(transect)
        id = transect
        t_begin = transects[transect][0][1]
        t_end = transects[transect][1][1]
        t_stations = gen_station_points(t_begin, t_end, station_point_density)
        arcpy.AddMessage(t_stations)
        station_groups[id] = t_stations
        for station in t_stations:
            nn = kd_tree.nearest_neighbor(tree, station)
            dist = get_distance(station, nn.point)
            if dist < tolerance:
                arcpy.AddMessage("---" + str(nn.point))
                if id not in groups:
                    point_groups[id] = [nn.point]
                    groups.add(id)
                else:
                    if point_groups[id][-1] != nn.point:
                        point_groups[id].append(nn.point)
    arcpy.AddMessage(point_groups)
    return station_groups, point_groups

# Converts the data structures generated into feature classes for viewing in ArcGIS Pro
# TODO figure out why saving to GDB corrups the feature
def write_geometry(point_lyr, point_groups, type, wsp):
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
    perim_points = arcpy.GetParameterAsText(2)
    station_point_density = int(arcpy.GetParameterAsText(3))
    tolerance = float(arcpy.GetParameterAsText(4))
    wsp = arcpy.GetParameterAsText(5) + "\\"
    fields = ["SHAPE@XY", id]
    perim_fields = ["SHAPE@XY", "Pair_ID"]

    point_lyr = arcpy.MakeFeatureLayer_management(points, 'points_layer')
    perim_lyr = arcpy.MakeFeatureLayer_management(perim_points, 'perim_layer')

    tree = pts_to_kd_tree(point_lyr, fields)
    perimeter_pts = get_perimeter_pts(perim_lyr, perim_fields)
    
    
    transects = gen_transects(perimeter_pts)

    for t in transects:
        arcpy.AddMessage(str(t))
        arcpy.AddMessage("---" + str(transects[t]))
    
    station_groups, node_groups = group_nodes_by_transect(tree, transects, tolerance)
    write_geometry(point_lyr, station_groups, 'stations', wsp)
    write_geometry(point_lyr, node_groups, 'neighbors', wsp)
