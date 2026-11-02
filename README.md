# Hiringhood Assessment Stats

Independent **post-assessment** Streamlit dashboard for three Data Engineer contests.

| Level | Contest ID |
|---|---|
| Junior | `6ae0de2aadbc2668e8190525` |
| Mid | `6ae0de9ac4a2c5c791cfea9f` |
| Senior | `6ae0dfbfadbc2668e8190529` |

## Status

**Assessment integrations mapped.** Candidate/recruiter and HH MCQ data are joined from the registration sources. JD-to-CV, Copilot, and My Mapit MCQ/Coding/completedAt are sourced from contest-specific `recruiterAddProfiles.jobseekerDetails` entries. My Mapit section scores retain their native denominators (sample: MCQ /20, Coding /80). Blank **does not** mean zero or not attempted.

### Report columns (exact order)

JS Name, Contest Name, Recruiter Name, Email, Phone Number, JD to CV Match Score, HH MCQ, Copilot Score, My Mapit MCQ, My Mapit Coding, My Mapit Attempted Date.

### Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export MONGODB_URI='mongodb+srv://READ_ONLY_ACCOUNT:REDACTED@CLUSTER/?retryWrites=false'
streamlit run app.py
```

Optional environment: `MONGO_DB` (Marketplace), `MATCHDAY_CONTEST_IDS` (comma-separated), `REFRESH_MINUTES` (25).

### Security

This report contains sensitive candidate data. **Make this repository private** and deploy with application-level authentication/SSO and role-based access; a private repository alone does not secure Streamlit. Use a MongoDB read-only user, network restrictions, and Streamlit Secrets. Never commit connection strings or exported candidate reports.

### Validation needed

Validate latest-upload precedence, duplicate candidate uploads, score coverage, recruiter attribution, and whether the latest scored MCQ attempt should be preferred over an in-progress attempt. This is read-only; validate live reporting behind authentication. No guessing or cross-contest reuse of scores.
