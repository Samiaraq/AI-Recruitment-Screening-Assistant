from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json
from pathlib import Path
from main import process_cvs
app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent
JOBS_FILE = BASE_DIR / "jobs.json"


def load_jobs():
    if not JOBS_FILE.exists():
        return {}

    with open(JOBS_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_jobs():
    with open(JOBS_FILE, "w", encoding="utf-8") as file:
        json.dump(
            {
                "jobs": jobs,
                "next_job_id": next_job_id
            },
            file,
            ensure_ascii=False,
            indent=4
        )
data = load_jobs()

jobs = {
    int(job_id): job
    for job_id, job in data.get("jobs", {}).items()
}

next_job_id = data.get("next_job_id", 1)

class JobTitle(BaseModel):
    job_name: str


class JobDescription(BaseModel):
    description: str

class CandidateDecision(BaseModel):
    filename: str
    decision: str
    
@app.get("/")
def home():
    return {
        "message": "AI Recruitment Screening Assistant API is running"
    }
@app.get("/jobs")
def get_jobs():
    return{
        "jobs": jobs
    }

# First POST: Create a job using its name
@app.post("/jobs")
def create_job(job: JobTitle):
    global next_job_id

    job_id = next_job_id

    jobs[job_id] = {
        "job_id": job_id,
        "title": job.job_name,
        "description": None
    }

    next_job_id += 1
    save_jobs()

    return {
        "message": "Job created successfully",
        "job": jobs[job_id]
    }


# Second POST: Add the description to the existing job
@app.post("/jobs/{job_id}/description")
def add_job_description(job_id: int, job: JobDescription):

    if job_id not in jobs:
        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )

    jobs[job_id]["description"] = job.description
    save_jobs()


    return {
        "message": "Job description added successfully",
        "job": jobs[job_id]
    }


class ScreeningRequest(BaseModel):
    mode: str
    number_of_cvs: int | None = None



@app.post("/jobs/{job_id}/screening")
def configure_screening(job_id: int, request: ScreeningRequest):

    if job_id not in jobs:
        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )

    if request.mode == "limited":

        if request.number_of_cvs is None or request.number_of_cvs <= 0:
            raise HTTPException(
                status_code=400,
                detail="Enter a positive number of CVs"
            )

        number_of_cvs = request.number_of_cvs

    elif request.mode == "all":
        number_of_cvs = None

    else:
        raise HTTPException(
            status_code=400,
            detail="Mode must be 'limited' or 'all'"
        )

    jobs[job_id]["screening"] = {
        "mode": request.mode,
        "number_of_cvs": number_of_cvs
    }
    save_jobs()

    return {
        "message": "Screening settings saved successfully",
        "job_id": job_id,
        "screening": jobs[job_id]["screening"]
    }

@app.post("/jobs/{job_id}/screening/start")
def start_screening(job_id: int):

    if job_id not in jobs:
        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )

    job = jobs[job_id]

    if not job.get("description"):
        raise HTTPException(
            status_code=400,
            detail="Add a job description before screening"
        )

    screening = job.get("screening")

    if not screening:
        raise HTTPException(
            status_code=400,
            detail="Configure screening settings first"
        )

    number_of_cvs = screening["number_of_cvs"]

    try:
        output = process_cvs(
            job["description"],
            number_of_cvs=number_of_cvs
        )
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Screening failed: {str(error)}"
        )

    job["results"] = output["results"]
    job["errors"] = output["errors"]
    save_jobs()

    return {
        "message": "Screening completed",
        "job_id": job_id,
        "results": output["results"],
        "errors": output["errors"]
    }
@app.get("/jobs/{job_id}/results")
def get_screening_results(job_id: int):

    if job_id not in jobs:
        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )

    return {
        "job_id": job_id,
        "results": jobs[job_id].get("results", []),
        "errors": jobs[job_id].get("errors", []),
        "decisions": jobs[job_id].get("decisions", {})
    }

@app.post("/jobs/{job_id}/decision")
def save_candidate_decision(job_id: int, candidate: CandidateDecision):

    if job_id not in jobs:
        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )

    allowed_decisions = ["Shortlist", "Review Later", "Reject"]

    if candidate.decision not in allowed_decisions:
        raise HTTPException(
            status_code=400,
            detail="Invalid candidate decision"
        )

    results = jobs[job_id].get("results", [])

    candidate_exists = any(
        item.get("filename") == candidate.filename
        for item in results
    )

    if not candidate_exists:
        raise HTTPException(
            status_code=404,
            detail="Candidate not found"
        )

    decisions = jobs[job_id].setdefault("decisions", {})
    decisions[candidate.filename] = candidate.decision

    save_jobs()

    return {
        "message": "Candidate decision saved successfully",
        "filename": candidate.filename,
        "decision": candidate.decision
    }