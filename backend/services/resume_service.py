import base64
import io
import json
from urllib.parse import quote_plus

from docx import Document
from pypdf import PdfReader

from services.ai_service import azure_chat_json

# Keep prompts bounded — a resume should never be anywhere near this long anyway
MAX_RESUME_CHARS = 15000

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
IMAGE_MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}

SYSTEM_PROMPT = (
    "You are an expert ATS (Applicant Tracking System) auditor and career coach for "
    "early-career tech candidates. Analyze the resume you are given.\n\n"
    "CRITICAL: Respond ONLY with a valid JSON object, no markdown fences, matching exactly:\n"
    "{\n"
    '  "ats_score": 78,\n'
    '  "summary": "2-3 sentence overall assessment",\n'
    '  "issues": [{"severity": "high", "issue": "what is wrong", "fix": "how to fix it"}],\n'
    '  "enhancements": ["specific rewrite or addition suggestion"],\n'
    '  "recommended_roles": [{"title": "Job title to search for", "reason": "why this fits", '
    '"keywords": "comma-separated ATS keywords to add"}]\n'
    "}\n"
    "Rules: ats_score is 0-100 reflecting ATS parseability and keyword strength. severity is "
    'one of "high", "medium", "low". Give 3-6 issues, 3-5 enhancements, and 3-5 recommended '
    "roles suited to the candidate's actual experience level. Be specific to this resume, "
    "never generic."
)


def _extract_text(filename: str, content: bytes) -> str:
    """Pulls plain text out of PDF/DOCX/TXT uploads. Raises ValueError on unusable files."""
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext == ".pdf":
        reader = PdfReader(io.BytesIO(content))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    elif ext == ".docx":
        doc = Document(io.BytesIO(content))
        text = "\n".join(p.text for p in doc.paragraphs)
    elif ext == ".txt":
        text = content.decode("utf-8", errors="replace")
    else:
        raise ValueError(f"Unsupported file type '{ext}'. Upload a PDF, DOCX, TXT, or image.")

    if not text.strip():
        raise ValueError("No readable text found in the file — if it's a scanned resume, upload it as an image instead.")
    return text[:MAX_RESUME_CHARS]


def _build_user_message(filename: str, content: bytes) -> dict:
    """Text files become a text prompt; images go to the model as vision input."""
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext in IMAGE_EXTENSIONS:
        data_uri = f"data:{IMAGE_MIME[ext]};base64,{base64.b64encode(content).decode()}"
        return {
            "role": "user",
            "content": [
                {"type": "text", "text": "Analyze this resume image for ATS issues and job fit."},
                {"type": "image_url", "image_url": {"url": data_uri}},
            ],
        }

    resume_text = _extract_text(filename, content)
    return {"role": "user", "content": f"Analyze this resume:\n\n{resume_text}"}


def analyze_resume(filename: str, content: bytes) -> dict:
    """Runs the GPT-5 ATS scan and attaches LinkedIn/Indeed search deep-links per role."""
    user_message = _build_user_message(filename, content)

    try:
        report = azure_chat_json([{"role": "system", "content": SYSTEM_PROMPT}, user_message])
    except Exception as e:
        raise RuntimeError(f"Resume analysis failed: {e}")

    # LinkedIn/Indeed have no open job-search APIs, so we deep-link into their search
    # pages with the recommended title pre-filled — zero keys, always up to date.
    for role in report.get("recommended_roles", []):
        query = quote_plus(str(role.get("title", "")))
        role["linkedin_url"] = f"https://www.linkedin.com/jobs/search/?keywords={query}"
        role["indeed_url"] = f"https://www.indeed.com/jobs?q={query}"

    return report
