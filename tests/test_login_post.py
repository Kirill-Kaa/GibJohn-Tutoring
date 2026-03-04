import unittest
import os, sys, uuid
from werkzeug.security import generate_password_hash
from app import app, db, User

class TestLoginPost(unittest.TestCase):

    def setUp(self):
        # Use the current app/database (this is your dev DB file)
        app.config["TESTING"] = True
        self.app = app
        self.client = app.test_client()

        # Generate a unique user each test run to avoid UNIQUE collisions
        self.suffix = uuid.uuid4().hex[:8]
        self.email = f"john_{self.suffix}@test.com"
        self.username = f"john_{self.suffix}"

        with self.app.app_context():
            # Make sure tables exist (won't drop anything)
            db.create_all()

            user = User(
                username=self.username,
                email=self.email,
                password_hash=generate_password_hash("123456")
            )
            db.session.add(user)
            db.session.commit()

    def test_login_correct_credentials(self):
        response = self.client.post(
            "/login",
            data={"email": self.email, "password": "123456"},
            follow_redirects=False
        )

        # Login should redirect to /dashboard
        self.assertEqual(response.status_code, 302)
        self.assertIn("/dashboard", response.headers.get("Location", ""))

    # NOTE: We don't drop tables here to avoid touching your dev DB.
    # If you switch to a test DB (Option 2), you can safely drop in tearDown.

if __name__ == "__main__":
    unittest.main()