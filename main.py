import openai
  import os
  import aiohttp
  from quart import Quart, render_template, request, send_file
  from quart_rate_limiter import RateLimiter, Limit
  from dotenv import load_dotenv
  from sklearn.feature_extraction.text import TfidfVectorizer
  from sklearn.metrics.pairwise import cosine_similarity
  import fitz  # PyMuPDF for PDF extraction
  from reportlab.lib.pagesizes import letter
  from reportlab.pdfgen import canvas
  import asyncio
  import numpy as np
  from werkzeug.utils import secure_filename  # To secure filenames

  # Load environment variables
  load_dotenv()
  openai.api_key = os.getenv("OPENAI_API_KEY")

  app = Quart(__name__)
  app.config['UPLOAD_FOLDER'] = 'uploads/'

  # Ensure upload folder exists
  if not os.path.exists(app.config['UPLOAD_FOLDER']):
      os.makedirs(app.config['UPLOAD_FOLDER'])

  # Configure quart-rate-limiter
  rate_limiter = RateLimiter(app)
  rate_limiter.add_rule(Limit("5/minute"), methods=["POST"])  # Limit to 5 POST requests per minute

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
      prompt = f"""
      Rewrite the following resume to better match the given job description.
      Make it professional, concise, and well-structured with sections like Summary, Skills, Work Experience, and Education.

      Job Description:
      {job_desc_text}

      Original Resume:
      {resume_text}

      Optimized Resume:
      """
      
      async with aiohttp.ClientSession() as session:
          async with session.post(
              "https://api.openai.com/v1/completions",
              json={
                  "model": "text-davinci-003",
                  "prompt": prompt,
                  "max_tokens": 1500,
                  "temperature": 0.7
              },
              headers={"Authorization": f"Bearer {openai.api_key}"}
          ) as response:
              result = await response.json()
              return result['choices'][0]['text'].strip()

  # Create PDF with updated content
  def create_pdf(output_path, resume_content):
      c = canvas.Canvas(output_path, pagesize=letter)
      c.setFont("Helvetica", 12)
      y_position = 750
      for line in resume_content.split("\n"):
          c.drawString(50, y_position, line)
          y_position -= 15
          if y_position < 50:
              c.showPage()
              y_position = 750
      c.save()

  # Route to upload a file
  @app.route('/', methods=['GET', 'POST'])
  @rate_limiter.limit("3/minute")  # Apply specific rate limit for this route
  async def upload_file():
      if request.method == 'POST':
          resume = (await request.files).get('resume')
          job_desc_text = (await request.form).get('job_description')
          if resume and job_desc_text:
              filename = secure_filename(resume.filename)  # Secure the filename
              resume_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
              await resume.save(resume_path)
              resume_text = await extract_pdf_text(resume_path)
              ats_score = await calculate_ats_score(resume_text, job_desc_text)
              optimized_resume = await rewrite_resume_with_openai(resume_text, job_desc_text)
              output_pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], 'optimized_resume.pdf')
              create_pdf(output_pdf_path, optimized_resume)
              return await send_file(output_pdf_path, as_attachment=True)
      return await render_template('upload.html')

  @app.route('/resume-preview')
  async def resume_preview():
      optimized_resume = request.args.get('resume_content', "No resume content available.")
      ats_score = request.args.get('ats_score', "No ATS score available.")
      return await render_template('resume_preview.html', resume_content=optimized_resume, ats_score=ats_score)

  if __name__ == "__main__":
      app.run(debug=True)
