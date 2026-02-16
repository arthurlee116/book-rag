import ast
import unittest
from pathlib import Path


class TestEmbeddingAggregationDecayWiring(unittest.TestCase):
    def test_weighted_embedding_mean_calls_pass_decay(self) -> None:
        """
        Regression test: Settings.embedding_aggregation_decay must be threaded into
        query/HyDE aggregation and fast-mode aggregation so env overrides are honored.

        This is a static (AST) test to avoid importing FastAPI app code in unit tests.
        """

        repo_root = Path(__file__).resolve().parents[2]
        chat_py = repo_root / "backend" / "app" / "chat_pipeline.py"
        tree = ast.parse(chat_py.read_text(encoding="utf-8"), filename=str(chat_py))

        decay_var_names: list[str] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Name) and func.id == "_weighted_embedding_mean":
                decay_kw = next((kw for kw in node.keywords if kw.arg == "decay"), None)
                self.assertIsNotNone(decay_kw, "_weighted_embedding_mean must be called with decay=")
                self.assertIsInstance(
                    decay_kw.value,
                    ast.Name,
                    "decay should be passed via a local variable to avoid duplicating settings access",
                )
                decay_var_names.append(decay_kw.value.id)

        self.assertGreaterEqual(
            len(decay_var_names),
            3,
            "Expected at least three _weighted_embedding_mean calls (fast + query + HyDE).",
        )
        self.assertIn(
            "fast_aggregation_decay",
            decay_var_names,
            "Fast-mode weighted aggregation must use fast_aggregation_decay.",
        )
        self.assertGreaterEqual(
            sum(1 for n in decay_var_names if n == "aggregation_decay"),
            2,
            "Normal query and HyDE aggregation must use aggregation_decay.",
        )
