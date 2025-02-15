from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, Spacer
from reportlab.pdfgen import canvas
from PyPDF2 import PdfReader, PdfWriter
import io

def create_resume_template(output_path, template_path, content):
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

    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)
    can.setFont("Helvetica", 12)

    elements = []

    # Add optimized resume content with formatting
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if line.strip().startswith("Professional Summary"):
            elements.append(Paragraph(line.strip(), section_title_style))
            elements.append(Spacer(1, 12))
        elif line.strip().startswith("Relevant Work Experience"):
            elements.append(Paragraph(line.strip(), section_title_style))
            elements.append(Spacer(1, 12))
        elif line.strip().startswith("Work Experience"):
            elements.append(Paragraph(line.strip(), section_title_style))
            elements.append(Spacer(1, 12))
        elif line.strip().startswith("Skills"):
            elements.append(Paragraph(line.strip(), section_title_style))
            elements.append(Spacer(1, 12))
        elif line.strip().startswith("Education"):
            elements.append(Paragraph(line.strip(), section_title_style))
            elements.append(Spacer(1, 12))
        else:
            elements.append(Paragraph(line.strip(), normal_style))
            elements.append(Spacer(1, 12))

    for element in elements:
        element.wrapOn(can, 6.5 * inch, 9 * inch)
        element.drawOn(can, inch, 10 * inch - element.height)

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

    with open(output_path, "wb") as outputStream:
        output.write(outputStream)
