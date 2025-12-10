from src import extractor, solver, terrain_renderer

def generate_map(text, with_routes=1):
    travel_info = extractor.get_all_travel_info(text)
    # extractor.pretty_print_travel_info(travel_info)

    locations = extractor.get_all_locations(travel_info)
    all_distances = extractor.get_distances(travel_info)
    (direction_constraints, direction_conflicts) = extractor.get_direction_constraints(travel_info)

    (distances, conflicts) = solver.check_conflicts(all_distances)

    (coords, distances) = solver.get_coords(locations, distances, direction_constraints)
    map_file_path = terrain_renderer.draw_terrain(coords, distances, conflicts, direction_conflicts, with_routes)

    all_conflicts = solver.remove_exact_duplicate_pairs(solver.extract_all_conflict_sentence_pairs(conflicts, direction_conflicts))

    return map_file_path, all_conflicts
