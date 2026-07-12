import json
from datetime import date, datetime
from pathlib import Path
import yaml

def _load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def _to_json_compatible(value):
    if isinstance(value, dict):
        return {str(key): _to_json_compatible(inner) for key, inner in value.items()}
    if isinstance(value, list):
        return [_to_json_compatible(item) for item in value]
    if isinstance(value, tuple):
        return [_to_json_compatible(item) for item in value]
    if isinstance(value, set):
        return sorted(_to_json_compatible(item) for item in value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    return value


def _resolve_paths():
    script_dir = Path(__file__).resolve().parent
    autocv_dir = script_dir.parent
    profile_path = autocv_dir / "data" / "profile.yaml"
    resumes_path = autocv_dir / "data" / "resumes.yaml"

    sibling_portfolio_dir = autocv_dir.parent / "portfolio-neo"
    nested_portfolio_dir = autocv_dir / "portfolio-neo"
    portfolio_dir = sibling_portfolio_dir if sibling_portfolio_dir.exists() else nested_portfolio_dir

    return profile_path, resumes_path, portfolio_dir / "src" / "data.json"


def sync():
    profile_path, resumes_path, portfolio_data_path = _resolve_paths()

    print(f"Reading profile data from {profile_path}...")
    if not profile_path.exists():
        print(f"Error: Profile file not found at {profile_path}")
        return 1

    try:
        profile_data = _load_yaml(profile_path)
    except yaml.YAMLError as error:
        print(f"Error parsing profile.yaml: {error}")
        return 1

    if profile_data is None:
        profile_data = {}

    print(f"Reading resumes configuration from {resumes_path}...")
    resumes_config = {"resumes": {}}
    if resumes_path.exists():
        try:
            resumes_config = _load_yaml(resumes_path) or {"resumes": {}}
        except yaml.YAMLError as error:
            print(f"Error parsing resumes.yaml: {error}")

    if not isinstance(resumes_config, dict):
        print("Error: resumes.yaml must contain a mapping at the top level.")
        return 1

    combined_data = _to_json_compatible(
        {"profile": profile_data, "resumes": resumes_config.get("resumes", {})}
    )

    print(f"Writing synced JSON data to {portfolio_data_path}...")
    portfolio_data_path.parent.mkdir(parents=True, exist_ok=True)

    with portfolio_data_path.open("w", encoding="utf-8") as file:
        json.dump(combined_data, file, indent=2, ensure_ascii=False)

    with portfolio_data_path.open("r", encoding="utf-8") as file:
        json.load(file)

    print("Sync complete successfully!")
    return 0

if __name__ == "__main__":
    raise SystemExit(sync())
