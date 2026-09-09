from database import init_db, init_users_table, save_topics, get_all_topics, mark_topic_done, delete_subject, get_all_subjects, init_settings_table, save_settings, get_settings, update_topic, create_user, get_user_by_username, get_user_by_id, get_all_users
from flask import Flask, request, render_template, url_for, redirect, session, flash
from scheduler import Topic, build_schedule
from parser import extract_topics_auto
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import secrets

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(16))
import uuid

def get_user_id():
    return session.get("user_id")


from functools import wraps

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped

def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.")
            return redirect(url_for("login"))
        if not session.get("is_admin"):
            flash("Admin access required.")
            return redirect(url_for("home_dashboard"))
        return view(*args, **kwargs)
    return wrapped

@app.route("/admin")
@admin_required
def admin_dashboard():
    users = get_all_users()
    user_stats = []
    for user in users:
        subjects = get_all_subjects(user["id"])
        user_stats.append({"username": user["username"], "is_admin": user["is_admin"], "subject_count": len(subjects)})
    return render_template("admin.html", user_stats=user_stats)

def _build_full_schedule(user_id):
    by_subject = {}
    for row in get_all_topics(user_id):
        if row["done"]:
            continue
        by_subject.setdefault(row["subject"], []).append(Topic(
            id=row["id"],
            name=row["name"],
            subject=row["subject"],
            weight=row["weight"],
            weakness=row["weakness"],
            exam_date=row["exam_date"],
        ))

    full_schedule = []
    for subject, topics in by_subject.items():
        settings = get_settings(user_id, subject)
        pace = settings["pace"]
        for topic, hours in build_schedule(topics, hours_per_day=settings["hours_per_day"], pace=pace):
            full_schedule.append({"topic": topic, "hours": hours, "score": topic.score(pace)})

    full_schedule.sort(key=lambda entry: entry["score"], reverse=True)
    return full_schedule
init_db()
init_settings_table()
init_users_table()
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.route("/")
def home():
    return render_template("landing.html")


@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload_page():
    if request.method == "POST":
        user_id = get_user_id()
        subject_name = request.form["subject_name"]
        uploaded_file = request.files["syllabus"]
        safe_name = f"{user_id}_{secure_filename(uploaded_file.filename)}"
        save_path = os.path.join(UPLOAD_FOLDER, safe_name)
        uploaded_file.save(save_path)

        topics = extract_topics_auto(save_path)
        if not topics:
            return render_template("manual_entry.html", subject_name=subject_name)
        return render_template("results.html", topics=topics, subject_name=subject_name)

    return render_template("upload.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        if not username or not password:
            flash("Username and password are required.")
            return render_template("register.html")

        if get_user_by_username(username):
            flash("That username is already taken.")
            return render_template("register.html")

        password_hash = generate_password_hash(password)
        create_user(username, password_hash)
        flash("Account created. Please log in.")
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        user = get_user_by_username(username)
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["is_admin"] = bool(user["is_admin"])
            flash(f"Welcome back, {user['username']}.")
            return redirect(url_for("home_dashboard"))

        flash("Incorrect username or password.", "error")
        return render_template("login.html")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "success")
    return redirect(url_for("login"))

@app.route("/schedule", methods=["GET", "POST"])
@login_required
def schedule():
    user_id = get_user_id()
    if request.method == "POST":
        subject_name = request.form["subject_name"]
        exam_date = request.form["exam_date"]
        hours_per_day = float(request.form["hours_per_day"])
        pace = int(request.form["pace"])
        save_settings(user_id, subject_name, hours_per_day, pace)

        names = request.form.getlist("topic_name")
        weights = request.form.getlist("weight")
        weaknesses = request.form.getlist("weakness")

        topics_data = []
        for name, weight, weakness in zip(names, weights, weaknesses):
            topics_data.append({
                "name": name,
                "weight": int(weight),
                "weakness": int(weakness),
                "exam_date": exam_date,
            })
        save_topics(user_id, subject_name, topics_data)

    return render_template("schedule.html", schedule=_build_full_schedule(user_id))

@app.route("/complete", methods=["POST"])
@login_required
def complete():
    user_id = get_user_id()
    mark_topic_done(user_id, int(request.form["topic_id"]))
    flash("Topic marked complete.")
    return render_template("schedule.html", schedule=_build_full_schedule(user_id))
@app.route("/edit-topic", methods=["POST"])
@login_required
def edit_topic():
    user_id = get_user_id()
    update_topic(
        user_id=user_id,
        topic_id=int(request.form["topic_id"]),
        weight=int(request.form["weight"]),
        weakness=int(request.form["weakness"]),
    )
    flash("Topic updated.")
    return render_template("schedule.html", schedule=_build_full_schedule(user_id))

@app.route("/manual-topics", methods=["POST"])
@login_required
def manual_topics():
    subject_name = request.form["subject_name"]
    raw_text = request.form["topic_list"]

    topics = [line.strip() for line in raw_text.splitlines() if line.strip()]

    return render_template("results.html", topics=topics, subject_name=subject_name)

@app.route("/manage")
@login_required
def manage():
    user_id = get_user_id()
    subjects = get_all_subjects(user_id)
    return render_template("manage_subjects.html", subjects=subjects)


@app.route("/delete-subject", methods=["POST"])
@login_required
def delete_subject_route():
    user_id = get_user_id()
    subject_name = request.form["subject_name"]
    delete_subject(user_id, subject_name)
    flash(f"{subject_name} deleted.")
    return redirect(url_for("manage"))

@app.route("/home")
@login_required
def home_dashboard():
    user_id = get_user_id()
    all_topics = get_all_topics(user_id)
    subjects = get_all_subjects(user_id)

    total_topics = len(all_topics)
    completed_topics = len([t for t in all_topics if t["done"]])
    pending_topics = total_topics - completed_topics

    return render_template(
        "home.html",
        subjects=subjects,
        total_topics=total_topics,
        completed_topics=completed_topics,
        pending_topics=pending_topics,
    )
@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=os.environ.get("FLASK_DEBUG") == "1")


