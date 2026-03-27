import tempfile
import unittest
from pathlib import Path

from doc_generator_ai.config import Config
from doc_generator_ai.discovery.project_structure import ProjectStructureScanner
from doc_generator_ai.analyzers.system_analyzer import SystemAnalyzer
from doc_generator_ai.generators.design_generator import DesignGenerator


class GeneralGeneratorTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        (root / "api").mkdir(parents=True)
        (root / "services").mkdir(parents=True)
        (root / "api" / "views.py").write_text("class UserView: ...\n", encoding="utf-8")
        (root / "services" / "worker.py").write_text("def run_job():\n    return True\n", encoding="utf-8")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_scan_and_analyze(self):
        config = Config(project_dir=self.temp_dir.name)
        structure = ProjectStructureScanner(config).scan()
        self.assertGreaterEqual(len(structure.files), 2)
        self.assertTrue(any(f.path.endswith("views.py") for f in structure.files))

        analysis = SystemAnalyzer().analyze(structure)
        self.assertGreaterEqual(analysis.python_symbol_count, 2)
        self.assertIn(".py", analysis.file_types)

    def test_no_ai_generation_all_supported(self):
        config = Config(project_dir=self.temp_dir.name)
        structure = ProjectStructureScanner(config).scan()
        analysis = SystemAnalyzer().analyze(structure)
        generator = DesignGenerator(config)

        for doc_type in config.docs_to_generate:
            content = generator.generate_simple(doc_type, structure, analysis, "test requirements")
            self.assertTrue(content.strip())


if __name__ == "__main__":
    unittest.main()
