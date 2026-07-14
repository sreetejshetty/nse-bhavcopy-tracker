"""
Fetches NSE's daily sec_bhavdata_full report (OHLC + volume + delivery %
for every listed security) and saves it into data/ as a dated CSV.

Meant to be run once a day (via GitHub Actions). It automatically walks
backward from today to find the most recent trading day that has data
published (skips weekends; NSE holidays just fall through to the next
older date), and keeps only the most recent 10 files so the repo doesn't
grow forever.
"""
import requests
import datetime
import os
import sys

DATA_DIR = "data"
BASE_URL = "https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_{}.csv"
NSE_HOME = "https://www.nseindia.com"
KEEP_LAST_N_FILES = 10

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/csv,application/csv,*/*",
}


def get_session():
    """NSE expects a browser-like session with cookies from a homepage
    visit before it will serve archive files."""
    s = requests.Session()
    s.headers.update(HEADERS)
    s.get(NSE_HOME, timeout=10)
    return s


def fetch_for_date(date_obj, session, retries=3):
    ddmmyyyy = date_obj.strftime("%d%m%Y")
    url = BASE_URL.format(ddmmyyyy)
    for _ in range(retries):
        try:
            resp = session.get(url, timeout=15)
            if resp.status_code == 200 and resp.text.strip().startswith("SYMBOL"):
                return resp.text
        except requests.RequestException:
            pass
    return None


def prune_old_files():
    files = sorted(f for f in os.listdir(DATA_DIR) if f.startswith("sec_bhavdata_full_"))
    for old in files[:-KEEP_LAST_N_FILES]:
        os.remove(os.path.join(DATA_DIR, old))
        print(f"Removed old file {old}")


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    session = get_session()
    today = datetime.date.today()

    for offset in range(0, 6):  # walk back up to 6 calendar days
        d = today - datetime.timedelta(days=offset)
        if d.weekday() >= 5:  # skip Sat/Sun
            continue
        filename = f"sec_bhavdata_full_{d.strftime('%d%m%Y')}.csv"
        path = os.path.join(DATA_DIR, filename)
        if os.path.exists(path):
            print(f"{filename} already saved, nothing to do")
            break
        data = fetch_for_date(d, session)
        if data:
            with open(path, "w") as f:
                f.write(data)
            print(f"Saved {filename}")
            break
        print(f"No data yet for {d} (holiday, weekend, or not published), trying earlier date")
    else:
        print("Could not fetch data for any recent date", file=sys.stderr)
        sys.exit(1)

    prune_old_files()


if __name__ == "__main__":
    main()
