# ATSResumizer

ATSResumizer is a web application designed to optimize resumes for Applicant Tracking Systems (ATS). It helps users rewrite their resumes to better match job descriptions, improving the chances of passing through ATS screenings.

## Features

- **Environment Variables Loading:** Utilizes `dotenv` to load environment variables, including the OpenAI API key.
- **Quart Web Application:** Initializes a Quart web application with necessary configurations such as `UPLOAD_FOLDER` and `secret_key`.
- **Rate Limiting:** Limits POST requests to 5 per minute using `quart_rate_limiter`.
- **Asynchronous ATS Score Calculation:** Calculates the ATS score by comparing the resume text and job description text using TF-IDF vectorization and cosine similarity.
- **PDF Text Extraction:** Extracts text from a PDF file asynchronously using PyMuPDF.
- **Resume Information Extraction:** Extracts contact information, work experiences, education section, and skills from the resume text.
- **Relevant Skills and Experiences Selection:** Selects relevant skills and 1 to 2 relevant work experiences from the resume that match the job description.
- **Text Sanitization:** Sanitizes text by removing unwanted symbols and asterisks.
- **Resume Rewriting with OpenAI:** Uses OpenAI's GPT API to rewrite the resume to better match the job description.
- **Web Routes:** Provides routes for file upload, resume preview, and optimized resume download.
- **PDF Generation:** Generates a PDF for the optimized resume using `fpdf`.

## Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/yourusername/ATSResumizer.git
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

4. The application will extract information from your resume, calculate the ATS score, rewrite the resume to better match the job description, and generate an optimized resume PDF for download.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request if you have any improvements or bug fixes.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
