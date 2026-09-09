import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

RESULTS_URL = "https://fciigp2026.fci.systems/results.php"
OUTPUT_FILE = Path("scores.json")


def score_value(text):
    text = text.strip()

    if not text:
        return None

    match = re.search(r"\b(100|[1-9]?\d)\b", text)
    if match:
        return int(match.group(1))

    return None


def load_existing():
    if not OUTPUT_FILE.exists():
        return {
            "lastUpdated": "",
            "source": RESULTS_URL,
            "scores": {}
        }

    try:
        with OUTPUT_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "lastUpdated": "",
            "source": RESULTS_URL,
            "scores": {}
        }


def main():
    headers = {
        "User-Agent": "Mozilla/5.0 FCI-IGP-2026-Results-Tracker"
    }

    response = requests.get(
        RESULTS_URL,
        headers=headers,
        timeout=30
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    existing = load_existing()
    scores = existing.get("scores", {})

    valid_rows = 0

    for table in soup.find_all("table"):
        headers_text = [
            th.get_text(" ", strip=True)
            for th in table.find_all("th")
        ]

        header_string = " ".join(headers_text)

        if (
            "Cat.No." not in header_string
            or "Handler" not in header_string
            or "Dog" not in header_string
        ):
            continue

        for row in table.find_all("tr"):
            cells = [
                td.get_text(" ", strip=True)
                for td in row.find_all("td")
            ]

            if len(cells) < 9:
                continue

            cat_no = cells[2].strip()

            if not re.fullmatch(
                r"[A-Z]{2}-(?:\d{2}|WC)",
                cat_no
            ):
                continue

            a = score_value(cells[6])
            b = score_value(cells[7])
            c = score_value(cells[8])

            if a is None and b is None and c is None:
                continue

            current = scores.get(cat_no, {})

            if a is not None:
                current["a"] = a

            if b is not None:
                current["b"] = b

            if c is not None:
                current["c"] = c

            scores[cat_no] = current
            valid_rows += 1

        break

    # 公式結果がまだ空の場合は既存データを消さない
    if valid_rows == 0:
        print("No official scores found. Existing scores.json kept.")
        return

    now = datetime.now(
        ZoneInfo("Asia/Tokyo")
    ).strftime("%Y-%m-%d %H:%M (JST)")

    output = {
        "lastUpdated": now,
        "source": RESULTS_URL,
        "scores": scores
    }

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(
            output,
            f,
            ensure_ascii=False,
            indent=2
        )

    print(f"Updated {valid_rows} competitors.")
    print(f"Last updated: {now}")


if __name__ == "__main__":
    main()
