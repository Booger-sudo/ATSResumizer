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

# Extract education section from resume
def extract_education_section(resume_text):
    education_section = []
    lines = resume_text.split("\n")
    start = False
    for line in lines:
        if "Education" in line:
            start = True
        if start:
            education_section.append(line)
    return "\n".join(education_section)

# Extract skills from resume
def extract_skills(resume_text):
    skills_section = []
    lines = resume_text.split("\n")
    start = False
    for line in lines:
        if "Skills" in line:
            start = True
        if start and line.strip() and "Education" not in line:
            skills_section.append(line.strip())
        if "Education" in line:
            break
    return skills_section

# Select relevant skills based on job description
def select_relevant_skills(skills, job_desc_text):
    relevant_skills = []
    for skill in skills:
        if skill.lower() in job_desc_text.lower():
            relevant_skills.append(skill)
    return "\n".join(relevant_skills)

# Sanitize text to remove unwanted symbols
def sanitize_text(text):
    unwanted_symbols = ["***", "---", "===", "~~~", "___"]
    for symbol in unwanted_symbols:
        text = text.replace(symbol, "")
    return text

# Rewrite resume with OpenAI
async def rewrite_resume_with_openai(resume_text, job_desc_text):
    education_section = extract_education_section(resume_text)
    skills = extract_skills(resume_text)
    relevant_skills = select_relevant_skills(skills, job_desc_text)
    
    messages = [
        {"role": "system", "content": "You are a professional resume writer."},
        {"role": "user", "content": f"Rewrite the following resume to better match the given job description. Make it professional, concise, and well-structured with sections like Professional Summary, Relevant Work Experience, Work Experience, Skills, and Education. Ensure to keep all existing education details and use the relevant skills from the original resume that match the job description.\n\nJob Description:\n{job_desc_text}\n\nOriginal Resume:\n{resume_text}\n\nOptimized Resume with Relevant Skills:\n{relevant_skills}\n\nEducation Section:\n{education_section}"}
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
            output_pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], 'optimized_resume.pdf')
            create_resume_template(output_pdf_path, template_path, optimized_resume, contact_information)
            return await send_file(output_pdf_path, as_attachment=True)
    return await render_template('upload.html')

@app.route('/resume-preview')
async def resume_preview():
    optimized_resume = request.args.get('resume_content', "No resume content available.")
    ats_score = request.args.get('ats_score', "No ATS score available.")
    return await render_template('resume_preview.html', resume_content=optimized_resume, ats_score=ats_score)

if __name__ == "__main__":
    app.run(debug=True)
