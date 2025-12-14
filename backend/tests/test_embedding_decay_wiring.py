import ast
import unittest
from pathlib import Path


class TestEmbeddingAggregationDecayWiring(unittest.TestCase):
    def test_weighted_embedding_mean_calls_pass_decay(self) -> None:
        """
        Regression test: Settings.embedding_aggregation_decay must be threaded into
        query/HyDE aggregation so env overrides are honored.

        This is a static (AST) test to avoid importing FastAPI app code in unit tests.
        """

        repo_root = Path(__file__).resolve().parents[2]
        main_py = repo_root / "backend" / "app" / "main.py"
        tree = ast.parse(main_py.read_text(encoding="utf-8"), filename=str(main_py))

        calls: list[ast.Call] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Name) and func.id == "_weighted_embedding_mean":
                calls.append(node)

        self.assertGreaterEqual(
            len(calls),
            2,
            "Expected at least two _weighted_embedding_mean calls (query + HyDE).",
        )

        for call in calls:
            decay_kw = next((kw for kw in call.keywords if kw.arg == "decay"), None)
            self.assertIsNotNone(decay_kw, "_weighted_embedding_mean must be called with decay=")
            self.assertIsInstance(
                decay_kw.value,
                ast.Name,
                "decay should be passed via a local variable to avoid duplicating settings access",
            )
            self.assertEqual(
                decay_kw.value.id,
                "aggregation_decay",
                "decay should come from Settings.embedding_aggregation_decay",
            )

