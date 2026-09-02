"""
Evidence-first job discovery.

This module collects public careers/job-page evidence without trying to bypass
robots, login walls, CAPTCHAs, or anti-bot controls.

Preferred production setup:
- GOOGLE_CSE_API_KEY
- GOOGLE_CSE_ID

The Google Custom Search API is used to discover public pages. We then fetch
the returned pages with a normal HTTP client, extract visible text and store
the evidence in data/discovered_jobs.csv.

If a company's careers_url is supplied, it is searched directly as well.

No vacancy is declared current here. This layer only collects evidence.
Gemini performs the final CURRENT / NOT_CURRENT / UNKNOWN classification.
"""
import csv, os, re, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from .evidence_store import connect, snapshot

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

HEADERS = {
    "User-Agent": "JobOutreachResearch/1.0 (public-careers research; contact via project owner)"
}
TIMEOUT = 15

def clean(text):
    return re.sub(r"\s+", " ", text or "").strip()

def fetch(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        return r.url, r.text
    except Exception as exc:
        print("FETCH FAILED", url, exc)
        return None, None

def extract_page(url, html):
    soup = BeautifulSoup(html, "html.parser")
    for x in soup(["script", "style", "noscript", "svg"]):
        x.decompose()
    title = clean(soup.title.get_text(" ", strip=True) if soup.title else "")
    text = clean(soup.get_text(" ", strip=True))
    links = []
    for a in soup.find_all("a", href=True):
        href = urljoin(url, a["href"])
        label = clean(a.get_text(" ", strip=True))
        if label and href.startswith(("http://", "https://")):
            links.append((label, href))
    return title, text[:12000], links

def likely_job_link(label, href):
    blob = f"{label} {href}".lower()
    terms = [
        "career", "careers", "job", "jobs", "opening", "vacancy",
        "position", "apply", "greenhouse", "lever", "ashby", "workable",
        "smartrecruiters", "wellfound"
    ]
    return any(t in blob for t in terms)

def google_search(query):
    key, cx = os.getenv("GOOGLE_CSE_API_KEY"), os.getenv("GOOGLE_CSE_ID")
    if not key or not cx:
        return []
    try:
        r = requests.get(
            "https://www.googleapis.com/customsearch/v1",
            params={"key": key, "cx": cx, "q": query, "num": 10},
            headers=HEADERS, timeout=TIMEOUT
        )
        r.raise_for_status()
        return r.json().get("items", [])
    except Exception as exc:
        print("SEARCH FAILED", query, exc)
        return []

def discovery_queries(company):
    name = company["company"]
    city = company.get("city", "")
    return [
        f'"{name}" careers jobs {city}',
        f'"{name}" "data scientist" OR "data engineer" OR "machine learning" jobs',
        f'"{name}" site:jobs.lever.co OR site:boards.greenhouse.io OR site:job-boards.greenhouse.io',
        f'"{name}" site:jobs.ashbyhq.com OR site:wellfound.com/company',
    ]

def collect_company(company):
    evidence = []
    careers_url = company.get("careers_url", "").strip()
    company_url = company.get("company_url", "").strip()

    if careers_url and not careers_url.startswith("REPLACE_"):
        final_url, html = fetch(careers_url)
        if html:
            title, text, links = extract_page(final_url, html)
            evidence.append({
                "source_url": final_url,
                "source_title": title,
                "source_text": text,
                "source_type": "careers_page"
            })
            for label, href in links:
                if likely_job_link(label, href):
                    final2, html2 = fetch(href)
                    if html2:
                        t2, txt2, _ = extract_page(final2, html2)
                        evidence.append({
                            "source_url": final2,
                            "source_title": t2 or label,
                            "source_text": txt2,
                            "source_type": "career_link"
                        })
    elif company_url and not company_url.startswith("REPLACE_"):
        final_url, html = fetch(company_url)
        if html:
            title, text, links = extract_page(final_url, html)
            evidence.append({
                "source_url": final_url,
                "source_title": title,
                "source_text": text,
                "source_type": "official_company_page"
            })
            guess_paths = ["/careers", "/jobs", "/careers/", "/join-us"]
            for guess in guess_paths:
                guessed = urljoin(final_url, guess)
                final2, html2 = fetch(guessed)
                if html2:
                    t2, txt2, _ = extract_page(final2, html2)
                    evidence.append({
                        "source_url": final2,
                        "source_title": t2 or guess.strip("/"),
                        "source_text": txt2,
                        "source_type": "careers_page"
                    })
            for label, href in links:
                if likely_job_link(label, href):
                    final2, html2 = fetch(href)
                    if html2:
                        t2, txt2, _ = extract_page(final2, html2)
                        evidence.append({
                            "source_url": final2,
                            "source_title": t2 or label,
                            "source_text": txt2,
                            "source_type": "career_link"
                        })

    for query in discovery_queries(company):
        for item in google_search(query):
            url = item.get("link", "")
            if not url:
                continue
            final_url, html = fetch(url)
            if not html:
                continue
            title, text, _ = extract_page(final_url, html)
            evidence.append({
                "source_url": final_url,
                "source_title": title or item.get("title", ""),
                "source_text": text,
                "source_type": "search_result"
            })
        time.sleep(0.4)

    # Deduplicate URLs.
    seen, out = set(), []
    for e in evidence:
        if e["source_url"] not in seen:
            seen.add(e["source_url"])
            out.append(e)
    return out

def main():
    companies = []
    with open(ROOT/"data/companies.csv", newline="", encoding="utf-8-sig") as f:
        companies = list(csv.DictReader(f))

    rows = []
    checked = datetime.now(timezone.utc).isoformat()
    evidence_db = connect()

    for company in companies:
        print("DISCOVERING", company["company"])
        evidence = collect_company(company)
        for e in evidence:
            snapshot(evidence_db, company["company"], e)
            rows.append({
                "company": company["company"],
                "city": company.get("city", ""),
                "source_url": e["source_url"],
                "source_title": e["source_title"],
                "source_type": e["source_type"],
                "source_text": e["source_text"],
                "checked_at": checked
            })

    path = ROOT/"data/discovered_evidence.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        fields = ["company","city","source_url","source_title","source_type","source_text","checked_at"]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    print(f"Saved {len(rows)} evidence records to {path}")

if __name__ == "__main__":
    main()
