"""
Django Documentation Generator - Main Entry Point

Usage:
    pipenv run python -m django_doc_generator --settings myproject.settings
    pipenv run python -m django_doc_generator --mode ast --project-dir /path/to/project
"""

import argparse
import os
import sys
from pathlib import Path

from .config import Config, DiscoveryMode, OutputFormat, set_config
from .discovery.model_finder import discover_models
from .analyzers.project_analyzer import ProjectAnalyzer, analyze_project
from .generators.er_generator import generate_er_diagram
from .generators.dfd_generator import generate_dfd
from .generators.flowchart_generator import generate_flowcharts
from .generators.doc_generator import generate_documentation
from .outputs.exporters import GeneratedContent, export_content


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate documentation for Django projects using AI.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using Django's app registry (requires settings module)
  python -m django_doc_generator --settings myproject.settings

  # Using AST parsing (no Django required)
  python -m django_doc_generator --mode ast --project-dir .

  # Generate without AI (simple rule-based generation)
  python -m django_doc_generator --settings myproject.settings --no-ai

  # Specify output directory
  python -m django_doc_generator --settings myproject.settings --output-dir ./docs
        """,
    )
    
    # Discovery mode options
    discovery = parser.add_argument_group("Discovery Options")
    discovery.add_argument(
        "--mode",
        choices=["django", "ast"],
        default="django",
        help="Model discovery mode (default: django)",
    )
    discovery.add_argument(
        "--settings",
        metavar="MODULE",
        help="Django settings module (e.g., myproject.settings)",
    )
    discovery.add_argument(
        "--project-dir",
        metavar="PATH",
        default=".",
        help="Project directory for AST mode (default: current directory)",
    )
    
    # Output options
    output = parser.add_argument_group("Output Options")
    output.add_argument(
        "--output-dir",
        metavar="PATH",
        default="./docs/generated",
        help="Output directory for generated files (default: ./docs/generated)",
    )
    output.add_argument(
        "--format",
        choices=["mermaid", "plantuml"],
        default="mermaid",
        help="Diagram output format (default: mermaid)",
    )
    
    # AI options
    ai = parser.add_argument_group("AI Options")
    ai.add_argument(
        "--no-ai",
        action="store_true",
        help="Generate without AI (simple rule-based generation)",
    )
    ai.add_argument(
        "--ai-provider",
        choices=["gemini", "openai"],
        default="gemini",
        help="AI provider to use (default: gemini)",
    )
    ai.add_argument(
        "--ai-model",
        metavar="MODEL",
        help="AI model to use (default: gemini-2.0-flash for Gemini)",
    )
    
    # Filter options
    filters = parser.add_argument_group("Filter Options")
    filters.add_argument(
        "--exclude",
        metavar="APPS",
        help="Comma-separated list of apps to exclude",
    )
    filters.add_argument(
        "--include-builtins",
        action="store_true",
        help="Include Django's built-in models in analysis",
    )
    
    # Generation options
    gen = parser.add_argument_group("Generation Options")
    gen.add_argument(
        "--only",
        metavar="TYPE",
        help="Only generate specific types: er,dfd,flowchart,docs (comma-separated)",
    )
    gen.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output",
    )
    
    return parser.parse_args()


def create_config(args: argparse.Namespace) -> Config:
    """Create configuration from command line arguments."""
    config = Config(
        django_settings_module=args.settings,
        project_dir=args.project_dir,
        discovery_mode=DiscoveryMode(args.mode),
        output_dir=args.output_dir,
        output_format=OutputFormat(args.format),
        ai_provider=args.ai_provider,
        include_builtins=args.include_builtins,
    )
    
    if args.ai_model:
        config.ai_model = args.ai_model
    
    if args.exclude:
        config.exclude_apps.extend(args.exclude.split(","))
    
    return config


def print_banner():
    """Print application banner."""
    print("""
╔═══════════════════════════════════════════════════════════════╗
║           Django Documentation Generator v1.0.0               ║
║      Generate ER diagrams, DFD, and flowcharts using AI       ║
╚═══════════════════════════════════════════════════════════════╝
    """)


def main():
    """Main entry point."""
    args = parse_args()
    
    print_banner()
    
    # Create and validate configuration
    config = create_config(args)
    
    # Validate early if not using AI
    if not args.no_ai:
        errors = config.validate()
        if errors:
            print("Configuration errors:")
            for error in errors:
                print(f"  ❌ {error}")
            sys.exit(1)
    elif args.mode == "django" and not config.django_settings_module:
        print("❌ Django settings module is required for DJANGO mode.")
        print("   Use --settings or set DJANGO_SETTINGS_MODULE environment variable.")
        sys.exit(1)
    
    set_config(config)
    
    # Determine what to generate
    generate_types = {"er", "dfd", "flowchart", "docs"}
    if args.only:
        generate_types = set(args.only.split(","))
    
    use_ai = not args.no_ai
    
    print(f"📂 Discovery mode: {config.discovery_mode.value.upper()}")
    print(f"🤖 AI enabled: {'Yes' if use_ai else 'No (rule-based)'}")
    print(f"📁 Output directory: {config.output_dir}")
    print()
    
    # Discover models
    print("🔍 Discovering models...")
    try:
        models = discover_models(config)
    except Exception as e:
        print(f"❌ Failed to discover models: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)
    
    if not models:
        print("⚠️  No models found!")
        if config.discovery_mode == DiscoveryMode.DJANGO:
            print("   Make sure your Django settings module is correct.")
        else:
            print("   Make sure your project directory contains models.py files.")
        sys.exit(1)
    
    print(f"   Found {len(models)} models")
    if args.verbose:
        for model in models:
            print(f"      - {model.full_name} ({len(model.fields)} fields)")
    print()
    
    # Analyze project
    print("📊 Analyzing project structure...")
    analyzer = ProjectAnalyzer(models)
    analysis = analyze_project(models)
    
    print(f"   Apps: {len(analysis.apps)}")
    print(f"   Relationships: {analysis.total_relationships}")
    
    patterns = analyzer.detect_patterns()
    pattern_count = sum(len(v) for v in patterns.values())
    if pattern_count:
        print(f"   Patterns detected: {pattern_count}")
    print()
    
    # Generate content
    content = GeneratedContent(raw_analysis=analysis)
    
    if "er" in generate_types:
        print("📐 Generating ER diagram...")
        try:
            content.er_diagram = generate_er_diagram(analysis, use_ai=use_ai)
            print("   ✅ ER diagram generated")
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()
    
    if "dfd" in generate_types:
        print("📊 Generating Data Flow Diagram...")
        try:
            content.dfd = generate_dfd(analysis, analyzer, use_ai=use_ai)
            print("   ✅ DFD generated")
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()
    
    if "flowchart" in generate_types:
        print("📈 Generating flowcharts...")
        try:
            content.flowcharts = generate_flowcharts(analysis, analyzer, use_ai=use_ai)
            print("   ✅ Flowcharts generated")
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()
    
    if "docs" in generate_types:
        print("📝 Generating documentation...")
        try:
            content.documentation = generate_documentation(analysis, analyzer, use_ai=use_ai)
            print("   ✅ Documentation generated")
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()
    
    print()
    
    # Export content
    print("💾 Exporting files...")
    try:
        files = export_content(content, config)
        print(f"   Created {len(files)} files:")
        for f in files:
            print(f"      📄 {f}")
    except Exception as e:
        print(f"❌ Failed to export: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)
    
    print()
    print("✨ Done! Documentation generated successfully.")


if __name__ == "__main__":
    main()
