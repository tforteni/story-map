def extract_travel_info(text: str) -> dict:
    # run NER (spaCy + fallback to LLM)
    # return dict with {origin, destination, mode, duration_days}
    ...