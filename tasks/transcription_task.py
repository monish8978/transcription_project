import os
import asyncio
from celery_app import celery
from app.services.deepgram_service import process_audio
from app.logger import log


def run_async(func, *args):
    return asyncio.run(func(*args))


# =========================
# ROLE CLASSIFIER (HYBRID)
# =========================
def classify_role(text: str, is_first_block=False):
    t = text.lower()

    agent_keywords = [
        "sir", "ma'am", "policy", "insurance", "premium",
        "dob", "verification", "cashless", "coverage",
        "benefit", "plan", "claim"
    ]

    customer_keywords = [
        "what", "how", "why", "कितना", "क्या",
        "i want", "problem", "confused", "not sure",
        "बताइए", "help"
    ]

    agent_score = sum(k in t for k in agent_keywords)
    customer_score = sum(k in t for k in customer_keywords)

    # first speaker bias (call usually starts with agent)
    if is_first_block:
        return "agent"

    if agent_score > customer_score:
        return "agent"
    elif customer_score > agent_score:
        return "customer"

    # fallback heuristic
    return "customer"


# =========================
# TRANSCRIPT FORMATTER
# =========================
def format_transcript(dg_response):
    try:
        log.info("Formatting transcript from Deepgram response using word-level diarization")

        # 1. Extract all words from all channels
        all_words = []
        channels = dg_response.get("results", {}).get("channels", [])
        for ch_idx, ch in enumerate(channels):
            alts = ch.get("alternatives", [])
            if alts:
                words = alts[0].get("words", [])
                for w in words:
                    spk = w.get("speaker")
                    if spk is None:
                        spk = 0
                    all_words.append({
                        "word": w.get("punctuated_word") or w.get("word") or "",
                        "start": w.get("start", 0),
                        "end": w.get("end", 0),
                        "speaker": spk,
                        "channel": ch_idx
                    })

        if not all_words:
            log.warning("No words found in Deepgram response. Returning empty.")
            return []

        # Sort words chronologically
        all_words.sort(key=lambda x: x["start"])

        # Determine whether to group by channel or speaker
        unique_channels = set(w["channel"] for w in all_words)
        use_channel = len(unique_channels) > 1

        # 2. Group words into turns/utterances
        utterances = []
        current_spk = all_words[0]["channel"] if use_channel else all_words[0]["speaker"]
        current_words = [all_words[0]["word"]]
        current_start = all_words[0]["start"]
        current_end = all_words[0]["end"]

        for w in all_words[1:]:
            spk = w["channel"] if use_channel else w["speaker"]
            
            # Start a new turn if speaker changes or there is a large silence gap (> 4.0s)
            if spk == current_spk and (w["start"] - current_end) < 4.0:
                current_words.append(w["word"])
                current_end = w["end"]
            else:
                utterances.append({
                    "speaker": current_spk,
                    "transcript": " ".join(current_words),
                    "start": current_start,
                    "end": current_end
                })
                current_spk = spk
                current_words = [w["word"]]
                current_start = w["start"]
                current_end = w["end"]

        utterances.append({
            "speaker": current_spk,
            "transcript": " ".join(current_words),
            "start": current_start,
            "end": current_end
        })

        # Build full text for each speaker/channel to run classification
        speaker_texts = {}
        for utt in utterances:
            spk = utt.get("speaker")
            if spk is None:
                spk = 0
            text = (utt.get("transcript") or "").lower()
            speaker_texts[spk] = speaker_texts.get(spk, "") + " " + text

        # Keywords for channel/speaker classification (Weighted scoring)
        import re

        agent_high_confidence = [
            "calling from", "thank you for calling", "welcome to", "how can i help",
            "how can i assist", "speaking with", "may i know", "may i have",
            "please confirm", "for connecting", "help you today", "my name is",
            "i am calling", "thank you for choosing", "sorry for", "apologize",
            "inconvenience", "delay", "connect", "transfer", "hold the call",
            "stay on the line", "am i speaking with", "you had shown interest"
        ]

        agent_medium_confidence = [
            "support", "representative", "verify", "verification", "check", "please wait",
            "dermatologist", "doctor", "clinic", "package", "sessions", "appointment",
            "consultation", "booking", "policy", "insurance", "premium", "coverage",
            "benefit", "claim", "assist", "sir", "ma'am", "नमस्ते", "जी"
        ]

        customer_high_confidence = [
            "looking for", "want to book", "i want to", "appointment chahiye",
            "booking karni", "starting price", "how much", "how many", "is it safe",
            "what is the price", "price kya", "price kitna", "safe for", "suitable for",
            "underarm", "under arm", "under arms", "hair reduction"
        ]

        customer_medium_confidence = [
            "problem", "confused", "not sure", "cost", "charges", "location", "address",
            "complaint", "query", "कितना", "क्या", "बताइए", "चाहिए", "प्रॉब्लम",
            "दिक्कत", "परेशानी", "प्राइस", "कीमत", "चार्ज", "लोकेशन", "पता"
        ]

        def count_keyword(text, keyword):
            escaped = re.escape(keyword)
            if " " in keyword:
                return text.count(keyword)
            else:
                pattern = rf"\b{escaped}\b"
                return len(re.findall(pattern, text, re.IGNORECASE | re.UNICODE))

        # Determine agent speaker/channel ID
        agent_spk = None
        max_score = -9999

        # Detect speaker who speaks first
        first_spk = utterances[0].get("speaker")
        if first_spk is None:
            first_spk = 0
        
        for spk, full_text in speaker_texts.items():
            # Calculate agent score
            agent_score = 0
            for kw in agent_high_confidence:
                agent_score += count_keyword(full_text, kw) * 10
            for kw in agent_medium_confidence:
                agent_score += count_keyword(full_text, kw) * 1

            # Calculate customer score
            customer_score = 0
            for kw in customer_high_confidence:
                customer_score += count_keyword(full_text, kw) * 10
            for kw in customer_medium_confidence:
                customer_score += count_keyword(full_text, kw) * 1

            score = agent_score - customer_score
            
            # First speaker bonus (usually agent initiates the conversation)
            if spk == first_spk:
                score += 5
                
            log.info(f"Speaker/Channel {spk} classification score details -> agent_score: {agent_score}, customer_score: {customer_score}, final_score: {score} (first_spk: {spk == first_spk})")

            if score > max_score:
                max_score = score
                agent_spk = spk

        log.info(f"Classified agent speaker/channel as: {agent_spk} (using channel: {use_channel})")

        # Merge consecutive utterances of the same speaker/channel
        merged_utterances = []
        current_spk = None
        current_text = []
        current_start = None
        current_end = None

        for utt in utterances:
            spk = utt.get("speaker")
            text = (utt.get("transcript") or "").strip()
            if not text:
                continue

            if spk == current_spk:
                current_text.append(text)
                current_end = utt.get("end", 0)
            else:
                if current_text:
                    merged_utterances.append({
                        "spk": current_spk,
                        "text": " ".join(current_text),
                        "start": current_start,
                        "end": current_end
                    })
                current_spk = spk
                current_text = [text]
                current_start = utt.get("start", 0)
                current_end = utt.get("end", 0)

        if current_text:
            merged_utterances.append({
                "spk": current_spk,
                "text": " ".join(current_text),
                "start": current_start,
                "end": current_end
            })

        # Pair up Agent and Customer turns
        final = []
        i = 0
        while i < len(merged_utterances):
            current = merged_utterances[i]
            is_agent = current["spk"] == agent_spk
            
            if is_agent:
                agent_text = current["text"]
                customer_text = ""
                # Since the list alternates, if there is a next turn, it must belong to customer
                if i + 1 < len(merged_utterances):
                    customer_text = merged_utterances[i+1]["text"]
                    i += 1
                final.append({
                    "agent": agent_text,
                    "customer": customer_text
                })
            else:
                final.append({
                    "agent": "",
                    "customer": current["text"]
                })
            i += 1

        return final

    except Exception as e:
        log.error(f"Error formatting transcript: {e}", exc_info=True)
        return [{"error": str(e)}]


@celery.task(bind=True, max_retries=3)
def transcribe_task(self, file_url, file_path):
    try:
        log.info("FILE PATH RECEIVED: %s", file_path)

        if not file_url and not file_path:
            return {
                "status": "FAILED",
                "error": "Provide either file_url or file_path"
            }
        
        if file_path and not os.path.exists(file_path):
            return {
                "status": "FAILED",
                "error": f"File not found: {file_path}"
            }

        # Deepgram call
        dg_json = run_async(process_audio, file_url, file_path)
        # log.info(dg_json)

        # Format transcript
        transcript = format_transcript(dg_json)

        return {
            "status": "SUCCESS",
            "transcript": transcript,
            "raw_dg": dg_json
        }

    except Exception as e:
        print("TASK ERROR:", str(e))
        raise self.retry(exc=e, countdown=10)
        
    finally:
        # अगर फाइल 'uploads' फोल्डर की है, तो प्रोसेस होने के बाद उसे डिलीट कर दें
        if file_path and "/var/www/html/uploads/" in file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                log.info("Deleted temp uploaded file: %s", file_path)
            except Exception as err:
                log.error("Failed to delete temp file: %s", err)