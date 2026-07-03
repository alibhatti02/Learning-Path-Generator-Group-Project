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

class QuizAnswer(BaseModel):
    question_number: int
    answer: str = Field(default="", max_length=5000)

# The frontend echoes the generated questions back on submit, so grading is stateless (no DB needed yet)
class QuizSubmitRequest(BaseModel):
    week_number: int = Field(ge=1, le=52)
    milestone: str = Field(min_length=1, max_length=300)
    questions: List[dict]
    answers: List[QuizAnswer]

