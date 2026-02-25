import ifcopenshell
import ifcopenshell.util.placement
from collections import defaultdict, deque
import math

ifc_model = ifcopenshell.open(r"C:\Users\burka\github-classroom\iaac-maai\intro-to-ifc-seidburka\assets\duplex.ifc")
spaces = ifc_model.by_type("IfcSpace")

# ================================================================
# SHARED CONSTANTS
# ================================================================

NON_HABITABLE_KEYWORDS = {
    "bathroom", "toilet", "wc", "storage", "corridor", "hall",
    "stair", "garage", "utility", "closet", "laundry", "mechanical",
    "lobby", "landing", "circulation", "roof", "foyer", "hallway"
}

UNKNOWN_LABEL = {"room"}

ROOM_REQUIREMENTS = {
    "living room":  {"min_area": 16.0, "min_height": 2.5},
    "bedroom":      {"min_area": 8.0,  "min_height": 2.5},
    "kitchen":      {"min_area": 7.0,  "min_height": 2.5},
    "bathroom":     {"min_area": 3.5,  "min_height": 2.3},
    "utility":      {"min_area": 1.5,  "min_height": 2.2},
    "hallway":      {"min_area": 1.0,  "min_height": 2.2},
    "foyer":        {"min_area": 1.0,  "min_height": 2.2},
    "default":      {"min_area": 4.0,  "min_height": 2.3},
}

MAX_TRAVEL_DISTANCE = 25.0
MIN_DOOR_WIDTH = 0.8

# ================================================================
# SHARED HELPER FUNCTIONS
# ================================================================

def get_space_label(space):
    return (space.LongName or space.Name or "").strip()

def is_habitable(space):
    label = get_space_label(space).lower()
    return not any(kw in label for kw in NON_HABITABLE_KEYWORDS)

def get_floor_area(space):
    for rel in space.IsDefinedBy:
        if rel.is_a("IfcRelDefinesByProperties"):
            pset = rel.RelatingPropertyDefinition
            if pset.is_a("IfcElementQuantity"):
                for q in pset.Quantities:
                    if "area" in q.Name.lower():
                        return q.AreaValue
    return None

def get_placement_xyz(element):
    try:
        m = ifcopenshell.util.placement.get_local_placement(element.ObjectPlacement)
        return m[0][3], m[1][3], m[2][3]
    except Exception:
        return None

def get_revit_dimensions(space):
    """Extract Area and Unbounded Height from PSet_Revit_Dimensions."""
    area, height = None, None
    for rel in space.IsDefinedBy:
        if rel.is_a("IfcRelDefinesByProperties"):
            pset = rel.RelatingPropertyDefinition
            if pset.is_a("IfcPropertySet") and "dimensions" in pset.Name.lower():
                for prop in pset.HasProperties:
                    if hasattr(prop, "NominalValue") and prop.NominalValue:
                        val = prop.NominalValue.wrappedValue
                        if prop.Name == "Area":
                            area = val
                        elif prop.Name == "Unbounded Height":
                            height = val
    return area, height

# ================================================================
# EXERCISE 2: WINDOW COMPLIANCE
# ================================================================

def get_window_area(window):
    if window.OverallWidth and window.OverallHeight:
        return window.OverallWidth * window.OverallHeight
    for rel in window.IsDefinedBy:
        if rel.is_a("IfcRelDefinesByProperties"):
            pset = rel.RelatingPropertyDefinition
            if pset.is_a("IfcElementQuantity"):
                for q in pset.Quantities:
                    if "area" in q.Name.lower():
                        return q.AreaValue
    return 0

def get_compliance_status(space, ratio):
    label = get_space_label(space).lower()
    if not is_habitable(space):
        return "-- SKIP", True
    if label in UNKNOWN_LABEL:
        return "?? UNKN", None
    if ratio is None:
        return "XX FAIL", False
    return ("OK PASS", True) if ratio >= 0.125 else ("XX FAIL", False)

