import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
from bson import ObjectId
from pymongo import MongoClient
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Hiringhood | Post-assessment Stats", page_icon="📊", layout="wide")
IST = ZoneInfo("Asia/Kolkata")
DB_NAME = os.getenv("MONGO_DB", "Marketplace")
DEFAULT_IDS = [
    "6ae0de9ac4a2c5c791cfea9f",  # Data Engineer - Mid
    "6ae0de2aadbc2668e8190525",  # Data Engineer - Junior
    "6ae0dfbfadbc2668e8190529",  # Data Engineer - Senior
]
CONTEST_IDS = [x.strip() for x in os.getenv("MATCHDAY_CONTEST_IDS", ",".join(DEFAULT_IDS)).split(",") if x.strip()]
REFRESH_MS = max(1, int(os.getenv("REFRESH_MINUTES", "25"))) * 60 * 1000


def sid(value):
    return str(value) if value is not None else ""


def mongo_ids(values):
    result = list(values)
    for value in values:
        if isinstance(value, str) and ObjectId.is_valid(value):
            result.append(ObjectId(value))
    return result


def timestamp(value):
    if not isinstance(value, datetime):
        return datetime.min.replace(tzinfo=timezone.utc)
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def fmt_date(value):
    return timestamp(value).astimezone(IST).strftime("%d %b %Y %I:%M %p") if isinstance(value, datetime) else ""


def normal_email(value):
    return str(value or "").strip().casefold()


def jobseeker_location(profile):
    """Prefer current employment location; use resume address when unavailable."""
    work = profile.get("work_experience") or []
    records = work if isinstance(work, list) else [work]
    current = next((w for w in records if isinstance(w, dict) and w.get("isCurrentlyWorking") and w.get("currentLocation")), None)
    if current:
        return str(current["currentLocation"]).strip()
    resume = ((profile.get("completeResumeDetails") or {}).get("parsed_resume") or {}).get("ResumeParserData") or {}
    addresses = resume.get("Address") or []
    if isinstance(addresses, dict):
        addresses = [addresses]
    for address in addresses:
        if not isinstance(address, dict):
            continue
        city = str(address.get("City") or "").strip()
        state = str(address.get("State") or "").strip()
        if city:
            return ", ".join(x for x in (city, state) if x and x.casefold() != city.casefold())
    return next((str(w.get("currentLocation")).strip() for w in records if isinstance(w, dict) and w.get("currentLocation")), "")


def name_from(profile, user):
    info = profile.get("personal_info") or {}
    return " ".join(str(info.get(k) or "").strip() for k in ("firstName", "middleName", "lastName")).strip() or " ".join(str(user.get(k) or "").strip() for k in ("firstName", "lastName")).strip() or user.get("name") or ""


@st.cache_resource
def get_client(uri):
    return MongoClient(uri, serverSelectionTimeoutMS=12000, readPreference="secondaryPreferred")


