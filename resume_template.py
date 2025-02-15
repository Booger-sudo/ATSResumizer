from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, Spacer, SimpleDocTemplate, Frame, PageTemplate
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib import colors
from PyPDF2 import PdfReader, PdfWriter
import fitz  # PyMuPDF for PDF extraction
import io

def extract_layout(template_path):
    doc = fitz.open(template_path)
    text = ""
    for page in doc:
        text += page.get_text("text")
    return text.split("\n")

def create_resume_template(output_path, template_path, content, contact_information):
    styles = getSampleStyleSheet()

    # Custom styles
    section_title_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        textColor=colors.darkblue,
        spaceAfter=12,
    )

    normal_style = ParagraphStyle(
        'Normal',
        parent=styles['BodyText'],
        fontSize=12,
        leading=14,
        spaceAfter=12,
    )

    layout_lines = extract_layout(template_path)

    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)
    can.setFont("Helvetica", 12)

    contact_info_lines = contact_information.split("\n")
    y_position = 10 * inch
    for line in contact_info_lines:
        can.drawString(0.5 * inch, y_position, line)
        y_position -= 0.2 * inch

    can.save()

    packet.seek(0)
    new_pdf = PdfReader(packet)

    existing_pdf = PdfReader(open(template_path, "rb"))
    output = PdfWriter()

    for i in range(len(existing_pdf.pages)):
        page = existing_pdf.pages[i]
        if i < len(new_pdf.pages):
            overlay = new_pdf.pages[i]
            page.merge_page(overlay)
        output.add_page(page)

    elements = []

    content_lines = content.split("\n")
    content_index = 0

    elements.append(Spacer(1, 1 * inch))  # Add space to avoid overlaying contact information

    for line in layout_lines:
        if "Professional Summary" in line:
            elements.append(Paragraph("Professional Summary", section_title_style))
            while content_index < len(content_lines) and "Professional Summary" not in content_lines[content_index]:
                content_index += 1
            content_index += 1
            while content_index < len(content_lines) and "Relevant Work Experience" not in content_lines[content_index]:
                elements.append(Paragraph(content_lines[content_index], normal_style))
                content_index += 1
        elif "Relevant Work Experience" in line:
            elements.append(Paragraph("Relevant Work Experience", section_title_style))
            while content_index < len(content_lines) and "Relevant Work Experience" not in content_lines[content_index]:
                content_index += 1
            content_index += 1
            while content_index < len(content_lines) and "Work Experience" not in content_lines[content_index]:
                elements.append(Paragraph(content_lines[content_index], normal_style))
                content_index += 1
        elif "Work Experience" in line:
            elements.append(Paragraph("Work Experience", section_title_style))
            while content_index < len(content_lines) and "Work Experience" not in content_lines[content_index]:
                content_index += 1
            content_index += 1
            while content_index < len(content_lines) and "Skills" not in content_lines[content_index]:
                elements.append(Paragraph(content_lines[content_index], normal_style))
                content_index += 1
        elif "Skills" in line:
            elements.append(Paragraph("Skills", section_title_style))
            while content_index < len(content_lines) and "Skills" not in content_lines[content_index]:
                content_index += 1
            content_index += 1
            while content_index < len(content_lines) and "Education" not in content_lines[content_index]:
                elements.append(Paragraph(content_lines[content_index], normal_style))
                content_index += 1
        elif "Education" in line:
            elements.append(Paragraph("Education", section_title_style))
            while content_index < len(content_lines) and "Education" not in content_lines[content_index]:
                content_index += 1
            content_index += 1
            while content_index < len(content_lines):
                elements.append(Paragraph(content_lines[content_index], normal_style))
                content_index += 1

    doc = SimpleDocTemplate(output_path, pagesize=letter)

    def add_page(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 12)
        contact_info_lines = contact_information.split("\n")
        y_position = 10 * inch
        for line in contact_info_lines:
            canvas.drawString(0.5 * inch, y_position, line)
            y_position -= 0.2 * inch
        canvas.restoreState()

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id='normal')
    template = PageTemplate(id='test', frames=frame, onPage=add_page)
    doc.addPageTemplates([template])

    doc.build(elements)
