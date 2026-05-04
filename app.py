import os
import sqlite3
from pathlib import Path
from functools import wraps
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, abort, g

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "site.db"
UPLOAD_FOLDER = BASE_DIR / "uploads"
ALLOWED_EXTENSIONS = {"pdf"}

app = Flask(__name__)
app.secret_key = "change-this-secret-key"
app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
app.config["MAX_CONTENT_LENGTH"] = 30 * 1024 * 1024

UPLOAD_FOLDER.mkdir(exist_ok=True)

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    db = sqlite3.connect(DB_PATH)
    db.execute("""
        CREATE TABLE IF NOT EXISTS exams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL CHECK(subject IN ('수학', '과학탐구')),
            title TEXT NOT NULL,
            year TEXT NOT NULL,
            exam_month TEXT NOT NULL,
            description TEXT,
            price INTEGER NOT NULL DEFAULT 0,
            pdf_filename TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db.commit()

    count = db.execute("SELECT COUNT(*) FROM exams").fetchone()[0]
    if count == 0:
        samples = [
            ("수학", "2026학년도 3월 수학 모의고사", "2026", "3월", "킬러 문항을 배제하고, 준킬러와 개념 연계를 강화한 수학 모의고사입니다.", 0, None),
            ("수학", "2026학년도 6월 수학 모의고사", "2026", "6월", "실전 감각을 끌어올리기 위한 난도 조절형 수학 모의고사입니다.", 0, None),
            ("과학탐구", "2026학년도 4월 통합 과학탐구 모의고사", "2026", "4월", "개념 이해와 자료 해석 능력을 함께 평가하는 과학탐구 모의고사입니다.", 0, None),
            ("과학탐구", "2026학년도 7월 과학탐구 실전형 모의고사", "2026", "7월", "그래프 해석과 응용 문항 중심의 실전형 과학탐구 모의고사입니다.", 0, None),
        ]
        db.executemany("""
            INSERT INTO exams (subject, title, year, exam_month, description, price, pdf_filename)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, samples)
        db.commit()
    db.close()

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("admin_logged_in"):
            flash("관리자 로그인이 필요합니다.")
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)
    return wrapped_view

@app.route("/")
def home():
    db = get_db()
    exams = db.execute("SELECT * FROM exams ORDER BY year DESC, id DESC").fetchall()
    math_exams = [e for e in exams if e["subject"] == "수학"]
    science_exams = [e for e in exams if e["subject"] == "과학탐구"]
    return render_template("index.html", math_exams=math_exams, science_exams=science_exams)

@app.route("/download/<filename>")
def download_file(filename):
    safe_name = os.path.basename(filename)
    file_path = UPLOAD_FOLDER / safe_name
    if not file_path.exists():
        abort(404)
    return send_from_directory(app.config["UPLOAD_FOLDER"], safe_name, as_attachment=True)

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        user_id = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if user_id == "admin" and password == "1234":
            session["admin_logged_in"] = True
            flash("관리자 로그인에 성공했습니다.")
            return redirect(url_for("admin_dashboard"))
        flash("아이디 또는 비밀번호가 올바르지 않습니다.")
    return render_template("admin_login.html")

@app.route("/admin/logout")
def admin_logout():
    session.clear()
    flash("로그아웃되었습니다.")
    return redirect(url_for("home"))

@app.route("/admin")
@login_required
def admin_dashboard():
    db = get_db()
    exams = db.execute("SELECT * FROM exams ORDER BY year DESC, id DESC").fetchall()
    return render_template("admin_dashboard.html", exams=exams)

