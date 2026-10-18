import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="AI Recruitment Screening Assistant",
    page_icon="📄",
    layout="wide"
)

# Initialize session state
if "page" not in st.session_state:
    st.session_state.page = "home"

if "job_id" not in st.session_state:
    st.session_state.job_id = None

if "job_title" not in st.session_state:
    st.session_state.job_title = ""

if "job_description" not in st.session_state:
    st.session_state.job_description = ""

if "screening_mode" not in st.session_state:
    st.session_state.screening_mode = "limited"

if "number_of_cvs" not in st.session_state:
    st.session_state.number_of_cvs = 5


# -------------------------
# Page 1: Job Title
# -------------------------
if st.session_state.page == "home":

    st.title("AI Recruitment Screening Assistant")
    st.write("Create a job to start screening candidates.")

    with st.form("job_title_form"):
        job_title = st.text_input(
            "Job Title",
            placeholder="e.g. AI Engineer"
        )

        continue_button = st.form_submit_button("Continue")

    if continue_button:
        if not job_title.strip():
            st.warning("Please enter a job title.")
        else:
            try:
                response = requests.post(
                    f"{API_URL}/jobs",
                    json={"job_name": job_title.strip()},
                    timeout=30
                )
                response.raise_for_status()

                job = response.json()["job"]

                st.session_state.job_id = job["job_id"]
                st.session_state.job_title = job_title.strip()
                st.session_state.job_description = ""
                st.session_state.screening_results = {}
                st.session_state.page = "details"

                st.rerun()

            except requests.RequestException as error:
                st.error(f"Could not create the job: {error}")

    # View previous jobs
    st.divider()
    st.subheader("View Previous Jobs")

    if st.button("Load Previous Jobs"):
        try:
            response = requests.get(
                f"{API_URL}/jobs",
                timeout=30
            )
            response.raise_for_status()

            st.session_state.previous_jobs = response.json().get(
                "jobs", {}
            )

        except requests.RequestException as error:
            st.error(f"Could not load previous jobs: {error}")

    previous_jobs = st.session_state.get("previous_jobs", {})

    if previous_jobs:
        for job_key, job in previous_jobs.items():
            job_id = job.get("job_id", job_key)
            title = job.get("title", f"Job {job_id}")

            with st.container():
                st.write(f"**{title}**")

                if st.button(
                    f"Open results — {title}",
                    key=f"open_job_{job_id}"
                ):
                    try:
                        response = requests.get(
                            f"{API_URL}/jobs/{job_id}/results",
                            timeout=30
                        )
                        response.raise_for_status()

                        st.session_state.job_id = job_id
                        st.session_state.job_title = title
                        st.session_state.job_description = job.get(
                            "description", ""
                        )
                        st.session_state.screening_results = (
                            response.json()
                        )

                        if st.session_state.screening_results.get(
                            "results"
                        ):
                            st.session_state.page = "results"
                        else:
                            st.session_state.page = "details"

                        st.rerun()

                    except requests.RequestException as error:
                        st.error(
                            f"Could not open this job: {error}"
                        )

    elif "previous_jobs" in st.session_state:
        st.info("No previous jobs found.")


