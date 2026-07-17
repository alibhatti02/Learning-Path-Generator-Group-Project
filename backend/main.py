from dotenv import load_dotenv
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from services.rate_limit import limiter
from routes.learning_path import router as learning_path_router
from routes.auth import router as auth_router
from routes.quiz import router as quiz_router
from routes.resume import router as resume_router
from routes.paths import router as paths_router
from routes.groups import router as groups_router
from routes.health import router as health_router
from services.database import init_db

# Load .env before anything reads the environment — don't rely on
# services calling load_dotenv() as an import side effect
load_dotenv()

app = FastAPI(title="Course Forge Backend API", version="1.0")

# Register the rate limiter and its 429 handler (limits are applied per-route via
# decorators in the routers). See services/rate_limit.py for the keying strategy.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Create the SQLite users table on boot if it doesn't exist yet
init_db()

REQUIRED_ENV_VARS = ["AZURE_OPENAI_API_KEY", "YOUTUBE_API_KEY", "JWT_SECRET"]

def check_required_config():
    missing = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
    if missing:
        print("\n" + "=" * 60)
        print("⚠️ MISSING REQUIRED CONFIG - app will run degraded:")
        for var in missing:
            print(f"   • {var}")
        print("     Copy .env.example to .env and fill these in.")
        print("=" * 60 + "\n")

check_required_config()

# =========================================================================
# Configure CORS Middleware so your React frontend can communicate safely
# =========================================================================
allowed_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount your learning path router to the app workspace, prepending "/api" to all its endpoints.
app.include_router(learning_path_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(quiz_router, prefix="/api")
app.include_router(resume_router, prefix="/api")
app.include_router(paths_router, prefix="/api")
app.include_router(groups_router, prefix="/api")
app.include_router(health_router, prefix="/api")

# Define a baseline GET endpoint at the absolute root URL to handle simple connectivity health checks.
@app.get("/")
def health_check():
    return {"status": "healthy", "message": "Course Forge API is running smoothly!"}