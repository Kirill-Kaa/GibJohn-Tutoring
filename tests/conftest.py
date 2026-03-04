import os
import pytest
from jinja2 import DictLoader
from werkzeug.security import generate_password_hash

# Import your app objects
import app as app_module
from app import db, User, Course, Assessment, Question

@pytest.fixture(scope="session")
def app():
    """Create a Flask app configured for testing."""
    app = app_module.app
    app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,  # if you use Flask-WTF forms later
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        SECRET_KEY="test-secret",
        LOGIN_DISABLED=False,
    )

    # Inject minimal templates so render_template works without filesystem
    app.jinja_loader = DictLoader({
        "index.html": "INDEX",
        "about.html": "ABOUT",
        "resources.html": "RESOURCES",
        "courses.html": "COURSES",
        "assessments.html": "ASSESSMENTS for {{ course.name }}",
        "take_assessment.html": "TAKE ASSESSMENT",
        "result.html": "RESULT: {{ score }}/{{ total }} ({{ percentage }})",
        "register.html": "REGISTER",
        "login.html": "LOGIN",
        "dashboard.html": "DASHBOARD for {{ user.username }}",
        "people.html": "PEOPLE",
        "messages.html": "MESSAGES",
        "conversation.html": "CONVERSATION",
    })
    with app.app_context():
        db.create_all()
    yield app
    # No teardown here; handled in db fixture per test function


@pytest.fixture(autouse=True)
def _isolated_db(app):
    """Ensure a clean DB per test. Drops all after each test."""
    with app.app_context():
        db.drop_all()
        db.create_all()
        yield
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


# ---------- Helper factories ----------

@pytest.fixture
def make_user(app):
    def _make_user(username="user", email="user@test.com", password="123456", role="student", points=0):
        u = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            role=role,
            points=points
        )
        db.session.add(u)
        db.session.commit()
        return u
    return _make_user


@pytest.fixture
def login(client):
    def _login(email, password="123456"):
        return client.post("/login", data={"email": email, "password": password}, follow_redirects=True)
    return _login


@pytest.fixture
def create_assessment(app):
    """Creates a Course, Assessment, and N multiple-choice questions (A-D)."""
    def _create_assessment(
        course_name="Math",
        assessment_title="Algebra 1",
        points_reward=50,
        questions=None  # list of dicts {text, a,b,c,d,correct}
    ):
        course = Course(name=course_name)
        db.session.add(course)
        db.session.commit()

        assessment = Assessment(title=assessment_title, course_id=course.id, points_reward=points_reward)
        db.session.add(assessment)
        db.session.commit()

        if questions is None:
            questions = [
                {
                    "question_text": "1+1?",
                    "option_a": "1", "option_b": "2", "option_c": "3", "option_d": "4",
                    "correct_answer": "B"
                },
                {
                    "question_text": "2+2?",
                    "option_a": "1", "option_b": "2", "option_c": "3", "option_d": "4",
                    "correct_answer": "D"
                },
                {
                    "question_text": "3+3?",
                    "option_a": "6", "option_b": "5", "option_c": "7", "option_d": "9",
                    "correct_answer": "A"
                },
            ]

        for q in questions:
            db.session.add(Question(
                question_text=q["question_text"],
                option_a=q["option_a"],
                option_b=q["option_b"],
                option_c=q["option_c"],
                option_d=q["option_d"],
                correct_answer=q["correct_answer"],
                assessment_id=assessment.id
            ))

        db.session.commit()
        return course, assessment
    return _create_assessment