def build_space_to_windows(ifc_model):
    """
    Map each IfcSpace to its windows.
    Strategy 1: window.ProvidesBoundaries -> RelatingSpace (exact IFC relationship)
    Strategy 2: geometry fallback — assign unmapped windows to the nearest space
                on the same storey by XY distance between placement origins.
    """
    space_windows = defaultdict(list)
    seen = set()
    unmapped_windows = []

    for window in ifc_model.by_type("IfcWindow"):
        found = False
        for boundary in window.ProvidesBoundaries:
            space = boundary.RelatingSpace
            if space and space.is_a("IfcSpace"):
                key = (space.GlobalId, window.GlobalId)
                if key not in seen:
                    seen.add(key)
                    space_windows[space.GlobalId].append(window)
                found = True
        if not found:
            unmapped_windows.append(window)

    print(f"  Primary mapping: {sum(len(v) for v in space_windows.values())} windows across {len(space_windows)} spaces")
    print(f"  Unmapped windows: {len(unmapped_windows)} - using geometry fallback")

    if unmapped_windows:
        space_xyz = {s.GlobalId: get_placement_xyz(s) for s in ifc_model.by_type("IfcSpace")}
        storey_spaces = defaultdict(list)
        for rel in ifc_model.by_type("IfcRelAggregates"):
            for child in rel.RelatedObjects:
                if child.is_a("IfcSpace"):
                    storey_spaces[rel.RelatingObject.GlobalId].append(child)
        for rel in ifc_model.by_type("IfcRelContainedInSpatialStructure"):
            for el in rel.RelatedElements:
                if el.is_a("IfcSpace"):
                    storey_spaces[rel.RelatingStructure.GlobalId].append(el)

        window_storey = {}
        for rel in ifc_model.by_type("IfcRelContainedInSpatialStructure"):
            for el in rel.RelatedElements:
                if el.is_a("IfcWindow"):
                    window_storey[el.GlobalId] = rel.RelatingStructure

        fallback_count = 0
        for window in unmapped_windows:
            win_xyz = get_placement_xyz(window)
            storey = window_storey.get(window.GlobalId)
            if not storey or not win_xyz:
                continue
            wx, wy = win_xyz[0], win_xyz[1]
            best_space, best_dist = None, float("inf")
            for space in storey_spaces.get(storey.GlobalId, []):
                sxyz = space_xyz.get(space.GlobalId)
                if not sxyz:
                    continue
                dist = math.sqrt((wx - sxyz[0])**2 + (wy - sxyz[1])**2)
                if dist < best_dist:
                    best_dist = dist
                    best_space = space
            if best_space:
                key = (best_space.GlobalId, window.GlobalId)
                if key not in seen:
                    seen.add(key)
                    space_windows[best_space.GlobalId].append(window)
                    fallback_count += 1

        print(f"  Geometry fallback assigned: {fallback_count} windows")

    return space_windows

def analyze_window_compliance(ifc_model, spaces):
    """
    Analyze window-to-floor ratio compliance per space against Catalan building code.
    Requirements:
      - Habitable spaces: window-to-floor ratio >= 12.5%
      - Minimum window dimensions: 60cm wide x 100cm tall (flagged as warning)
    Non-habitable spaces are skipped. Generic 'Room' spaces are marked unknown.
    Returns a list of dicts with compliance results per space.
    """
    print("Building window map...")
    space_windows = build_space_to_windows(ifc_model)
    results = []

    print("\nResults:")
    print("-" * 105)

    for space in spaces:
        floor_area = get_floor_area(space)
        windows = space_windows.get(space.GlobalId, [])
        label = get_space_label(space)

        undersized = [
            w for w in windows
            if w.OverallWidth and w.OverallHeight
            and (w.OverallWidth < 0.6 or w.OverallHeight < 1.0)
        ]

        total_window_area = sum(get_window_area(w) for w in windows)
        ratio = total_window_area / floor_area if (floor_area and total_window_area > 0) else None
        status, compliant = get_compliance_status(space, ratio)

        ratio_str = f"{ratio:.1%}" if ratio is not None else "N/A"
        area_str  = f"{floor_area:.1f}" if floor_area else "N/A"
        warn      = f" | WARN: {len(undersized)} undersized" if undersized else ""
        near_miss = ""
        if compliant is False and ratio is not None and ratio >= 0.10:
            near_miss = f" | NEAR MISS ({ratio:.1%} vs 12.5%)"

        print(
            f"{status} | {space.Name:<6} | {label:<20} | "
            f"Floor: {area_str:>7}m2 | Win: {len(windows):>2} | "
            f"WinArea: {total_window_area:.2f}m2 | Ratio: {ratio_str:>6}"
            f"{warn}{near_miss}"
        )

        results.append({
            "space": space.Name, "label": label,
            "habitable": is_habitable(space), "floor_area": floor_area,
            "window_count": len(windows), "total_window_area": total_window_area,
            "ratio": ratio, "undersized_windows": len(undersized), "compliant": compliant,
        })

    print("-" * 105)
    total_checked = sum(1 for r in results if r["habitable"] and r["compliant"] is not None)
    total_pass    = sum(1 for r in results if r["compliant"] is True and r["habitable"])
    total_skip    = sum(1 for r in results if not r["habitable"])
    total_unknown = sum(1 for r in results if r["compliant"] is None)
    print(f"Summary: {total_pass}/{total_checked} habitable spaces pass | {total_skip} skipped | {total_unknown} unknown")
    return results

