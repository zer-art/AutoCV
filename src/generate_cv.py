import os
import re
import sys
import yaml
import argparse
import markdown
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from weasyprint import HTML, CSS
from pathlib import Path

console = Console()



def format_metrics(text):
    """Bolds metrics in the text (e.g., 95%, <100ms, 50+)."""
    if not text:
        return text
    
    # Patterns to match metrics
    patterns = [
        r"(\d+(?:\.\d+)?%)",  # Percentages (95%, 98.4%)
        r"((?:[<~]\s*)?\d+(?:\.\d+)?\s*(?:seconds?|ms|s|FPS|minutes?|hours?/week|query permutations))", # Time/Rates/Units (seconds? before s, no leading space captured)
        r"(NDCG@\d+)",  # Specific metrics
        r"(\d+\+\s+(?:sources|categories|samples))"  # Counts with context (50+ sources)
    ]
    
    for p in patterns:
        text = re.sub(p, r"**\1**", text, flags=re.IGNORECASE)
    
    # Clean up double bolding (e.g., ****text**** or duplicate asterisks)
    text = re.sub(r"\*\*+", "**", text)
    
    return text

def load_profile(profile_path):
    if not os.path.exists(profile_path):
        console.print(
            f"[bold red]Error:[/bold red] Profile file not found at {profile_path}"
        )
        sys.exit(1)
    with open(profile_path, "r") as f:
        try:
            return yaml.safe_load(f)
        except yaml.YAMLError as exc:
            console.print(f"[bold red]Error parsing YAML:[/bold red] {exc}")
            sys.exit(1)


def load_resumes_config(path):
    if not os.path.exists(path):
        return {"resumes": {}}
    with open(path, "r") as f:
        return yaml.safe_load(f) or {"resumes": {}}


def save_resumes_config(path, data):
    with open(path, "w") as f:
        yaml.dump(data, f, sort_keys=False)


def interactive_wizard(profile_data, resumes_config_path, default_name=None):
    console.print(Panel.fit("Interactive Resume Builder", style="bold blue"))

    if default_name:
        config_name = default_name
        console.print(f"Creating configuration: [bold green]{config_name}[/bold green]")
    else:
        config_name = questionary.text(
            "Name for this resume configuration (e.g., 'data_scientist', 'google_cv'):"
        ).ask()
        if not config_name:
            console.print("[red]Operation cancelled.[/red]")
            sys.exit(1)

    # 1. Summary Selection
    summary_choices = ["Use Default Summary"]
    if "custom_summaries" in profile_data:
        summary_choices.extend(
            [f"Pre-set: {k}" for k in profile_data["custom_summaries"].keys()]
        )
    summary_choices.append("Write Custom Summary (One-off)")

    summary_selection = questionary.select(
        "Select Professional Summary:", choices=summary_choices
    ).ask()

    selected_summary_key = None
    custom_summary_text = None

    if summary_selection.startswith("Pre-set"):
        selected_summary_key = summary_selection.split(": ")[1]
    elif "Write Custom" in summary_selection:
        custom_summary_text = questionary.text("Enter your custom summary:").ask()

    # 2. Projects Selection
    projects = profile_data.get("projects", [])
    project_choices = [p.get("name", "Unnamed") for p in projects]
    selected_project_names = questionary.checkbox(
        "Select Projects to Include:", choices=project_choices
    ).ask()

    # Determine versions for selected projects
    selected_projects = {}
    for p in projects:
        if p.get("name") in selected_project_names:
            versions = p.get("versions", {})
            if versions:
                choices = ["default"] + list(versions.keys())
                version = questionary.select(
                    f"Select version for project '{p.get('name')}':", choices=choices
                ).ask()
                selected_projects[p.get("name")] = version
            else:
                selected_projects[p.get("name")] = "default"

    # 3. Open Source Selection
    include_os = questionary.confirm("Include Open Source Contributions section?").ask()
    selected_os_contributions = []
    if include_os:
        os_data = profile_data.get("open_source", [])
        # Create descriptive labels
        os_choices = []
        for os_item in os_data:
            label = f"{os_item.get('project')} - {os_item.get('title')}"
            os_choices.append(questionary.Choice(title=label, value=os_item))

        selected_os_items = questionary.checkbox(
            "Select Open Source Contributions:", choices=os_choices
        ).ask()
        # We store just the titles or some identifier to map back, but for simplicity in config let's store titles/project keys
        # Or better yet, store the 'title' + 'project' to uniquely identify or just the full object in runtime?
        # For YAML config, we should store identifiers. Let's store 'title'.
        selected_os_contributions = [item.get("title") for item in selected_os_items]

    # 4. Skills Selection
    all_skills = []
    if "skills" in profile_data:
        for cat, skills in profile_data["skills"].items():
            all_skills.extend(skills)

    selected_skills = questionary.checkbox(
        "Select Skills to Include:", choices=sorted(list(set(all_skills)))
    ).ask()

    # 5. Certifications Selection
    certs = profile_data.get("certifications", [])
    cert_choices = [c.get("name") for c in certs]
    selected_certs = questionary.checkbox(
        "Select Certifications to Include:", choices=cert_choices
    ).ask()

    # Construct Config
    new_config = {
        "summary_type": (
            "custom"
            if custom_summary_text
            else ("preset" if selected_summary_key else "default")
        ),
        "summary_key": selected_summary_key,
        "custom_summary_text": custom_summary_text,
        "projects": selected_projects,
        "open_source_enabled": include_os,
        "open_source": selected_os_contributions,
        "skills": selected_skills,
        "certifications": selected_certs,
    }

    # Save
    current_config = load_resumes_config(resumes_config_path)
    current_config["resumes"][config_name] = new_config
    save_resumes_config(resumes_config_path, current_config)

    console.print(
        f"[green]Configuration '{config_name}' saved to data/resumes.yaml![/green]"
    )
    return config_name


