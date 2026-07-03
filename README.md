# Course Forge — AI-Powered Learning Path Generator

🧭 Full-stack web application that generates personalized, structured learning roadmaps for any topic. Built with **FastAPI** (backend), **React + Vite** (frontend), **Azure OpenAI** (pathway generation), and **Ollama** (quiz generation).

> **For end users:** Use the web interface at `http://localhost:5173` — create an account (or sign in) and start generating paths.  
> **For developers:** Instructions below cover running both backend and frontend locally.

---

## 🚀 What It Does

- **Generate personalized learning paths:** Takes a topic, experience level, and daily time commitment as input
- **Dynamic timeline calculation:** AI calculates optimal learning duration based on complexity and available time
- **Live resources:** Automatically fetches curated resources (videos, articles, tutorials) for each week
- **Weekly milestones:** Structured curriculum with focus areas, practice tasks, and mini-exercises
- **Quiz generation & grading:** Weekly milestone quizzes (3 multiple-choice + 2 open-ended) with AI-powered per-question feedback
- **User accounts:** Register/login with secure sessions — passwords stored only as bcrypt hashes, never plaintext
- **Responsive UI:** Clean, modern interface with a login gate, roadmap view, and quiz flow

---

## 🛠️ Tech Stack

### Backend
- **Python 3.11+** with FastAPI
- **Azure OpenAI** — generates personalized learning paths; automatic fallback for quizzes
- **Ollama (qwen3.5:9b)** — generates and grades milestone quizzes (primary quiz model)
- **SQLite + bcrypt + PyJWT** — user accounts, password hashing, and token-based sessions
- **Uvicorn** — ASGI server
- **Pydantic** — data validation
- **CORS middleware** — enables frontend communication

### Frontend
- **React 18** with Vite
- **Lucide React** — icons
- **Vite** — fast build tooling
- **Firebase** — deployment-ready

---

## 📁 Project Structure

```
Course_Forge/
├── backend/
│   ├── main.py                 # FastAPI entry point, CORS config, DB init
│   ├── requirements.txt         # Python dependencies
│   ├── .env                     # Local config (create this yourself)
│   ├── courseforge.db           # SQLite user database (auto-created, gitignored)
│   ├── models/
│   │   └── schemas.py           # Pydantic request/response models (paths, auth, quizzes)
│   ├── routes/
│   │   ├── learning_path.py     # /api/generate endpoint
│   │   ├── auth.py              # /api/auth/register, /login, /me
│   │   └── quiz.py              # /api/quiz/generate, /api/quiz/submit
│   └── services/
│       ├── ai_service.py        # Azure OpenAI integration
│       ├── resource_service.py  # Resource fetching
│       ├── quiz_service.py      # Quiz gen/grading (Ollama primary, Azure fallback)
│       ├── auth_service.py      # bcrypt hashing, JWT creation/validation
│       └── database.py          # SQLite connection + schema
│
└── frontend/
    ├── index.html
    ├── package.json
    ├── vite.config.js
    └── src/
        ├── App.jsx              # Main React component (login gate, roadmap, quizzes)
        ├── App.css              # Styling
        └── assets/              # Images and icons
```

---

## ⚙️ Setup Instructions

