# Django Documentation Generator

A Python tool to analyze Django project models and generate design documentation (ER diagrams, DFD, flowcharts) using AI.

## Features

- **Automatic Model Discovery**: Finds all Django models in your project
- **Relationship Analysis**: Maps ForeignKey, ManyToMany, and OneToOne relationships
- **AI-Powered Documentation**: Uses Google Gemini API to generate:
  - Entity-Relationship (ER) diagrams
  - Data Flow Diagrams (DFD)
  - Process Flowcharts
  - System documentation

## Installation

1. Copy the `django_doc_generator` folder to your Django project root
2. Install dependencies:
   ```bash
   pipenv install google-generativeai
   ```

3. Set your API key:
   ```bash
   export GEMINI_API_KEY="your-api-key-here"
   ```

## Usage

```bash
# From your Django project root
pipenv run python -m django_doc_generator --settings myproject.settings

# Or set environment variable
export DJANGO_SETTINGS_MODULE=myproject.settings
pipenv run python -m django_doc_generator

# Generate specific outputs
pipenv run python -m django_doc_generator --output-dir ./docs --format mermaid

# Use AST mode (no Django initialization required)
pipenv run python -m django_doc_generator --mode ast --project-dir .
```

## Output

Generated documentation will be saved to the `./docs/generated/` directory:
- `er_diagram.md` - Entity-Relationship diagram in Mermaid format
- `dfd.md` - Data Flow Diagram
- `flowcharts.md` - Process flowcharts
- `models_analysis.json` - Raw model analysis data

## Configuration

You can customize behavior via command-line arguments or environment variables:

| Argument | Env Variable | Description |
|----------|--------------|-------------|
| `--settings` | `DJANGO_SETTINGS_MODULE` | Django settings module path |
| `--output-dir` | `DOC_OUTPUT_DIR` | Output directory (default: `./docs/generated`) |
| `--format` | `DOC_FORMAT` | Output format: `mermaid`, `plantuml` |
| `--mode` | `DOC_MODE` | Discovery mode: `django`, `ast` |
| `--exclude` | - | Apps to exclude (comma-separated) |

## Requirements

- Python 3.9+
- Django 3.2+ (for django mode)
- google-generativeai
