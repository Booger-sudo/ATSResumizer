import re
import openai
import os
import aiohttp
from quart import Quart, render_template, request, send_file, flash, url_for, make_response, redirect
from dotenv import load_dotenv
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import fitz  # PyMuPDF for PDF extraction
import asyncio
import numpy as np
from werkzeug.utils import secure_filename  # To secure filenames
from resume_template import create_resume_template, create_resume_docx
from datetime import datetime
import webbrowser
import time 
import signal
from fpdf import FPDF
import threading

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Quart(__name__, static_folder='static')
upload_folder = os.getenv("UPLOAD_FOLDER", os.path.join(os.path.expanduser("~"), "ATSResumizer_uploads"))
app.config['UPLOAD_FOLDER'] = upload_folder
app.secret_key = os.getenv("SECRET_KEY", 'supersecretkey')  # Needed for flashing messages

# Ensure upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Asynchronous ATS Score Calculation
#Add weight to sections for better ATS accuracy 
async def calculate_ats_score(resume_text, job_desc_text):
    print("Calculating ATS score...")
    vectorizer = TfidfVectorizer(stop_words='english')
    tfidf_matrix = vectorizer.fit_transform([resume_text, job_desc_text])
    similarity_score = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
    print(f"ATS score calculated: {similarity_score}")
    return round(similarity_score * 100, 2)

# Extract text from a PDF
async def extract_pdf_text(pdf_path):
    print(f"Extracting text from PDF: {pdf_path}")
    doc = fitz.open(pdf_path)
    resume_text = "".join(page.get_text("text") for page in doc)
    print(f"Extracted resume text: {resume_text[:500]}...")  # Print first 500 characters for brevity
    return resume_text.strip()

# Extract contact information from resume
def extract_contact_information(resume_text):
    contact_information = []
    lines = resume_text.split("\n")
    for line in lines:
        if "Professional Summary" in line:
            break
        contact_information.append(line)
    return "\n".join(contact_information)

# Extract work experiences from resume and sort by date
def extract_work_experiences(resume_text):
    experiences = []
    lines = resume_text.split("\n")
    start = False

    for line in lines:
        if "Work Experience" in line:
            if start:  # Stop if "Work Experience" appears again
                break
            start = True
            continue  # Skip the header itself

        if start and line.strip() and "Education" not in line and "Skills" not in line:
            experiences.append(line.strip())

        if "Education" in line or "Skills" in line:
            break
    return experiences

def sort_work_experiences_by_date(experiences):
    def extract_dates(experience):
        dates = []
        for word in experience.split():
            try:
                date = datetime.strptime(word, "%B %Y")
                dates.append(date)
            except ValueError:
                continue
        return dates

    return sorted(experiences, key=lambda x: extract_dates(x)[-1] if extract_dates(x) else datetime.min, reverse=True)

# Extract education section from resume
def extract_education_section(resume_text):
    education_section = []
    lines = resume_text.split("\n")
    start = False
    
    for line in lines:
        line_lower = line.lower()
        
        if re.search(r'\beducation\b', line_lower):  # Detects "Education" as a section
            start = True
            continue  # Skip the header line itself
        
        if start:
            if re.search(r'\b(experience|skills|certifications|projects|summary)\b', line_lower):  
                break  # Stop at the next section
            
            if line.strip():  # Avoid empty lines
                education_section.append(line.strip())
    
    return "\n".join(education_section)

# Extract certifications and licenses from resume
def extract_certifications_licenses(resume_text):
    certifications_section = []
    lines = resume_text.split("\n")
    start = False
    
    for line in lines:
        line_lower = line.lower()
        
        if "certifications" in line_lower or "licenses" in line_lower:
            start = True
            continue  # Skip the header line itself
        
        if start:
            if re.search(r'\b(experience|education|skills|projects|summary)\b', line_lower):
                break  # Stop at the next section
            
            if line.strip():  # Avoid empty lines
                certifications_section.append(line.strip())
    
    return "\n".join(certifications_section)

