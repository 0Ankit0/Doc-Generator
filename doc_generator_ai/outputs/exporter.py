"""Output export helpers."""

from pathlib import Path
import json


def export_documents(output_dir: str, docs: dict[str, str], structure: dict, analysis: dict) -> list[str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    created: list[str] = []

    structure_path = out / "project_structure.json"
    structure_path.write_text(json.dumps(structure, indent=2), encoding="utf-8")
    created.append(str(structure_path))

    analysis_path = out / "system_analysis.json"
    analysis_path.write_text(json.dumps(analysis, indent=2), encoding="utf-8")
    created.append(str(analysis_path))

    for doc_type, content in docs.items():
        path = out / f"{doc_type}.md"
        path.write_text(content.strip() + "\n", encoding="utf-8")
        created.append(str(path))

    index = out / "index.md"
    lines = ["# Generated Documentation", "", "## Files", ""]
    for p in created:
        name = Path(p).name
        lines.append(f"- [{name}](./{name})")
    index.write_text("\n".join(lines) + "\n", encoding="utf-8")
    created.insert(0, str(index))

    return created