@st.cache_data(ttl=60, show_spinner="Reading MongoDB…")
def load_data(_client, ids):
    db = _client[DB_NAME]
    cid_values = mongo_ids(list(ids))
    contests = list(db.contests.find({"contestId": {"$in": cid_values}}, {"contestId": 1, "details.jobDetails.jobTitle": 1}))
    titles = {sid(c.get("contestId")): (c.get("details") or {}).get("jobDetails", {}).get("jobTitle", sid(c.get("contestId"))) for c in contests}
    members = list(db.jobSeekerContests.find({"contestId": {"$in": cid_values}}, {"contestId": 1, "jobSeekerId": 1, "applicationStatus": 1, "byRecruiter": 1, "referedBy": 1, "createdAt": 1}))
    attempts = list(db.mcqAttempts.find({"contestId": {"$in": cid_values}}, {"contestId": 1, "jobseekerId": 1, "recruiterId": 1, "status": 1, "startedAt": 1, "submittedAt": 1, "result.percentageScore": 1}))
    candidate_ids = {sid(x.get("jobSeekerId")) for x in members if x.get("jobSeekerId")}
    candidate_ids.update(sid(x.get("jobseekerId")) for x in attempts if x.get("jobseekerId"))
    users = list(db.users.find({"_id": {"$in": mongo_ids(list(candidate_ids))}}, {"email": 1, "source": 1, "name": 1, "firstName": 1, "lastName": 1}))
    profiles = list(db.jobSeekerProfile.find({"_id": {"$in": mongo_ids(list(candidate_ids))}}, {"personal_info.firstName": 1, "personal_info.middleName": 1, "personal_info.lastName": 1, "personal_info.email": 1, "personal_info.phoneNumber": 1, "work_experience.currentLocation": 1, "work_experience.isCurrentlyWorking": 1, "completeResumeDetails.parsed_resume.ResumeParserData.Address.City": 1, "completeResumeDetails.parsed_resume.ResumeParserData.Address.State": 1}))
    # One upload may appear multiple times. Choose a candidate/contest-specific record without multiplying totals.
    uploads = list(db.recruiterAddProfiles.find({"contestId": {"$in": cid_values}}, {"contestId": 1, "recruiterId": 1, "jobseekerDetails.jsId": 1, "jobseekerDetails.source": 1, "jobseekerDetails.createdAt": 1, "jobseekerDetails.firstName": 1, "jobseekerDetails.lastName": 1, "jobseekerDetails.email": 1, "jobseekerDetails.phoneNumber": 1, "jobseekerDetails.scores.resumeMatch.OverallScore": 1, "jobseekerDetails.snsScoreResult.resumeMatch.OverallScore": 1, "jobseekerDetails.copilotScore": 1, "jobseekerDetails.mymapitInterview.sectionDetails.sectionName": 1, "jobseekerDetails.mymapitInterview.sectionDetails.marksScored": 1, "jobseekerDetails.mymapitInterview.sectionDetails.totalMarks": 1, "jobseekerDetails.mymapitInterview.completedAt": 1}))
    recruiter_ids = {sid(a.get("recruiterId")) for a in attempts if a.get("recruiterId")}
    recruiter_ids.update(sid(u.get("recruiterId")) for u in uploads if u.get("recruiterId"))
    recruiters = list(db.recruiterProfile.find({"_id": {"$in": mongo_ids(list(recruiter_ids))}}, {"basic_details.firstName": 1, "basic_details.middleName": 1, "basic_details.lastName": 1, "additionalData.display_name": 1}))
    recruiter_users = list(db.users.find({"_id": {"$in": mongo_ids(list(recruiter_ids))}}, {"email": 1, "role": 1}))
    bookings = list(db.matchdaySlotBookings.find({}, {"userId": 1, "email": 1, "slotDate": 1, "slotTime": 1, "createdAt": 1}))
    return titles, members, attempts, users, profiles, uploads, recruiters, recruiter_users, bookings


