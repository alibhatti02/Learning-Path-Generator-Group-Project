import os
import json
from openai import AzureOpenAI
from dotenv import load_dotenv

# Automatically load environmental variables from the backend/.env file
load_dotenv()

# Extract your Azure credentials from the runtime environment
api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "")
api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-05-01-preview")

# Lazily initialize the Azure OpenAI client so the app can still boot (auth, health checks)
# when Azure credentials are absent — the error surfaces on first AI call instead of at import.
_client = None

def get_azure_client() -> AzureOpenAI:
    global _client
    if _client is None:
        _client = AzureOpenAI(
            azure_endpoint=endpoint.rstrip("/"),
            api_key=api_key,
            api_version=api_version
        )
    return _client

def generate_learning_roadmap(topic: str, hours_per_day: int, level: str) -> dict:
    """
    Submits user metrics to Azure OpenAI, allows the AI to dynamically 
    determine the duration of the path, and returns a structured dictionary.
    """
    try:
        # We explicitly command the model to gauge complexity and calculate the required weeks
        user_prompt = (
            f"Create a comprehensive learning path for the topic '{topic}'. "
            f"The user is a '{level}' and can commit exactly {hours_per_day} hours per day. "
            f"Based on the depth of this topic and their daily time commitment, you must dynamically "
            f"determine the optimal number of weeks required to reach a competent milestone."
        )
        
        # Added 'calculated_total_weeks' to the payload blueprint so the frontend knows the timeline size
        system_prompt = (
            "You are an expert technical curriculum designer. Your job is to evaluate a topic's difficulty, "
            "calculate the total number of weeks needed based on a user's daily hours commitment, and output a structured plan.\n\n"
            "CRITICAL: You must respond ONLY with a valid JSON object. Do not include markdown code block formatting (like ```json). "
            "The JSON object must strictly match this structure:\n"
            "{\n"
            "  \"title\": \"Title of the learning path\",\n"
            "  \"calculated_total_weeks\": 6,\n"
            "  \"daily_hours_commitment\": 2,\n"
            "  \"weeks\": [\n"
            "    {\n"
            "      \"week_number\": 1,\n"
            "      \"focus\": \"Main focus area for this week\",\n"
            "      \"topics\": [\"Topic 1\", \"Topic 2\"],\n"
            "      \"search_queries\": [\"Optimized search item 1\",\"Optimized search item 2\"],\n"
            "      \"practice\": [\"Practice task 1\", \"Practice task 2\"],\n"
            "      \"mini_exercise\": \"Short weekly assignment details\"\n"
            "    }\n"
            "  ],\n"
            "  \"learning_outcomes\": [\"Outcome 1\", \"Outcome 2\"]\n"
            "}"
        )
        
        # Dispatch the request to your deployment
        response = get_azure_client().chat.completions.create(
            model=deployment_name,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        
        raw_content = response.choices[0].message.content
        return json.loads(raw_content)

    except Exception as e:
        print("\n" + "="*60)
        print(f"🔍 AZURE DIAGNOSTIC TRACE:\n{str(e)}")
        print("="*60 + "\n")
        
        return {"error": f"AI Generation Failed: {str(e)}"}