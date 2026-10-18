from ollama import chat 
from pathlib import Path
MODEL_NAME = "qwen3:8b" 

def load_job_description():
    BASE_DIR = Path(__file__).resolve().parent
    JOB_FILE = BASE_DIR / "job_description.txt"

    return JOB_FILE.read_text(encoding="utf-8")




def check_cv_match(job_description, cv_text):
    rule = f"""
    You are an AI CV screening assistant.

    Compare the job description with the CV text carefully.

    Evaluate the candidate using these rules:

    1. Identify the must-have skills explicitly required
       in the job description.
    2. Check which must-have skills are supported by
       evidence in the CV.
    3. List the missing must-have skills.
    4. If at least one must-have skill is missing,
       answer NO.
    5. If all must-have skills are present, answer YES,
       then explain why the candidate matches.
    6. Do not assume a skill exists unless the CV
       provides supporting evidence.
    7. If the job description does not clearly specify
       must-have skills, evaluate the overall match
       and explain the limitation.

    Return your answer in this exact format:

    1- Match: YES or NO
    2- Must-Have Skills Found: list the skills
    3- Missing Must-Have Skills: list the skills
    4- Evidence from CV: explain the supporting evidence
    5- Explanation: explain the final decision

    Job Description:
    {job_description}

    CV Text:
    {cv_text}
    """

    try:
        response = chat(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "user",
                    "content": rule
                }
            ]
        )
        return response["message"]["content"]

    except Exception as error:
        print(f"Error matching CV: {error}")
        return None
