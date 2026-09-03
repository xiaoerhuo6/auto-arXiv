"""arXiv API fetcher -- pull new papers for given categories."""
import math
import time
import re
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from xml.etree import ElementTree

import requests


ARXIV_API_URL = "http://export.arxiv.org/api/query"
NS = {"atom": "http://www.w3.org/2005/Atom",
      "arxiv": "http://arxiv.org/schemas/atom"}


def fetch_latest_papers(categories: List[str], max_results: int = 200,
                        lookback_days: int = 1) -> List[Dict[str, Any]]:
    """Fetch papers from arXiv API, querying each category in order of priority.

    Categories are queried one by one in the order they are given, so higher-priority
    categories (listed first) get filled first. Duplicates across categories are removed.
    """
    seen_ids = set()
    papers = []
    per_page = min(100, max_results)

    now = datetime.now(timezone.utc)
    since = now - timedelta(days=lookback_days)
    date_str = since.strftime("%Y%m%d%H%M%S")
    now_str = now.strftime("%Y%m%d%H%M%S")

    for cat in categories:
        if len(papers) >= max_results:
            break

        remaining = max_results - len(papers)
        fetch_count = min(per_page, remaining)

        query = f"cat:{cat}+AND+submittedDate:[{date_str}+TO+{now_str}]"
        url = f"{ARXIV_API_URL}?search_query={query}&start=0&max_results={fetch_count}&sortBy=submittedDate&sortOrder=descending"

        retries = 3
        cat_papers = []
        for attempt in range(retries):
            try:
                resp = requests.get(url, timeout=60)
                if resp.status_code == 429:
                    wait = 10 * (attempt + 1)
                    print(f"[Rate limited] Waiting {wait}s...")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                cat_papers = _parse_response(resp.text)
                break
            except requests.exceptions.Timeout:
                wait = 10 * (attempt + 1)
                print(f"[Timeout] Retrying in {wait}s...")
                time.sleep(wait)
            except Exception as e:
                if attempt < retries - 1:
                    wait = 5 * (attempt + 1)
                    print(f"[Warning] {e}. Retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    print(f"[Warning] Failed to fetch category '{cat}' after {retries} retries: {e}")
                    cat_papers = []

        new_papers = []
        for p in cat_papers:
            if p["arxiv_id"] not in seen_ids and len(papers) + len(new_papers) < max_results:
                seen_ids.add(p["arxiv_id"])
                new_papers.append(p)

        papers.extend(new_papers)
        time.sleep(0.3)  # be polite

    return papers


def _parse_response(xml_text: str) -> List[Dict[str, Any]]:
    root = ElementTree.fromstring(xml_text)
    papers = []
    for entry in root.findall("atom:entry", NS):
        paper = {
            "arxiv_id": _get_text(entry, "atom:id", NS).split("/")[-1],
            "title": _clean_text(_get_text(entry, "atom:title", NS)),
            "authors": [a.find("atom:name", NS).text or ""
                        for a in entry.findall("atom:author", NS)],
            "abstract": _clean_text(_get_text(entry, "atom:summary", NS)),
            "published": _get_text(entry, "atom:published", NS),
            "updated": _get_text(entry, "atom:updated", NS),
            "categories": [c.get("term") for c in entry.findall("atom:category", NS)],
            "link": _get_link(entry),
        }
        papers.append(paper)
    return papers


def _get_text(entry, tag, ns):
    el = entry.find(tag, ns)
    return el.text.strip() if el is not None and el.text else ""


def _clean_text(text: str) -> str:
    text = re.sub(r"\n", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _get_link(entry):
    for link in entry.findall("atom:link", NS):
        if link.get("title") == "pdf":
            return link.get("href")
    return ""
