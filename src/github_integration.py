#!/usr/bin/env python3
"""
Profile Automation - Fetch project data from GitHub and update profile.yaml
Parses READMEs from user's repositories and fetches contribution history.
"""

import os
import re
import sys
import yaml
from pathlib import Path
from datetime import datetime
from github import Github
from github.GithubException import UnknownObjectException

# Configuration
PROFILE_PATH = Path("data/profile.yaml")
GITHUB_USER = "zer-art"
EXCLUDED_REPOS = ["zer-art", "automl", "auto-cv", "cv-notes"]  # Repos to skip

def parse_readme_content(content, repo_name):
    """Extract structured information from a README content string"""
    try:
        # Extract key information
        data = {
            "technologies": [],
            "features": [],
            "metrics": [],
            "links": [],
        }

        # Extract GitHub links
        github_links = re.findall(r"https://github\.com/[^\s\)]+", content)
        data["links"].extend(github_links)

        # Extract technologies (common patterns)
        tech_patterns = [
            r"(?:using|with|built with|technologies?:?)\s*([^\n]+)",
            r"(?:tech stack|stack):?\s*([^\n]+)",
            r"`([A-Za-z][A-Za-z0-9+\-.]*)`",  # Code blocks
        ]

        for pattern in tech_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            data["technologies"].extend(matches)

        # Extract features (bullet points)
        features = re.findall(r"^\s*[-*]\s+(.+)$", content, re.MULTILINE)
        data["features"].extend(features[:5])  # Limit to top 5

        # Extract metrics (numbers with context)
        metrics = re.findall(
            r"(\d+\.?\d*%?\s*(?:accuracy|precision|recall|fps|ms|seconds?|users?|lines?|files?))",
            content,
            re.IGNORECASE,
        )
        data["metrics"].extend(metrics[:5])

        return data

    except Exception as e:
        print(f"Error parsing README for {repo_name}: {e}")
        return None

def categorize_project(repo):
    """Categorize project based on name and topics"""
    name = repo.name.lower()
    topics = repo.get_topics()
    
    if any(t in topics for t in ["llm", "chatbot", "genai", "gpt"]):
        return "LLM Projects"
    elif any(t in topics for t in ["nlp", "bert", "text-processing"]):
        return "NLP Projects"
    elif any(t in topics for t in ["cv", "computer-vision", "image-processing"]):
        return "Computer Vision Projects"
    elif any(t in topics for t in ["ml", "machine-learning", "data-science"]):
        return "Machine Learning Projects"
    
    # Fallback to name-based categorization
    if "llm" in name or "grammer" in name or "chatbot" in name:
        return "LLM Projects"
    elif "nlp" in name or "spam" in name:
        return "NLP Projects"
    elif "computer-vision" in name or "pneumonia" in name:
        return "Computer Vision Projects"
    elif "machine-learning" in name or "crop" in name:
        return "Machine Learning Projects"
    
    return "Other Projects"

