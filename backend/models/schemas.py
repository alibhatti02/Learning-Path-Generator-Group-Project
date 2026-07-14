# Import the BaseModel class from pydantic, which handles data validation, type checking, and parsing for API data payloads.
from pydantic import BaseModel, Field
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


# ============================== Auth ==============================

class AuthRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    # bcrypt only reads the first 72 bytes, so cap the password there
    password: str = Field(min_length=8, max_length=72)

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    email: str


# ============================== Quiz ==============================

class QuizGenerateRequest(BaseModel):
    milestone: str = Field(min_length=1, max_length=300)
    week_number: int = Field(ge=1, le=52)
    group_id: Optional[int] = None

class QuizAnswer(BaseModel):
    question_number: int
    answer: str = Field(default="", max_length=5000)

# The client only sends the quiz_id + its answers; the server grades against the
# questions it stored at generation time (see quiz_attempts), so answers never leave the server.
class QuizSubmitRequest(BaseModel):
    quiz_id: int
    answers: List[QuizAnswer]


# ============================== Group Skills ==============================

class GroupCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    skill_topic: str = Field(min_length=1, max_length=200)
    experience_level: str = "beginner"


class GroupJoinRequest(BaseModel):
    invite_code: str = Field(min_length=1, max_length=32)


class SetHoursRequest(BaseModel):
    # Capped so the leaderboard mechanic can't push someone into an unsustainable daily grind
    hourly_commitment: float = Field(ge=0.25, le=8)


class GroupSummary(BaseModel):
    id: int
    name: str
    skill_topic: str
    experience_level: str
    invite_code: str
    member_count: int
    max_members: int
    status: str
    created_at: str


# Public-facing leaderboard row — deliberately has NO hours/pace field. This is the
# only shape other members are ever allowed to see for one another.
class LeaderboardEntry(BaseModel):
    user_id: int
    display_name: str
    rank: int
    total_points: int
    current_week: int
    status: str
    is_me: bool = False


class GroupLeaderboardResponse(BaseModel):
    group: GroupSummary
    leaderboard: List[LeaderboardEntry]
    average_current_week: float  # anonymized pace signal, no individual is exposed


# Private view — only ever returned for the requesting user's own membership
class MyMembershipResponse(BaseModel):
    group_id: int
    hourly_commitment: Optional[float] = None
    calculated_weeks: Optional[int] = None
    current_week: int
    total_points: int
    status: str
    roadmap: Optional[dict] = None
    is_creator: bool = False


class WeekCompleteRequest(BaseModel):
    quiz_id: int