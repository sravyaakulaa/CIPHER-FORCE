import os
import json
import re
import requests
from dotenv import load_dotenv

load_dotenv()

def _fallback_analysis(resume_text, job_description=""):
    """Useful baseline if API isn't configured; not represented as generative AI."""
    text = resume_text.lower()
    common = ["python", "java", "javascript", "sql", "mysql", "flask", "html", "css",
              "communication", "teamwork", "linux", "git", "cybersecurity", "data analysis"]
    found = [skill for skill in common if skill in text]
    missing = [skill for skill in common if skill not in text]
    jd_terms = []
    if job_description:
        jd_terms = list(dict.fromkeys(re.findall(r"\b[a-zA-Z][a-zA-Z+#.]{2,}\b", job_description.lower())))
        jd_terms = [x for x in jd_terms if x not in {"the", "and", "with", "for", "you", "are", "our", "this", "that"}]
    matched = [term for term in jd_terms if term in text]
    missing_jd = [term for term in jd_terms if term not in text][:15]
    score = min(100, max(15, 35 + len(found) * 4 + (len(matched) * 2 if job_description else 0)))
    return {
        "score": score,
        "summary": "Basic keyword-based review. Configure GEMINI_API_KEY in .env to enable AI-generated feedback.",
        "strengths": [f"Detected skill/keyword: {s}" for s in found[:8]] or ["Resume text was extracted successfully."],
        "improvements": ["Add measurable outcomes to project and experience bullet points.",
                         "Use clear section headings and consistent date formatting.",
                         "Tailor the resume to the specific job description."],
        "missing_skills": missing_jd if job_description else missing[:10],
        "keyword_matches": matched[:20],
        "formatting_tips": ["Use a simple, single-column layout for easier parsing.",
                            "Use standard headings such as Education, Skills, Projects, and Experience."],
        "disclaimer": "This is an estimate and does not guarantee how any employer's ATS will rank the resume."
    }


def analyze_resume(resume_text, job_description=""):
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        if os.getenv("ALLOW_BASIC_ANALYSIS", "true").lower() == "true":
            return _fallback_analysis(resume_text, job_description)
        raise RuntimeError("GEMINI_API_KEY is missing. Add it to your .env file.")
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    prompt = f"""
You are a practical resume reviewer. Review the resume text and optional job description.
Return ONLY valid JSON with exactly these keys:
score (integer 0-100), summary (string), strengths (array of strings),
improvements (array of strings), missing_skills (array of strings),
keyword_matches (array of strings), formatting_tips (array of strings),
disclaimer (string).
Be constructive, do not invent experience or credentials, and distinguish evidence from suggestions.
Score clarity, completeness, relevant skills, measurable impact, and keyword alignment.
If no job description is supplied, do not pretend to calculate job-specific matching.
The score is an advisory estimate, not a real ATS result.
RESUME TEXT:
{resume_text[:18000]}
JOB DESCRIPTION:
{job_description[:7000] if job_description else "(not provided)"}
"""
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}
    }
    response = requests.post(url, params={"key": api_key}, json=payload, timeout=60)
    if not response.ok:
        raise RuntimeError(f"Gemini API error ({response.status_code}): {response.text[:500]}")
    data = response.json()
    try:
        output = data["candidates"][0]["content"]["parts"][0]["text"]
        result = json.loads(output)
        score = int(result.get("score", 0))
        result["score"] = max(0, min(100, score))
        for key in ["strengths", "improvements", "missing_skills", "keyword_matches", "formatting_tips"]:
            if not isinstance(result.get(key), list):
                result[key] = []
        result.setdefault("summary", "Review complete.")
        result.setdefault("disclaimer", "This is an estimate, not a guarantee of ATS performance.")
        return result
    except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError("The AI response could not be parsed. Please try again.") from exc
