def extract_travel_info(text: str) -> dict:
    # run NER (spaCy + fallback to LLM)
    # return dict with {origin, destination, mode, duration_days}
    ...

from transformers import pipeline, logging
import spacy

logging.set_verbosity_error()

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
    