def profile_to_markdown(data, config):
    """Converts profile dictionary to Markdown string using the provided configuration."""
    md = []

    # Header (Always included)
    md.append(f"# {data.get('name', 'Name')}")
    contact = []
    if data.get("email"):
        contact.append(f"**Email:** {data.get('email')}")
    if data.get("phone"):
        contact.append(f"**Phone:** {data.get('phone')}")
    if data.get("location"):
        contact.append(f"**Location:** {data.get('location')}")
    if data.get("linkedin"):
        contact.append(
            f"**LinkedIn:** [{data.get('linkedin')}](https://{data.get('linkedin')})"
        )
        contact.append(
            f"**GitHub:** [{data.get('github')}](https://{data.get('github')})"
        )
    if data.get("website"):
        contact.append(
            f"**Portfolio:** [{data.get('website')}](https://{data.get('website')})"
        )
    md.append(" | ".join(contact))
    md.append("")

    # Summary
    summary_text = data.get("summary", "")
    if config:
        if config.get("summary_type") == "custom" and config.get("custom_summary_text"):
            summary_text = config.get("custom_summary_text")
        elif config.get("summary_type") == "preset" and config.get("summary_key"):
            summary_text = data.get("custom_summaries", {}).get(
                config.get("summary_key"), summary_text
            )

    if summary_text:
        md.append("## Professional Summary")
        md.append(summary_text.strip())
        md.append("")

    # Education (Always included if present)
    if data.get("education"):
        md.append("## Education")
        for edu in data["education"]:
            # Single line format as requested
            header_line = f"### {edu.get('degree', 'Degree')} - {edu.get('institution', 'Institution')} | {edu.get('duration', 'Date')} | {edu.get('location', '')}"
            md.append(header_line)

            if edu.get("cgpa"):
                md.append(f"- **CGPA:** {edu.get('cgpa')}")
            if edu.get("coursework"):
                md.append(f"- **Coursework:** {', '.join(edu['coursework'])}")
            if edu.get("achievements"):
                md.append("- **Achievements:**")
                md.append('<div class="education-achievements" markdown="1">')
                md.append("")
                for ach in edu["achievements"]:
                    md.append(f"- {ach}")
                md.append("")
                md.append("</div>")
            md.append("")

    # Skills
    # If config has specific skills, use those. Else use all.
    skills_to_show = config.get("skills") if config else None

    if data.get("skills"):
        md.append("## Skills")
        md.append('<div class="skills-columns" markdown="1">')
        md.append("")  # Ensure separation for markdown parsing
        # If we have a flat list of selected skills
        if skills_to_show is not None:
            for category, items in data["skills"].items():
                # Filter items in this category that are in the selected list
                filtered_items = [item for item in items if item in skills_to_show]
                if filtered_items:
                    cat_name = category.replace("_", " ")
                    md.append(f"- **{cat_name}:** {', '.join(filtered_items)}")
        else:
            # Show all
            for category, items in data["skills"].items():
                cat_name = category.replace("_", " ")
                md.append(f"- **{cat_name}:** {', '.join(items)}")

        md.append("")
        md.append("</div>")
        md.append("")

    # Experience (Always included)
    if data.get("experience"):
        md.append("## Experience")
        for exp in data["experience"]:
            # Single line format: Role - Company | Date | Location
            header = f"### {exp.get('position', 'Role')} - {exp.get('organization', 'Company')} | {exp.get('duration', 'Date')} | {exp.get('location', '')}"

            # Check for generic url or github
            url = (
                exp.get("url")
                or exp.get("link")
                or exp.get("github")
                or exp.get("website")
            )
            if url:
                header += f" [[Certificate]]({url})"

            md.append(header)

            if exp.get("achievements"):
                for ach in exp["achievements"]:
                    md.append(f"- {ach}")
            md.append("")

    # Projects
    project_config = config.get("projects") if config else None
    if data.get("projects"):
        # Filter
        projects = data["projects"]
        if project_config is not None:
            if isinstance(project_config, list):
                projects = [p for p in projects if p.get("name") in project_config]
            else:
                projects = [p for p in projects if p.get("name") in project_config]

        if projects:
            md.append("## Projects")
            for proj in projects:
                version = "default"
                if project_config and isinstance(project_config, dict):
                    version = project_config.get(proj.get("name"), "default")
                
                display_proj = proj.copy()
                if version != "default" and "versions" in proj and version in proj["versions"]:
                    display_proj.update(proj["versions"][version])

                title = display_proj.get("name", "Project")
                details = []
                if display_proj.get("date"):
                    details.append(display_proj.get("date"))
                if display_proj.get("association"):
                    details.append(display_proj.get("association"))

                header = f"### {title}"
                if details:
                    header += f" | {' | '.join(details)}"

                # Check for github and url
                if display_proj.get("github"):
                    header += f" [[Github]]({display_proj.get('github')})"
                if display_proj.get("url"):
                    header += f" [[Live]]({display_proj.get('url')})"

                md.append(header)

                if display_proj.get("description"):
                    md.append(format_metrics(display_proj.get("description").strip()))
                if display_proj.get("achievements"):
                    md.append("")
                    for ach in display_proj["achievements"]:
                        md.append(f"- {format_metrics(ach)}")
                if display_proj.get("tags"):
                    # Ensure separation
                    md.append("")
                    md.append(f"**Tech Stack:** {', '.join(display_proj['tags'])}")
                md.append("")

    # Open Source
    os_enabled = config.get("open_source_enabled", True) if config else True
    os_titles = config.get("open_source") if config else None

    if os_enabled and data.get("open_source"):
        # Filter
        os_data = data["open_source"]
        if os_titles is not None:
            os_data = [item for item in os_data if item.get("title") in os_titles]

        if os_data:
            md.append("## Open Source Contributions")
            for os_contrib in os_data:
                title = f"{os_contrib.get('project')} {os_contrib.get('pr_number', '')}"

                details = []
                if os_contrib.get("date"):
                    details.append(os_contrib.get("date"))
                if os_contrib.get("status"):
                    details.append(os_contrib.get("status"))

                header = f"### {title}"
                if details:
                    header += f" | {' | '.join(details)}"

                link_text = ""
                if os_contrib.get("url"):
                    header += f" [[Github]]({os_contrib.get('url')})"

                md.append(header)
                md.append(os_contrib.get("description", ""))
                if os_contrib.get("achievements"):
                    md.append("")
                    for ach in os_contrib["achievements"]:
                        md.append(f"- {ach}")
                md.append("")

    # Certifications
    cert_names = config.get("certifications") if config else None
    if data.get("certifications"):
        certs = data["certifications"]
        if cert_names is not None:
            certs = [c for c in certs if c.get("name") in cert_names]

        if certs:
            md.append("## Certifications")
            md.append('<div class="certifications-columns" markdown="1">')
            md.append("")
            for cert in certs:
                link_text = ""
                if cert.get("credential_url"):
                    link_text = f" [[Certificate]]({cert.get('credential_url')})"

                line = f"- **{cert.get('name')}** - {cert.get('issuer')} ({cert.get('date')}){link_text}"
                md.append(line)
            md.append("")
            md.append("</div>")
            md.append("")

    # Languages (Spoken) - Added at user request
    if data.get("languages"):
        md.append("## Languages")
        langs = [
            f"{lang.get('language')} ({lang.get('proficiency')})"
            for lang in data["languages"]
        ]
        md.append(", ".join(langs))
        md.append("")

    return "\n".join(md)


