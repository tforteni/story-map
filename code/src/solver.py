import numpy as np
from scipy.optimize import least_squares

def get_coords(locations, distances, direction_constraints):
    # Map location names to indices
    loc_index = {loc: i for i, loc in enumerate(locations)}
    distance_lookup = {}
    for (l1, l2), dist_entry in distances.items():
        d = dist_entry[0]
        distance_lookup[(l1, l2)] = d
        distance_lookup[(l2, l1)] = d
    avg_distance = np.mean(list(distance_lookup.values())) if distance_lookup else 1.0

    def residuals(coords):
        coords = coords.reshape(-1, 2)
        res = []
        # Distance matching residuals
        for (l1, l2), dist_list in distances.items():
            d = dist_list[0]
            i, j = loc_index[l1], loc_index[l2]
            xi, yi = coords[i]
            xj, yj = coords[j]
            res.append(np.sqrt((xi - xj)**2 + (yi - yj)**2) - d)

        for (a, b), vec_list in direction_constraints.items():
            i, j = loc_index[a], loc_index[b]
            xi, yi = coords[i]
            xj, yj = coords[j]
            dx, dy = xj - xi, yj - yi
            norm = np.sqrt(dx*dx + dy*dy) + 1e-6
            weight = distance_lookup.get((a, b), avg_distance)

            for vec, _ in vec_list:  # iterate over all valid vectors
                res.append(weight * ((dx / norm) - vec[0]))
                res.append(weight * ((dy / norm) - vec[1]))

        # Repulsion residuals (soft constraint)
        MIN_DIST = 15.0  # change depending on map scale
        for i in range(len(coords)):
            for j in range(i + 1, len(coords)):
                dx = coords[i, 0] - coords[j, 0]
                dy = coords[i, 1] - coords[j, 1]
                dist = np.sqrt(dx * dx + dy * dy) + 1e-6
                # Penalize overlap more strongly the closer they get while keeping residual length constant
                res.append(max(0.0, (MIN_DIST - dist) / MIN_DIST))

        # This section encourages the points to not be in a straight line
        if len(coords) >= 3:
            xs = coords[:, 0]
            ys = coords[:, 1]
            var_x = np.var(xs)
            var_y = np.var(ys)

            # If variance along one axis dominates (line-like), penalize it
            if var_x > 1e-6 and var_y > 1e-6:
                ratio = max(var_x, var_y) / (min(var_x, var_y) + 1e-6)
                res.append(0.01 * ratio)

        dirs = np.array([vec for vec_list in direction_constraints.values() for vec, _ in vec_list])
        if len(dirs) > 1:
            mean_dir = np.mean(dirs, axis=0)
            spread = np.mean(np.linalg.norm(dirs - mean_dir, axis=1))
            res.append(0.01 / (spread + 1e-3))

        return res

    # Initial guess
    x0 = (np.random.rand(len(locations) * 2) - 0.5) * 500


    if len(locations) > 1:
        d = distances.get((locations[0], locations[1]),
                      distances.get((locations[1], locations[0]), (1.0, None)))
        d = d[0]
        theta = np.random.rand() * 2 * np.pi
        x0[2], x0[3] = d * np.cos(theta), d * np.sin(theta)

    result = least_squares(residuals, x0)

    coords_array = result.x.reshape(-1, 2)
    coords = {name: tuple(coord) for name, coord in zip(locations, coords_array)}

    updated_distances = {}

    for (l1, l2), (orig_d, entry) in distances.items():
        if l1 in coords and l2 in coords:
            (x1, y1), (x2, y2) = coords[l1], coords[l2]
            modelled_d = np.sqrt((x1 - x2)**2 + (y1 - y2)**2)
            updated_distances[(l1, l2)] = (modelled_d, entry)
        else:
            updated_distances[(l1, l2)] = (orig_d, entry)

    return coords, updated_distances

def check_conflicts(distances):
    kept = {}
    conflicts = {}

    for pair, dist_list in distances.items():
        key = tuple(sorted(pair))
        first = dist_list[0]

        # Supports both 2-tuple and 3-tuple forms
        if len(first) == 3:
            base_distance, base_entry, base_type = first
        else:
            base_distance, base_entry = first
            base_type = "real"

        kept[key] = (base_distance, base_entry)

        # Check the rest for conflicts
        for dset in dist_list[1:]:
            if len(dset) == 3:
                d, entry, dtype = dset
            else:
                d, entry = dset
                dtype = "real"

            # Only treat as a conflict if both are real (skip default/default)
            if base_type == "real" and dtype == "real" and not np.isclose(d, base_distance, rtol=1e-5, atol=1e-5):
                conflicts.setdefault(key, [(base_distance, base_entry)]).append((d, entry))

    return kept, conflicts

def extract_all_conflict_sentence_pairs(distance_conflicts, direction_conflicts):
    """
    Extracts sentence pairs for both distance and direction conflicts.
    
    Args:
        distance_conflicts: dict from check_conflicts() 
        direction_conflicts: dict from get_direction_constraints()
    
    Returns:
        List of tuples: (sentence1, sentence2)
    """
    def extract_pairs(conflicts):
        grouped = []
        for entries in conflicts.values():
            sentences = []

            for entry in entries:
                if len(entry) == 3:
                    _, entry_list, _ = entry
                else:
                    _, entry_list = entry

                if not entry_list:
                    continue

                raw = str(entry_list[0]).strip()
                clean = raw.split(": ", 1)[1] if ": " in raw else raw
                sentences.append(clean)

            if len(sentences) < 2:
                continue

            base = sentences[0]
            for other in sentences[1:]:
                grouped.append((base, other))
        return grouped

    distance_pairs = extract_pairs(distance_conflicts)
    direction_pairs = extract_pairs(direction_conflicts)

    return distance_pairs + direction_pairs

def remove_exact_duplicate_pairs(pairs):
    seen = set()
    unique = []
    for a, b in pairs:
        if (a, b) not in seen:
            unique.append((a, b))
            seen.add((a, b))
    return unique