### Prerequisites
- **Python 3.11+** on your machine
- **Node.js 18+** for frontend
- **Azure OpenAI API credentials** (for pathway generation)
- **YouTube Data API v3 key** (for live video resources in paths) — *each teammate creates their own free key; see [Getting your own YouTube API key](#-getting-your-own-youtube-api-key-required--one-per-teammate)*
- **Ollama** (for quiz generation) — *optional; quizzes automatically fall back to Azure OpenAI when Ollama isn't running*

---

### Backend Setup

#### 1. Navigate to the backend directory
```bash
cd Course_Forge/backend
```

#### 2. Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows
```

#### 3. Install dependencies
```bash
pip install -r requirements.txt
```

#### 4. Create a `.env` file
In the `backend/` directory, copy the provided template and fill in your values:
```bash
cp .env.example .env
```
Each variable is documented inline in `.env.example`. For reference, the full set:

```env
# ============================================================================
# REQUIRED: Azure OpenAI (for generating learning paths)
# Get these from your Azure portal: https://portal.azure.com
# - AZURE_OPENAI_API_KEY: Your Azure OpenAI resource's API key
# - AZURE_OPENAI_ENDPOINT: Your resource URL (e.g., https://my-resource.openai.azure.com/)
# - AZURE_OPENAI_DEPLOYMENT_NAME: The name of your deployed model (e.g., "gpt-4")
# ============================================================================
AZURE_OPENAI_API_KEY=your-azure-key-here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=your-deployment-name
AZURE_OPENAI_API_VERSION=2024-05-01-preview

# ============================================================================
# REQUIRED: YouTube Data API v3 key (live video resources in learning paths)
# Each teammate creates their OWN key — see "Getting your own YouTube API key"
# below. Without it, paths generate but every week is missing its videos.
# ============================================================================
YOUTUBE_API_KEY=your-youtube-api-key

# ============================================================================
# REQUIRED: Frontend CORS origins (which URLs can call the backend)
# Keep both for local dev; add your production domain when you deploy
# ============================================================================
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# ============================================================================
# REQUIRED: JWT signing secret (for login sessions)
# Generate a random secret by running this once in your terminal:
#   python -c "import secrets; print(secrets.token_hex(32))"
# Then paste the output below. This keeps your login tokens secure.
# If you skip this, sessions will expire every time the server restarts.
# ============================================================================
JWT_SECRET=your-random-secret-here

# ============================================================================
# OPTIONAL: Ollama configuration (for free, fast quiz generation locally)
# - If Ollama is NOT running, quizzes will automatically use Azure OpenAI instead
# - Only set these if you have Ollama installed and running (`ollama serve`)
# - To check if Ollama is working: curl http://localhost:11434/api/tags
# ============================================================================
OLLAMA_HOST=http://localhost:11434
QUIZ_MODEL=qwen3.5:9b
```

**⚠️ Never commit `.env`. It's already in `.gitignore`.**

**Quick setup if you don't have Azure yet:**
If you don't have Azure OpenAI credentials yet, you can still test the login and UI locally — just skip `AZURE_OPENAI_*` for now and you'll get a 503 error only when you try to generate a path. Add the credentials later when you're ready to test the full flow.

#### 5. Start the backend server
```bash
uvicorn main:app --reload
```

The backend will start at `http://127.0.0.1:8000`  
Swagger docs available at `http://127.0.0.1:8000/docs`

---

### Frontend Setup

#### 1. Navigate to the frontend directory
```bash
cd Course_Forge/frontend
```

#### 2. Install dependencies
```bash
npm install
```

#### 3. Start the dev server
```bash
npm run dev
```

The frontend will start at `http://localhost:5173`

---

## 🔑 Getting your own YouTube API key (required — one per teammate)

Learning paths pull real video links from the YouTube Data API. **Every teammate needs their own key in their own Google Cloud project.**

> **Why can't we share one key?** YouTube quota is **10,000 units/day per Google Cloud *project*** (not per key), and each search costs 100 units. One path generation runs ~30+ searches ≈ 3,200 units — so a single shared project supports only ~3 path generations per day *for the whole team*. Separate projects = separate quota pools.

#### 1. Create a Google Cloud project
Go to [Google Cloud Console](https://console.cloud.google.com/) → project dropdown (top bar) → **New Project**. Name it anything (e.g., `course-forge-dev`). Free, no billing needed.

#### 2. Enable the YouTube Data API
**APIs & Services → Library** → search **"YouTube Data API v3"** → **Enable**.

#### 3. Create the key
**APIs & Services → Credentials → Create Credentials → API key.**
- Under **API restrictions**, restrict the key to **YouTube Data API v3** only
- Leave **Application restrictions** as **None** (the key is used server-side from FastAPI)
- Skip "Authenticate through a service account" — not needed for YouTube

#### 4. Add it to your `.env`
```env
YOUTUBE_API_KEY=your-new-key
```
Restart the backend afterwards — `--reload` only watches `.py` files, so `.env` changes need a manual restart.

**How to tell it's working:** generate a path and the weeks include real YouTube links. If instead the backend logs show `⚠️ WARNING: YOUTUBE_API_KEY missing`, the key isn't being read. A `403` from the YouTube API usually means daily quota is exhausted — it resets at midnight Pacific time.

---

## 📖 API Endpoints

### Base URL
```
http://127.0.0.1:8000/api
```

### `POST /generate` — Generate a Learning Path
**Currently Implemented** ✅

Generate a personalized learning roadmap for any topic.

**Request:**
```json
{
  "topic": "Learn Python for Data Science",
  "experience_level": "intermediate",
  "hours_per_day": 2
}
```

**Response:**
```json
{
  "title": "Python for Data Science Learning Path",
  "calculated_total_weeks": 8,
  "daily_hours_commitment": 2,
  "weeks": [
    {
      "week_number": 1,
      "focus": "Python fundamentals and NumPy basics",
      "topics": ["Variables", "Data types", "NumPy arrays"],
      "practice": ["Install Python", "Write basic scripts"],
      "mini_exercise": "Create a NumPy array and perform basic operations",
      "live_resources": [
        {
          "title": "NumPy Tutorial",
          "url": "https://...",
          "source": "YouTube"
        }
      ]
    }
  ],
  "learning_outcomes": ["Understand Python basics", "Use NumPy effectively"]
}
```

---

### Authentication
**Implemented** ✅

All `/generate` and `/quiz/*` endpoints require a Bearer token. Accounts live in a local SQLite
database (`courseforge.db`, gitignored) — passwords are stored only as **bcrypt hashes** (one-way,
unrecoverable by anyone, including developers).

- `POST /auth/register` — `{ "email", "password" }` → `{ access_token, token_type, email }` (password min 8 chars)
- `POST /auth/login` — same request/response; 401 on bad credentials
- `GET /auth/me` — returns the current user for a valid token

Send the token on protected calls: `Authorization: Bearer <access_token>`

---

### `POST /quiz/generate` — Generate a Quiz
**Implemented** ✅ *(Ollama `qwen3.5:9b` primary, Azure OpenAI fallback)*

Generate multiple choice and open-ended questions for a milestone.

**Request:**
```json
{
  "milestone": "Python fundamentals and NumPy basics",
  "week_number": 1
}
```

**Response:**
```json
{
  "week_number": 1,
  "milestone": "Python fundamentals and NumPy basics",
  "questions": [
    {
      "question_number": 1,
      "type": "multiple_choice",
      "question": "What is a NumPy array?",
      "options": ["A", "B", "C", "D"],
      "correct_answer": "A"
    },
    {
      "question_number": 4,
      "type": "open_ended",
      "question": "Explain when you would use a NumPy array over a Python list."
    }
  ]
}
```

---

### `POST /quiz/submit` — Grade Quiz Answers
**Implemented** ✅ *(MCQs graded deterministically; open-ended answers graded by AI)*

Submit quiz answers and receive AI-powered feedback.

**Request:**
```json
{
  "week_number": 1,
  "milestone": "Python fundamentals and NumPy basics",
  "questions": [...],
  "answers": [
    { "question_number": 1, "answer": "A" },
    { "question_number": 2, "answer": "True, because..." }
  ]
}
```

**Response:**
```json
{
  "week_number": 1,
  "score": 4,
  "total": 5,
  "passed": true,
  "feedback": [
    { "question_number": 1, "correct": true, "explanation": "..." }
  ],
  "overall_feedback": "Great understanding of the fundamentals!"
}
```

---

## 🤖 AI Model Routing

### Current Implementation
- **Azure OpenAI** — Generates personalized learning paths (configurable deployment)
- **Ollama (qwen3.5:9b)** — Primary model for quiz generation and open-ended answer grading
- **Automatic fallback** — If Ollama is unreachable (not running locally, or the backend is deployed to Azure without an Ollama host), quiz calls transparently fall back to Azure OpenAI
- **Deterministic MCQ grading** — Multiple-choice answers are scored in code against the stored correct answer; only open-ended answers go to the LLM

### Why Two Models?
- **Azure OpenAI** excels at complex curriculum design and understanding nuanced learning requirements
- **Ollama's qwen3.5:9b** efficiently generates and grades quizzes locally, reducing API costs and latency

---

## 🧪 Testing the API

### Option 1: Swagger UI (Recommended)
1. Start the backend: `uvicorn main:app --reload`
2. Open `http://127.0.0.1:8000/docs`
3. Click an endpoint → "Try it out" → Fill in request → "Execute"

### Option 2: cURL
Protected endpoints need a Bearer token — register once, then pass it in the header:
```bash
# 1. Register (or /api/auth/login if the account exists) and grab the access_token
curl -X POST "http://127.0.0.1:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"atleast8chars"}'

# 2. Call protected endpoints with the token
curl -X POST "http://127.0.0.1:8000/api/generate" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{"topic":"Learn Python","experience_level":"beginner","hours_per_day":2}'
```

### Option 3: Frontend UI
1. Start the backend and frontend
2. Open `http://localhost:5173`
3. Fill in the form and generate a path

---

## 🛠️ Setting Up Ollama for Quiz Generation

*This setup is optional — quiz endpoints automatically fall back to Azure OpenAI when Ollama isn't reachable. Run Ollama locally for free, low-latency quizzes.*

#### 1. Install Ollama
Download from https://ollama.com and follow installation instructions.

#### 2. Pull the required model
```bash
ollama pull qwen3.5:9b
```

**Note:** qwen3.5:9b requires ~6GB RAM. A machine with ≥16GB RAM is recommended.

#### 3. Start Ollama
```bash
ollama serve
```

#### 4. Update backend `.env`
```env
OLLAMA_HOST=http://localhost:11434
QUIZ_MODEL=qwen3.5:9b
```

---

## 📝 Project Contributions

### What my Partner (pratyushPtr) Built
- ✅ Full FastAPI backend with Azure OpenAI integration
- ✅ Learning path generation with dynamic timeline calculation
- ✅ Live resource fetching and injection
- ✅ React frontend with Vite and responsive UI
- ✅ CORS middleware for frontend-backend communication
- ✅ Dockerfiles for deployment

### What I'm Adding
- ✅ Ollama integration for quiz generation (`quiz_service.py`) with Azure OpenAI fallback
- ✅ `/api/quiz/generate` endpoint
- ✅ `/api/quiz/submit` endpoint with AI grading
- ✅ Quiz model routing and prompt engineering
- ✅ User accounts: register/login (SQLite + bcrypt + JWT) protecting all generation endpoints
- ✅ Frontend login/signup gate with persistent sessions and logout

---

## 🚀 Deployment

### Backend (Docker)
```bash
cd backend
docker build -t course-forge-backend .
docker run -p 8000:8000 --env-file .env course-forge-backend
```

### Frontend (Firebase/Vercel)
```bash
cd frontend
npm run build
firebase deploy
```

---

## 🐛 Troubleshooting

### Backend won't start
- Ensure Python 3.11+ is installed: `python --version`
- Verify virtual environment is activated
- Check `.env` file has all required Azure credentials

### Frontend can't connect to backend
- Ensure backend is running on `http://127.0.0.1:8000`
- Check CORS `ALLOWED_ORIGINS` in backend `.env`
- Open browser console (F12) for error messages

### Ollama errors
- Verify Ollama is running: `ollama serve` in a separate terminal
- Check model is installed: `ollama list` (and that it matches `QUIZ_MODEL` in `.env`)
- Verify `OLLAMA_HOST` in `.env` matches your setup
- Quizzes still work without Ollama — they fall back to Azure OpenAI (check backend logs for the fallback warning)

### Missing video resources / YouTube warnings
- `⚠️ WARNING: YOUTUBE_API_KEY missing` in backend logs → add your key to `.env` (see [Getting your own YouTube API key](#-getting-your-own-youtube-api-key-required--one-per-teammate)) and restart the backend
- Paths generate but weeks have no video links → same cause as above, or your daily YouTube quota ran out (`403` errors in logs); quota resets at midnight Pacific time
- Remember: `.env` changes require a **manual** backend restart — `--reload` only watches `.py` files

### Login/session issues
- "Session expired" on every restart → set a fixed `JWT_SECRET` in `.env`
- 401 on `/api/generate` or `/api/quiz/*` → the request is missing/expired its `Authorization: Bearer` token; log in again

---

## 📚 Resources

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Ollama Documentation](https://ollama.com/)
- [Azure OpenAI API](https://learn.microsoft.com/en-us/azure/cognitive-services/openai/)
- [React Documentation](https://react.dev/)
- [Vite Documentation](https://vitejs.dev/)

---

## 👥 Team

| Role | Responsibility |
|------|-----------------|
| **pratyushPtr** | Full-stack development (FastAPI backend, React frontend, Azure OpenAI integration) |
| **You** | Ollama integration for quiz generation, prompt engineering, deployment |

---

## 📌 Notes for Developers

- **No keys in code:** All credentials live in `.env` — never commit them
- **Use `--reload` during dev:** Backend auto-restarts on file changes
- **Check Swagger:** Open `/docs` to explore endpoints and schemas
- **Passwords are unrecoverable by design:** Only bcrypt hashes touch the database — there is no way (and no backdoor) to read a user's password
- **Known MVP tradeoff:** Generated quizzes include `correct_answer` in the payload the browser echoes back on submit, so grading stays stateless. Moving quiz storage server-side (planned with DB persistence) closes this
- **Model configs are flexible:** Override model names via `.env` without touching code

---

**Last updated:** July 2026  
**Status:** Pathway generation, user accounts, and quiz generation/grading all live