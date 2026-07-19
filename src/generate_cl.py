import os
import sys
import yaml
import argparse
import markdown
import questionary
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from weasyprint import HTML, CSS
from pathlib import Path

console = Console()

def load_yaml(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        try:
            return yaml.safe_load(f) or {}
        except yaml.YAMLError as exc:
            console.print(f"[bold red]Error parsing YAML {path}:[/bold red] {exc}")
            sys.exit(1)

def save_yaml(path, data):
    with open(path, "w") as f:
        yaml.dump(data, f, sort_keys=False)

def interactive_wizard(profile_data, templates_data, configs_path, default_name=None):
    console.print(Panel.fit("Interactive Cover Letter Builder", style="bold blue"))

    config_name = default_name
    if not config_name:
        config_name = questionary.text(
            "Name for this cover letter configuration (e.g., 'gs_operations'):"
        ).ask()
        if not config_name:
            console.print("[red]Operation cancelled.[/red]")
            sys.exit(1)

    templates = templates_data.get("templates", {})
    if not templates:
        console.print("[red]No templates found in data/cover_letters_templates.yaml. Please add some first.[/red]")
        sys.exit(1)
    
    template_choices = list(templates.keys())
    selected_template = questionary.select(
        "Select a Cover Letter Template:", choices=template_choices
    ).ask()

    default_date = datetime.now().strftime("%B %d, %Y")
    date_val = questionary.text(f"Date (default: {default_date}):").ask()
    if not date_val:
        date_val = default_date
        
    company = questionary.text("Company Name:").ask()
    company_location = questionary.text("Company Location (optional):").ask()
    
    hm = questionary.text("Hiring Manager Name (leave blank if unknown):").ask()
    if not hm.strip():
        hm = "Hiring Manager"

    new_config = {
        "template": selected_template,
        "date": date_val,
        "company": company,
        "company_location": company_location,
        "hiring_manager": hm
    }

    current_config = load_yaml(configs_path)
    if "cover_letters" not in current_config:
        current_config["cover_letters"] = {}
    current_config["cover_letters"][config_name] = new_config
    save_yaml(configs_path, current_config)

    console.print(f"[green]Configuration '{config_name}' saved to data/cover_letters.yaml![/green]")
    return config_name

def generate_markdown(profile, templates_data, config):
    template_name = config.get("template", "default")
    templates = templates_data.get("templates", {})
    template_text = templates.get(template_name, templates.get("default", ""))

    if not template_text:
        return "Template not found."

    mapping = {
        "name": profile.get("name", "Your Name"),
        "email": profile.get("email", "email@example.com"),
        "phone": profile.get("phone", ""),
        "location": profile.get("location", ""),
        "linkedin": profile.get("linkedin", ""),
        "date": config.get("date", ""),
        "company": config.get("company", ""),
        "company_location": config.get("company_location", ""),
        "hiring_manager": config.get("hiring_manager", "Hiring Manager"),
    }
    
    # Simple substitution
    for key, value in mapping.items():
        template_text = template_text.replace(f"{{{key}}}", str(value))
        
    return template_text

def convert_to_pdf(markdown_input, output_filename):
    with open(markdown_input, "r", encoding="utf-8") as f:
        markdown_text = f.read()

    # Use nl2br to preserve single newlines for address blocks and letter spacing
    html_body = markdown.markdown(markdown_text, extensions=["extra", "smarty", "nl2br"])

    css_style = """
    @page { margin: 2.0cm; size: A4; }
    body { 
        font-family: 'Helvetica', 'Arial', sans-serif; 
        font-size: 10.5pt; 
        line-height: 1.35; 
        color: #333; 
    }
    p { 
        margin-bottom: 1em; 
        text-align: justify;
    }
    strong {
        font-weight: bold;
    }
    """
    html_content = f"<!DOCTYPE html><html><head><meta charset='utf-8'></head><body>{html_body}</body></html>"
    HTML(string=html_content).write_pdf(output_filename, stylesheets=[CSS(string=css_style)])

def main():
    parser = argparse.ArgumentParser(description="Generate Cover Letter")
    parser.add_argument("--new", help="Start interactive builder to create a new cover letter config")
    parser.add_argument("--cl", help="Name of the cover letter config to use")
    parser.add_argument("--output", help="Output PDF filename")
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent.parent
    data_dir = base_dir / "data"
    public_dir = base_dir / "public" / "cover_letters"
    src_dir = base_dir / "src"

    profile_path = data_dir / "profile.yaml"
    templates_path = data_dir / "cover_letters_templates.yaml"
    configs_path = data_dir / "cover_letters.yaml"
    temp_md_path = src_dir / "temp_cl.md"

    public_dir.mkdir(parents=True, exist_ok=True)

    if not profile_path.exists():
        console.print("[red]profile.yaml not found.[/red]")
        sys.exit(1)
        
    profile_data = load_yaml(profile_path)
    templates_data = load_yaml(templates_path)

    config_name = "default"
    config = None

    if args.new:
        config_name = interactive_wizard(profile_data, templates_data, configs_path, args.new)
        all_configs = load_yaml(configs_path)
        config = all_configs.get("cover_letters", {}).get(config_name)
    elif args.cl:
        config_name = args.cl
        all_configs = load_yaml(configs_path)
        config = all_configs.get("cover_letters", {}).get(config_name)
        if not config:
            console.print(f"[bold red]Error:[/bold red] Cover letter config '{config_name}' not found.")
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)

    console.print(f"[blue]Generating Cover Letter using config: {config_name}[/blue]")
    
    md_content = generate_markdown(profile_data, templates_data, config)
    with open(temp_md_path, "w") as f:
        f.write(md_content)

    if args.output:
        output_name = args.output
        if not output_name.endswith(".pdf"):
            output_name += ".pdf"
    else:
        output_name = f"{config_name}_cl.pdf"

    output_path = public_dir / output_name
    console.print(f"Generating PDF at {output_path}...")
    try:
        convert_to_pdf(temp_md_path, output_path)
        console.print(f"[bold green]✅ Success! Cover Letter PDF saved to: {output_path}[/bold green]")
    except Exception as e:
        console.print(f"[bold red]❌ Error generating PDF:[/bold red] {e}")

if __name__ == "__main__":
    main()
