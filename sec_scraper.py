# sec_scraper.py
import os
import zipfile

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from pathlib import Path
from config import HEADERS


PROJECT_DIR = Path(__file__).resolve().parent
DOWNLOAD_DIR = PROJECT_DIR / "downloads"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)


def get_cik(ticker):
    cik_url = 'https://www.sec.gov/files/company_tickers.json'
    headers = {'User-Agent': 'jason@focusuniversal.com'}
    response = requests.get(cik_url, headers=HEADERS)
    data = response.json()
    for entry in data.values():
        if entry['ticker'].lower() == ticker.lower():
            return str(entry['cik_str']).zfill(10)
    return None


def get_latest_8k_url(cik):
    feed_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    headers = {'User-Agent': 'sec-downloader-app'}
    response = requests.get(feed_url, headers=headers)
    if response.status_code != 200:
        return None

    data = response.json()
    for filing in data.get("filings", {}).get("recent", {}).get("form", []):
        if filing == "8-K":
            index = data["filings"]["recent"]["form"].index(filing)
            accession = data["filings"]["recent"]["accessionNumber"][index].replace("-", "")
            xbrl_accession = data["filings"]["recent"]["accessionNumber"][index]
            return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession}/{xbrl_accession}-xbrl.zip"
    return None

def get_unique_filename(path: Path) -> Path:
    """Avoid overwriting existing files — append (1), (2), etc."""
    base = path.stem
    ext = path.suffix
    counter = 1
    while path.exists():
        path = path.with_name(f"{base} ({counter}){ext}")
        counter += 1
    return path

def download_ixbrl_zip(zip_url, ticker, cik):
    """Download ZIP, rename it, and extract it to a folder."""
    try:
        response = requests.get(zip_url, headers=HEADERS, stream=True)
        if response.status_code == 200 and 'application/zip' in response.headers.get('Content-Type', ''):
            filename = zip_url.split('/')[-1]
            renamed = f"{ticker.upper()}_{filename}"
            zip_path = get_unique_filename(DOWNLOAD_DIR / renamed)

            # Save ZIP file
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"[✓] Saved ZIP to: {zip_path}")

            # Get 8-K filing date
            extract_dir = DOWNLOAD_DIR / f"{ticker.upper()}_newest"
            extract_dir.mkdir(exist_ok=True)

            # Extract ZIP
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            print(f"[✓] Extracted to: {extract_dir}")

            return extract_dir
        else:
            print(f"[!] Unexpected status/code: {response.status_code}, {response.headers.get('Content-Type')}")
            return None
    except Exception as e:
        print("[✗] Download or extract failed:", e)
        return None


def run_downloader(ticker):
    cik = get_cik(ticker)
    if not cik:
        return "CIK not found for ticker."

    index_json_url = get_latest_8k_url(cik)
    if not index_json_url:
        return "Latest 8-K filing not found."

    zip_path = download_ixbrl_zip(index_json_url, ticker, cik)
    if not zip_path:
        return "No iXBRL .zip file found in the filing."

    return f"Downloaded: {zip_path}"