# ================================================================
# EXERCISE 1: BUILDING CODE COMPLIANCE (AREA + HEIGHT)
# ================================================================

def get_room_type(space):
    label = get_space_label(space).lower()
    for room_type in ROOM_REQUIREMENTS:
        if room_type in label:
            return room_type
    return "default"

def check_space_compliance(spaces):
    """
    Check each space against Catalan building code minimum requirements.
    Validates minimum floor area and ceiling height per room type.
    Returns a list of dicts with pass/fail results and failure reasons.
    """
    results = []
    print("\n=== EXERCISE 1: BUILDING CODE COMPLIANCE ===")
    print("-" * 105)

    for space in spaces:
        label      = get_space_label(space)
        room_type  = get_room_type(space)
        reqs       = ROOM_REQUIREMENTS[room_type]
        area, height = get_revit_dimensions(space)
        min_area   = reqs["min_area"]
        min_height = reqs["min_height"]
        failures, warnings = [], []

        if area is None:
            warnings.append("area data missing"); area_pass = None
        elif area < min_area:
            failures.append(f"area {area:.1f}m2 < {min_area}m2 required"); area_pass = False
        else:
            area_pass = True

        if height is None:
            warnings.append("height data missing"); height_pass = None
        elif height < min_height:
            failures.append(f"height {height:.2f}m < {min_height}m required"); height_pass = False
        else:
            height_pass = True

        if failures:
            compliant, status = False, "XX FAIL"
        elif warnings:
            compliant, status = None, "?? WARN"
        else:
            compliant, status = True, "OK PASS"

        area_str   = f"{area:.1f}"   if area   is not None else "N/A"
        height_str = f"{height:.2f}" if height is not None else "N/A"
        fail_str   = " | REASONS: " + "; ".join(failures) if failures else ""
        warn_str   = " | WARN: "    + "; ".join(warnings) if warnings and not failures else ""

        print(
            f"{status} | {space.Name:<6} | {label:<20} | {room_type:<12} | "
            f"Area: {area_str:>7}m2 (min {min_area}m2) | "
            f"Height: {height_str}m (min {min_height}m){fail_str}{warn_str}"
        )

        results.append({
            "space": space.Name, "label": label, "room_type": room_type,
            "area": area, "height": height, "min_area": min_area,
            "min_height": min_height, "area_pass": area_pass,
            "height_pass": height_pass, "compliant": compliant,
            "failures": failures, "warnings": warnings,
        })

    print("-" * 105)
    print(f"Summary: {sum(1 for r in results if r['compliant'] is True)} pass | "
          f"{sum(1 for r in results if r['compliant'] is False)} fail | "
          f"{sum(1 for r in results if r['compliant'] is None)} data warnings")
    return results

# ================================================================
# BONUS: FIRE SAFETY & EVACUATION ROUTES
# ================================================================