# -------------------------
# Page 2: Job Details
# -------------------------
elif st.session_state.page == "details":

    st.title("Job Details")
    st.subheader(st.session_state.job_title)

    with st.form("job_details_form"):

        job_description = st.text_area(
            "Job Description",
            value=st.session_state.job_description,
            height=220,
            placeholder="Enter the job description..."
        )

        st.subheader("Screening Settings")

        screening_mode = st.radio(
            "Number of CVs to screen",
            ["Limited number", "All available CVs"],
            horizontal=True
        )

        number_of_cvs = 5

        if screening_mode == "Limited number":
            number_of_cvs = st.number_input(
                "Number of CVs",
                min_value=1,
                value=st.session_state.number_of_cvs,
                step=1
            )

        col1, col2 = st.columns(2)

        with col1:
            back_button = st.form_submit_button("Back")

        with col2:
            start_button = st.form_submit_button("Start Screening")

    if back_button:
        st.session_state.page = "home"
        st.rerun()

    if start_button:
        if not job_description.strip():
            st.warning("Please enter a job description.")
        else:
            try:
                job_id = st.session_state.job_id

                description_response = requests.post(
                    f"{API_URL}/jobs/{job_id}/description",
                    json={"description": job_description.strip()},
                    timeout=30
                )
                description_response.raise_for_status()

                if screening_mode == "Limited number":
                    screening_payload = {
                        "mode": "limited",
                        "number_of_cvs": int(number_of_cvs)
                    }
                else:
                    screening_payload = {"mode": "all"}

                settings_response = requests.post(
                    f"{API_URL}/jobs/{job_id}/screening",
                    json=screening_payload,
                    timeout=30
                )
                settings_response.raise_for_status()

                st.session_state.job_description = job_description.strip()
                st.session_state.number_of_cvs = int(number_of_cvs)
                st.session_state.screening_mode = (
                    "limited"
                    if screening_mode == "Limited number"
                    else "all"
                )

                with st.spinner(
                    "Screening CVs... Please wait."
                ):
                    screening_response = requests.post(
                        f"{API_URL}/jobs/{job_id}/screening/start",
                        timeout=None
                    )
                    screening_response.raise_for_status()

                st.session_state.screening_results = (
                    screening_response.json()
                )
                st.session_state.page = "results"
                st.rerun()

            except requests.RequestException as error:
                st.error(f"Screening failed: {error}")


# -------------------------
# Page 3: Results
# -------------------------
elif st.session_state.page == "results":

    st.title("Screening Results")
    st.subheader(st.session_state.job_title)

    job_id = st.session_state.get("job_id")
    data = st.session_state.get("screening_results", {})
    results = data.get("results", [])
    saved_decisions = {}

    # Load saved decisions only when a job ID exists
    if job_id is not None:
        try:
            response = requests.get(
                f"{API_URL}/jobs/{job_id}/results",
                timeout=30
            )
            response.raise_for_status()
            saved_decisions = response.json().get("decisions", {})
        except requests.RequestException as error:
            st.warning(f"Could not load saved decisions: {error}")

    matching_candidates = []
    non_matching_candidates = []

    for candidate in results:
        result_text = candidate.get("result", "").lower()

       
        if "match: yes" in result_text:
            matching_candidates.append(candidate)
        elif "match: no" in result_text:
            non_matching_candidates.append(candidate)

    col1, col2 = st.columns(2)
    col1.metric("Matching Candidates", len(matching_candidates))
    col2.metric("Non-Matching Candidates", len(non_matching_candidates))

    st.divider()
    st.subheader("✅ Matching Candidates")

    if matching_candidates:
        for index, candidate in enumerate(matching_candidates, start=1):
            filename = candidate.get("filename", "Unknown CV")

            with st.expander(f"{index}. {filename}"):
                st.write(candidate.get("result", ""))

                current_decision = saved_decisions.get(filename)
                st.write("**Candidate Action**")

                if current_decision:
                    st.info(f"Current decision: {current_decision}")
                else:
                    st.caption("No decision saved yet.")

                col1, col2, col3 = st.columns(3)

                decisions = {
                    "Shortlist": "shortlist",
                    "Review Later": "review_later",
                    "Reject": "reject"
                }

                for col, (decision, key_name) in zip(
                    [col1, col2, col3],
                    decisions.items()
                ):
                    with col:
                        if st.button(
                            decision,
                            key=f"{key_name}_{job_id}_{filename}"
                        ):
                            try:
                                response = requests.post(
                                    f"{API_URL}/jobs/{job_id}/decision",
                                    json={
                                        "filename": filename,
                                        "decision": decision
                                    },
                                    timeout=30
                                )
                                response.raise_for_status()
                                st.rerun()
                            except requests.RequestException as error:
                                st.error(
                                    f"Could not save decision: {error}"
                                )
    else:
        st.info("No matching candidates found.")

    st.divider()
    st.subheader("❌ Non-Matching Candidates")

    if non_matching_candidates:
        for index, candidate in enumerate(non_matching_candidates, start=1):
            with st.expander(
                f"{index}. {candidate.get('filename', 'Unknown CV')}"
            ):
                st.write(candidate.get("result", ""))
    else:
        st.info("No non-matching candidates found.")

    if st.button("Create Another Job"):
        st.session_state.page = "home"
        st.session_state.job_id = None
        st.session_state.job_title = ""
        st.session_state.job_description = ""
        st.session_state.pop("screening_results", None)
        st.rerun()
