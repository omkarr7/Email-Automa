import argparse
import csv
import os
import re
from collections import defaultdict

from .config import ROOT, profile, settings
from .evidence_ai import classify
from .evidence_store import connect as connect_evidence_store
from .evidence_store import evidence_ids_for_urls, save_fact
from .gmail import resolve_resume_pdf_path, send_message
from .inbox_monitor import monitor as monitor_replies
from .matcher import score_job
from .nudge_runner import main as run_nudges
from .outreach_db import (
    already_contacted,
    connect,
    insert_prepared,
    mark_sent,
    prepared_rows,
)
from .renderer import render
from .research_ai import extract as extract_facts
from .truth import approve_facts
from .validators import validate_body, validate_contact


def read_csv(name):
    base_path = ROOT / "data" / name
    local_path = base_path.with_name(f"{base_path.stem}.local{base_path.suffix}")
    path = local_path if local_path.exists() else base_path
    with open(path, newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def read_evidence():
    path = ROOT / "data" / "discovered_evidence.csv"
    if not path.exists():
        return defaultdict(list)
    grouped = defaultdict(list)
    for row in read_csv("discovered_evidence.csv"):
        grouped[row["company"].lower()].append(row)
    return grouped


def read_jobs():
    path = ROOT / "data" / "jobs.csv"
    grouped = defaultdict(list)
    if not path.exists():
        return grouped
    for row in read_csv("jobs.csv"):
        grouped[row["company"].lower()].append(row)
    return grouped


def is_true(value):
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def is_placeholder(value):
    text = str(value or "").strip()
    lowered = text.lower()
    return (not text) or "replace_" in lowered or "example.com" in lowered or "{{" in text


def valid_public_url(url):
    return bool(url) and url.startswith(("http://", "https://")) and not is_placeholder(url)


def find_contact(contacts, company_name):
    for contact in contacts:
        if contact.get("company", "").lower() == company_name.lower():
            return contact
    return None


def manual_company_fact(company):
    note = company.get("current_signal") or company.get("domain")
    if not note:
        return []
    return [
        {
            "fact_type": "company_context",
            "fact_text": note,
            "value": company.get("company_url") or "",
            "status": "VERIFIED",
            "confidence": 1.0,
            "source_urls": [company.get("company_url")] if valid_public_url(company.get("company_url")) else [],
            "evidence_ids": [],
        }
    ]


def approved_facts_from_evidence(company, evidence):
    if not evidence:
        return []

    extracted = extract_facts(company, evidence)
    approved, _ = approve_facts(company, extracted, evidence)
    store = connect_evidence_store()
    materialized = []
    seen = set()

    for fact in approved:
        cloned = dict(fact)
        urls = [url for url in cloned.get("source_urls", []) if valid_public_url(url)]
        ids = evidence_ids_for_urls(store, company["company"], urls)
        cloned["evidence_ids"] = ids
        dedupe_key = (
            cloned.get("fact_type"),
            cloned.get("fact_text"),
            jsonish(cloned.get("value")),
            tuple(ids),
        )
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        save_fact(store, company["company"], cloned, ids)
        materialized.append(cloned)
    return materialized


def jsonish(value):
    return repr(value)


def manual_job_facts(job):
    title = job.get("job_title", "").strip()
    url = job.get("job_url", "").strip()
    if not title or not valid_public_url(url):
        return []
    vacancy = {
        "job_title": title,
        "job_url": url,
        "location": job.get("location", "").strip(),
        "description": job.get("description", "").strip(),
        "years_required": job.get("years_required", "0"),
    }
    return [
        {
            "fact_type": "current_vacancy",
            "fact_text": f"{title} is manually verified in jobs.csv",
            "value": vacancy,
            "status": "VERIFIED",
            "confidence": 1.0,
            "source_urls": [url],
            "evidence_ids": [],
        },
        {
            "fact_type": "current_vacancy_url",
            "fact_text": f"Verified vacancy URL for {title}",
            "value": url,
            "status": "VERIFIED",
            "confidence": 1.0,
            "source_urls": [url],
            "evidence_ids": [],
        },
    ]


def best_manual_job(company, jobs, candidate_profile):
    valid = [
        job for job in jobs
        if is_true(job.get("active")) and job.get("job_title") and valid_public_url(job.get("job_url"))
    ]
    if not valid:
        return None
    return max(valid, key=lambda job: score_job(job, candidate_profile, company))


def select_truth_backed_job(approved_facts):
    for fact in approved_facts:
        if fact.get("fact_type") == "current_vacancy" and isinstance(fact.get("value"), dict):
            value = dict(fact["value"])
            if value.get("job_title") and valid_public_url(value.get("job_url")):
                value.setdefault("years_required", "0")
                return value
    return None


def build_personalisation(company, candidate_profile, ai_result, approved_facts, job):
    reason = ai_result.get("company_reason") or company.get("current_signal") or f"your work in {company.get('domain', 'data and AI')}"
    relevant_area = ai_result.get("relevant_area") or company.get("domain") or "data and AI"
    candidate_fit = ai_result.get("candidate_fit")
    if not candidate_fit:
        skills = []
        for values in (candidate_profile.get("skills") or {}).values():
            skills.extend(str(value) for value in values[:2])
        candidate_fit = ", ".join(skills[:4]) or "data governance, analytics, Python and SQL"

    evidence_notes = ai_result.get("evidence_notes") or []
    evidence_urls = ai_result.get("evidence_urls") or []
    if not evidence_notes:
        for fact in approved_facts:
            text = fact.get("fact_text")
            if text:
                evidence_notes.append(text)
    if not evidence_urls:
        for fact in approved_facts:
            for url in fact.get("source_urls", []):
                if valid_public_url(url) and url not in evidence_urls:
                    evidence_urls.append(url)

    confidence = ai_result.get("confidence", 0)
    if approved_facts or job:
        confidence = max(confidence, 0.8)
    elif company.get("current_signal"):
        confidence = max(confidence, 0.75)

    return {
        "reason": reason,
        "relevant_area": relevant_area,
        "candidate_fit": candidate_fit,
        "confidence": confidence,
        "evidence_notes": evidence_notes,
        "evidence_urls": evidence_urls,
    }


def speculative_score(company, candidate_profile, personalisation):
    text = " ".join(
        [
            company.get("domain", ""),
            company.get("current_signal", ""),
            personalisation.get("reason", ""),
            personalisation.get("relevant_area", ""),
        ]
    ).lower()
    skills = set()
    for group in (candidate_profile.get("skills") or {}).values():
        skills.update(str(skill).lower() for skill in group)
    matched = [skill for skill in skills if skill and skill in text]
    city_match = 10 if company.get("city", "").lower() in {"bengaluru", "mumbai", "pune"} else 0
    return min(100, 35 + min(35, len(matched) * 6) + city_match)


def dedupe_facts(facts):
    out = []
    seen = set()
    for fact in facts:
        key = (fact.get("fact_type"), fact.get("fact_text"), jsonish(fact.get("value")))
        if key in seen:
            continue
        seen.add(key)
        out.append(fact)
    return out


def prepare():
    cfg = settings()
    candidate_profile = profile()
    companies = read_csv("companies.csv")
    contacts = read_csv("contacts.csv")
    evidence_by_company = read_evidence()
    jobs_by_company = read_jobs()
    conn = connect()
    outbox = ROOT / "outbox"
    outbox.mkdir(parents=True, exist_ok=True)
    prepared = 0

    for company in companies:
        contact = find_contact(contacts, company["company"])
        if not contact or not contact.get("email") or not is_true(contact.get("verified")):
            continue
        if already_contacted(conn, contact["email"]):
            continue

        evidence = evidence_by_company.get(company["company"].lower(), [])
        manual_job = best_manual_job(company, jobs_by_company.get(company["company"].lower(), []), candidate_profile)
        if not evidence and not manual_job:
            print("NO EVIDENCE", company["company"])
            continue

        approved = manual_company_fact(company)
        approved.extend(approved_facts_from_evidence(company, evidence))
        if manual_job:
            approved.extend(manual_job_facts(manual_job))
        approved = dedupe_facts(approved)

        ai_result = classify(company, evidence, candidate_profile) if evidence else {
            "company_reason": company.get("current_signal") or f"your work in {company.get('domain', 'data and AI')}",
            "candidate_fit": "",
            "relevant_area": company.get("domain", "data and AI"),
            "confidence": 0.8 if manual_job else 0.75,
            "evidence_notes": [],
            "evidence_urls": [],
            "safe_to_contact": bool(manual_job or company.get("current_signal")),
            "vacancy_status": "CURRENT" if manual_job else "UNKNOWN",
        }

        if not ai_result.get("safe_to_contact"):
            continue

        personalisation = build_personalisation(company, candidate_profile, ai_result, approved, manual_job)
        if personalisation["confidence"] < cfg["minimum_personalisation_confidence"]:
            continue

        job = manual_job or select_truth_backed_job(approved)
        score = score_job(job, candidate_profile, company) if job else speculative_score(company, candidate_profile, personalisation)
        if score < cfg["minimum_outreach_score"]:
            continue

        context = {
            "candidate": candidate_profile["candidate"],
            "company": company,
            "recipient_name": contact.get("contact_name") or "there",
            "job": job or {"job_title": "relevant opportunity", "description": "data and analytics"},
            "personalisation": personalisation,
        }
        template = "initial/vacancy_match.jinja" if job else "initial/no_vacancy.jinja"
        rendered = render(template, context)
        subject, body = rendered.split("\n", 1)
        subject = subject.replace("Subject:", "").strip()
        body = body.strip()

        errors = validate_contact(contact["email"]) + validate_body(body)
        if job and valid_public_url(job.get("job_url")) and job["job_url"] not in body:
            errors.append("Missing verified vacancy URL in email body")
        if errors:
            print("BLOCKED:", company["company"], errors)
            continue

        insert_prepared(
            conn,
            company=company["company"],
            contact_email=contact["email"],
            contact_name=contact.get("contact_name", ""),
            contact_designation=contact.get("contact_role", ""),
            job_title=(job or {}).get("job_title", ""),
            email_type="initial",
            subject=subject,
            body=body,
            outreach_score=score,
            personalisation_confidence=personalisation["confidence"],
            approved_facts=approved,
            evidence_ids=[item for fact in approved for item in fact.get("evidence_ids", [])],
            original_email={"subject": subject, "body": body},
        )
        prepared += 1

        note_lines = "\n".join("- " + note for note in personalisation["evidence_notes"]) or "- none"
        url_lines = "\n".join("- " + url for url in personalisation["evidence_urls"]) or "- none"
        path = outbox / f"{prepared:03d}_{re.sub(r'[^a-zA-Z0-9]+', '_', company['company'])}.txt"
        path.write_text(
            f"TO: {contact['email']}\n"
            f"SCORE: {score}\n"
            f"JOB URL: {(job or {}).get('job_url', '')}\n"
            f"EVIDENCE NOTES:\n{note_lines}\n"
            f"EVIDENCE URLS:\n{url_lines}\n"
            f"SUBJECT: {subject}\n\n{body}\n",
            encoding="utf-8",
        )
        print(f"PREPARED {company['company']} | score={score} | vacancy={'yes' if job else 'no'}")

    print(f"Prepared {prepared} emails. Nothing was sent.")


def send_prepared():
    if os.getenv("SEND_ENABLED", "false").lower() != "true":
        raise SystemExit("SEND_ENABLED is not true. Refusing to send.")

    cfg = settings()
    conn = connect()
    rows = prepared_rows(conn, email_type="initial")
    limit = int(os.getenv("DAILY_INITIAL_LIMIT", str(cfg["daily_initial_limit"])))
    nudge_after_days = int(os.getenv("NUDGE_AFTER_DAYS", str(cfg["followup_days"])))
    attachment_paths = []
    resume_path = resolve_resume_pdf_path()
    if resume_path:
        attachment_paths = [resume_path]
        print(f"Using resume attachment: {resume_path}")
    else:
        raise RuntimeError("No resume PDF found. Put it at data/resume.pdf or set RESUME_PDF_PATH.")

    for row in rows[:limit]:
        result = send_message(
            row["contact_email"],
            row["subject"],
            row["body"],
            attachment_paths=attachment_paths,
        )
        mark_sent(
            conn,
            row["id"],
            result.get("id"),
            thread_id=result.get("threadId"),
            nudge_after_days=nudge_after_days,
        )
        print("SENT", row["id"], row["contact_email"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=["init", "prepare", "send", "monitor", "nudge"],
        required=True,
    )
    args = parser.parse_args()

    if args.mode == "init":
        connect()
        print("Database initialised.")
    elif args.mode == "prepare":
        prepare()
    elif args.mode == "send":
        send_prepared()
    elif args.mode == "monitor":
        print(monitor_replies())
    else:
        run_nudges()


if __name__ == "__main__":
    main()
