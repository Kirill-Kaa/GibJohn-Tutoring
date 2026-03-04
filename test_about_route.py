import unittest
from app import app

class TestAboutRoute(unittest.TestCase):

    def setUp(self):
        # Create Flask test client
        self.client = app.test_client()

    def test_about_page(self):
        # Simulate browser visiting /about
        response = self.client.get("/about")

        # Check that the page loaded correctly
        self.assertEqual(response.status_code, 200)

        # Optional: check that template content is in the response
        # (only works if "about.html" contains the word "About")
        self.assertIn(b"About", response.data)

if __name__ == "__main__":
    unittest.main()