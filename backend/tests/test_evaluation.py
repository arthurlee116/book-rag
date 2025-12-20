import unittest
from fastapi.testclient import TestClient
from backend.app.main import app

class TestEvaluationEndpoint(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_evaluation_no_record_returns_404(self):
        # Create a new session ID that has no chat history/evaluation
        session_id = "test-no-eval-session"

        # Call /evaluation - should 404 since no evaluation
        response = self.client.get(
            "/evaluation",
            headers={"X-Session-Id": session_id},
        )

        self.assertEqual(response.status_code, 404)
        self.assertIn("No evaluation record", response.json()["detail"])

if __name__ == "__main__":
    unittest.main()
