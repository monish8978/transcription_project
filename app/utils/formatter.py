def clean_text(text: str) -> str:
    text = text.strip()
    words = []
    prev = None

    for w in text.split():
        if w.lower() != prev:
            words.append(w)
        prev = w.lower()

    return " ".join(words)


def format_conversation(data):
    utterances = data.get("results", {}).get("utterances", [])
    role_map = {}
    results = []

    def get_role(speaker_id):
        if speaker_id not in role_map:
            role_map[speaker_id] = "agent" if len(role_map) == 0 else "customer"
        return role_map[speaker_id]

    for utt in utterances:
        text = (utt.get("transcript") or "").strip()
        speaker = utt.get("speaker", 0)

        if not text:
            continue

        results.append({
            "role": get_role(speaker),
            "text": clean_text(text)
        })

    return results


def pair_conversation(conversation):
    paired = []
    current = {"agent": None, "customer": None}

    for item in conversation:
        if item["role"] == "agent":
            if current["agent"] and current["customer"]:
                paired.append(current.copy())
                current = {"agent": None, "customer": None}
            current["agent"] = item["text"]
        else:
            current["customer"] = item["text"]

    if current["agent"] and current["customer"]:
        paired.append(current)

    return paired