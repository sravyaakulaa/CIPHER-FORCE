import os
import json
import secrets
from datetime import datetime
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from database import init_db, get_connection
from ai_analyzer import analyze_resume
from pdf_generator import create_resume_pdf
from resume_parser import extract_pdf_text

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", secrets.token_hex(32))
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "uploads")
app.config["OUTPUT_FOLDER"] = os.path.join(app.root_path, "generated_resumes")
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["OUTPUT_FOLDER"], exist_ok=True)
ALLOWED_EXTENSIONS = {"pdf"}


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def current_user():
    if not session.get("user_id"):
        return None
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id, name, email FROM users WHERE id=%s", (session["user_id"],))
        return cur.fetchone()
    finally:
        conn.close()


@app.context_processor
def inject_user():
    return {"current_user": current_user()}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or not email or len(password) < 8:
            flash("Enter your name and email. Password must be at least 8 characters.", "danger")
            return render_template("register.html")
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT id FROM users WHERE email=%s", (email,))
            if cur.fetchone():
                flash("An account with that email already exists.", "danger")
                return render_template("register.html")
            cur.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s)",
                (name, email, generate_password_hash(password))
            )
            conn.commit()
            user_id = cur.lastrowid
            session["user_id"] = user_id
            flash("Account created. Welcome!", "success")
            return redirect(url_for("dashboard"))
        except Exception:
            conn.rollback()
            app.logger.exception("Registration failed")
            flash("Could not create the account. Check your database configuration.", "danger")
        finally:
            conn.close()
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        conn = get_connection()
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT id, password_hash FROM users WHERE email=%s", (email,))
            user = cur.fetchone()
            if user and check_password_hash(user["password_hash"], password):
                session.clear()
                session["user_id"] = user["id"]
                flash("Welcome back!", "success")
                return redirect(url_for("dashboard"))
            flash("Incorrect email or password.", "danger")
        finally:
            conn.close()
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT COUNT(*) AS total FROM analyses WHERE user_id=%s", (session["user_id"],))
        total = cur.fetchone()["total"]
        cur.execute(
            "SELECT id, title, score, created_at FROM analyses WHERE user_id=%s ORDER BY created_at DESC LIMIT 5",
            (session["user_id"],)
        )
        recent = cur.fetchall()
    finally:
        conn.close()
    return render_template("dashboard.html", total=total, recent=recent)


@app.route("/builder", methods=["GET", "POST"])
@login_required
def builder():
    if request.method == "POST":
        data = {
            "name": request.form.get("name", "").strip(),
            "email": request.form.get("email", "").strip(),
            "phone": request.form.get("phone", "").strip(),
            "location": request.form.get("location", "").strip(),
            "linkedin": request.form.get("linkedin", "").strip(),
            "website": request.form.get("website", "").strip(),
            "summary": request.form.get("summary", "").strip(),
            "education": request.form.get("education", "").strip(),
            "experience": request.form.get("experience", "").strip(),
            "projects": request.form.get("projects", "").strip(),
            "skills": request.form.get("skills", "").strip(),
            "certifications": request.form.get("certifications", "").strip(),
        }
        if not data["name"]:
            flash("Please enter your name.", "danger")
            return render_template("builder.html", data=data)
        filename = f"resume_{session['user_id']}_{secrets.token_hex(5)}.pdf"
        output_path = os.path.join(app.config["OUTPUT_FOLDER"], filename)
        try:
            create_resume_pdf(data, output_path)
            conn = get_connection()
            try:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO analyses (user_id, title, score, source_text, result_json, pdf_filename) "
                    "VALUES (%s,%s,%s,%s,%s,%s)",
                    (session["user_id"], f"{data['name']} - Resume", None,
                     json.dumps(data, ensure_ascii=False), json.dumps({"type": "builder"}, ensure_ascii=False), filename)
                )
                conn.commit()
            finally:
                conn.close()
            return send_file(output_path, as_attachment=True, download_name="my_resume.pdf")
        except Exception:
            app.logger.exception("Resume generation failed")
            flash("Could not generate PDF. Please check the server logs.", "danger")
    return render_template("builder.html", data={})


