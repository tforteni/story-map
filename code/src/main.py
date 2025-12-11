import sys
from src import extractor, solver, terrain_renderer_local

# usage: python3 -m src.main INPUT_FILE WITH_ROUTES(1 or 0)
# e.g. python3 -m src.main data/example1.txt 1
def main():
    file = sys.argv[1]
    with_routes = int(sys.argv[2]) if len(sys.argv) == 3 else 0
    try:
        with open(file, "r") as f:
            text = f.read()
    except FileNotFoundError:
        print(f"Error: File '{file}' not found.")

    travel_info = extractor.get_all_travel_info(text)
    extractor.pretty_print_travel_info(travel_info)

    locations = extractor.get_all_locations(travel_info)
    all_distances = extractor.get_distances(travel_info)
    (direction_constraints, direction_conflicts) = extractor.get_direction_constraints(travel_info)

    (distances, conflicts) = solver.check_conflicts(all_distances)

    (coords, distances) = solver.get_coords(locations, distances, direction_constraints)
    map_file_path = terrain_renderer_local.draw_terrain(coords, distances, conflicts, direction_conflicts, with_routes)

    all_conflicts = solver.remove_exact_duplicate_pairs(solver.extract_all_conflict_sentence_pairs(conflicts, direction_conflicts))
    print("Conflicts: ")
    if all_conflicts:
        print(all_conflicts)
    else:
        print("None")
    return map_file_path, all_conflicts

if __name__=="__main__":
    main()