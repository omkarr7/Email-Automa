from src.matcher import score_job

def test_data_engineer_matches():
    profile = {
        "skills": {
            "data": ["Python", "SQL", "ETL", "data pipelines"],
            "ml": ["machine learning"]
        }
    }
    company = {"domain": "Data Infrastructure", "current_signal": "actively hiring"}
    job = {
        "job_title": "Data Engineer",
        "description": "Python SQL ETL data pipelines",
        "years_required": "1",
        "location": "Bengaluru"
    }
    assert score_job(job, profile, company) >= 60
