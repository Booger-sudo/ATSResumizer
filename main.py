import re
import openai
import os
import aiohttp
from quart import Quart, render_template, request, send_file, flash, redirect, url_for
from dotenv import load_dotenv
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import fitz  # PyMuPDF for PDF extraction
import asyncio
import numpy as np
from werkzeug.utils import secure_filename  # To secure filenames
from resume_template import create_resume_template
from datetime import datetime

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Quart(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.secret_key = 'supersecretkey'  # Needed for flashing messages

# Ensure upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Check if quart_rate_limiter and Limit are available
try:
    from quart_rate_limiter import RateLimiter, Limit
    rate_limiter = RateLimiter(app)
    if hasattr(rate_limiter, 'add_rule'):
        rate_limiter.add_rule(Limit("5/minute"), methods=["POST"])  # Limit to 5 POST requests per minute
    else:
        print("Warning: 'add_rule' method not found in RateLimiter. Rate limiting rules not applied.")
except ImportError:
    rate_limiter = None
    print("Warning: quart_rate_limiter or Limit is not available. Rate limiting will be disabled.")

# Asynchronous ATS Score Calculation
async def calculate_ats_score(resume_text, job_desc_text):
    vectorizer = TfidfVectorizer(stop_words='english')
    tfidf_matrix = vectorizer.fit_transform([resume_text, job_desc_text])
    similarity_score = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
    return round(similarity_score * 100, 2)

# Extract text from a PDF
async def extract_pdf_text(pdf_path):
    doc = fitz.open(pdf_path)
    resume_text = "".join(page.get_text("text") for page in doc)
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
            start = True
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

# Extract skills from resume
def extract_skills(resume_text):
    skills_section = []
    lines = resume_text.split("\n")
    start = False
    
    for line in lines:
        line_lower = line.lower()
        
        if "skills" in line_lower:
            start = True
            continue  # Skip the header line itself
        
        if start:
            if "education" in line_lower or "certifications" in line_lower:
                break  # Stop at education or similar section
            
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
    unwanted_symbols = ["***", "---", "===", "~~~", "___"]
    for symbol in unwanted_symbols:
        text = text.replace(symbol, "")
    text = text.replace("*", "")  # Remove any remaining asterisks
    return text

# Rewrite resume with OpenAI
async def rewrite_resume_with_openai(resume_text, job_desc_text):
    education_section = extract_education_section(resume_text)
    skills = extract_skills(resume_text)
    relevant_skills = select_relevant_skills(skills, job_desc_text)
    work_experiences = extract_work_experiences(resume_text)
    sorted_work_experiences = sort_work_experiences_by_date(work_experiences)
    relevant_experiences = []
    for exp in sorted_work_experiences:
        if len(relevant_experiences) < 2 and any(skill.lower() in exp.lower() for skill in relevant_skills.split("\n")):
            relevant_experiences.append(exp)

    messages = [
        {"role": "system", "content": "You are a professional resume writer."},
        {"role": "user", "content": f"Rewrite the following resume to better match the given job description. Make it professional, concise, and well-structured with sections like Professional Summary, Work Experience, Education, and Skills. Here is the resume:\n{resume_text}\nHere is the job description:\n{job_desc_text}"}
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
                    sanitized_resume = sanitize_text(optimized_resume)
                    return sanitized_resume, None
                else:
                    print("Error: 'choices' not found in OpenAI API response")
                    return None, "Error: Unable to rewrite resume. 'choices' not found in API response."
        except Exception as e:
            print(f"Exception occurred while calling OpenAI API: {e}")
            return None, "Error: Unable to rewrite resume. Please try again."

# Route to upload a file
@app.route('/', methods=['GET', 'POST'])
async def upload_file():
    if request.method == 'POST':
        resume = (await request.files).get('resume')
        job_desc_text = (await request.form).get('job_description')
        template_path = os.path.join(app.config['UPLOAD_FOLDER'], 'Base_Resume.pdf')
        if resume and job_desc_text:
            filename = secure_filename(resume.filename)  # Secure the filename
            resume_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            await resume.save(resume_path)
            resume_text = await extract_pdf_text(resume_path)
            ats_score = await calculate_ats_score(resume_text, job_desc_text)
            optimized_resume, error = await rewrite_resume_with_openai(resume_text, job_desc_text)
            if error:
                await flash(error)
                return await render_template('upload.html')
            contact_information = extract_contact_information(resume_text)  # Extract contact information here
            work_experiences = extract_work_experiences(resume_text)  # Extract work experiences here
            sorted_work_experiences = sort_work_experiences_by_date(work_experiences)
            top_work_experiences = "\n".join(sorted_work_experiences[:3])  # Get top 3 most recent work experiences
            education_section = extract_education_section(resume_text)  # Extract education section here
            output_pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], 'optimized_resume.pdf')
            create_resume_template(output_pdf_path, template_path, optimized_resume, contact_information, top_work_experiences, education_section)
            return await send_file(output_pdf_path, as_attachment=True)
    return await render_template('upload.html')

@app.route('/resume-preview')
async def resume_preview():
    optimized_resume = request.args.get('resume_content', "No resume content available.")
    ats_score = request.args.get('ats_score', "No ATS score available.")
    return await render_template('resume_preview.html', resume_content=optimized_resume, ats_score=ats_score)

if __name__ == "__main__":
    app.run(debug=True)
