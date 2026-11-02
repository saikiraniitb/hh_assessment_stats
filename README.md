# Hiringhood Assessment Stats

Independent **post-assessment** Streamlit dashboard for three Data Engineer contests.

| Level | Contest ID |
|---|---|
| Junior | `6ae0de2aadbc2668e8190525` |
| Mid | `6ae0de9ac4a2c5c791cfea9f` |
| Senior | `6ae0dfbfadbc2668e8190529` |

## Status

**Phase 1 scaffold.** Candidate/recruiter data and Hiringhood MCQ scores are joined using the existing verified `hh_registrations` logic. JD-to-CV, Copilot, My Mapit MCQ, My Mapit Coding and My Mapit attempt-date fields intentionally remain blank until source collections, join keys, and score scales are verified. Blank **does not** mean zero or not attempted.

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

### Pending integration

Map each external assessment's collection/API, candidate ID, contest/JD ID, assessment type, result field, score scale, timestamp, and latest-vs-best attempt rules. Prefer stable keys. Do not join people solely by name; assess email-based matching for collisions before enabling.
