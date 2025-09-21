import sys
from src import extractor, solver, visualizer

def main():
    file = sys.argv[1]
    try:
        with open(file, "r") as f:
            text = f.read()
    except FileNotFoundError:
        print(f"Error: File '{file}' not found.")

    travel_info = extractor.get_all_travel_info(text)
    extractor.pretty_print_travel_info(travel_info)
    # print(travel_info)

    locations = extractor.get_all_locations(travel_info) 
    distances = extractor.get_distances(travel_info)
    print(distances)

    coords = solver.get_coords(locations,distances)
    visualizer. plot_map(coords, distances, True)


if __name__=="__main__":
    main()