def convert_to_pdf(markdown_input, output_filename, css_path=None):
    with open(markdown_input, "r", encoding="utf-8") as f:
        markdown_text = f.read()

    html_body = markdown.markdown(markdown_text, extensions=["extra", "smarty"])

    default_css = """
    @page { margin: 0.45cm 0.55cm; size: A4; }
    body { 
        font-family: 'Helvetica', 'Arial', sans-serif; 
        font-size: 8.8pt; 
        line-height: 1.18; 
        color: #333; 
        margin: 0;
        padding: 0;
    }
    h1 { 
        text-align: center; 
        text-transform: uppercase; 
        color: #2c3e50; 
        border-bottom: 1.5px solid #2c3e50; 
        padding-bottom: 2.5px; 
        margin-bottom: 6px; 
        margin-top: 0;
        font-size: 13.5pt; 
        letter-spacing: 0.5px;
    }
    h2 { 
        color: #2c3e50; 
        border-bottom: 1px solid #ddd; 
        padding-bottom: 2px; 
        margin-top: 7px; 
        margin-bottom: 3.5px; 
        font-size: 10.8pt; 
        text-transform: uppercase; 
        letter-spacing: 0.3px;
        break-after: avoid;
        page-break-after: avoid;
    }
    h3 { 
        color: #34495e; 
        margin-top: 5px; 
        margin-bottom: 1.2px; 
        font-size: 9.8pt; 
        font-weight: bold; 
        line-height: 1.18;
        break-after: avoid;
        page-break-after: avoid;
    }
    p { 
        margin-top: 1px;
        margin-bottom: 1.8px; 
        text-align: justify;
    }
    ul { 
        margin-top: 1px; 
        padding-left: 18px; 
        margin-bottom: 1.8px; 
    }
    li { 
        margin-bottom: 0.3px; 
        line-height: 1.22;
        break-inside: avoid;
        page-break-inside: avoid;
    }
    strong { 
        color: #000; 
        font-weight: 600;
    }
    a { 
        color: #2980b9; 
        text-decoration: none; 
        font-size: 0.95em;
    }
    .skills-columns { 
        column-count: 2; 
        column-gap: 30px; 
        margin-bottom: 4px;
        break-inside: avoid;
        page-break-inside: avoid;
    }
    .skills-columns ul {
        margin: 0;
        padding: 0;
    }
    .education-achievements { 
        column-count: 2; 
        column-gap: 20px; 
        margin-top: 2px;
        margin-bottom: 2px;
        break-inside: avoid;
        page-break-inside: avoid;
    }
    .education-achievements ul {
        margin: 0;
        padding-left: 15px;
    }
    .certifications-columns { 
        column-count: 2; 
        column-gap: 20px; 
        margin-top: 2px;
        margin-bottom: 2px;
        break-inside: avoid;
        page-break-inside: avoid;
    }
    .certifications-columns ul {
        margin: 0;
        padding-left: 15px;
    }
    @media print {
        .skills-columns { column-count: 2; }
        .education-achievements { column-count: 2; }
        .certifications-columns { column-count: 2; }
        body { font-size: 8.8pt; }
    }
    """

    css_to_use = default_css
    if css_path and os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            css_to_use = f.read()

    html_content = f"<!DOCTYPE html><html><head><meta charset='utf-8'></head><body>{html_body}</body></html>"
    HTML(string=html_content).write_pdf(
        output_filename, stylesheets=[CSS(string=css_to_use)]
    )


