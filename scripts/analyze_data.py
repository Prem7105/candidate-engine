import json
import gzip
from collections import Counter
import time
from datetime import datetime
import os

def parse_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except:
        return None

def analyze(filepath):
    print(f"Analyzing {filepath}...")
    start_time = time.time()
    
    total = 0
    honeypot_flags = Counter()
    keyword_stuffers = 0
    
    # We will sample a bunch of stats to find exact thresholds
    exp_vs_durations = []
    
    opener = gzip.open if filepath.endswith('.gz') else open
    mode = "rt" if filepath.endswith('.gz') else "r"
    
    with opener(filepath, mode, encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            try:
                c = json.loads(line)
            except:
                continue
                
            total += 1
            if total % 20000 == 0:
                print(f"Processed {total}...")
                
            profile = c.get("profile", {})
            career = c.get("career_history", [])
            skills = c.get("skills", [])
            
            years_exp = profile.get("years_of_experience", 0)
            
            # 1. Experience mismatch
            career_months = sum(j.get("duration_months", 0) for j in career)
            career_years = career_months / 12.0
            if years_exp > 0 and career_years > 0:
                if years_exp / career_years > 2.0:
                    honeypot_flags['exp_mismatch_2x'] += 1
                if years_exp / career_years > 3.0:
                    honeypot_flags['exp_mismatch_3x'] += 1
                    
            # 2. Expert with 0 duration
            expert_zero = sum(1 for s in skills if s.get("proficiency") in ("expert", "advanced") and s.get("duration_months", 0) == 0)
            if expert_zero >= 3:
                honeypot_flags['expert_zero_3+'] += 1
            if expert_zero >= 5:
                honeypot_flags['expert_zero_5+'] += 1
            if expert_zero >= 10:
                honeypot_flags['expert_zero_10+'] += 1
                
            # 3. Keyword Stuffing: Marketing/Sales with many AI skills
            title = profile.get("current_title", "").lower()
            if any(t in title for t in ["marketing", "sales", "hr", "account", "operations"]):
                ai_skills = sum(1 for s in skills if s.get("name", "").lower() in ["python", "machine learning", "artificial intelligence", "deep learning", "nlp", "llm", "embeddings", "faiss"])
                if ai_skills >= 5:
                    keyword_stuffers += 1
                    
            # 4. Impossible dates
            for job in career:
                start = parse_date(job.get("start_date"))
                if start and start > datetime.today().date():
                    honeypot_flags['future_start_date'] += 1
                    
    print("\n--- Analysis Results ---")
    print(f"Total processed: {total}")
    print(f"Time: {time.time() - start_time:.1f}s")
    print(f"Honeypot heuristic hits:")
    for k, v in honeypot_flags.most_common():
        print(f"  {k}: {v}")
    print(f"Obvious keyword stuffers (non-tech with 5+ AI skills): {keyword_stuffers}")

if __name__ == "__main__":
    analyze(r"e:\Hackathon\[PUB] India_runs_data_and_ai_challenge\India_runs_data_and_ai_challenge\candidates.jsonl")
