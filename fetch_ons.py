"""
fetch_ons.py
Fetches the latest ONS EMP13 XLS (employment by industry),
parses all three sheets (People / Men / Women),
and writes data.json in the format the dashboard expects.

ONS dataset page:
https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/
employmentandemployeetypes/datasets/employmentbyindustryemp13
"""

import json
import re
import sys
import io
import requests
import pandas as pd
from pathlib import Path

ONS_PAGE = (
    "https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/"
    "employmentandemployeetypes/datasets/employmentbyindustryemp13"
)

KEY_MAP = {
    "All employment":            "all",
    "Public sector":             "pub",
    "Private sector":            "priv",
    "Agriculture":               "agr",
    "Mining & energy":           "min",
    "Manufacturing":             "mfg",
    "Construction":              "con",
    "Wholesale & retail":        "ret",
    "Transport & storage":       "trn",
    "Accommodation & food":      "acc",
    "Information & comms":       "ict",
    "Financial & insurance":     "fin",
    "Real estate":               "est",
    "Professional & scientific": "pro",
    "Admin & support":           "adm",
    "Public admin & defence":    "pad",
    "Education":                 "edu",
    "Health & social work":      "hea",
    "Other services":            "oth",
}

SECTOR_KEYS = ["agr","min","mfg","con","ret","trn","acc","ict","fin",
               "est","pro","adm","pad","edu","hea","oth"]

SECTOR_NAMES = {
    "Agriculture, forestry & fishing":                     "agr",
    "Mining, energy and water supply":                     "min",
    "Manufacturing":                                       "mfg",
    "Construction":                                        "con",
    "Wholesale, retail & repair of motor vehicles":        "ret",
    "Transport & storage":                                 "trn",
    "Accommod-ation & food services":                      "acc",
    "Accommodation & food services":                       "acc",
    "Information & communication":                         "ict",
    "Financial & insurance activities":                    "fin",
    "Real estate activities":                              "est",
    "Professional, scientific & technical activities":     "pro",
    "Administrative & support services":                   "adm",
    "Public admin & defence; social security":             "pad",
    "Education":                                           "edu",
    "Human health & social work activities":               "hea",
    "Other services":                                      "oth",
}


def find_xls_url(page_url: str) -> str:
    """Scrape the ONS dataset page to find the current .xls download link."""
    r = requests.get(page_url, timeout=30)
    r.raise_for_status()
    # ONS links look like /file?uri=/.../.../emp13...xls
    matches = re.findall(r'href="(/file\?uri=[^"]+emp13[^"]*\.xls[x]?)"', r.text, re.I)
    if not matches:
        # Fallback: any xls link containing emp13
        matches = re.findall(r'href="(/file\?uri=[^"]+\.xls[x]?)"', r.text, re.I)
    if not matches:
        raise RuntimeError("Could not find EMP13 download link on ONS page")
    url = "https://www.ons.gov.uk" + matches[0]
    print(f"Found XLS: {url}")
    return url


def download_xls(url: str) -> bytes:
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    return r.content


def parse_sheet(xls_bytes: bytes, sheet_name: str) -> list[dict]:
    """Parse one sheet of the EMP13 XLS into a list of period records."""
    df = pd.read_excel(io.BytesIO(xls_bytes), sheet_name=sheet_name, header=None)

    # Row 4 (index 4) contains the column headers
    headers = df.iloc[4, :].tolist()

    # Map column index → short key
    col_to_key = {}
    for col_idx, h in enumerate(headers):
        h_str = str(h).strip()
        # Total employment is in col 1
        if "All in employment" in h_str:
            col_to_key[col_idx] = "all"
        elif "Public sector" in h_str:
            col_to_key[col_idx] = "pub"
        elif "Private sector" in h_str:
            col_to_key[col_idx] = "priv"
        else:
            # Try sector name lookup
            for full_name, key in SECTOR_NAMES.items():
                if full_name.lower() in h_str.lower():
                    col_to_key[col_idx] = key
                    break

    records = []
    # Data starts at row 8 (index 8), skip footer notes
    for _, row in df.iloc[8:].iterrows():
        period = str(row.iloc[0]).strip()
        # Only keep valid quarter rows like "Jan-Mar 2025"
        if not re.match(r'^(Jan|Apr|Jul|Oct)-(Mar|Jun|Sep|Dec) \d{4}$', period):
            continue

        rec = {"period": period}
        for col_idx, key in col_to_key.items():
            val = row.iloc[col_idx]
            if pd.isna(val) or str(val).strip() in ("", ".."):
                rec[key] = None
            else:
                try:
                    rec[key] = int(round(float(val)))
                except (ValueError, TypeError):
                    rec[key] = None

        # Ensure all sector keys exist (nulled out for Men/Women sheets)
        for k in SECTOR_KEYS:
            if k not in rec:
                rec[k] = None

        if rec.get("all"):
            records.append(rec)

    return records


def main():
    output_path = Path(__file__).parent.parent / "data.json"

    print("Fetching ONS EMP13 page...")
    xls_url = find_xls_url(ONS_PAGE)

    print("Downloading XLS...")
    xls_bytes = download_xls(xls_url)
    print(f"Downloaded {len(xls_bytes):,} bytes")

    print("Parsing sheets...")
    people = parse_sheet(xls_bytes, "People")
    men    = parse_sheet(xls_bytes, "Men")
    women  = parse_sheet(xls_bytes, "Women")

    print(f"  People: {len(people)} quarters, latest: {people[-1]['period']}")
    print(f"  Men:    {len(men)} quarters")
    print(f"  Women:  {len(women)} quarters")

    # Load existing data to check if anything changed
    if output_path.exists():
        with open(output_path) as f:
            existing = json.load(f)
        existing_latest = existing["People"][-1]["period"]
        new_latest = people[-1]["period"]
        if existing_latest == new_latest:
            print(f"No new data (latest is still {new_latest}). Skipping write.")
            sys.exit(0)
        print(f"New data found: {existing_latest} → {new_latest}")

    data = {"People": people, "Men": men, "Women": women}
    with open(output_path, "w") as f:
        json.dump(data, f, separators=(",", ":"))

    print(f"Written {output_path} ({output_path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
