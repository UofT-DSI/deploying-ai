"""Build a compact travel knowledge JSONL dataset from Wikivoyage summaries."""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from pathlib import Path


USER_AGENT = "TripSmithDatasetBuilder/1.0 (assignment-2)"
BASE_URL = "https://en.wikivoyage.org/api/rest_v1/page/summary/"
OUTPUT_FILE = Path(__file__).resolve().parent / "travel_knowledge.jsonl"

# Broad destination coverage so semantic search handles common travel questions.
DESTINATIONS = [
    "Tokyo",
    "Kyoto",
    "Osaka",
    "Sapporo",
    "Seoul",
    "Busan",
    "Bangkok",
    "Chiang Mai",
    "Singapore",
    "Hong Kong",
    "Taipei",
    "Beijing",
    "Shanghai",
    "Hanoi",
    "Ho Chi Minh City",
    "Bali",
    "Jakarta",
    "Kuala Lumpur",
    "Manila",
    "Delhi",
    "Mumbai",
    "Istanbul",
    "Dubai",
    "Cairo",
    "Marrakesh",
    "Cape Town",
    "Nairobi",
    "Athens",
    "Rome",
    "Milan",
    "Venice",
    "Florence",
    "Barcelona",
    "Madrid",
    "Lisbon",
    "Porto",
    "Paris",
    "London",
    "Dublin",
    "Amsterdam",
    "Brussels",
    "Berlin",
    "Prague",
    "Vienna",
    "Budapest",
    "Zurich",
    "Reykjavik",
    "Copenhagen",
    "Stockholm",
    "Oslo",
    "Helsinki",
    "Warsaw",
    "Edinburgh",
    "New York City",
    "Los Angeles",
    "San Francisco",
    "Chicago",
    "Miami",
    "Vancouver",
    "Toronto",
    "Montreal",
    "Mexico City",
    "Cancun",
    "Havana",
    "San Juan",
    "Bogota",
    "Lima",
    "Santiago",
    "Buenos Aires",
    "Rio de Janeiro",
    "Sao Paulo",
    "Sydney",
    "Melbourne",
    "Auckland",
]


def _clean_text(text: str) -> str:
    """Normalize whitespace so stored passages are prompt-friendly."""
    text = re.sub(r"\s+", " ", text or "").strip()
    return text


def _summary_for_destination(destination: str) -> str:
    """Fetch summary text for a destination from Wikivoyage REST API."""
    encoded = urllib.parse.quote(destination.replace(" ", "_"))
    req = urllib.request.Request(
        BASE_URL + encoded,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=25) as response:
        payload = json.loads(response.read().decode("utf-8", errors="replace"))

    # Prefer "extract", then fallback to plain text description.
    extract = _clean_text(payload.get("extract", ""))
    if extract:
        return extract
    description = _clean_text(payload.get("description", ""))
    return description


def build_dataset() -> list[dict]:
    """Create record list with stable ids and source attribution fields."""
    records: list[dict] = []
    for idx, destination in enumerate(DESTINATIONS, start=1):
        try:
            text = _summary_for_destination(destination)
        except Exception:
            continue
        if not text:
            continue

        title_slug = destination.replace(" ", "_")
        records.append(
            {
                "id": f"wv_{idx:04d}",
                "destination": destination,
                "topic": "overview",
                "source": "Wikivoyage",
                "source_url": f"https://en.wikivoyage.org/wiki/{title_slug}",
                "license": "CC BY-SA 4.0",
                "text": text,
            }
        )
    return records


def write_jsonl(records: list[dict]) -> None:
    """Persist records as UTF-8 JSONL for semantic service ingestion."""
    lines = [json.dumps(record, ensure_ascii=True) for record in records]
    OUTPUT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    """CLI entrypoint used to refresh dataset before submission."""
    records = build_dataset()
    if not records:
        raise RuntimeError("No records were downloaded from Wikivoyage.")
    write_jsonl(records)
    print(f"Wrote {len(records)} records to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
