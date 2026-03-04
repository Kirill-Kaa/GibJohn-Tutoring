import unittest
from app import app

class TestHomeRoute(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()

    def test_home_page(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        # Check for something that is ACTUALLY in the page
        self.assertIn(b"Home", response.data)

if __name__ == "__main__":
    unittest.main()