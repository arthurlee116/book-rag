import os
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

from backend.app.config import Settings, load_settings


@contextmanager
def _isolated_env():
    old = os.environ.copy()
    try:
        # Remove values that could affect tested defaults.
        for key in list(os.environ.keys()):
            if key.startswith("ERR_") or key.startswith("OPENROUTER_") or key == "ENV_FILE":
                os.environ.pop(key, None)
        # Point to a definitely missing env file.
        os.environ["ENV_FILE"] = "/__nonexistent__/book-rag/.env"
        yield
    finally:
        os.environ.clear()
        os.environ.update(old)


class TestConfigDefaultsConsistency(unittest.TestCase):
    def test_settings_and_loader_defaults_match_for_core_tunables(self) -> None:
        with _isolated_env():
            with tempfile.TemporaryDirectory() as td:
                old_cwd = Path.cwd()
                try:
                    os.chdir(td)
                    loaded = load_settings()
                finally:
                    os.chdir(old_cwd)

        static_defaults = Settings()
        self.assertEqual(loaded.chunk_target_tokens, static_defaults.chunk_target_tokens)
        self.assertEqual(loaded.chunk_overlap_tokens, static_defaults.chunk_overlap_tokens)
        self.assertEqual(loaded.chat_model, static_defaults.chat_model)
        self.assertEqual(loaded.chat_model_simple, static_defaults.chat_model_simple)
        self.assertEqual(loaded.chat_model_complex, static_defaults.chat_model_complex)
        self.assertEqual(loaded.drift_sim_threshold, static_defaults.drift_sim_threshold)
        self.assertEqual(
            loaded.hyde_drift_sim_threshold,
            static_defaults.hyde_drift_sim_threshold,
        )
        self.assertEqual(loaded.retrieval_parallelism, static_defaults.retrieval_parallelism)
        self.assertEqual(loaded.context_include_neighbors, static_defaults.context_include_neighbors)
        self.assertEqual(loaded.fast_mode_include_neighbors, static_defaults.fast_mode_include_neighbors)
        self.assertEqual(loaded.chat_history_max_turns, static_defaults.chat_history_max_turns)
        self.assertEqual(loaded.chat_history_max_chars, static_defaults.chat_history_max_chars)
        self.assertEqual(loaded.answer_repeat_guard_enabled, static_defaults.answer_repeat_guard_enabled)
        self.assertEqual(
            loaded.answer_repeat_answer_similarity_min,
            static_defaults.answer_repeat_answer_similarity_min,
        )
        self.assertEqual(
            loaded.answer_repeat_query_similarity_max,
            static_defaults.answer_repeat_query_similarity_max,
        )


if __name__ == "__main__":
    unittest.main()
