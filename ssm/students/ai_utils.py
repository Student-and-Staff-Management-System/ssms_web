from google import genai
from django.conf import settings
from google.genai import types
import json
import logging
import os
from dotenv import load_dotenv

load_dotenv()
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(BASE_DIR, '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)

logger = logging.getLogger(__name__)


def generate_resume_content(student_data):
    """
    Generates professional resume content using Gemini AI based on student data.
    Uses adaptive prompting based on available data richness.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY is not set in environment.")
        return {"error": "API Key not configured. Please contact administrator."}

    client = genai.Client(api_key=api_key)

    # Enhanced data assessment
    has_projects = bool(student_data.get('projects'))
    has_skills = bool(student_data.get('skills'))
    project_count = len(student_data.get('projects', []))
    skill_count = len(student_data.get('skills', []))
    
    # Determine optimal strategy
    # If student has ANY projects, use enhancement mode to respect their input
    is_fresher_mode = not has_projects
    
    if is_fresher_mode:
        prompt = _build_fresher_prompt(student_data)
    else:
        prompt = _build_enhancement_prompt(student_data)

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',  # Available high-performance model
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.7,
                max_output_tokens=8192,
            )
        )
        
        # Robust JSON parsing
        parsed_data = _parse_ai_response(response.text)
        
        # Validate and sanitize output
        validated_data = _validate_resume_data(parsed_data, student_data)
        
        return validated_data

    except Exception as e:
        logger.error(f"Error calling Gemini API: {str(e)}")
        return _handle_api_error(e, client)


def _build_fresher_prompt(student_data):
    """Builds prompt for students with minimal project/skill data."""
    return f"""
You are an expert ATS Resume Writer specializing in academic resumes for university students.

**STUDENT PROFILE:**
- Name: {student_data.get('name')}
- Program: {student_data.get('degree')} in {student_data.get('department')}
- Current Status: Student with limited industry experience

**SITUATION:** This student has minimal project data. Your goal is to create a compelling, truthful resume that highlights academic achievements and potential.

**STRICT REQUIREMENTS:**
1. **NO FABRICATION**: Never invent fake projects, companies, or experiences
2. **ONE PAGE CONSTRAINT**: Content must fit on a single page
3. **ATS-OPTIMIZED**: Use industry-standard keywords and formatting

**CONTENT STRATEGY - "Academic Excellence Showcase":**

### 1. Professional Summary (3-4 lines)
Write a compelling summary that:
- Highlights academic focus and learning achievements
- Emphasizes analytical thinking and technical foundation
- Shows enthusiasm for applying knowledge
- Uses keywords: "detail-oriented", "problem-solving", "quick learner"

### 2. Academic Projects Section (CRITICAL - Coursework as Projects)
Since no real projects exist, transform **3-4 major coursework modules** into project-style entries:

**Format for EACH:**
- **Title**: Course name (e.g., "Database Management Systems - Academic Project")
- **Role**: "Academic Coursework" or "Course Project"
- **Description**: Write 3-4 bullet points describing:
  - Key concepts mastered
  - Practical applications or labs completed
  - Tools/technologies used
  - Problem-solving approaches learned

**Example Structure:**
• Designed and implemented normalized database schemas for [domain] using SQL and ER modeling techniques
• Optimized query performance through indexing strategies, achieving [measurable improvement if applicable]
• Developed understanding of ACID properties and transaction management in multi-user environments

### 3. Technical Skills (8-12 items)
Infer realistic skills based on {student_data.get('department')} curriculum:
- Programming languages typically taught
- Tools and frameworks covered in courses
- Fundamental concepts (Data Structures, Algorithms, etc.)
- Any software commonly used in labs

### 4. Soft Skills (4-6 items)
Include high-value professional traits:
- Problem Solving
- Analytical Thinking
- Team Collaboration
- Time Management
- Adaptability
- Continuous Learning

### 5. Relevant Coursework (8-12 subjects)
List the most impressive/relevant courses from {student_data.get('department')}

**OUTPUT FORMAT (Valid JSON only):**
{{
    "summary": "3-4 line professional summary with strong keywords...",
    "projects_enhanced": [
        {{
            "title": "Course Name - Academic Project",
            "role": "Academic Coursework",
            "description": "• First achievement point using action verb\\n• Second technical detail with specifics\\n• Third outcome or learning with metrics if possible"
        }}
    ],
    "hard_skills": ["Skill1", "Skill2", "Skill3", ...],
    "soft_skills": ["Soft1", "Soft2", "Soft3", ...],
    "coursework_highlight": ["Course1", "Course2", ...]
}}

**QUALITY CHECKLIST:**
✓ All content is truthful and based on academic background
✓ Descriptions use strong action verbs (Developed, Implemented, Analyzed, Designed)
✓ Each project description has measurable outcomes where possible
✓ Skills are realistic for the program level
✓ Total content fits on one page when formatted
"""


def _build_enhancement_prompt(student_data):
    """Builds prompt for students with existing projects and skills."""
    projects_text = json.dumps(student_data.get('projects', []), indent=2)
    skills_text = ', '.join(student_data.get('skills', []))
    
    return f"""
You are a Senior Technical Recruiter and Resume Coach with experience at FAANG companies.

**STUDENT PROFILE:**
- Name: {student_data.get('name')}
- Program: {student_data.get('degree')} in {student_data.get('department')}
- Provided Skills: {skills_text}
- Provided Projects: {projects_text}

**YOUR MISSION:** Transform this raw data into a polished, ATS-friendly, recruiter-ready resume.

**STRICT REQUIREMENTS:**
1. **PRIORITIZE USER DATA:** You MUST use the provided projects ('expense detector', etc.) as the core content. Do NOT ignore them.
2. **ENHANCE, DON'T REPLACE:** Rewrite the provided project descriptions to be professional and technical (STAR method), but keep the core subject matter.
3. **ONE PAGE**: Ensure content density is appropriate.
4. **ATS OPTIMIZATION**: Use keywords, avoid graphics/tables in descriptions.
5. **IMPACT FOCUS**: Quantify achievements wherever possible.

**ENHANCEMENT STRATEGY - "STAR Method Elevation":**

### 1. Professional Summary (3-4 lines)
Synthesize their experience into a unique value proposition:
- Lead with strongest technical skills
- Highlight most impressive project outcomes
- Show trajectory and career readiness
- Use power words: "skilled", "proven", "demonstrated"

### 2. Projects Enhancement (Use STAR/CAR Method)
For EACH project, restructure descriptions to tell a compelling story:

**STAR Framework:**
- **Situation/Context**: What problem or challenge existed?
- **Task**: What was your specific responsibility?
- **Action**: What technologies and approaches did you use?
- **Result**: What was the measurable outcome?

**Enhancement Rules:**
- Start each bullet with strong action verbs (Engineered, Architected, Optimized, Implemented)
- Add specific metrics where applicable (improved performance by X%, reduced time by Y)
- Highlight technical complexity (data structures used, scale handled, etc.)
- Mention collaboration if it was a team project
- Bold key technologies: **React**, **Python**, **AWS**

**Example Transformation:**
BEFORE: "Made a website for booking appointments"
AFTER: "• Developed a full-stack appointment booking system using **React** and **Node.js**, supporting 500+ concurrent users with real-time availability updates\\n• Implemented secure JWT-based authentication and role-based access control (RBAC) for patient and doctor portals\\n• Reduced appointment scheduling time by 60% through optimized database queries and caching strategies"

### 3. Skills Organization
- **Keep all provided skills** but reorganize logically
- Group by category if possible (Languages, Frameworks, Tools, Concepts)
- Add 2-3 complementary skills if they're obvious prerequisites:
  - If React → likely knows JavaScript, HTML, CSS
  - If Machine Learning → likely knows NumPy, Pandas
  - If Backend → likely knows REST APIs, databases
- List 10-15 hard skills maximum
- 4-6 soft skills

### 4. Relevant Coursework (8-10 items)
Select courses that complement the project work shown

**OUTPUT FORMAT (Valid JSON only):**
{{
    "summary": "Compelling 3-4 line professional summary...",
    "projects_enhanced": [
        {{
            "title": "Original Project Title",
            "role": "Original or Enhanced Role",
            "description": "• **Context**: Specific situation or problem\\n• **Implementation**: Technical approach with bolded tools\\n• **Outcome**: Quantified result or impact"
        }}
    ],
    "hard_skills": ["Skill1", "Skill2", ...],
    "soft_skills": ["Leadership", "Problem Solving", ...],
    "coursework_highlight": ["Course1", "Course2", ...]
}}

**QUALITY CHECKLIST:**
✓ Each project has 3-4 impactful bullet points
✓ Metrics and numbers included where possible
✓ Technical complexity is evident
✓ Language is confident and professional
✓ Skills list is comprehensive but focused
✓ All JSON is properly formatted
"""


def _parse_ai_response(response_text):
    """Robustly parse JSON from AI response."""
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        # Try to extract JSON from markdown code blocks
        text = response_text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response: {e}\nResponse: {response_text[:500]}")
            raise ValueError("AI returned invalid JSON format")


def _validate_resume_data(parsed_data, original_data):
    """Validate and sanitize AI-generated resume data."""
    validated = {
        'summary': '',
        'projects_enhanced': [],
        'hard_skills': [],
        'soft_skills': [],
        'coursework_highlight': []
    }
    
    # Validate summary
    if 'summary' in parsed_data and isinstance(parsed_data['summary'], str):
        validated['summary'] = parsed_data['summary'][:500]  # Cap length
    
    # Validate projects
    if 'projects_enhanced' in parsed_data and isinstance(parsed_data['projects_enhanced'], list):
        for project in parsed_data['projects_enhanced'][:5]:  # Max 5 projects
            if isinstance(project, dict) and all(k in project for k in ['title', 'role', 'description']):
                validated['projects_enhanced'].append({
                    'title': str(project['title'])[:100],
                    'role': str(project['role'])[:50],
                    'description': str(project['description'])[:800]
                })
    
    # Validate skills
    for skill_type in ['hard_skills', 'soft_skills']:
        if skill_type in parsed_data and isinstance(parsed_data[skill_type], list):
            validated[skill_type] = [str(s)[:50] for s in parsed_data[skill_type][:15]]
    
    # Validate coursework
    if 'coursework_highlight' in parsed_data and isinstance(parsed_data['coursework_highlight'], list):
        validated['coursework_highlight'] = [str(c)[:60] for c in parsed_data['coursework_highlight'][:12]]
    
    return validated


def _handle_api_error(error, client):
    """Handle API errors gracefully with helpful messages."""
    error_msg = str(error)
    
    if "404" in error_msg:
        # Try to get available models
        try:
            valid_models = [m.name for m in client.models.list() 
                          if 'generateContent' in m.supported_generation_methods]
            return {"error": f"Model not found. Available models: {', '.join(valid_models[:3])}"}
        except:
            return {"error": "Model not found. Please check your API configuration."}
    
    elif "429" in error_msg:
        return {"error": "API rate limit exceeded. Please try again in a few moments."}
    
    elif "403" in error_msg:
        return {"error": "API access denied. Please verify your API key."}
    
    else:
        return {"error": f"AI service error: {error_msg[:200]}"}