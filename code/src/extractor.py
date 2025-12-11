def extract_travel_info(text: str) -> dict:
    # run NER (spaCy + fallback to LLM)
    # return dict with {origin, destination, mode, duration_days}
    ...

from transformers import pipeline, logging
import spacy
import re
from word2number import w2n
import numpy as np
from collections import defaultdict
from src import config

class Entry:
    sentence_count = 1
    def __init__(self, sentence):
        self.sentence_id = Entry.sentence_count
        self.sentence = sentence
        self.sent_info = []
        Entry.sentence_count += 1
    
    def __repr__(self):
        return f"Sentence {self.sentence_id}: {self.sentence}"

sentence_count = 0

logging.set_verbosity_error()

walking_pace = 20
DEFAULT_DAYS = 10  # number of days to assume when none given
def default_distance():
    return days_to_distance(DEFAULT_DAYS, walking_pace)

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
        "direction_modifier": {"advmod", "npadvmod", "prep", "attr"},  # e.g. "is south of"
        "ref_prep": "of",
        "invert": False
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
        for (a, b, *_) in entry.get("directions", []):
            locs.add(a)
            locs.add(b)
    return sorted(locs)

def get_distances(travel_info):
    distances = {}

    for info in travel_info:
        entry = info["entry"]
        locs = info['locations']

        # Compute real distance if date present
        is_real = bool(info['date'])
        if is_real:
            date_text = info['date'][0]
            total_distance = days_to_distance(days(date_text), walking_pace)
        else:
            total_distance = days_to_distance(days(f"{DEFAULT_DAYS} days"), walking_pace)

        segments = len(locs) - 1
        if segments > 0:
            segment_distance = total_distance / segments
            for i in range(segments):
                pair = tuple(sorted((locs[i], locs[i + 1]))) 
                
                if pair not in distances:
                    distances[pair] = [(segment_distance, entry, "real" if is_real else "default")]

                else:
                    prev_d, prev_entry, prev_type = distances[pair][0]

                    if prev_type == "default" and is_real:
                        distances[pair] = [(segment_distance, entry, "real")]

                    elif prev_type == "real" and is_real:
                        distances[pair].append((segment_distance, entry, "real"))

        # Fallback for direction-only sentences
        if not info.get("date"):
            for (a, b, _) in info.get("directions", []):
                pair = (a, b)
                if pair not in distances:
                    distances[pair] = [(default_distance(), entry, "default")]

    return distances