def build_spatial_graph(ifc_model, spaces):
    """
    Build a graph of spaces connected by doors.
    Primary:  door.ProvidesBoundaries -> two distinct IfcSpace = interior door
    Fallback: door reports 1 space -> geometry nearest neighbor within 8m
    Exterior: door reports 1 space, no close neighbor -> exit node
    Stair:    stair spaces connected to nearest neighbors by proximity
    Manual:   cross-connect A/B units via foyer and living room adjacency
    """
    graph = defaultdict(list)
    exits = set()

    space_by_id   = {s.GlobalId: s for s in spaces}
    space_by_name = {s.Name: s for s in spaces}
    space_xyz     = {s.GlobalId: get_placement_xyz(s) for s in spaces}

    storey_spaces = defaultdict(list)
    for rel in ifc_model.by_type("IfcRelAggregates"):
        for child in rel.RelatedObjects:
            if child.is_a("IfcSpace"):
                storey_spaces[rel.RelatingObject.GlobalId].append(child)
    for rel in ifc_model.by_type("IfcRelContainedInSpatialStructure"):
        for el in rel.RelatedElements:
            if el.is_a("IfcSpace"):
                storey_spaces[rel.RelatingStructure.GlobalId].append(el)

    door_storey = {}
    for rel in ifc_model.by_type("IfcRelContainedInSpatialStructure"):
        for el in rel.RelatedElements:
            if el.is_a("IfcDoor"):
                door_storey[el.GlobalId] = rel.RelatingStructure

    for door in ifc_model.by_type("IfcDoor"):
        connected = []
        seen_ids = set()
        for b in door.ProvidesBoundaries:
            s = b.RelatingSpace
            if s and s.is_a("IfcSpace"):
                resolved = space_by_id.get(s.GlobalId) or space_by_name.get(s.Name)
                if resolved and resolved.GlobalId not in seen_ids:
                    connected.append(resolved)
                    seen_ids.add(resolved.GlobalId)

        if len(connected) >= 2:
            s1, s2 = connected[0], connected[1]
            graph[s1.GlobalId].append((s2.GlobalId, door))
            graph[s2.GlobalId].append((s1.GlobalId, door))
            if len(connected) == 3:
                s3 = connected[2]
                graph[s1.GlobalId].append((s3.GlobalId, door))
                graph[s3.GlobalId].append((s1.GlobalId, door))
                graph[s2.GlobalId].append((s3.GlobalId, door))
                graph[s3.GlobalId].append((s2.GlobalId, door))

        elif len(connected) == 1:
            known_space = connected[0]
            door_xyz = get_placement_xyz(door)
            storey   = door_storey.get(door.GlobalId)
            best_space, best_dist = None, float("inf")

            if door_xyz and storey:
                dx, dy = door_xyz[0], door_xyz[1]
                for candidate in storey_spaces.get(storey.GlobalId, []):
                    if candidate.GlobalId == known_space.GlobalId:
                        continue
                    cxyz = space_xyz.get(candidate.GlobalId)
                    if not cxyz:
                        continue
                    dist = math.sqrt((dx - cxyz[0])**2 + (dy - cxyz[1])**2)
                    if dist < best_dist:
                        best_dist = dist
                        best_space = candidate

            if best_space and best_dist < 8.0:
                graph[known_space.GlobalId].append((best_space.GlobalId, door))
                graph[best_space.GlobalId].append((known_space.GlobalId, door))
            else:
                exits.add(known_space.GlobalId)

    # Connect stair spaces to nearest neighbors (no door data in IFC)
    stair_spaces = [s for s in spaces if "stair" in get_space_label(s).lower()]
    for stair in stair_spaces:
        stair_xyz = space_xyz.get(stair.GlobalId)
        if not stair_xyz:
            continue
        distances = []
        for s in spaces:
            if s.GlobalId == stair.GlobalId:
                continue
            sxyz = space_xyz.get(s.GlobalId)
            if not sxyz:
                continue
            dist = math.sqrt((stair_xyz[0]-sxyz[0])**2 + (stair_xyz[1]-sxyz[1])**2)
            distances.append((dist, s))
        distances.sort()
        for dist, neighbor in distances[:4]:
            if dist < 20.0:
                graph[stair.GlobalId].append((neighbor.GlobalId, None))
                graph[neighbor.GlobalId].append((stair.GlobalId, None))

    # Cross-connect A/B units — foyers are adjacent, living rooms share exit zone
    for pair in [("A101", "B101"), ("A102", "B102"), ("A105", "B105")]:
        sa = space_by_name.get(pair[0])
        sb = space_by_name.get(pair[1])
        if sa and sb:
            graph[sa.GlobalId].append((sb.GlobalId, None))
            graph[sb.GlobalId].append((sa.GlobalId, None))

    # Connect B side hallway to B side foyer and B side stair
    for pair in [("B201", "B101"), ("B201", "B105")]:
        sa = space_by_name.get(pair[0])
        sb = space_by_name.get(pair[1])
        if sa and sb:
            graph[sa.GlobalId].append((sb.GlobalId, None))
            graph[sb.GlobalId].append((sa.GlobalId, None))

# B103 Kitchen has no door data in IFC — connect to nearest foyer manually
    b103 = space_by_name.get("B103")
    b101 = space_by_name.get("B101")
    if b103 and b101:
        graph[b103.GlobalId].append((b101.GlobalId, None))
        graph[b101.GlobalId].append((b103.GlobalId, None))

    # Connect R301 roof to nearest stair
    r301 = space_by_name.get("R301")
    a105 = space_by_name.get("A105")
    if r301 and a105:
        graph[r301.GlobalId].append((a105.GlobalId, None))
        graph[a105.GlobalId].append((r301.GlobalId, None))

    return graph, exits, space_by_id

