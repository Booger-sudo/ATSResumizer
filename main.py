import openai
import os
import aiohttp
from quart import Quart, render_template, request, send_file, flash
from dotenv import load_dotenv
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import fitz  # PyMuPDF for PDF extraction
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
import asyncio
import numpy as np
from werkzeug.utils import secure_filename  # To secure filenames

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

# Rewrite resume with OpenAI
async def rewrite_resume_with_openai(resume_text, job_desc_text):
    messages = [
        {"role": "system", "content": "You are a professional resume writer."},
        {"role": "user", "content": f"Rewrite the following resume to better match the given job description. Make it professional, concise, and well-structured with sections like Summary, Skills, Work Experience, and Education. Ensure it follows the same layout as Base_Resume.pdf. Do not add the job description as a new work experience. Instead, choose one from existing work experience that closely relates and add it to a section called 'Relevant Work Experience' placed between the 'Professional Summary' section and the 'Work Experience' section. The Professional Summary should be at least one full paragraph.\n\nJob Description:\n{job_desc_text}\n\nOriginal Resume:\n{resume_text}\n\nOptimized Resume:"}
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
                    return result['choices'][0]['message']['content'].strip(), None
                else:
                    print("Error: 'choices' not found in OpenAI API response")
                    return None, "Error: Unable to rewrite resume. 'choices' not found in API response."
        except Exception as e:
            print(f"Exception occurred while calling OpenAI API: {e}")
            return None, "Error: Unable to rewrite resume. Please try again."

# Create PDF with updated content
def create_pdf(output_path, base_resume_path, optimized_resume_content):
    doc = SimpleDocTemplate(output_path, pagesize=letter)
    styles = getSampleStyleSheet()

    # Custom styles
    section_title_style = styles['Heading2']
    section_title_style.textColor = colors.darkblue

    normal_style = styles['BodyText']
    normal_style.fontSize = 12

    elements = []

    # Add optimized resume content with formatting
    for line in optimized_resume_content.split("\n"):
        if line.strip().startswith("Professional Summary"):
            elements.append(Paragraph(line.strip(), section_title_style))
        elif line.strip().startswith("Relevant Work Experience"):
            elements.append(Paragraph(line.strip(), section_title_style))
        elif line.strip().startswith("Work Experience"):
            elements.append(Paragraph(line.strip(), section_title_style))
        elif line.strip().startswith("Skills"):
            elements.append(Paragraph(line.strip(), section_title_style))
        elif line.strip().startswith("Education"):
            elements.append(Paragraph(line.strip(), section_title_style))
        else:
            elements.append(Paragraph(line.strip(), normal_style))
        elements.append(Spacer(1, 12))

    doc.build(elements)

# Route to upload a file
@app.route('/', methods=['GET', 'POST'])
async def upload_file():
    if request.method == 'POST':
        resume = (await request.files).get('resume')
        job_desc_text = (await request.form).get('job_description')
        base_resume = os.path.join(app.config['UPLOAD_FOLDER'], 'Base_Resume.pdf')
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
            output_pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], 'optimized_resume.pdf')
            create_pdf(output_pdf_path, base_resume, optimized_resume)
            return await send_file(output_pdf_path, as_attachment=True)
    return await render_template('upload.html')

@app.route('/resume-preview')
async def resume_preview():
    optimized_resume = request.args.get('resume_content', "No resume content available.")
    ats_score = request.args.get('ats_score', "No ATS score available.")
    return await render_template('resume_preview.html', resume_content=optimized_resume, ats_score=ats_score)

if __name__ == "__main__":
    app.run(debug=True)