# Extract skills from resume
def extract_skills(resume_text):
    skills_section = []
    lines = resume_text.split("\n")
    start = False
    
    for line in lines:
        line_lower = line.lower()
        
        if "skills" in line.lower():
            start = True
            continue  # Skip the header line itself
        
        if start:
            if "education" in line.lower() or "certifications" in line.lower():
                break  # Stop at education or similar section
            
            if start:
                if re.search(r'\b(experience|education|certifications|projects|summary)\b', line_lower):
                    break  # Stop at the next section
                if line.strip():  # Avoid empty lines
                    skills_section.append(line.strip())
    
    return skills_section

# Select relevant skills based on job description
def select_relevant_skills(skills, job_desc_text):
    job_desc_lower = job_desc_text.lower()
    relevant_skills = {skill for skill in skills if re.search(rf'\b{re.escape(skill.lower())}\b', job_desc_lower)}
    return "\n".join(relevant_skills)

# Sanitize text to remove unwanted symbols
def sanitize_text(text):
    unwanted_symbols = ["***", "---", "===", "~~~", "___", "###"]
    for symbol in unwanted_symbols:
        text = text.replace(symbol, "")
    text = text.replace("*", "")  # Remove any remaining asterisks
    return text

# Rewrite resume with OpenAI
async def rewrite_resume_with_openai(resume_text, job_desc_text):
    print("Rewriting resume with OpenAI...")
    education_section = extract_education_section(resume_text)
    skills = extract_skills(resume_text)
    relevant_skills = select_relevant_skills(skills, job_desc_text)
    work_experiences = extract_work_experiences(resume_text)
    sorted_work_experiences = sort_work_experiences_by_date(work_experiences)
    relevant_experiences = []
    for exp in sorted_work_experiences:
        if len(relevant_experiences) < 2 and any(skill.lower() in exp.lower() for skill in relevant_skills.split("\n")):
            relevant_experiences.append(exp)
    
    # Ensure only 5 work experiences max are included and avoid duplication
    top_work_experiences = relevant_experiences + [exp for exp in sorted_work_experiences if exp not in relevant_experiences][:5-len(relevant_experiences)]

    top_us_industries = [
        "Healthcare and Social Assistance", "Retail Trade", "Professional, Scientific, and Technical Services", 
        "Manufacturing", "Finance and Insurance", "Educational Services", "Construction", 
        "Wholesale Trade", "Information", "Transportation and Warehousing", "Administrative and Support", 
        "Real Estate and Rental and Leasing", "Public Administration", "Accommodation and Food Services", 
        "Other Services (except Public Administration)", "Management of Companies and Enterprises", 
        "Arts, Entertainment, and Recreation", "Utilities", "Mining, Quarrying, and Oil and Gas Extraction", 
        "Agriculture, Forestry, Fishing and Hunting"
    ]

    messages = [
        {"role": "system", "content": "You are a professional resume writer. You do not make mistakes. You do not duplicate work experiences and you take great pride in your work."},
        {"role": "user", "content": f"Rewrite the following resume to better match the given job description. Make it professional, concise, and well-structured with sections like Professional Summary, Relevant Experience (1-2 entries), Work Experience (max 5 entries), Skills, Education, etc. Consider the top 20 work industries in the US: {', '.join(top_us_industries)}. Ensure that the sections are clearly differentiated and well-organized. Highlight similarities between the resume and the job description without copying text directly from the job description. Use keywords from the job description to improve ATS compatibility.\n\nResume:\n{resume_text}\n\nJob Description:\n{job_desc_text}"}
    ]

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                "https://api.openai.com/v1/chat/completions",
                json={
                    "model": "gpt-4o-mini",
                    "messages": messages,
                    "max_tokens": 1500,
                    "temperature": 0.7
                },
                headers={"Authorization": f"Bearer {openai.api_key}"}
            ) as response:
                if response.status != 200:
                    error_message = await response.json()
                    print(f"Error: OpenAI API request failed with status {response.status}: {error_message}")
                    return None, f"Error: Unable to rewrite resume. API returned status {response.status}."
                result = await response.json()
                if 'choices' in result:
                    optimized_resume = result['choices'][0]['message']['content'].strip()
                    print(f"Optimized resume: {optimized_resume[:500]}...")  # Print first 500 characters for brevity
                    sanitized_resume = sanitize_text(optimized_resume)
                    deduplicated_resume = deduplicate_text(sanitized_resume)
                    return deduplicated_resume, None
                else:
                    print("Error: 'choices' not found in OpenAI API response")
                    return None, "Error: Unable to rewrite resume. 'choices' not found in API response."
        except Exception as e:
            print(f"Exception occurred while calling OpenAI API: {e}")
            return None, "Error: Unable to rewrite resume. Please try again."

