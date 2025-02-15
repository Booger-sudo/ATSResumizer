# ATS Resumizer

ATS Resumizer is a web application that optimizes resumes to better match job descriptions. It uses OpenAI's GPT-4 model to rewrite resumes, ensuring they are professional, concise, and well-structured. The application also calculates an ATS (Applicant Tracking System) score to determine how well the resume matches the job description.

## Features

- Upload a PDF resume
- Input a job description
- Optimize the resume to match the job description
- Calculate ATS score
- Download the optimized resume as a PDF

## Requirements

- Python 3.11
- Quart
- OpenAI API Key
- Other dependencies listed in `requirements.txt`

## Installation

1. Clone the repository:

    ```bash
    git clone https://github.com/yourusername/ats-resumizer.git
    cd ats-resumizer
    ```

2. Create a virtual environment and activate it:

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3. Install the required dependencies:

    ```bash
    pip install -r requirements.txt
    ```

4. Set up environment variables:

    Create a `.env` file in the root directory and add your OpenAI API key:

    ```env
    OPENAI_API_KEY=your_openai_api_key
    ```

## Usage

1. Run the application:

    ```bash
    python main.py
    ```

2. Open your web browser and go to `http://127.0.0.1:5000`.

3. Upload your resume (PDF) and input the job description.

4. Click on "Optimize Resume" to get the optimized resume and ATS score.

5. Download the optimized resume as a PDF.

## File Descriptions

- `main.py`: The main application file that handles file uploads, resume optimization, and PDF generation.
- `resume_template.py`: Contains functions for creating the resume template and generating the PDF.
- `templates/upload.html`: The HTML template for the upload form.
- `templates/resume_preview.html`: The HTML template for the resume preview.
- `static/styles.css`: Custom CSS styles for the web application.
- `requirements.txt`: List of required Python packages.
- `Base_Resume.pdf`: The base template for the resume.

## Example Input Data

### Sample Resume Text

```
John Doe
1234 Elm Street
Anytown, USA 12345
(555) 555-5555
johndoe@example.com

Professional Summary
---
Experienced software developer with a strong background in developing scalable web applications and working with cross-functional teams.

Relevant Work Experience
***
Software Developer at TechCorp (2020 - Present)
- Developed and maintained web applications using React and Node.js.
- Collaborated with UX designers to implement user-friendly interfaces.

Skills
---
- JavaScript
- React.js
- Node.js
- Git
- Agile development

Education
---
Bachelor of Science in Computer Science, State University (2016 - 2020)
```

### Sample Job Description

```
We are looking for a talented software developer to join our team. The ideal candidate should have experience with JavaScript, React.js, and Node.js. Familiarity with Git and Agile development practices is a plus.
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgments

- OpenAI for providing the GPT-4 model
- Quart for the web framework
- ReportLab for PDF generation
