"""CLI entrypoint for the general AI documentation generator."""

from __future__ import annotations

import argparse
import sys

from .config import Config, SUPPORTED_DOC_TYPES
from .discovery.project_structure import ProjectStructureScanner
from .analyzers.system_analyzer import SystemAnalyzer
from .generators.design_generator import DesignGenerator
from .outputs.exporter import export_documents


DEFAULT_DOCS = [
    "overview",
    "architecture",
    "components",
    "deployment",
    "dfd",
    "sequence",
    "flowchart",
    "requirements",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="General AI documentation generator for any codebase.",
    )
    parser.add_argument("--project-dir", default=".", help="Target project path")
    parser.add_argument("--output-dir", default="./docs/generated", help="Where docs will be written")
    parser.add_argument("--ai-provider", choices=["gemini", "openai"], default="gemini")
    parser.add_argument("--ai-model", default="gemini-2.0-flash")
    parser.add_argument("--no-ai", action="store_true", help="Use deterministic templates")
    parser.add_argument(
        "--system-design-docs",
        default=",".join(DEFAULT_DOCS),
        help=(
            "Comma-separated docs to generate: "
            + ",".join(sorted(SUPPORTED_DOC_TYPES))
        ),
    )
    parser.add_argument(
        "--requirements",
        default="",
        help="Extra user requirements to steer generated docs",
    )
    parser.add_argument(
        "--include-patterns",
        default="",
        help="Optional comma-separated glob patterns to include (e.g. '*.py,services/*').",
    )
    parser.add_argument("--max-files", type=int, default=1500)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    docs_to_generate = [d.strip() for d in args.system_design_docs.split(",") if d.strip()]

    config = Config(
        project_dir=args.project_dir,
        output_dir=args.output_dir,
        ai_provider=args.ai_provider,
        ai_model=args.ai_model,
        max_files=args.max_files,
        docs_to_generate=docs_to_generate,
        include_patterns=[p.strip() for p in args.include_patterns.split(",") if p.strip()],
    )

    errors = config.validate(use_ai=not args.no_ai)
    if errors:
        for error in errors:
            print(f"❌ {error}")
        sys.exit(1)

    print("🔎 Step 1/4: Scanning file and folder structure...")
    structure = ProjectStructureScanner(config).scan()

    print("🧠 Step 2/4: Analyzing architecture hints...")
    analysis = SystemAnalyzer().analyze(structure)

    print("📝 Step 3/4: Generating selected documentation...")
    generator = DesignGenerator(config)
    docs: dict[str, str] = {}
    for doc_type in config.docs_to_generate:
        if args.no_ai:
            docs[doc_type] = generator.generate_simple(doc_type, structure, analysis, args.requirements)
        else:
            docs[doc_type] = generator.generate(doc_type, structure, analysis, args.requirements)
        print(f"   ✅ {doc_type}")

    print("💾 Step 4/4: Exporting outputs...")
    created = export_documents(
        output_dir=config.output_dir,
        docs=docs,
        structure=structure.to_dict(),
        analysis=analysis.to_dict(),
    )

    print(f"✨ Done. Created {len(created)} files in {config.output_dir}")


if __name__ == "__main__":
    main()
