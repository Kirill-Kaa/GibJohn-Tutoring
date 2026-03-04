import re
from app import User

def test_register_and_login_flow(client):
    # Register
    resp = client.post("/register", data={
        "username": "alice",
        "email": "alice@test.com",
        "password": "secret"
    }, follow_redirects=True)
    assert resp.status_code == 200  # renders login after redirect

    # Verify user in DB
    u = User.query.filter_by(email="alice@test.com").first()
    assert u is not None
    assert u.check_password("secret") is True

    # Login
    resp = client.post("/login", data={"email": "alice@test.com", "password": "secret"}, follow_redirects=True)
    assert resp.status_code == 200
    assert b"DASHBOARD" in resp.data  # landed on dashboard


def test_login_fails_with_bad_credentials(client, make_user):
    make_user(username="bob", email="bob@test.com", password="correct")
    resp = client.post("/login", data={"email": "bob@test.com", "password": "wrong"}, follow_redirects=True)
    # stays on login page (flash message would be set, we won't assert exact text)
    assert b"LOGIN" in resp.data


def test_login_required_redirects_to_login(client):
    # Not logged-in user tries to access protected routes
    for url in ["/dashboard", "/people", "/messages", "/logout", "/assessment/1", "/conversation/1", "/start-conversation/1"]:
        resp = client.get(url)
        # Flask-Login uses 302 redirect to login by default
        assert resp.status_code in (302, 401)
        # Optionally verify redirect target contains "login"
        if resp.status_code == 302:
            assert "/login" in resp.headers.get("Location", "")