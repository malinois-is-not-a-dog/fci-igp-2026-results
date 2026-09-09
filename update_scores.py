import json
import re
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

RESULTS_URL = "https://fciigp2026.fci.systems/results.php"
OUTPUT_FILE = Path("scores.json")


def score_value(text):
    text = text.strip()

    if not text:
        return None

    match = re.search(r"^(100|[0-9]{1,2})$", text)

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


def get_rendered_html():
    options = Options()

    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=options)

    try:
        driver.get(RESULTS_URL)

        # JavaScriptで結果表が描画されるのを待つ
        for _ in range(30):
            html = driver.page_source

            if re.search(r"[A-Z]{2}-(?:\d{2}|WC)", html):
                return html

            time.sleep(1)

        return driver.page_source

    finally:
        driver.quit()


def main():
    html = get_rendered_html()

    soup = BeautifulSoup(html, "html.parser")

    existing = load_existing()
    scores = existing.get("scores", {})

    valid_rows = 0

    for table in soup.find_all("table"):

        header_cells = table.find_all("th")

        headers = [
            th.get_text(" ", strip=True)
            for th in header_cells
        ]

        header_string = " ".join(headers)

        if (
            "Cat.No." not in header_string
            or "Handler" not in header_string
            or "Dog" not in header_string
            or "A" not in headers
            or "B" not in headers
            or "C" not in headers
        ):
            continue

        try:
            cat_index = headers.index("Cat.No.")
            a_index = headers.index("A")
            b_index = headers.index("B")
            c_index = headers.index("C")
        except ValueError:
            continue

        for row in table.find_all("tr"):

            cells = [
                td.get_text(" ", strip=True)
                for td in row.find_all("td")
            ]

            if len(cells) <= max(
                cat_index,
                a_index,
                b_index,
                c_index
            ):
                continue

            cat_no = cells[cat_index].strip()

            if not re.fullmatch(
                r"[A-Z]{2}-(?:\d{2}|WC)",
                cat_no
            ):
                continue

            a = score_value(cells[a_index])
            b = score_value(cells[b_index])
            c = score_value(cells[c_index])

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

    if valid_rows == 0:
        print("No rendered official scores found.")
        print("Existing scores.json kept.")
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
