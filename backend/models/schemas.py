# Import the BaseModel class from pydantic, which handles data validation, type checking, and parsing for API data payloads.
from pydantic import BaseModel
# Import the List class from typing to let us specify when a data field must contain a collection of structured objects.
from typing import List, Optional

# Define a class representing the strict data structure our backend expects to receive from the frontend user interface.
class PathRequest(BaseModel):
   topic: str
   experience_level: str
   hours_per_day: int

# Sub-Structure for Youtube Links
class LiveResources(BaseModel):
    title: str
    url: str

# Define a structure representing a single week's container inside the broader multi-week learning strategy.
class WeeklyModule(BaseModel):
    week_number: int
    focus: str
    topics: List[str]
    live_resources: List[LiveResources] = []
    practice: List[str] = []
    mini_exercise: Optional[str] = None

# Define the comprehensive payload response structure that our FastAPI application will output back to the client side.
class PathResponse(BaseModel):
   title: str
   calculated_total_weeks: int
   weeks: List[WeeklyModule]

