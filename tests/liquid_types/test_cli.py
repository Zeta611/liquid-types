import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class CliTests(unittest.TestCase):
    def run_file(self, source: str, mode: str = "check") -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "example.lq"
            path.write_text(source, encoding="utf-8")
            return subprocess.run(
                [sys.executable, "-m", "liquid_types", mode, str(path)],
                capture_output=True,
                text=True,
            )

    def test_valid_program(self):
        result = self.run_file("""
            (let inc = (x) => { let one = 1; x + one }
                : x:int => int[v | v = x + 1];
            let n = 41; inc(n)) : int[v | v = 42]
        """)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.endswith("example.lq: type checks\n"))
        self.assertEqual(result.stderr, "")

    def test_failed_refinement(self):
        result = self.run_file("1 : int[v | v > 1]")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("Refinement constraint is not valid", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_syntax_error(self):
        result = self.run_file("let x = ; x")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("line 1", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_mismatched_signature_names(self):
        result = self.run_file("val f : int; let g = 1; g")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Signature for 'f'", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.lq"
            result = subprocess.run(
                [sys.executable, "-m", "liquid_types", "check", str(path)],
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 1)
        self.assertIn(str(path), result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_run_prints_result(self):
        result = self.run_file(
            "(let x = 40; let y = 2; x + y) : int[v | v = 42]", "run"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "42\n")
        self.assertEqual(result.stderr, "")

    def test_run_rejects_invalid_contract_before_evaluating(self):
        result = self.run_file("1 : int[v | v > 1]", "run")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("Refinement constraint is not valid", result.stderr)

    def test_run_function_result(self):
        result = self.run_file("(x) => { x } : int => int", "run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "<function>\n")
