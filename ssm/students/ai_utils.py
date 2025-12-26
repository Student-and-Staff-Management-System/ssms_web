
from google import genai
from django.conf import settings
from google.genai import types
import json
import logging

logger = logging.getLogger(__name__)

def generate_resume_content(student_data):
    """
    Generates professional resume content using Gemini AI based on student data.
    """
    api_key = getattr(settings, 'GEMINI_API_KEY', None)
    if not api_key:
        logger.error("GEMINI_API_KEY is not set in settings.")
        return {"error": "API Key not configured."}

    client = genai.Client(api_key=api_key)

    # Construct the Prompt
    prompt = f"""
    Act as a professional Resume Writer and ATS Optimization Expert. 
    I will provide you with raw data about a student. 
    Your task is to expanding this into a high-quality, full-page professional resume content.
    
    **Instructions:**
    1. **Professional Summary**: Write a compelling, paragraph-length summary (60-80 words) highlighting their potential, academic background, and key skills.
    2. **Projects**: For each project provided, rewrite the description using the **STAR method** (Situation, Task, Action, Result). Expand it to be detailed and multiline (at least 3-4 bullet points per project). Use strong action verbs.
    3. **Soft Skills**: Infer 4-5 relevant soft skills based on their projects and potential profile.
    4. **Formatting**: Return ONLY valid JSON.
    
    **Input Data:**
    Name: {student_data.get('name')}
    Degree: {student_data.get('degree')}
    Department: {student_data.get('department')}
    Skills: {', '.join(student_data.get('skills', []))}
    Projects: {json.dumps(student_data.get('projects', []))}
    
    **Required JSON Output Structure:**
    {{
        "summary": "...", 
        "projects_enhanced": [
            {{ "title": "Project Title", "role": "Role", "description": "• Bullet 1\n• Bullet 2..." }} 
        ],
        "hard_skills": ["Skill1", "Skill2"],
        "soft_skills": ["SoftSkill1", "SoftSkill2"],
        "coursework_highlight": ["Subject1", "Subject2"] 
    }}
    """

    try:
        response = client.models.generate_content(
            model='gemini-flash-lite-latest', # Stable alias for lowest latency/cost model
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            )
        )
        
        try:
            return json.loads(response.text)
        except json.JSONDecodeError:
            text_response = response.text.strip()
            if text_response.startswith("```json"):
                text_response = text_response[7:]
            if text_response.endswith("```"):
                text_response = text_response[:-3]
            return json.loads(text_response)

    except Exception as e:
        logger.error(f"Error calling Gemini API: {str(e)}")
        
        # Diagnostic: List valid models if 404 or other error
        valid_models = []
        try:
            for m in client.models.list():
                if 'generateContent' in m.supported_generation_methods:
                    valid_models.append(m.name)
        except:
            pass
            
        error_msg = str(e)
        if "404" in error_msg:
            error_msg = f"Model 'gemini-1.5-flash-001' not found. Available: {', '.join(valid_models[:5])}..."
        elif "429" in error_msg:
            error_msg = "Quota exceeded (Free Tier). Please wait a moment."
            
        return {"error": error_msg}