def main():
    parser = argparse.ArgumentParser(description="Generate CV from profile.yaml")
    parser.add_argument(
        "--new", help="Start interactive builder to create a new resume config"
    )
    parser.add_argument(
        "--resume", help="Name of the resume config to use (from data/resumes.yaml)"
    )
    parser.add_argument("--output", help="Output PDF filename")
    args = parser.parse_args()

    # Paths
    base_dir = Path(__file__).resolve().parent.parent
    data_dir = base_dir / "data"
    public_dir = base_dir / "public" / "resumes"
    src_dir = base_dir / "src"

    profile_path = data_dir / "profile.yaml"
    resumes_path = data_dir / "resumes.yaml"
    resume_md_path = src_dir / "temp_resume.md"
    jd_path = src_dir / "temp_jd.md"

    public_dir.mkdir(parents=True, exist_ok=True)

    profile_data = load_profile(profile_path)

    # Mode selection
    config = None
    config_name = "default"

    if args.new:
        config_name = interactive_wizard(
            profile_data, resumes_path, default_name=args.new
        )
        # Load the newly created config
        all_configs = load_resumes_config(resumes_path)
        config = all_configs["resumes"][config_name]
    elif args.resume:
        config_name = args.resume
        all_configs = load_resumes_config(resumes_path)
        if config_name not in all_configs.get("resumes", {}):
            console.print(
                f"[bold red]Error:[/bold red] Resume config '{config_name}' not found in data/resumes.yaml"
            )
            console.print(
                "Available configs:", ", ".join(all_configs.get("resumes", {}).keys())
            )
            sys.exit(1)
        config = all_configs["resumes"][config_name]
    else:
        # Check if user wants to use interactive mode implied or just default dump
        # For now, let's guide them if no args are passed or just dump everything?
        # Let's simple dump everything if no specific config is asked, matching old behavior but without role filter
        pass

    console.print(f"[blue]Generating resume using config: {config_name}[/blue]")

    # Generate Markdown
    md_content = profile_to_markdown(profile_data, config)
    with open(resume_md_path, "w") as f:
        f.write(md_content)

    # Output PDF
    if args.output:
        output_name = args.output
        if not output_name.endswith(".pdf"):
            output_name += ".pdf"
    else:
        output_name = f"{config_name}_resume.pdf"

    output_path = public_dir / output_name

    console.print(f"Generating PDF at {output_path}...")
    try:
        convert_to_pdf(resume_md_path, output_path)
        console.print(
            f"[bold green]✅ Success! PDF saved to: {output_path}[/bold green]"
        )
    except Exception as e:
        console.print(f"[bold red]❌ Error generating PDF:[/bold red] {e}")


if __name__ == "__main__":
    main()
