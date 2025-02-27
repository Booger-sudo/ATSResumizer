# ATSResumizer

ATSResumizer is a web application designed to optimize resumes for Applicant Tracking Systems (ATS). It helps users rewrite their resumes to better match job descriptions, improving the chances of passing through ATS screenings.

## Functions

- **Environment Variables Loading:** Utilizes `dotenv` to load environment variables.
- **Quart Web Application:** Initializes a Quart web application for handling file uploads and generating optimized resumes.
- **Rate Limiting:** Limits POST requests to prevent abuse and ensure fair usage.
- **Asynchronous ATS Score Calculation:** Calculates an ATS score based on the similarity between the resume and job description.
- **PDF Text Extraction:** Extracts text from uploaded PDF resumes.
- **Resume Information Extraction:** Extracts contact information, work experiences, education, and skills from the resume.
- **Relevant Skills and Experiences Selection:** Selects relevant skills and work experiences that match the job description.
- **Text Sanitization:** Cleans up the text by removing unwanted symbols.
- **Resume Rewriting with OpenAI:** Uses OpenAI's GPT API to rewrite the resume to better match the job description.
- **PDF Generation:** Generates a PDF for the optimized resume.

## Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/Booger-sudo/ATSResumizer.git
    cd ATSResumizer
    ```

2. Create and activate a virtual environment:
    ```sh
    python3 -m venv venv
    source venv/bin/activate
    ```

3. Install the required dependencies:
    ```sh
    pip install -r requirements.txt
    ```

4. Create a `.env` file in the root directory and add your OpenAI API key:
    ```env
    OPENAI_API_KEY=your_openai_api_key
    ```

## Usage

1. Run the Quart web application:
    ```sh
    python main.py
    ```

2. Open your web browser and navigate to `http://localhost:5000`.

3. Upload your resume (in PDF format) and paste the job description.

4. The application will process the resume, calculate the ATS score, rewrite the resume to match the job description, and generate an optimized resume PDF for download.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
