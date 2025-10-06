def extract_travel_info(text: str) -> dict:
    # run NER (spaCy + fallback to LLM)
    # return dict with {origin, destination, mode, duration_days}
    ...

from transformers import pipeline, logging
import spacy
import re
from word2number import w2n
import numpy as np

logging.set_verbosity_error()

walking_pace = 20

DIRECTION_PATTERNS = [
    {
        "type": "travel",
        "verbs": {"go", "move", "travel", "journey", "walk", "ride", "head"},
        "direction_modifier": {"advmod", "npadvmod", "prep", "attr"},
        "origin_prep": "from",
        "dest_prep": {"to", "toward", "into"},
        "invert": False
    },
    {
        "type": "positional",
        "verbs": {"be", "lie"},
        "direction_prep": "prep",  # e.g. "is south of"
        "ref_prep": "of",
        "invert": True
    },
    {
        "type": "region",
        "verbs": {"go", "move", "travel", "head"},
        "main_prep": {"to", "toward"},
        "region_prep": "of",
        "invert": False
    }
]

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
            # distances[pair] = segment_distance
            distances.setdefault(pair, []).append(segment_distance)
    return distances

def get_all_travel_info(paragraph: str):
    # Extract travel events from a paragraph. Combines information that may be spread across sentences, e.g. 'They went from Callahan to Rivenfell. It took 30 days.'
    nlp = spacy.load("en_core_web_sm")

    ner = pipeline(
        "ner",
        model="dbmdz/bert-large-cased-finetuned-conll03-english",
        aggregation_strategy="simple"
    )

    doc = nlp(paragraph)
    sent_infos = [extract_travel_info(sent.text, nlp, ner) for sent in doc.sents]

    merged = []
    current = None

    for info in sent_infos:
        has_path = bool(info.get("locations"))
        has_date = bool(info.get("date"))
        has_direction = bool(info.get("directions"))

        # Case 1: New travel segment begins
        if has_path or has_direction:
            if current:
                merged.append(current)
            current = {
                "locations": info.get("locations", []),
                "date": info.get("date", []),
                "directions": info.get("directions", []),
            }

        # Case 2: Continuation of previous segment (e.g. "It took 30 days")
        # This wouldn't also append like "The journey took them south." I'm not sure if I should make it do so
        elif has_date and current:
            current["date"].extend(info["date"])

        # Case 3: look for adverbs like 'then', 'afterward' to extend current segment
        elif current:
            text_lower = " ".join([t.lower() for t in info.get("date", [])]) + " " + info.get("locations", [None])[0] if info.get("locations") else ""
            if any(word in text_lower for word in ["then", "after", "next", "afterward", "later"]):
                continue

    # Append final segment if any
    if current:
        merged.append(current)

    return merged

TRAVEL_WORDS = {"travel", "journey", "go", "went", "ride", "rode", "walk", "moved"}

DIRECTION_WORDS = {
    "north": (0, 1),
    "south": (0, -1),
    "east": (1, 0),
    "west": (-1, 0),
    "northeast": (np.sqrt(0.5), np.sqrt(0.5)),
    "northwest": (-np.sqrt(0.5), np.sqrt(0.5)),
    "southeast": (np.sqrt(0.5), -np.sqrt(0.5)),
    "southwest": (-np.sqrt(0.5), -np.sqrt(0.5))
}

def get_direction_constraints(all_info):
    constraints = {}
    for entry in all_info:
        for (a, b, dir_name) in entry.get("directions", []):
            constraints[(a, b)] = DIRECTION_WORDS[dir_name]
    return constraints

INVERSE_DIRECTION = {
    "north": "south",
    "south": "north",
    "east": "west",
    "west": "east",
    "northeast": "southwest",
    "northwest": "southeast",
    "southeast": "northwest",
    "southwest": "northeast"
}

def extract_directions(sent_doc, all_locations):
    directions = []

    for token in sent_doc:
        lemma = token.lemma_.lower()

        for rule in DIRECTION_PATTERNS:
            if lemma not in rule["verbs"]:
                continue

            # --- Travel pattern ---
            if rule["type"] == "travel":
                dir_word = None
                for child in token.children:
                    if child.dep_ in rule["direction_modifier"] and child.text.lower() in DIRECTION_WORDS:
                        dir_word = child.text.lower()
                if not dir_word:
                    continue

                origin, dest = None, None
                for child in token.children:
                    if child.dep_ == "prep":
                        if child.lemma_ == rule["origin_prep"]:
                            for pobj in child.children:
                                if pobj.text in all_locations:
                                    origin = pobj.text
                        elif child.lemma_ in rule["dest_prep"]:
                            for pobj in child.children:
                                if pobj.text in all_locations:
                                    dest = pobj.text

                if origin and dest:
                    directions.append((origin, dest, dir_word))

            # --- Positional pattern --- 
            elif rule["type"] == "positional":
                subj = None
                dir_word = None
                obj = None
                for child in token.children:
                    if child.dep_ == "nsubj" and child.text in all_locations:
                        subj = child.text
                    if child.dep_ == rule["direction_prep"] and child.text.lower() in DIRECTION_WORDS:
                        dir_word = child.text.lower()
                        for gc in child.children:
                            if gc.dep_ == "pobj" and gc.text in all_locations:
                                obj = gc.text
                if subj and obj and dir_word:
                    direction = INVERSE_DIRECTION[dir_word] if rule["invert"] else dir_word
                    directions.append((obj, subj, direction))

            # --- Region pattern ("to/toward the north of X") ---
            elif rule["type"] == "region":
                for child in token.children:
                    if child.dep_ == "prep" and child.lemma_ in rule["main_prep"]:
                        direction_word, ref_loc = None, None
                        for g in child.children:
                            if g.text.lower() in DIRECTION_WORDS:
                                direction_word = g.text.lower()
                                for gg in g.children:
                                    if gg.dep_ == "prep" and gg.lemma_ == rule["region_prep"]:
                                        for pobj in gg.children:
                                            if pobj.text in all_locations:
                                                ref_loc = pobj.text
                        if direction_word and ref_loc:
                            synthetic = f"{direction_word}_of_{ref_loc}"
                            directions.append((ref_loc, synthetic, direction_word))
    return directions

def extract_travel_info(text, nlp, ner) -> dict:
    info = {}

    entities = ner(text)

    # info["locations"] = [ent["word"] for ent in entities if ent.get("entity_group") == "LOC"]
    all_locations = [ent["word"] for ent in entities if ent.get("entity_group") == "LOC"]

    sent_doc = nlp(text)
    # for token in sent_doc:
    #     print(token.text, token.dep_, token.head.text, token.pos_)

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
    info["directions"] = extract_directions(sent_doc, all_locations)
    # print(info["directions"])
    return info

def pretty_print_travel_info(all_info):
    for i, info in enumerate(all_info, start=1):
        print(f"--- Sentence {i} ---")
        locations = ", ".join(info["locations"]) if info["locations"] else "None"
        print(f"Locations: {locations}")
        print(f"Dates: {info["date"]}")
        print(f"Direction: {info["directions"]}")
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