def build_rows(data):
    titles, members, attempts, users, profiles, uploads, recruiters, recruiter_users, bookings = data
    user_map = {sid(u["_id"]): u for u in users}
    profile_map = {sid(p["_id"]): p for p in profiles}
    recruiter_map = {sid(r["_id"]): r for r in recruiters}
    recruiter_user_map = {sid(u["_id"]): u for u in recruiter_users}
    # Preserve contest-specific membership, even if the same candidate joins several contests.
    membership = {}
    for m in members:
        k = (sid(m.get("contestId")), sid(m.get("jobSeekerId")))
        if k[0] and k[1] and (k not in membership or timestamp(m.get("createdAt")) > timestamp(membership[k].get("createdAt"))):
            membership[k] = m
    latest = {}
    for a in attempts:
        k = (sid(a.get("contestId")), sid(a.get("jobseekerId")))
        if not k[0] or not k[1]:
            continue
        old = latest.get(k)
        if not old or timestamp(a.get("submittedAt") or a.get("startedAt")) >= timestamp(old.get("submittedAt") or old.get("startedAt")):
            latest[k] = a
    sources = {}
    for upload in uploads:
        cid = sid(upload.get("contestId"))
        for item in upload.get("jobseekerDetails", []):
            k = (cid, sid(item.get("jsId")))
            if k not in sources or timestamp(item.get("createdAt")) >= timestamp(sources[k][0].get("createdAt")):
                sources[k] = (item, sid(upload.get("recruiterId")))
    member_ids = {jid for _, jid in membership}
    member_emails = {normal_email(user_map.get(jid, {}).get("email") or (profile_map.get(jid, {}).get("personal_info") or {}).get("email")) for jid in member_ids}
    member_emails.discard("")
    # Bookings contain no contest ID. They are candidate-level and may appear for multiple contests.
    booking_map = {}
    for b in bookings:
        bid = sid(b.get("userId"))
        email = normal_email(b.get("email"))
        if bid not in member_ids and email not in member_emails:
            continue
        if bid:
            keys = [bid]
        else:
            keys = [jid for jid in member_ids if normal_email(user_map.get(jid, {}).get("email") or (profile_map.get(jid, {}).get("personal_info") or {}).get("email")) == email]
        for jid in keys:
            old = booking_map.get(jid)
            if old is None or timestamp(b.get("createdAt")) >= timestamp(old.get("createdAt")):
                booking_map[jid] = b
    rows = []
    for cid, jid in sorted(set(membership) | set(latest)):
        m = membership.get((cid, jid), {})
        a = latest.get((cid, jid), {})
        u = user_map.get(jid, {})
        p = profile_map.get(jid, {})
        info = p.get("personal_info") or {}
        upload, upload_rid = sources.get((cid, jid), ({}, ""))
        rid = upload_rid or sid(a.get("recruiterId"))
        r = recruiter_map.get(rid, {})
        details = r.get("basic_details") or {}
        recruiter_name = " ".join(str(details.get(k) or "").strip() for k in ("firstName", "middleName", "lastName")).strip() or (r.get("additionalData") or {}).get("display_name") or ""
        rec_email = recruiter_user_map.get(rid, {}).get("email") or details.get("email") or ""
        if not recruiter_name and rec_email:
            recruiter_name = rec_email.split("@")[0].replace(".", " ").title()
        completed = a.get("status") == "evaluated" and bool(a.get("submittedAt"))
        has_attempt = bool(a)
        booking = booking_map.get(jid) if (cid, jid) in membership else None
        if completed and booking:
            state = "🟢 MCQ + slot booked"
        elif completed:
            state = "🟠 MCQ completed only"
        elif booking:
            state = "🔵 Slot booked, MCQ pending"
        elif a.get("status") == "in_progress":
            state = "🟡 MCQ in progress"
        else:
            state = "⚪ Not completed"
        mapit = upload.get("mymapitInterview") or {}
        sections = mapit.get("sectionDetails") or []
        def section_score(kind):
            matching = [sec for sec in sections if isinstance(sec, dict) and kind in str(sec.get("sectionName") or "").casefold()]
            return matching[0].get("marksScored") if matching else None
        resume_score = (upload.get("scores") or {}).get("resumeMatch") or (upload.get("snsScoreResult") or {}).get("resumeMatch") or {}
        rows.append({
            "Contest": titles.get(cid, cid), "Contest ID": cid,
            "Name": name_from(p, u),
            "Email": u.get("email") or info.get("email") or "",
            "Phone Number": info.get("phoneNumber") or "",
            "Jobseeker Location": jobseeker_location(p),
            "Profile Source": upload.get("source") or u.get("source") or "",
            "Recruiter Name": recruiter_name,
            "Recruiter Email": rec_email,
            "MCQ Given?": "Yes" if has_attempt else "No",
            "MCQ Given For": titles.get(cid, cid) if has_attempt else "",
            "Status": state, "MCQ Status": a.get("status") or "Not started",
            "Score (%)": (a.get("result") or {}).get("percentageScore"),
            "MCQ Started (IST)": fmt_date(a.get("startedAt")),
            "Submitted (IST)": fmt_date(a.get("submittedAt")),
            "Application Status": m.get("applicationStatus") or "",
            "Slot Date": booking.get("slotDate", "") if booking else "",
            "Slot Time": booking.get("slotTime", "") if booking else "",
            "JD to CV Match Score": resume_score.get("OverallScore"),
            "Copilot Score": upload.get("copilotScore"),
            "My Mapit MCQ": section_score("mcq"),
            "My Mapit Coding": section_score("coding"),
            "My Mapit Attempted Date": fmt_date(mapit.get("completedAt")),
            "Jobseeker ID": jid,
        })
    return pd.DataFrame(rows)


