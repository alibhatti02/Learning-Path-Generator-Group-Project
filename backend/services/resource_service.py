import json
import os
import urllib.parse

import requests
from dotenv import load_dotenv

from services.database import get_db

# Ensure environment variables are freshly accessible
load_dotenv()

# Extract the YouTube credential from the sandbox runtime environment
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"

# Each search costs 100 of the 10,000 daily quota units (= 100 searches/day),
# so cached results are the difference between quota anxiety and not caring.
CACHE_TTL_DAYS = int(os.getenv("YOUTUBE_CACHE_TTL_DAYS", "30"))


def _cache_get(query: str, ignore_ttl: bool = False) -> list[dict] | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT results_json, cached_at >= datetime('now', ?) AS fresh FROM youtube_cache WHERE query = ?",
            (f"-{CACHE_TTL_DAYS} days", query),
        ).fetchone()
    if row is None or not (row["fresh"] or ignore_ttl):
        return None
    return json.loads(row["results_json"])


def _cache_put(query: str, results: list[dict]) -> None:
    with get_db() as conn:
        conn.execute(
            "INSERT INTO youtube_cache (query, results_json, cached_at) VALUES (?, ?, datetime('now')) "
            "ON CONFLICT(query) DO UPDATE SET results_json = excluded.results_json, cached_at = excluded.cached_at",
            (query, json.dumps(results)),
        )


def _search_fallback(query: str) -> list[dict]:
    """Zero-quota fallback: a plain YouTube search link in the same shape as a real resource.
    Never cached, so the real API result fills in once quota/key is available again."""
    search_url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(f"{query} tutorial")
    return [{
        "title": f"Search YouTube: {query}",
        "url": search_url,
        "type": "search"
    }]


def fetch_resources_for_query(query: str) -> list[dict]:
    """
    Accepts a target search query from the AI, hits the live YouTube Data API,
    and returns a clean, structured list of real video titles and URLs.
    Results are cached in SQLite so repeat queries never touch the quota.
    """
    # Guard clause: Fail gracefully back to the router if no API key is provided
    # (missing-key warning is handled once at startup in main.py)
    if not YOUTUBE_API_KEY:
        return _search_fallback(query)

    cached = _cache_get(query)
    if cached is not None:
        return cached

    # Configure the exact payload criteria Google's search engine expects
    params = {
        "part": "snippet",
        "q": f"{query} tutorial",  # Appending "tutorial" refines results for educational context
        "maxResults": 2,            # Grabbing the top 2 highest-ranking matches
        "type": "video",            # Restrict lookup blocks to videos only (skips playlists/channels)
        "videoEmbeddable": "true",  # Ensures videos are legally allowed to play on external apps
        "key": YOUTUBE_API_KEY
    }

    try:
        # Execute the live network request
        response = requests.get(YOUTUBE_SEARCH_URL, params=params, timeout=5)

        # Immediately elevate downstream HTTP status errors (e.g., 403 Quota Exceeded, 400 Bad Key)
        response.raise_for_status()

        data = response.json()
        structured_resources = []

        # Iterate through the returned items array from Google
        for item in data.get("items", []):
            video_id = item.get("id", {}).get("videoId")
            snippet = item.get("snippet", {})
            title = snippet.get("title")

            if video_id and title:
                # Construct a legitimate, clickable deep-link to the target video
                video_url = f"https://www.youtube.com/watch?v={video_id}"

                structured_resources.append({
                    "title": title,
                    "url": video_url,
                    "type": "video"
                })

        _cache_put(query, structured_resources)
        return structured_resources

    except Exception as e:
        # Log network errors directly into the local terminal window for debugging.
        # requests embeds the full request URL in the message — strip the query string
        # so the API key never lands in the logs.
        print("\n" + "="*60)
        print(f"⚠️ YOUTUBE API PIPELINE EXCEPTION:\n{str(e).split('?')[0]}")
        print("="*60 + "\n")

        # Quota exhausted or network down: a stale cached result beats no result
        stale = _cache_get(query, ignore_ttl=True)
        if stale is not None:
            return stale

        return _search_fallback(query)