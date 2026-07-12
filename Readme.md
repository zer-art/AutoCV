# AutoCV - Automated Resume Builder

An interactive CLI tool for creating tailored, professional resumes from a single source of truth. AutoCV allows you to maintain all your professional information in one place and generate customized resumes for different roles and applications.

## Features

- 📝 **Interactive Configuration** - Wizard-based interface to select resume content
- 🎯 **Tailored Resumes** - Create role-specific resumes from your master profile
- 🔄 **Reusable Configurations** - Save and reuse resume "recipes" for different positions
- 📊 **GitHub Integration** - Automatically pull open source contributions
- 🎨 **Professional PDF Output** - Clean, ATS-friendly resume formatting
- 📦 **Version Control Friendly** - All data stored in YAML files

## Prerequisites

- Python 3.13+
- [Pixi](https://pixi.sh/) package manager

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd AutoCV
```

2. Install dependencies using Pixi:
```bash
pixi install
```

## Project Structure

```
AutoCV/
├── data/
│   ├── profile.yaml      # Your master profile (projects, skills, experience)
│   ├── resumes.yaml      # Saved resume configurations
│   └── applied.yaml      # Track job applications (optional)
├── src/
│   ├── generate_cv.py    # Main resume generation script
│   └── github_integration.py  # GitHub API integration
├── public/               # Generated PDF resumes
└── pixi.toml            # Project dependencies
```

## Usage

### 1. Create a New Resume Configuration

Run the interactive wizard to create a tailored resume:

```bash
pixi run python src/generate_cv.py --new my_role_name
```

The wizard will guide you through:
- **Professional Summary**: Choose a preset or write a custom one
- **Projects**: Select specific projects from your profile
- **Open Source**: Toggle the section on/off and select contributions
- **Skills & Certifications**: Choose exactly what to include

This saves your "recipe" to `data/resumes.yaml` for future use.

### 2. Generate PDF Resume

Once you have a configuration, generate the PDF:

```bash
pixi run python src/generate_cv.py --resume my_role_name
```

This creates `public/my_role_name_resume.pdf`.

### 3. Update Existing Configuration

To modify an existing resume configuration:

```bash
pixi run python src/generate_cv.py --new my_role_name
```

The wizard will detect the existing configuration and let you update it.

## Configuration

### Setting Up Your Profile

Edit `data/profile.yaml` to include:
- Personal information (name, email, phone, location)
- Professional summary options
- Work experience
- Projects
- Skills (categorized)
- Certifications
- Education
- Open source contributions

### Resume Configurations

Each saved configuration in `data/resumes.yaml` contains:
- Selected professional summary
- Chosen projects
- Included skills and certifications
- Open source contribution preferences

## Examples

**Create a data science resume:**
```bash
pixi run python src/generate_cv.py --new data_scientist
# Follow prompts to select relevant projects and skills
pixi run python src/generate_cv.py --resume data_scientist
```

**Create a backend engineering resume:**
```bash
pixi run python src/generate_cv.py --new backend_engineer
pixi run python src/generate_cv.py --resume backend_engineer
```

## Development

### Dependencies

Key dependencies managed by Pixi:
- `reportlab` - PDF generation
- `weasyprint` - HTML to PDF conversion with CSS
- `PyYAML` - YAML file handling
- `PyGithub` - GitHub API integration
- `questionary` - Interactive CLI prompts
- `rich` - Beautiful terminal formatting

### Adding Features

The codebase is organized into:
- `generate_cv.py` - Main script with wizard and PDF generation logic
- `github_integration.py` - GitHub API integration for contributions

## Tips

- Keep your `profile.yaml` comprehensive - include all projects, skills, and experiences
- Create different resume configurations for different types of roles
- Update your profile regularly as you complete new projects
- Use descriptive names for configurations (e.g., `senior_data_engineer`, `ml_researcher`)
- Version control your `data/` folder to track resume evolution

## Troubleshooting

**PDF Generation Issues:**
- Ensure all dependencies are installed: `pixi install`
- Check that `public/` directory exists and is writable

**Configuration Not Found:**
- Verify the configuration name matches an entry in `data/resumes.yaml`
- Use `--new` to create a new configuration if needed

## License

[Add your license information here]

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Author

Pawan Parida
