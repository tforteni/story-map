from src import extractor, solver, visualizer, config #maybe i can delete config

def generate_map(text, with_routes=1):
    travel_info = extractor.get_all_travel_info(text)
    extractor.pretty_print_travel_info(travel_info)
    # print(travel_info)

    locations = extractor.get_all_locations(travel_info) #don't worry about this for now
    all_distances = extractor.get_distances(travel_info)
    (direction_constraints, direction_conflicts) = extractor.get_direction_constraints(travel_info)

    (distances, conflicts) = solver.check_conflicts(all_distances)

    (coords, distances) = solver.get_coords(locations, distances, direction_constraints)
    map_file_path = visualizer.plot_map(coords, distances, conflicts, direction_conflicts, with_routes)

    return map_file_path
