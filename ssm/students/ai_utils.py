
from google import genai
from django.conf import settings
from google.genai import types
import json
import logging
import os
logger = logging.getLogger(__name__)

def generate_resume_content(student_data):
    """
    Generates professional resume content using Gemini AI based on student data.
    """
    
    if not api_key:
        logger.error("GEMINI_API_KEY is not set in settings.")
        return {"error": "API Key not configured."}

    client = genai.Client(api_key=api_key)

    # Determine Strategy based on data availability
    is_fresher_mode = not student_data.get('projects') or not student_data.get('skills')
    
    strategy_instruction = ""
    if is_fresher_mode:
        strategy_instruction = f"""
        **SPECIAL SCENARIO: FRESHER / NO DATA ENTRY**
        The student has provided NO specific skills or projects. 
        **You MUST ACT as a Career Mentor.**
        
        1.  **INFER Skills**: Based on their Degree ({student_data.get('degree')}) and Department ({student_data.get('department')}), list 6-8 high-value, relevant technical skills that a top student in this field *should* have.
        2.  **CREATE a Capstone Project**: Hallucinate a strong, impressive "Senior Year Capstone Project" relevant to their field. Give it a title, a role (e.g., "Lead Student Developer"), and a rich STAR-method description of what they *could* have built. 
        3.  **Tone**: Emphasize "Fast Learner," "Academic Excellence," and "High Potential."
        """

    # Construct the Prompt
    prompt = f"""
    You are an expert Resume Writer and Career Strategist with decades of experience at top tech firms (FAANG).
    The user is a student/fresher who needs a **one-page, high-impact resume** that is completely filled but **STRICTLY limited to one page**.
    
    {strategy_instruction}

    **YOUR GOAL:** 
    Create dense, high-quality content that fits perfectly on a single page. Do not over-generate.
    
    **CRITICAL INSTRUCTIONS:**
    
    1.  **Professional Summary (concise)**:
        - Write a robust, 3-4 line summary (max 60-80 words).
        - Focus on 'Unfair Advantage' and key technical strengths.
        - Use words like "Results-oriented," "Innovative," "Passionate."

    2.  **Projects (High Impact, Compact)**:
        - For EACH project (or the created Capstone), generate a **Title** and a **Role**.
        - Write a **Description** using the **STAR Method**.
        - **Constraint**: Max 3-4 bullet points per project. Ensure they are punchy and fit on the page.
        - **Format**:
            *   **Situation/Task**: "Identified a need for..."
            *   **Action**: "Architected a solution using [Tech]..."
            *   **Result**: "Achieved X% improvement..."
        - Infer plausible technical details if input is sparse.

    3.  **Technical Skills**:
        - Group them efficiently (e.g., "Languages," "Frameworks").

    4.  **Soft Skills**:
        - Generate 5-6 high-level soft skills.

    5.  **Coursework**:
        - List 6-8 relevant subjects.
    
    **Input Data:**
    Name: {student_data.get('name')}
    Degree: {student_data.get('degree')}
    Department: {student_data.get('department')}
    Skills: {', '.join(student_data.get('skills', []))}
    Projects: {json.dumps(student_data.get('projects', []))}
    
    **Required JSON Output Structure:**
    {{
        "summary": "Full text string...", 
        "projects_enhanced": [
            {{ 
                "title": "Project Name", 
                "role": "Role Name", 
                "description": "• **Situation:** [Text]...\\n• **Action:** [Text]...\\n• **Result:** [Text]..." 
            }} 
        ],
        "hard_skills": ["Skill1 (Expert)", "Skill2"],
        "soft_skills": ["Skill1", "Skill2", ...],
        "coursework_highlight": ["Subject 1", "Subject 2", ...] 
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
