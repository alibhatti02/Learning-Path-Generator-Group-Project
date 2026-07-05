from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from services.ai_service import generate_learning_roadmap
from services.auth_service import get_current_user
from services.path_service import save_path
from services.resource_service import fetch_resources_for_query

router = APIRouter(tags=["generation"])

class PathRequest(BaseModel):
    """
    Updated schema tracking daily user availability intervals instead of absolute project lengths.
    """
    topic: str
    experience_level: str
    hours_per_day: int

@router.post("/generate")
def create_path(request: PathRequest, user: dict = Depends(get_current_user)):
    """
    Processes incoming configuration values, calls the dynamic timeline service,
    injects live resources, and returns structured object data.
    """
    # 1. Request base JSON roadmap object structure from Azure OpenAI
    roadmap_data = generate_learning_roadmap(
        topic=request.topic,
        hours_per_day=request.hours_per_day,
        level=request.experience_level
    )

    # 2. Immediately intercept service-level failures
    if "error" in roadmap_data:
        raise HTTPException(status_code=500, detail=roadmap_data["error"])

    # 3. Resolve every week's YouTube links in parallel — running ~2 queries × N weeks
    #    sequentially was the biggest post-AI latency source in this endpoint
    weeks = roadmap_data.get("weeks", [])
    all_queries = [q for week in weeks for q in (week.get("search_queries") or [])]

    results: dict[str, list] = {}
    if all_queries:
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = dict(zip(all_queries, pool.map(fetch_resources_for_query, all_queries)))

    for week in weeks:
        week_resources = []
        for query in week.get("search_queries") or []:
            week_resources.extend(results.get(query, []))

        # Inject the final compiled resources array directly into the week node
        week["live_resources"] = week_resources

        # Pop the temporary search queries from the object payload so it stays completely clean
        week.pop("search_queries", None)

    # 4. Persist the finished roadmap as a session so it shows up in the user's history
    roadmap_data["path_id"] = save_path(
        user_id=user["id"],
        topic=request.topic,
        experience_level=request.experience_level,
        hours_per_day=request.hours_per_day,
        roadmap=roadmap_data,
    )

    # 5. Return the fully enhanced, structured JSON data back down the wire
    return roadmap_data