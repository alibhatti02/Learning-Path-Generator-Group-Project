# Import the core FastAPI application class to launch your programmatic web server framework.
from fastapi import FastAPI
# Import the CORS middleware to allow cross-origin requests from your frontend browser window.
from fastapi.middleware.cors import CORSMiddleware
# Import the modular router from your routes directory to attach it here.
from backend.routes.learning_path import router as learning_path_router

# Instantiate your global FastAPI application app, which coordinates configuration and middleware.
app = FastAPI(title="Course Forge Backend API", version="1.0")

# =========================================================================
# Configure CORS Middleware so your React frontend can communicate safely
# =========================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # React default Vite local development port
        "http://127.0.0.1:5173",  # Alternate local loopback address
    ],
    allow_credentials=True,
    allow_methods=["*"],          # Allows all HTTP methods (POST, GET, OPTIONS, etc.)
    allow_headers=["*"],          # Allows all incoming headers (Content-Type, Authorization, etc.)
)

# Mount your learning path router to the app workspace, prepending "/api" to all its endpoints.
app.include_router(learning_path_router, prefix="/api")

# Define a baseline GET endpoint at the absolute root URL to handle simple connectivity health checks.
@app.get("/")
def health_check():
    # Return a status message that FastAPI instantly converts to a structured JSON string response.
    return {"status": "healthy", "message": "Course Forge API is running smoothly!"}