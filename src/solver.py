import numpy as np
from scipy.optimize import least_squares

#GET COORDINATES

def get_coords(locations, distances, direction_constraints):
    # Map location names to indices
    loc_index = {loc: i for i, loc in enumerate(locations)}

    def residuals(coords):
        coords = coords.reshape(-1, 2)
        res = []
        # Distance matching residuals
        for (l1, l2), d in distances.items():
            i, j = loc_index[l1], loc_index[l2]
            xi, yi = coords[i]
            xj, yj = coords[j]
            res.append(np.sqrt((xi - xj)**2 + (yi - yj)**2) - d)

        for (a, b), vec in direction_constraints.items():
            i, j = loc_index[a], loc_index[b]
            xi, yi = coords[i]
            xj, yj = coords[j]
            dx, dy = xj - xi, yj - yi
            norm = np.sqrt(dx*dx + dy*dy) + 1e-6
            dot = (dx/norm)*vec[0] + (dy/norm)*vec[1]
            res.append(0.5 * (1 - dot))

        # Repulsion residuals (soft constraint)
        for i in range(len(coords)):
            for j in range(i+1, len(coords)):
                dx = coords[i,0] - coords[j,0]
                dy = coords[i,1] - coords[j,1]
                dist = np.sqrt(dx*dx + dy*dy)
                if dist < 1e-3:  # if too close, push apart
                    res.append(1.0 / (dist + 1e-6))
        return res

    # Initial guess
    # x0 = np.random.rand(len(locations) * 2)
    x0 = (np.random.rand(len(locations) * 2) - 0.5) * 500

    # Anchor first two points
    # x0[0], x0[1] = 0.0, 0.0  # first location at origin
    # if len(locations) > 1:
    #     d = distances.get((locations[0], locations[1]),
    #                       distances.get((locations[1], locations[0]), 1.0))
    #     x0[2], x0[3] = d, 0.0  # second location on x-axis

    if len(locations) > 1:
        d = distances.get((locations[0], locations[1]),
                      distances.get((locations[1], locations[0]), 1.0))
        theta = np.random.rand() * 2 * np.pi
        x0[2], x0[3] = d * np.cos(theta), d * np.sin(theta)
    

    # Solve
    result = least_squares(residuals, x0)

    coords_array = result.x.reshape(-1, 2)
    coords = {name: tuple(coord) for name, coord in zip(locations, coords_array)}

    return coords

def check_conflicts(distances):
    kept = {}
    conflicts = {}
    for pair, dist_list in distances.items():
        key = tuple(sorted(pair))
        if key not in kept:
            kept[key] = dist_list[0]
            if len(dist_list) > 1:
                # additional entries beyond the first are potential conflicts
                for v in dist_list[1:]:
                    if not np.isclose(v, kept[key], rtol=1e-5, atol=1e-5):
                        conflicts[key] = [kept[key], v]
        else:
            for v in dist_list:
                if not np.isclose(v, kept[key], rtol=1e-5, atol=1e-5):
                    # print(f"⚠️ Conflict detected between {a} and {b}: "
                        #       f"{kept[key]} vs {d}")
                    conflicts.setdefault(key, [kept[key]]).append(v)
    return kept, conflicts

