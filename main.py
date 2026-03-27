"""Backward-compatible entrypoint.

The project has been generalized beyond Django and now delegates to
doc_generator_ai.cli.
"""

from doc_generator_ai.cli import main

if __name__ == "__main__":
    main()