def bfs_evacuation(start_id, graph, exits, space_map):
    """BFS from start space to nearest exit. Returns (distance, path)."""
    if start_id in exits:
        return 0.0, [space_map[start_id].Name]

    visited = {start_id: None}
    queue   = deque([(start_id, 0.0)])

    while queue:
        current_id, dist = queue.popleft()
        for neighbor_id, door in graph[current_id]:
            if neighbor_id not in visited:
                visited[neighbor_id] = current_id
                neighbor = space_map.get(neighbor_id)
                area     = get_revit_dimensions(neighbor)[0] if neighbor else None
                step     = math.sqrt(area) if area else 3.0
                new_dist = dist + step

                if neighbor_id in exits:
                    path = [space_map[neighbor_id].Name]
                    node = current_id
                    while node is not None:
                        path.append(space_map[node].Name)
                        node = visited[node]
                    path.reverse()
                    return new_dist, path

                queue.append((neighbor_id, new_dist))

    return None, []

def analyze_evacuation_routes(ifc_model, spaces):
    """
    Analyze fire safety evacuation routes per Catalan building code.
    Requirements:
      - Max travel distance to exit: <= 25m
      - Min door width: 0.8m
    Builds spatial graph using door boundaries with geometry and stair fallbacks.
    Runs BFS from each space to find nearest exit.
    Returns list of dicts with compliance results per space.
    """
    print("\n=== BONUS: FIRE SAFETY & EVACUATION ROUTES ===")
    graph, exits, space_map = build_spatial_graph(ifc_model, spaces)

    print(f"  Spaces: {len(spaces)} | Graph edges: {sum(len(v) for v in graph.values()) // 2}")
    print(f"  Exit spaces ({len(exits)}): {[space_map[e].Name for e in exits if e in space_map]}")

    # Door width compliance
    print("\nDoor Width Check (min 0.8m):")
    print("-" * 72)
    narrow = []
    for door in ifc_model.by_type("IfcDoor"):
        w = door.OverallWidth
        if w is not None:
            ok  = w >= MIN_DOOR_WIDTH
            tag = "OK  " if ok else "FAIL"
            if not ok:
                narrow.append(door)
            print(f"  {tag} | Width: {w:.2f}m | {door.Name[-50:]}")
    print(f"  Result: {len(narrow)} doors below {MIN_DOOR_WIDTH}m minimum")

    # BFS evacuation per space
    print("\nEvacuation Distance per Space (max 25m):")
    print("-" * 95)

    results = []
    for space in spaces:
        dist, path = bfs_evacuation(space.GlobalId, graph, exits, space_map)
        label = get_space_label(space)

        if dist is None:
            status, compliant, dist_str = "XX ISOL", False, "NO EXIT"
        elif dist <= MAX_TRAVEL_DISTANCE:
            status, compliant, dist_str = "OK PASS", True,  f"{dist:.1f}m"
        else:
            status, compliant, dist_str = "XX FAIL", False, f"{dist:.1f}m"

        path_str = " -> ".join(path) if path else "none"
        print(f"{status} | {space.Name:<6} | {label:<20} | Dist: {dist_str:>8} | {path_str}")

        results.append({
            "space": space.Name, "label": label,
            "travel_distance": dist, "path": path, "compliant": compliant,
        })

    print("-" * 95)
    passed   = sum(1 for r in results if r["compliant"])
    isolated = sum(1 for r in results if r["travel_distance"] is None)
    failed   = sum(1 for r in results if not r["compliant"])
    print(f"Summary: {passed} pass | {failed} fail | {isolated} isolated")
    print(f"Narrow doors: {len(narrow)} | Max allowed travel: {MAX_TRAVEL_DISTANCE}m")
    return results

# ================================================================
# RUN ALL THREE
# ================================================================

print("=" * 105)
print("EXERCISE 2: WINDOW COMPLIANCE")
print("=" * 105)
window_results = analyze_window_compliance(ifc_model, spaces)

print("\n")
print("=" * 105)
print("EXERCISE 1: BUILDING CODE COMPLIANCE")
print("=" * 105)
compliance_results = check_space_compliance(spaces)

print("\n")
print("=" * 105)
print("BONUS: FIRE SAFETY & EVACUATION ROUTES")
print("=" * 105)
evacuation_results = analyze_evacuation_routes(ifc_model, spaces)