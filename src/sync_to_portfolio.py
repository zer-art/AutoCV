import os
import json
import yaml

def sync():
    # Resolve paths relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    autocv_dir = os.path.dirname(script_dir)
    profile_path = os.path.join(autocv_dir, "data", "profile.yaml")
    resumes_path = os.path.join(autocv_dir, "data", "resumes.yaml")
    
    # Target data.json in portfolio-neo (try sibling first, then subdirectory)
    portfolio_dir = os.path.join(os.path.dirname(autocv_dir), "portfolio-neo")
    if not os.path.exists(portfolio_dir):
        portfolio_dir = os.path.join(autocv_dir, "portfolio-neo")
    
    portfolio_data_path = os.path.join(portfolio_dir, "src", "data.json")
    
    print(f"Reading profile data from {profile_path}...")
    if not os.path.exists(profile_path):
        print(f"Error: Profile file not found at {profile_path}")
        return
        
    with open(profile_path, "r", encoding="utf-8") as f:
        try:
            profile_data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            print(f"Error parsing profile.yaml: {e}")
            return
            
    print(f"Reading resumes configuration from {resumes_path}...")
    resumes_config = {"resumes": {}}
    if os.path.exists(resumes_path):
        with open(resumes_path, "r", encoding="utf-8") as f:
            try:
                resumes_config = yaml.safe_load(f) or {"resumes": {}}
            except yaml.YAMLError as e:
                print(f"Error parsing resumes.yaml: {e}")
                # Continue with empty resumes list if resumes.yaml has issues but profile.yaml is fine
                
    combined_data = {
        "profile": profile_data,
        "resumes": resumes_config.get("resumes", {})
    }
    
    print(f"Writing synced JSON data to {portfolio_data_path}...")
    os.makedirs(os.path.dirname(portfolio_data_path), exist_ok=True)
    with open(portfolio_data_path, "w", encoding="utf-8") as f:
        json.dump(combined_data, f, indent=2, ensure_ascii=False)
        
    print("Sync complete successfully!")

if __name__ == "__main__":
    sync()