@app.route("/admin/create", methods=["POST"])
@login_required
def admin_create():
    subject = request.form.get("subject", "").strip()
    title = request.form.get("title", "").strip()
    year = request.form.get("year", "").strip()
    exam_month = request.form.get("exam_month", "").strip()
    description = request.form.get("description", "").strip()
    price = 0

    if subject not in ("수학", "과학탐구"):
        flash("과목은 수학 또는 과학탐구만 등록할 수 있습니다.")
        return redirect(url_for("admin_dashboard"))

    if not title or not year or not exam_month:
        flash("제목, 연도, 월은 필수입니다.")
        return redirect(url_for("admin_dashboard"))

    pdf_filename = None
    file = request.files.get("pdf_file")
    if file and file.filename:
        if not allowed_file(file.filename):
            flash("PDF 파일만 업로드할 수 있습니다.")
            return redirect(url_for("admin_dashboard"))
        safe_name = secure_filename(file.filename)
        unique_name = f"{subject}_{year}_{exam_month}_{safe_name}"
        file.save(UPLOAD_FOLDER / unique_name)
        pdf_filename = unique_name

    db = get_db()
    db.execute("""
        INSERT INTO exams (subject, title, year, exam_month, description, price, pdf_filename)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (subject, title, year, exam_month, description, price, pdf_filename))
    db.commit()
    flash("자료가 등록되었습니다.")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/edit/<int:exam_id>", methods=["GET", "POST"])
@login_required
def admin_edit(exam_id):
    db = get_db()
    exam = db.execute("SELECT * FROM exams WHERE id = ?", (exam_id,)).fetchone()
    if not exam:
        abort(404)

    if request.method == "POST":
        subject = request.form.get("subject", "").strip()
        title = request.form.get("title", "").strip()
        year = request.form.get("year", "").strip()
        exam_month = request.form.get("exam_month", "").strip()
        description = request.form.get("description", "").strip()

        if subject not in ("수학", "과학탐구"):
            flash("과목은 수학 또는 과학탐구만 선택할 수 있습니다.")
            return redirect(url_for("admin_edit", exam_id=exam_id))

        if not title or not year or not exam_month:
            flash("제목, 연도, 월은 필수입니다.")
            return redirect(url_for("admin_edit", exam_id=exam_id))

        pdf_filename = exam["pdf_filename"]
        file = request.files.get("pdf_file")
        if file and file.filename:
            if not allowed_file(file.filename):
                flash("PDF 파일만 업로드할 수 있습니다.")
                return redirect(url_for("admin_edit", exam_id=exam_id))
            safe_name = secure_filename(file.filename)
            unique_name = f"{subject}_{year}_{exam_month}_{safe_name}"
            file.save(UPLOAD_FOLDER / unique_name)
            pdf_filename = unique_name

        remove_pdf = request.form.get("remove_pdf")
        if remove_pdf == "1":
            if exam["pdf_filename"]:
                old_file = UPLOAD_FOLDER / exam["pdf_filename"]
                if old_file.exists():
                    old_file.unlink()
            pdf_filename = None

        db.execute("""
            UPDATE exams
            SET subject = ?, title = ?, year = ?, exam_month = ?, description = ?, price = 0, pdf_filename = ?
            WHERE id = ?
        """, (subject, title, year, exam_month, description, pdf_filename, exam_id))
        db.commit()
        flash("자료가 수정되었습니다.")
        return redirect(url_for("admin_dashboard"))

    return render_template("admin_edit.html", exam=exam)

@app.route("/admin/delete/<int:exam_id>", methods=["POST"])
@login_required
def admin_delete(exam_id):
    db = get_db()
    exam = db.execute("SELECT * FROM exams WHERE id = ?", (exam_id,)).fetchone()
    if not exam:
        abort(404)

    if exam["pdf_filename"]:
        file_path = UPLOAD_FOLDER / exam["pdf_filename"]
        if file_path.exists():
            file_path.unlink()

    db.execute("DELETE FROM exams WHERE id = ?", (exam_id,))
    db.commit()
    flash("자료가 삭제되었습니다.")
    return redirect(url_for("admin_dashboard"))

with app.app_context():
    init_db()

if __name__ == "__main__":
    app.run(debug=True)