st.title("Hiringhood · Post-assessment Statistics")
st.caption("Data Engineer Junior / Mid / Senior · read-only · 25-minute refresh")
st.info("JD–CV, Copilot and My Mapit scores come from contest-specific recruiter uploads. A blank cell means no matched value; 0 means a recorded zero.")
uri = os.getenv("MONGODB_URI", "")
if not uri:
    try:
        uri = st.secrets.get("MONGODB_URI", "")
    except Exception:
        uri = ""
if not uri:
    st.error("Set MONGODB_URI in private Streamlit secrets using a read-only MongoDB account.")
    st.stop()
if any(not ObjectId.is_valid(cid) for cid in CONTEST_IDS):
    st.error("Invalid contest ID configuration.")
    st.stop()
st_autorefresh(interval=REFRESH_MS, limit=None, key="assessment_refresh")
if st.button("Refresh data"):
    st.cache_data.clear()
    st.rerun()
try:
    data = load_data(get_client(uri), tuple(CONTEST_IDS))
    candidates = build_rows(data)
except Exception as exc:
    st.error("Unable to read assessment data; check MongoDB access and collection permissions.")
    st.caption(type(exc).__name__)
    st.stop()
if candidates.empty:
    st.warning("No candidates found in the configured contests.")
    st.stop()

# Empty values are intentional pending verified collection mappings; do not infer a score.
report = pd.DataFrame({
    "JS Name": candidates["Name"],
    "Contest Name": candidates["Contest"],
    "Recruiter Name": candidates["Recruiter Name"],
    "Email": candidates["Email"],
    "Phone Number": candidates["Phone Number"],
    "JD to CV Match Score": candidates["JD to CV Match Score"],
    "HH MCQ": candidates["Score (%)"],
    "Copilot Score": candidates["Copilot Score"],
    "My Mapit MCQ": candidates["My Mapit MCQ"],
    "My Mapit Coding": candidates["My Mapit Coding"],
    "My Mapit Attempted Date": candidates["My Mapit Attempted Date"],
})
contest_options = list(report["Contest Name"].dropna().unique())
selected = st.multiselect("Contests", contest_options, default=contest_options)
search = st.text_input("Search candidate, email, phone or recruiter")
view = report[report["Contest Name"].isin(selected)].copy()
if search:
    cols = ["JS Name", "Email", "Phone Number", "Recruiter Name"]
    view = view[view[cols].fillna("").astype(str).apply(lambda s: s.str.contains(search, case=False, regex=False)).any(axis=1)]
c1, c2, c3 = st.columns(3)
c1.metric("Contest candidate rows", len(view))
c2.metric("HH MCQ scored", int(view["HH MCQ"].notna().sum()))
c3.metric("Contests selected", len(selected))
st.dataframe(view, hide_index=True, use_container_width=True, height=520)
st.download_button("Export filtered CSV", view.to_csv(index=False).encode("utf-8-sig"), file_name="hh_assessment_stats.csv", mime="text/csv")
from io import BytesIO
buffer = BytesIO()
with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
    view.to_excel(writer, sheet_name="Assessment Stats", index=False)
st.download_button("Export filtered Excel", buffer.getvalue(), file_name="hh_assessment_stats.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
st.caption("One row per (contest ID, jobseeker ID). HH MCQ is latest recorded attempt per contest; blank score may indicate incomplete attempt. No external assessment values are fabricated.")