def deduplicate_text(text):
    seen = set()
    deduplicated_lines = []
    for line in text.split("\n"):
        if line not in seen:
            seen.add(line)
            deduplicated_lines.append(line)
    return "\n".join(deduplicated_lines)

# Route to upload a file
@app.route('/', methods=['GET', 'POST'])
async def upload_file():
    if request.method == 'POST':
        print("Received POST request for file upload.")
        resume = (await request.files).get('resume')
        job_desc_text = (await request.form).get('job_description')
        file_format = (await request.form).get('file_format')
        template_path = os.path.join(app.config['UPLOAD_FOLDER'], 'Base_Resume.pdf')#test another template 'stylish_resume_template.pdf'
        if resume and job_desc_text:
            filename = secure_filename(resume.filename)
            print(f"Uploaded resume filename: {filename}")
            if '..' in filename or '/' in filename or '\\' in filename:
                await flash("Invalid filename")
                return await render_template('upload.html')
            resume_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            await resume.save(resume_path)
            print(f"Saved resume to: {resume_path}")
            resume_text = await extract_pdf_text(resume_path)
            ats_score = await calculate_ats_score(resume_text, job_desc_text)
            optimized_resume, error = await rewrite_resume_with_openai(resume_text, job_desc_text)
            if error:
                await flash(error)
                return await render_template('upload.html')
            sanitized_resume = sanitize_text(optimized_resume)
            print(f"Sanitized resume: {sanitized_resume[:500]}...")  # Print first 500 characters for brevity
            return redirect(url_for('resume_preview', resume_content=sanitized_resume, ats_score=ats_score))
    return await render_template('upload.html')

@app.route('/resume-preview')
async def resume_preview():
    optimized_resume = request.args.get('resume_content', "No resume content available.")
    ats_score = request.args.get('ats_score', "No ATS score available.")
    
    # Debug prints
    print(f"Received resume_content: {optimized_resume[:500]}...")  # Print first 500 characters for brevity
    print(f"Received ats_score: {ats_score}")
    
    sanitized_resume = sanitize_text(optimized_resume)
    
    # Debug prints
    print(f"Sanitized resume_content: {sanitized_resume[:500]}...")  # Print first 500 characters for brevity
    
    return await render_template('resume_preview.html', resume_content=sanitized_resume, ats_score=ats_score)

@app.route('/download-resume')
async def download_resume():
    resume_content = request.args.get('resume_content', "No resume content available.")
    file_format = request.args.get('file_format', 'pdf')
    
    print(f"Downloading resume in format: {file_format}")
    
    if file_format == 'docx':
        resume_path = os.path.join(app.config['UPLOAD_FOLDER'], 'optimized_resume.docx')
        create_resume_docx(resume_content, resume_path)
        print(f"DOCX file path: {resume_path}")
        return await send_file(resume_path, as_attachment=True)
    else:
        resume_path = os.path.join(app.config['UPLOAD_FOLDER'], 'optimized_resume.pdf')
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font('Arial', size=12)
        pdf.multi_cell(0, 10, resume_content)
        pdf.output(resume_path)
        print(f"PDF file path: {resume_path}")
        if not os.path.exists(resume_path):
            return "File not found", 404
        return await send_file(resume_path, as_attachment=True)

def handle_shutdown():
    loop = asyncio.get_event_loop()
    loop.stop()

def open_browser():
    webbrowser.open_new("http://localhost:5000")

if __name__ == "__main__":
    threading.Timer(1, open_browser).start()  # Open the browser after 1 second
    signal.signal(signal.SIGINT, lambda s, f: handle_shutdown())
    signal.signal(signal.SIGTERM, lambda s, f: handle_shutdown())
    app.run(debug=True, port=5000)