@app.route("/analyzer", methods=["GET", "POST"])
@login_required
def analyzer():
    if request.method == "POST":
        uploaded = request.files.get("resume")
        job_description = request.form.get("job_description", "").strip()
        if not uploaded or not uploaded.filename:
            flash("Choose a PDF resume to upload.", "danger")
            return render_template("analyzer.html")
        if not uploaded.filename.lower().endswith(".pdf"):
            flash("Only PDF files are supported.", "danger")
            return render_template("analyzer.html")
        safe_name = secure_filename(uploaded.filename)
        stored_name = f"{session['user_id']}_{secrets.token_hex(6)}_{safe_name}"
        path = os.path.join(app.config["UPLOAD_FOLDER"], stored_name)
        uploaded.save(path)
        try:
            resume_text = extract_pdf_text(path)
            if len(resume_text.strip()) < 40:
                flash("We couldn't read enough text from this PDF. Try a text-based PDF rather than a scanned image.", "danger")
                return render_template("analyzer.html")
            result = analyze_resume(resume_text, job_description)
            title = safe_name[:180]
            conn = get_connection()
            try:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO analyses (user_id, title, score, source_text, result_json, pdf_filename) "
                    "VALUES (%s,%s,%s,%s,%s,%s)",
                    (session["user_id"], title, result.get("score"), resume_text[:60000],
                     json.dumps(result, ensure_ascii=False), None)
                )
                conn.commit()
                analysis_id = cur.lastrowid
            finally:
                conn.close()
            return redirect(url_for("result", analysis_id=analysis_id))
        except Exception as exc:
            app.logger.exception("Resume analysis failed")
            message = str(exc) if app.debug else "Analysis failed. Check your Gemini API key, internet connection, and server logs."
            flash(message, "danger")
        finally:
            try:
                os.remove(path)
            except OSError:
                pass
    return render_template("analyzer.html")


@app.route("/result/<int:analysis_id>")
@login_required
def result(analysis_id):
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM analyses WHERE id=%s AND user_id=%s", (analysis_id, session["user_id"]))
        item = cur.fetchone()
    finally:
        conn.close()
    if not item:
        flash("Analysis not found.", "danger")
        return redirect(url_for("history"))
    try:
        result_data = json.loads(item["result_json"] or "{}")
    except json.JSONDecodeError:
        result_data = {}
    return render_template("result.html", item=item, result=result_data)


@app.route("/history")
@login_required
def history():
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT id, title, score, created_at FROM analyses WHERE user_id=%s ORDER BY created_at DESC",
            (session["user_id"],)
        )
        items = cur.fetchall()
    finally:
        conn.close()
    return render_template("history.html", items=items)


@app.route("/download/<int:analysis_id>")
@login_required
def download(analysis_id):
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT pdf_filename FROM analyses WHERE id=%s AND user_id=%s", (analysis_id, session["user_id"]))
        item = cur.fetchone()
    finally:
        conn.close()
    if not item or not item["pdf_filename"]:
        flash("No generated resume PDF is attached to this record.", "warning")
        return redirect(url_for("history"))
    path = os.path.join(app.config["OUTPUT_FOLDER"], os.path.basename(item["pdf_filename"]))
    if not os.path.isfile(path):
        flash("The generated PDF is no longer on this server. Generate the resume again.", "warning")
        return redirect(url_for("history"))
    return send_file(path, as_attachment=True, download_name="my_resume.pdf")


@app.route("/delete/<int:analysis_id>", methods=["POST"])
@login_required
def delete_analysis(analysis_id):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM analyses WHERE id=%s AND user_id=%s", (analysis_id, session["user_id"]))
        conn.commit()
    finally:
        conn.close()
    flash("History record deleted.", "success")
    return redirect(url_for("history"))


@app.errorhandler(413)
def too_large(_error):
    flash("File is too large. Maximum upload size is 5 MB.", "danger")
    return redirect(url_for("analyzer"))


if __name__ == "__main__":
    try:
        init_db()
    except Exception:
        app.logger.exception("Database initialization failed")
        print("Database setup failed. Check .env values and ensure MySQL is running.")
    app.run(debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")
