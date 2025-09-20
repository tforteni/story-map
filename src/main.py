import sys
from src import extractor

def main():
    file = sys.argv[1]
    try:
        with open(file, "r") as f:
            text = f.read()
    except FileNotFoundError:
        print(f"Error: File '{file}' not found.")

    travel_info = extractor.get_all_travel_info(text)
    # extractor.pretty_print_travel_info(travel_info)
    print(travel_info)

    location_pairs = extractor.get_location_pairs(text)
    print(location_pairs)


if __name__=="__main__":
    main()