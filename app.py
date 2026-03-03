from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

import json, csv, sqlite3
import click
from contextlib import contextmanager

import os
from openai import OpenAI

client = OpenAI(api_key="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")

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'your_secret_key'

# def get_db():
#     db = app.config.get("DATABASE", "Gibdb.db")
#     conn = sqlite3.connect(db, check_same_thread=False)
#     conn.row_factory = sqlite3.Row
#     return conn


def load_questions_from_json():
    with open("questions.json", "r") as file:
        data = json.load(file)

    for course_name, assessments in data.items():

        # Check if course already exists
        course = Course.query.filter_by(name=course_name).first()
        if not course:
            course = Course(name=course_name)
            db.session.add(course)
            db.session.commit()

        for assessment_title, questions in assessments.items():

            # Check if assessment already exists
            assessment = Assessment.query.filter_by(
                title=assessment_title,
                course_id=course.id
            ).first()

            if not assessment:
                assessment = Assessment(
                    title=assessment_title,
                    course_id=course.id
                )
                db.session.add(assessment)
                db.session.commit()

            for q in questions:

                # Check if question already exists
                existing_question = Question.query.filter_by(
                    question_text=q["question_text"],
                    assessment_id=assessment.id
                ).first()

                if not existing_question:
                    question = Question(
                        question_text=q["question_text"],
                        option_a=q["option_a"],
                        option_b=q["option_b"],
                        option_c=q["option_c"],
                        option_d=q["option_d"],
                        correct_answer=q["correct_answer"],
                        assessment_id=assessment.id
                    )

                    db.session.add(question)

            db.session.commit()


db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    points = db.Column(db.Integer, default=0)
    role = db.Column(db.String(20), default="student")  
    # values: "student" or "tutor"

    results = db.relationship('Result', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

    assessments = db.relationship('Assessment', backref='course', lazy=True)

class Assessment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    points_reward = db.Column(db.Integer, default=50)

    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)

    questions = db.relationship('Question', backref='assessment', lazy=True)

class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    tutor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    messages = db.relationship('Message', backref='conversation', lazy=True)

    student = db.relationship('User', foreign_keys=[student_id])
    tutor = db.relationship('User', foreign_keys=[tutor_id])


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    sender = db.relationship('User', backref='sent_messages')


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_text = db.Column(db.Text, nullable=False)

    option_a = db.Column(db.String(200))
    option_b = db.Column(db.String(200))
    option_c = db.Column(db.String(200))
    option_d = db.Column(db.String(200))

    correct_answer = db.Column(db.String(1))  # A, B, C, or D

    assessment_id = db.Column(db.Integer, db.ForeignKey('assessment.id'), nullable=False)

class Result(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    score = db.Column(db.Integer)
    total_questions = db.Column(db.Integer)
    percentage = db.Column(db.Float)

    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    assessment_id = db.Column(db.Integer, db.ForeignKey('assessment.id'))

    assessment = db.relationship("Assessment")


@app.route("/courses")
def courses():
    all_courses = Course.query.all()
    return render_template("courses.html", courses=all_courses)

@app.route("/course/<int:course_id>")
def course_detail(course_id):
    course = Course.query.get_or_404(course_id)
    return render_template("assessments.html", course=course)

@app.route("/assessment/<int:assessment_id>", methods=["GET", "POST"])
@login_required
def take_assessment(assessment_id):
    assessment = Assessment.query.get_or_404(assessment_id)
    questions = assessment.questions

    if request.method == "POST":
        score = 0

        for question in questions:
            selected = request.form.get(f"question_{question.id}")
            if selected == question.correct_answer:
                score += 1

        if len(questions) > 0:
            percentage = (score / len(questions)) * 100
        else:
            percentage = 0

        result = Result(
            score=score,
            total_questions=len(questions),
            percentage=percentage,
            user_id=current_user.id,
            assessment_id=assessment.id
        )

        db.session.add(result)

        # Give points only if passed
        if percentage >= 70:
            current_user.points += assessment.points_reward

        db.session.commit()

        return render_template("result.html",
                               score=score,
                               total=len(questions),
                               percentage=percentage)

    return render_template("take_assessment.html",
                           assessment=assessment,
                           questions=questions)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        hashed_password = generate_password_hash(password)

        new_user = User(
            username=username,
            email=email,
            password_hash=hashed_password
        )

        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful! Please login.")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    user_results = Result.query.filter_by(
        user_id=current_user.id
    ).order_by(Result.timestamp.desc()).all()

    return render_template("dashboard.html",
                           user=current_user,
                           results=user_results)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/resources")
