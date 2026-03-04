from app import db, Result, Assessment, User

def test_take_assessment_score_and_points_award(client, make_user, login, create_assessment):
    user = make_user(username="student", email="student@test.com", password="123456", role="student")
    _, assessment = create_assessment(points_reward=50)

    # Must be logged in
    login(email="student@test.com")

    # GET the page (renders template)
    resp = client.get(f"/assessment/{assessment.id}")
    assert resp.status_code == 200
    assert b"TAKE ASSESSMENT" in resp.data

    # Prepare answers: get all questions for that assessment
    questions = assessment.questions
    assert len(questions) == 3

    # Case 1: Fail with 2/3 (66.67%) — no points
    form_data = {
        f"question_{questions[0].id}": questions[0].correct_answer,  # correct
        f"question_{questions[1].id}": questions[1].correct_answer,  # correct
        f"question_{questions[2].id}": "B"  # incorrect
    }
    resp = client.post(f"/assessment/{assessment.id}", data=form_data, follow_redirects=True)
    assert resp.status_code == 200
    # Verify a Result row is stored
    r = Result.query.filter_by(user_id=user.id, assessment_id=assessment.id).order_by(Result.id.desc()).first()
    assert r is not None
    assert r.score == 2
    assert r.total_questions == 3
    assert 66.0 < r.percentage < 67.0  # 66.66...
    # Points unchanged
    db.session.refresh(user)
    assert user.points == 0

    # Case 2: Pass with 3/3 (100%) — points added
    form_data = {f"question_{q.id}": q.correct_answer for q in questions}
    resp = client.post(f"/assessment/{assessment.id}", data=form_data, follow_redirects=True)
    assert resp.status_code == 200
    r2 = Result.query.filter_by(user_id=user.id, assessment_id=assessment.id).order_by(Result.id.desc()).first()
    assert r2.score == 3
    assert r2.percentage == 100.0
    db.session.refresh(user)
    assert user.points == 50  # assessment.points_reward


def test_take_assessment_with_zero_questions(client, make_user, login, create_assessment):
    user = make_user(email="zero@test.com")
    # Create assessment with no questions
    _, assessment = create_assessment(questions=[])
    login("zero@test.com")

    # POST empty form
    resp = client.post(f"/assessment/{assessment.id}", data={}, follow_redirects=True)
    assert resp.status_code == 200

    r = Result.query.filter_by(user_id=user.id, assessment_id=assessment.id).first()
    assert r is not None
    assert r.total_questions == 0
    assert r.percentage == 0
    db.session.refresh(user)
    assert user.points == 0  # no pass award