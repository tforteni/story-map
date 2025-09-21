def extract_travel_info(text: str) -> dict:
    # run NER (spaCy + fallback to LLM)
    # return dict with {origin, destination, mode, duration_days}
    ...

from transformers import pipeline, logging
import spacy
import re
from word2number import w2n

logging.set_verbosity_error()

walking_pace = 20

def get_all_locations(travel_info):
    locs = set()
    for entry in travel_info:
        for loc in entry["locations"]:
            locs.add(loc)
    return sorted(locs)

def get_distances(travel_info):
    distances = {}
    for entry in travel_info:
        locs = entry['locations']
        #HARD CODED DEFAULT - This is the default distance that maybe can later be implemented to take context in
        # if not entry['date']:
        #     # continue
        date_text = entry['date'][0] if entry['date'] else "10 days"
        total_distance = days_to_distance(days(date_text), walking_pace)
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

TRAVEL_WORDS = {"travel", "journey", "go", "went", "ride", "rode", "walk", "moved"}

def extract_travel_info(text, nlp, ner) -> dict:
    info = {}

    entities = ner(text)

    # info["locations"] = [ent["word"] for ent in entities if ent.get("entity_group") == "LOC"]
    all_locations = [ent["word"] for ent in entities if ent.get("entity_group") == "LOC"]

    sent_doc = nlp(text)

    info["date"] = [ent.text for ent in sent_doc.ents if ent.label_ in ("DATE", "TIME")]
    # print(f"\nText: {text}")
    # print(f"Locations: {info["locations"]}")
    # print(f"Dates: {info["date"]}")

    locations = []
    for token in sent_doc:
        if token.lemma_.lower() in TRAVEL_WORDS:
            # Look at prepositions attached to the verb
            for child in token.children:
                if child.dep_ == "prep" and child.lemma_ in ("from", "to", "toward", "into"):
                    for pobj in child.children:
                        # if pobj.ent_type_ in ("LOC", "GPE"):
                        if pobj.text in all_locations:
                            locations.append(pobj.text)
    info["locations"] = locations
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
    if not time_text:
        return None
    
    if re.match(r"^(a|one)\s+day", time_text):
        return 1
    if re.match(r"^(a|one)\s+week", time_text):
        return 7
    if re.match(r"^(a|one)\s+month", time_text):
        return 30
    if re.match(r"^(a|one)\s+year", time_text):
        return 365
    if match := re.match(r"(\d+)\s*day", time_text):
        return int(match.group(1))
    if match := re.match(r"(\d+)\s*week", time_text):
        return int(match.group(1)) * 7
    if match := re.match(r"(\d+)\s*month", time_text):
        return int(match.group(1)) * 30
    if match := re.match(r"(\d+)\s*year", time_text):
        return int(match.group(1)) * 365

    try:
        tokens = time_text.split()
        num = w2n.word_to_num(tokens[0])  # e.g. "ten" → 10
        unit = tokens[1]
        if "day" in unit:
            return num
        if "week" in unit:
            return num * 7
        if "month" in unit:
            return num * 30
        if "year" in unit:
            return num * 365
    except Exception:
        return None

def days_to_distance(days, pace):
    return days * pace