
from flask import Flask, render_template, request, send_file
import os
import pdfplumber
import re

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.piecharts import Pie

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# ---------------- SKILLS ----------------
SKILLS = [
    "python", "java", "c", "c++", "html", "css", "javascript",
    "sql", "mysql", "flask", "django", "react", "nodejs",
    "machine learning", "deep learning", "data analysis",
    "numpy", "pandas", "git", "github", "api", "rest api"
]

# ---------------- PDF EXTRACTION ----------------
def extract_text(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

# ---------------- SMART SKILL DETECTION ----------------
def find_skills(text):
    text = text.lower()
    extracted = set()

    for skill in SKILLS:
        if skill in text:
            extracted.add(skill)

    words = text.split()
    for word in words:
        word = word.strip(".,()[]{}:;")

        if word in SKILLS:
            extracted.add(word)

    return list(extracted)

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
        if line and "@" not in line and len(line) > 2:
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

# ---------------- CHATGPT STYLE SUGGESTIONS ----------------
def generate_ai_suggestions(matched, missing, resume_text):
    suggestions = []

    if len(missing) > 0:
        suggestions.append("Add missing skills: " + ", ".join(missing))

    if len(matched) < 3:
        suggestions.append("Your resume has low skill match. Add more technical keywords.")

    if "project" not in resume_text.lower():
        suggestions.append("Add a Projects section with real-world applications.")

    if "experience" not in resume_text.lower():
        suggestions.append("Include Internship or Work Experience section.")

    suggestions.append("Use strong action verbs like 'developed', 'built', 'designed'.")

    return suggestions

# ---------------- SCORE EXPLANATION (NEW FEATURE) ----------------
def explain_score(score, matched, missing, resume_text):
    reasons = []

    if score < 40:
        reasons.append("Low ATS score due to poor skill matching with job description.")
    elif score < 70:
        reasons.append("Moderate ATS score. Some required skills are missing.")
    else:
        reasons.append("Good ATS score. Resume matches most job requirements.")

    if len(missing) > 0:
        reasons.append("Missing important skills: " + ", ".join(missing))

    if len(matched) < 3:
        reasons.append("Very few matching technical skills found.")

    if "project" not in resume_text.lower():
        reasons.append("No Projects section detected.")

    if "experience" not in resume_text.lower():
        reasons.append("No Internship/Experience section found.")

    return reasons

# ---------------- PIE CHART ----------------
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
def generate_pdf(name, email, phone, score, matched, missing, suggestions, explanation):

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

    content.append(Paragraph("Skill Match Overview", styles["Heading2"]))
    content.append(create_pie_chart(len(matched), len(missing)))
    content.append(Spacer(1, 12))

    content.append(Paragraph("AI Suggestions:", styles["Heading2"]))
    for s in suggestions:
        content.append(Paragraph(f"- {s}", styles["BodyText"]))

    content.append(Spacer(1, 12))

    content.append(Paragraph("Why Your Score is This (Explanation):", styles["Heading2"]))
    for r in explanation:
        content.append(Paragraph(f"- {r}", styles["BodyText"]))

    doc.build(content)
    return file_path

# ---------------- MAIN ROUTE ----------------
@app.route("/", methods=["GET", "POST"])
def home():

    filename = None
    resume_text = ""

    score = 0
    matched = []
    missing = []
    suggestions = []
    explanation = []

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

            suggestions = generate_ai_suggestions(matched, missing, resume_text)
            explanation = explain_score(score, matched, missing, resume_text)

            app.config["last_report"] = {
                "name": name,
                "email": email,
                "phone": phone,
                "score": score,
                "matched": matched,
                "missing": missing,
                "suggestions": suggestions,
                "explanation": explanation
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
        certifications=certifications,
        explanation=explanation
    )

# ---------------- DOWNLOAD ----------------
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
        data["suggestions"],
        data["explanation"]
    )

    return send_file(file_path, as_attachment=True)

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)