def resources():
    return render_template("resources.html")

@app.route("/people")
@login_required
def people():
    query = request.args.get("q")

    if query:
        users = User.query.filter(
            User.username.ilike(f"%{query}%"),
            User.id != current_user.id
        ).all()
    else:
        users = User.query.filter(User.id != current_user.id).all()

    return render_template("people.html", users=users)

@app.route("/messages")
@login_required
def messages():

    if current_user.role == "student":
        conversations = Conversation.query.filter_by(
            student_id=current_user.id
        ).all()
    else:
        conversations = Conversation.query.filter_by(
            tutor_id=current_user.id
        ).all()

    return render_template("messages.html", conversations=conversations)

@app.route("/conversation/<int:conversation_id>", methods=["GET", "POST"])
@login_required
def conversation(conversation_id):
    conversation = Conversation.query.get_or_404(conversation_id)

    if request.method == "POST":
        content = request.form["content"]

        message = Message(
            conversation_id=conversation.id,
            sender_id=current_user.id,
            content=content
        )

        db.session.add(message)
        db.session.commit()

        return redirect(url_for("conversation", conversation_id=conversation.id))

    return render_template("conversation.html", conversation=conversation)

@app.route("/start-conversation/<int:user_id>")
@login_required
def start_conversation(user_id):

    other_user = User.query.get_or_404(user_id)

    # Check if conversation already exists (both directions)
    existing = Conversation.query.filter(
        ((Conversation.student_id == current_user.id) & 
         (Conversation.tutor_id == other_user.id)) |
        ((Conversation.student_id == other_user.id) & 
         (Conversation.tutor_id == current_user.id))
    ).first()

    if existing:
        return redirect(url_for("conversation", conversation_id=existing.id))

    # Create new conversation
    conversation = Conversation(
        student_id=current_user.id,
        tutor_id=other_user.id
    )

    db.session.add(conversation)
    db.session.commit()

    return redirect(url_for("conversation", conversation_id=conversation.id))

def seed_users():
    # Check if users already exist
    if User.query.count() > 1:
        return "Users already seeded."

    users = [
        # Tutors
        User(
            username="tutor_math",
            email="math@school.com",
            password_hash=generate_password_hash("123456"),
            role="tutor",
            points=0
        ),
        User(
            username="tutor_english",
            email="english@school.com",
            password_hash=generate_password_hash("123456"),
            role="tutor",
            points=0
        ),

        # Students
        User(
            username="student_anna",
            email="anna@school.com",
            password_hash=generate_password_hash("123456"),
            role="student",
            points=0
        ),
        User(
            username="student_john",
            email="john@school.com",
            password_hash=generate_password_hash("123456"),
            role="student",
            points=0
        ),
    ]

    db.session.add_all(users)
    db.session.commit()

    return "Demo users created successfully!"


@app.route("/ai-chatbot", methods=["POST"])
@login_required
def ai_chatbot():

    user_message = request.json.get("message")

    response = client.chat.completions.create(
        model="gpt-4o-mini",  # affordable + good
        messages=[
            {"role": "system", "content": "You are a helpful educational assistant for students and tutors."},
            {"role": "user", "content": user_message}
        ]
    )

    ai_reply = response.choices[0].message.content

    return {"response": ai_reply}


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        load_questions_from_json()
        #seed_users()
    app.run(debug=True)