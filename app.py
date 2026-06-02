from flask import Flask, render_template, request, send_file
import os
import pdfplumber
import re

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# ✅ Pie chart imports (NO matplotlib needed)
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.piecharts import Pie

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

SKILLS = [
    "python", "java", "c++", "html", "css", "javascript",
    "sql", "mysql", "flask", "git", "react", "nodejs",
    "machine learning", "data analysis"
]

# ---------------- PDF TEXT EXTRACTION ----------------
def extract_text(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

# ---------------- SKILL DETECTION ----------------
def find_skills(text):
    text = text.lower()
    return [skill for skill in SKILLS if skill in text]

# ---------------- BASIC EXTRACTIONS ----------------
def extract_email(text):
    match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    return match.group() if match else "Not Found"

def extract_phone(text):
    match = re.search(r'(\+91\s?)?[0-9]{10}', text)
    return match.group() if match else "Not Found"

def extract_name(text):
    lines = text.split("\n")
    for line in lines:
        line = line.strip()
        if line and "@" not in line:
            return line
    return "Not Found"

def extract_section(text, section_name):
    lines = text.split("\n")
    capture = False
    section_content = []

    for line in lines:
        if section_name.lower() in line.lower():
            capture = True
            continue
        if capture:
            if line.strip() == "":
                break
            section_content.append(line.strip())

    return " ".join(section_content)

# ---------------- PIE CHART FUNCTION ----------------
def create_pie_chart(matched_count, missing_count):
    drawing = Drawing(200, 200)

    pie = Pie()
    pie.x = 50
    pie.y = 50
    pie.width = 100
    pie.height = 100

    pie.data = [matched_count, missing_count]
    pie.labels = ["Matched", "Missing"]

    pie.slices.strokeWidth = 0.5

    drawing.add(pie)
    return drawing

# ---------------- PDF REPORT ----------------
def generate_pdf(name, email, phone, score, matched, missing, suggestions):

    file_path = "ats_report.pdf"
    doc = SimpleDocTemplate(file_path)
    styles = getSampleStyleSheet()

    content = []

    content.append(Paragraph("AI Resume Analyzer Report", styles["Title"]))
    content.append(Spacer(1, 12))

    content.append(Paragraph(f"Name: {name}", styles["BodyText"]))
    content.append(Paragraph(f"Email: {email}", styles["BodyText"]))
    content.append(Paragraph(f"Phone: {phone}", styles["BodyText"]))
    content.append(Spacer(1, 12))

    content.append(Paragraph(f"ATS Score: {score}%", styles["Heading2"]))
    content.append(Spacer(1, 12))

    # ✅ PIE CHART ADDED HERE
    content.append(Paragraph("Skill Match Overview", styles["Heading2"]))
    content.append(create_pie_chart(len(matched), len(missing)))
    content.append(Spacer(1, 12))

    content.append(Paragraph(f"Matched Skills: {', '.join(matched)}", styles["BodyText"]))
    content.append(Spacer(1, 12))

    content.append(Paragraph(f"Missing Skills: {', '.join(missing)}", styles["BodyText"]))
    content.append(Spacer(1, 12))

    content.append(Paragraph("Suggestions:", styles["Heading2"]))

    for s in suggestions:
        content.append(Paragraph(f"- {s}", styles["BodyText"]))

    doc.build(content)

    return file_path

# ---------------- MAIN ROUTE ----------------
@app.route("/", methods=["GET", "POST"])
def home():

    filename = None
    resume_text = ""

    score = None
    matched = []
    missing = []
    suggestions = []

    name = ""
    email = ""
    phone = ""

    education = ""
    skills_section = ""
    projects = ""
    certifications = ""

    if request.method == "POST":

        file = request.files["resume"]
        job_desc = request.form["job_desc"]

        if file and file.filename != "":

            filename = file.filename

            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)

            resume_text = extract_text(filepath)

            name = extract_name(resume_text)
            email = extract_email(resume_text)
            phone = extract_phone(resume_text)

            education = extract_section(resume_text, "Education")
            skills_section = extract_section(resume_text, "Skills")
            projects = extract_section(resume_text, "Projects")
            certifications = extract_section(resume_text, "Certifications")

            resume_skills = find_skills(resume_text)
            jd_skills = find_skills(job_desc)

            matched = list(set(resume_skills) & set(jd_skills))
            missing = list(set(jd_skills) - set(resume_skills))

            score = round((len(matched) / len(jd_skills)) * 100) if jd_skills else 0

            for skill in missing:
                suggestions.append(f"Consider adding {skill} to your resume.")

            # save for PDF download
            app.config["last_report"] = {
                "name": name,
                "email": email,
                "phone": phone,
                "score": score,
                "matched": matched,
                "missing": missing,
                "suggestions": suggestions
            }

    return render_template(
        "index.html",
        filename=filename,
        resume_text=resume_text,
        score=score,
        matched=matched,
        missing=missing,
        suggestions=suggestions,
        name=name,
        email=email,
        phone=phone,
        education=education,
        skills_section=skills_section,
        projects=projects,
        certifications=certifications
    )

# ---------------- DOWNLOAD ROUTE ----------------
@app.route("/download")
def download():

    data = app.config.get("last_report", None)

    if not data:
        return "No report found. Please analyze a resume first."

    file_path = generate_pdf(
        data["name"],
        data["email"],
        data["phone"],
        data["score"],
        data["matched"],
        data["missing"],
        data["suggestions"]
    )

    return send_file(file_path, as_attachment=True)

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)