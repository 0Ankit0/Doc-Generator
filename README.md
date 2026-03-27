# AI Doc Generator (General-Purpose)

A package-first, AI-powered documentation generator for **any software project** (not only Django).

It works in four steps:
1. Scan your file/folder structure.
2. Extract lightweight source symbols (classes/functions from Python files).
3. Analyze architecture hints by directory/file patterns.
4. Generate selected design docs (DFD, sequence diagram, flowcharts, architecture docs, component design, deployment notes, and more).

## What changed from the old Django-specific version?

- ✅ Repositioned as a **general doc generator** for any repository.
- ✅ First-class **project structure discovery** (files + folders as the primary source).
- ✅ Added **selectable system design output** with `--system-design-docs`.
- ✅ Added **sequence diagram generation**.
- ✅ Packaged with `pyproject.toml` and CLI script so it can be installed and used anywhere.

## Installation

```bash
pip install .
```

Optional provider extras:

```bash
pip install .[gemini]
pip install .[openai]
```

## Usage

### Run directly as a module

```bash
python -m doc_generator_ai --project-dir . --output-dir ./docs/generated
```

### Run via installed console command

```bash
doc-generator-ai --project-dir . --output-dir ./docs/generated
```

### Select what to generate (new)

```bash
doc-generator-ai \
  --project-dir . \
  --system-design-docs overview,architecture,components,deployment,dfd,sequence,flowchart,requirements
```

### Add user requirements to steer output

```bash
doc-generator-ai \
  --project-dir . \
  --include-patterns "*.py,*.md,src/*" \
  --requirements "Focus on auth flows, API boundaries, and async jobs."
```

### No-AI mode (template-based fallback)

```bash
doc-generator-ai --project-dir . --no-ai
```

## Output files

In `--output-dir` you get:

- `project_structure.json`
- `system_analysis.json`
- `overview.md` (if selected)
- `architecture.md` (if selected)
- `dfd.md` (if selected)
- `sequence.md` (if selected)
- `flowchart.md` (if selected)
- `requirements.md` (if selected)
- `components.md` (if selected)
- `deployment.md` (if selected)
- `index.md`

## Environment variables

- `GEMINI_API_KEY` (when using `--ai-provider gemini`)
- `OPENAI_API_KEY` (when using `--ai-provider openai`)

## Notes

- The generator intentionally starts with repository structure to support mixed stacks and non-framework-specific projects.
- You can refine outputs by adding detailed `--requirements` text and selecting only the needed doc types.
