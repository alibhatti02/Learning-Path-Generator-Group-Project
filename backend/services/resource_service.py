import os
import requests
from dotenv import load_dotenv

# Ensure environment variables are freshly accessible
load_dotenv()

# Extract the YouTube credential from the sandbox runtime environment
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"

def fetch_resources_for_query(query: str) -> list[dict]:
    """
    Accepts a target search query from the AI, hits the live YouTube Data API,
    and returns a clean, structured list of real video titles and URLs.
    """
    # Guard clause: Fail gracefully back to the router if no API key is provided
    if not YOUTUBE_API_KEY:
        print("⚠️ WARNING: YOUTUBE_API_KEY missing from environment variables.")
        return []

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

        return structured_resources

    except Exception as e:
        # Log network errors directly into the local terminal window for debugging
        print("\n" + "="*60)
        print(f"⚠️ YOUTUBE API PIPELINE EXCEPTION:\n{str(e)}")
        print("="*60 + "\n")

        # Return an empty list on failure so the entire application loop doesn't crash
        return []