import importlib
import sys
import unittest


class TestRetrievalInitImportLight(unittest.TestCase):
    def test_importing_retrieval_does_not_import_hybrid_retriever(self) -> None:
        # Ensure a clean slate for this module under test.
        sys.modules.pop("backend.app.retrieval", None)
        sys.modules.pop("backend.app.retrieval.hybrid_retriever", None)

        importlib.import_module("backend.app.retrieval")

        self.assertNotIn(
            "backend.app.retrieval.hybrid_retriever",
            sys.modules,
            msg="`backend.app.retrieval` should remain import-light and not import "
            "`hybrid_retriever` implicitly.",
        )

