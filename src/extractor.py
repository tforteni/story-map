def extract_travel_info(text: str) -> dict:
    # run NER (spaCy + fallback to LLM)
    # return dict with {origin, destination, mode, duration_days}
    ...

from transformers import pipeline, logging
import spacy
import re

logging.set_verbosity_error()

walking_pace = 20

def get_all_locations(all_info):
    locs = set()
    for entry in all_info:
        for loc in entry["locations"]:
            locs.add(loc)
    return sorted(locs)

def get_location_pairs(text: str):
    info = get_all_travel_info(text)
    distances = {}
    for entry in info:
        locs = entry['locations']
        if not entry['date']:
            continue
        total_distance = days_to_distance(days(entry['date'][0]), walking_pace)
        segments = len(locs) - 1
        if segments == 0:
            continue
        segment_distance = total_distance / segments
        for i in range(segments):
            pair = (locs[i], locs[i+1])
            distances[pair] = segment_distance
    return distances

def get_all_travel_info(paragraph: str):
    all_info = []
    nlp = spacy.load("en_core_web_sm")

    ner = pipeline(
        "ner",
        model="dbmdz/bert-large-cased-finetuned-conll03-english",
        aggregation_strategy="simple"
    )

    doc = nlp(paragraph)
    all_info = [extract_travel_info(sent.text, nlp, ner) for sent in doc.sents]
    return all_info

def extract_travel_info(text, nlp, ner) -> dict:
    info = {}

    entities = ner(text)

    info["locations"] = [ent["word"] for ent in entities if ent.get("entity_group") == "LOC"]

    sent_doc = nlp(text)

    info["date"] = [ent.text for ent in sent_doc.ents if ent.label_ in ("DATE", "TIME")]
    # print(f"\nText: {text}")
    # print(f"Locations: {info["locations"]}")
    # print(f"Dates: {info["date"]}")
    return info

def pretty_print_travel_info(all_info):
    for i, info in enumerate(all_info, start=1):
        print(f"--- Sentence {i} ---")
        locations = ", ".join(info["locations"]) if info["locations"] else "None"
        dates = ", ".join(info["date"]) if info["date"] else "None"
        print(f"Locations: {locations}")
        print(f"Dates: {dates}")
        print()
    
def days(time_text: str) -> int | None:
    if re.match(r"^(a|one)\s+week", time_text):
        return 7
    if match := re.match(r"(\d+)\s*day", time_text):
        return int(match.group(1))
    if match := re.match(r"(\d+)\s*week", time_text):
        return int(match.group(1)) * 7
    if match := re.match(r"(\d+)\s*month", time_text):
        return int(match.group(1)) * 30
    if match := re.match(r"(\d+)\s*year", time_text):
        return int(match.group(1)) * 365

    return None

def days_to_distance(days, pace):
    return days * pace