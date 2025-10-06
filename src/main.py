import sys
from src import extractor, solver, visualizer

# usage: python3 -m src.main INPUT_FILE WITH_ROUTES(1 or 0)
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
    # print(travel_info)

    locations = extractor.get_all_locations(travel_info) #don't worry about this for now
    all_distances = extractor.get_distances(travel_info)
    direction_constraints = extractor.get_direction_constraints(travel_info)

    (distances, conflicts) = solver.check_conflicts(all_distances)

    coords = solver.get_coords(locations,distances, direction_constraints)
    visualizer. plot_map(coords, distances, conflicts, with_routes)


if __name__=="__main__":
    main()