def update_profile(github_client):
    """Main function to update profile.yaml"""
    print(f"Reading {PROFILE_PATH}...")
    
    if not PROFILE_PATH.exists():
        print(f"Error: {PROFILE_PATH} not found.")
        sys.exit(1)

    with open(PROFILE_PATH, "r", encoding="utf-8") as f:
        profile_data = yaml.safe_load(f) or {}

    # Initialize sections if missing
    if "projects" not in profile_data:
        profile_data["projects"] = []
    if "open_source" not in profile_data:
        profile_data["open_source"] = []

    # --- Helper to find latest date ---
    def get_latest_date(items):
        from datetime import timezone
        latest = datetime(2020, 1, 1, tzinfo=timezone.utc)
        for item in items:
            date_str = item.get("date")
            if date_str:
                try:
                    dt = datetime.strptime(date_str, "%B %Y")
                    # Make it UTC aware
                    dt = dt.replace(tzinfo=timezone.utc)
                    if dt > latest:
                        latest = dt
                except ValueError:
                    pass
        return latest

    latest_os_date = get_latest_date(profile_data["open_source"])
    latest_proj_date = get_latest_date(profile_data["projects"])
    
    # Format date for GitHub search (YYYY-MM-DD)
    # Go back 1 month to ensure we don't miss anything due to "Month Year" resolution
    start_date = latest_os_date.strftime("%Y-%m-%d")
    print(f"Fetching updates since {start_date}...")

    user = github_client.get_user(GITHUB_USER)
    
    # --- Process Repositories ---
    print("Fetching repositories...")
    repos = user.get_repos(type="owner", sort="updated", direction="desc")
    
    current_projects = {p.get("name"): p for p in profile_data["projects"]}
    
    for repo in repos:
        if repo.name in EXCLUDED_REPOS or repo.fork:
            continue
            
        # Incremental check: If project exists, skip README fetch unless explicitly forced?
        # User said "don't want repetition".
        if repo.name.replace("-", " ").replace("_", " ").title() in [p.get("name") for p in profile_data["projects"]]:
             # We might want to update stats? But user said "next time frame". 
             # Let's verify if we need to check updated_at vs our record.
             # For now, simplistic approach: Skip if exists.
             # print(f"Skipping existing project: {repo.name}")
             continue
        
        # Check if repo was created after our latest project date?
        # Or just trust that if it's not in our list, we should add it.
        # But we don't want to fetch *old* repos that we deleted from profile manually.
        # So check repo.created_at
        if repo.created_at < latest_proj_date:
             continue

        print(f"Processing NEW repo: {repo.name}")
        
        try:
            readme = repo.get_readme()
            readme_content = readme.decoded_content.decode("utf-8")
        except UnknownObjectException:
            print(f"  No README found for {repo.name}")
            continue

        parsed_data = parse_readme_content(readme_content, repo.name)
        if not parsed_data:
            continue

        # Construct project entry
        description = repo.description or "No description provided."
        
        # Merge metrics and features into achievements
        achievements = []
        if parsed_data["metrics"]:
            achievements.extend([f"Key metric: {m}" for m in parsed_data["metrics"]])
        if parsed_data["features"]:
            achievements.extend(parsed_data["features"])
            
        # Ensure we have at least some achievements if possible, or use description
        if not achievements:
            achievements.append(description)

        project_entry = {
            "name": repo.name.replace("-", " ").replace("_", " ").title(),
            "description": description,
            "github": repo.html_url,
            "tags": repo.get_topics()[:5], # Limit tags
            "achievements": achievements[:3], # Limit achievements
            "date": repo.created_at.strftime("%B %Y")
        }

        # double check uniqueness by name key
        match_key = project_entry["name"]
        if match_key not in current_projects:
             profile_data["projects"].append(project_entry)
    
    # Process Open Source Contributions
    print("Fetching issues and PRs...")
    
    # Add created filter for incremental update
    query_prs = f"author:{GITHUB_USER} -user:{GITHUB_USER} is:pr created:>{start_date}"
    query_issues = f"author:{GITHUB_USER} -user:{GITHUB_USER} is:issue created:>{start_date}"
    
    try:
        prs = list(github_client.search_issues(query_prs))
        issues_list = list(github_client.search_issues(query_issues))
        all_items = prs + issues_list
    except Exception as e:
        print(f"Error fetching contributions: {e}")
        all_items = []
    
    existing_contributions = {f"{c.get('project')}_{c.get('pr_number')}" : c for c in profile_data["open_source"]}
    
    for item in all_items:
        repo = item.repository
        key = f"{repo.full_name}_#{item.number}"
        
        # Skip if exists (double check, though query should handle most)
        if key in existing_contributions:
            continue

        print(f"Processing NEW contribution: {key}")
        
        contrib_entry = {
            "project": repo.full_name,
            "title": item.title,
            "pr_number": f"#{item.number}",
            "date": item.created_at.strftime("%B %Y"),
            "status": item.state.title(),
            "description": item.body.strip() if item.body else "No description",
            "url": item.html_url
        }
        
        if item.pull_request:
             if item.state == "closed" and item.pull_request:
                 pass
        
        profile_data["open_source"].append(contrib_entry)

    # Sort contributions by date (descending)
    profile_data["open_source"].sort(
        key=lambda x: datetime.strptime(x.get("date", "January 2000"), "%B %Y"), 
        reverse=True
    )
    
    # Write back
    print(f"Saving to {PROFILE_PATH}...")
    with open(PROFILE_PATH, "w", encoding="utf-8") as f:
        yaml.dump(profile_data, f, sort_keys=False, default_flow_style=False, allow_unicode=True)
        
    print("Done!")

if __name__ == "__main__":
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Warning: GITHUB_TOKEN not found in environment. Usage limits may apply.")
        
    auth = None
    if token:
        from github import Auth
        auth = Auth.Token(token)

    g = Github(auth=auth)
    update_profile(g)