def get_all_travel_info(paragraph: str):
    """
    Extracts and merges travel events that may be spread across sentences.
    Handles:
      - duration follow-ups ("It took 30 days.")
      - conflicting durations ("It took 30 days. It took 2 days.")
      - direction follow-ups ("A is north of B.")
      - conflicting directions ("A is north of B. A is south of B.")
    """

    config.all_entries = {} # clear past sentences
    Entry.sentence_count = 1

    nlp = spacy.load("en_core_web_sm")
    ner = pipeline(
        "ner",
        model="dbmdz/bert-large-cased-finetuned-conll03-english",
        aggregation_strategy="first"
    )

    doc = nlp(paragraph)

    for sent in doc.sents:
        id = Entry.sentence_count
        entry = Entry(sent.text)
        config.all_entries[id] = entry
        entry.sent_info = extract_travel_info(sent.text, nlp, ner)

    merged = []
    current = None
    conflicts = []
    current_has_date = False
    current_has_direction = False

    for entry in config.all_entries.values():
        info = entry.sent_info
        has_path = bool(info.get("locations"))
        has_date = bool(info.get("date"))
        has_direction = bool(info.get("directions"))

        # New trip begins
        if has_path or has_direction:
            if current:
                merged.append(current)
                merged += conflicts
                conflicts = []
            current = {
                "locations": info.get("locations", []),
                "date": info.get("date", []),
                "directions": info.get("directions", []),
                "entry": [entry],
            }
            current_has_date = bool(info.get("date"))
            current_has_direction = bool(info.get("directions"))

        elif has_date and current:
            if not current_has_date:
                current["date"].extend(info["date"])
                current_has_date = True
                current["entry"].append(entry),
            else:
                # conflicting duration → new entry
                conflicts.append({
                    "locations": current["locations"],
                    "date": info["date"],
                    "directions": current["directions"],
                    "entry": [entry],
                })

        elif has_direction and current:
            new_dir = info["directions"]
            if not current_has_direction:
                # first direction → attach it
                current["directions"].extend(new_dir)
                current_has_direction = True
                current["entry"].append(entry),
            else:
                # conflicting direction → new entry
                conflicts.append({
                    "locations": current["locations"],
                    "date": current["date"],
                    "directions": new_dir,
                    "entry": [entry],
                })

    if current:
        merged.append(current)
        merged += conflicts

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
    constraints = defaultdict(list)
    conflicts = defaultdict(list)

    for info in all_info:
        entry = info["entry"]

        for (a, b, dir_name) in info.get("directions", []):
            s_key = tuple(sorted((a, b)))
            vec = DIRECTION_WORDS[dir_name]

            if (a, b) != s_key:
                vec = (-vec[0], -vec[1])  # flip direction to match s_key

            is_conflict = False
            for existing_vec, existing_entry in constraints[s_key]:
                x_conflict = existing_vec[0] != 0 and vec[0] != 0 and np.sign(existing_vec[0]) != np.sign(vec[0])
                y_conflict = existing_vec[1] != 0 and vec[1] != 0 and np.sign(existing_vec[1]) != np.sign(vec[1])

                if x_conflict or y_conflict:
                    conflicts.setdefault(s_key, [(existing_vec, existing_entry)]).append((vec, entry))
                    is_conflict = True
                    break

            if not is_conflict:
                constraints[s_key].append((vec, entry))

    return constraints, conflicts

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

            if rule["type"] == "travel":
                dir_word = None
                origin, dest = None, None

                for child in token.children:
                    if child.dep_ in rule["direction_modifier"] and child.text.lower() in DIRECTION_WORDS:
                        dir_word = child.text.lower()

                        for gchild in child.subtree:
                            if gchild.dep_ == "prep" and gchild.lemma_ in ("from", "to", "toward", "into"):
                                for pobj in gchild.children:
                                    if pobj.text in all_locations:
                                        if gchild.lemma_ == "from":
                                            origin = pobj.text
                                        elif gchild.lemma_ in ("to", "toward", "into"):
                                            dest = pobj.text

                if not origin or not dest:
                    for child in token.children:
                        if child.dep_ == "prep" and child.lemma_ in ("from", "to", "toward", "into"):
                            for pobj in child.children:
                                if pobj.text in all_locations:
                                    if child.lemma_ == "from":
                                        origin = pobj.text
                                    elif child.lemma_ in ("to", "toward", "into"):
                                        dest = pobj.text

                if origin and dest and dir_word:
                    directions.append((origin, dest, dir_word))

            elif rule["type"] == "positional":
                subj = None
                dir_word = None
                obj = None
                if token.dep_ == "relcl" or token.lemma_.lower() in rule["verbs"]:
                    for child in token.children:
                        if child.dep_ == "nsubj" and child.text in all_locations:
                            subj = child.text
                        if child.text.lower() in DIRECTION_WORDS:
                            dir_word = child.text.lower()
                            for gc in child.subtree:
                                if gc.dep_ == "prep" and gc.lemma_ == rule["ref_prep"]:
                                    for pobj in gc.children:
                                        if pobj.dep_ == "pobj" and pobj.text in all_locations:
                                            obj = pobj.text
                    if not subj and token.head.text in all_locations:
                        subj = token.head.text

                    if subj and obj and dir_word:
                        direction = INVERSE_DIRECTION[dir_word] if rule["invert"] else dir_word
                        directions.append((obj, subj, direction))

    return directions

def extract_travel_info(text, nlp, ner) -> dict:
    info = {}

    entities = ner(text)

    all_locations = [ent["word"] for ent in entities if ent.get("entity_group") == "LOC"]

    sent_doc = nlp(text)
    # Debug text
    # for token in sent_doc:
    #     print(token.text, token.dep_, token.head.text, token.pos_)

    info["date"] = [ent.text for ent in sent_doc.ents if ent.label_ in ("DATE", "TIME")]

    locations = set()

    for token in sent_doc:
        if token.lemma_.lower() in TRAVEL_WORDS:
            travel_verb = token
        elif token.head.lemma_.lower() in TRAVEL_WORDS:
            travel_verb = token.head
        else:
            continue
   
        for child in travel_verb.children:
            if child.dep_ == "prep" and child.lemma_ in ("from", "to", "toward", "into"):
                for pobj in child.children:
                    if pobj.text in all_locations:
                        locations.add(pobj.text)

        for child in travel_verb.children:
            if child.text.lower() in DIRECTION_WORDS:
                for gchild in child.subtree:
                    if gchild.dep_ == "prep" and gchild.lemma_ in ("from", "to", "toward", "into"):
                        for pobj in gchild.children:
                            if pobj.text in all_locations:
                                locations.add(pobj.text)

    info["locations"] = list(locations)
    info["directions"] = extract_directions(sent_doc, all_locations)
    return info


def pretty_print_travel_info(all_info):
    for i, info in enumerate(all_info, start=1):
        print(f"--- Sentence {i} ---")
        locations = ", ".join(info["locations"]) if info["locations"] else "None"
        print(f"Locations: {locations}")
        print(f"Dates: {info["date"]}")
        print(f"Direction: {info["directions"]}")
        print(f"Entry: {info["entry"]}")
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
        num = w2n.word_to_num(tokens[0])
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