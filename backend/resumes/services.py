from io import BytesIO

import pymupdf
from docx import Document


class ResumeExtractionError(Exception):
    pass


def extract_pdf_text(uploaded_file):
    try:
        uploaded_file.seek(0)
        with pymupdf.open(stream=uploaded_file.read(), filetype='pdf') as document:
            text = '\n\n'.join(page.get_text() for page in document)
    except Exception as error:
        raise ResumeExtractionError('This PDF could not be read. Please upload a valid, unencrypted PDF.') from error
    finally:
        uploaded_file.seek(0)

    if not text.strip():
        raise ResumeExtractionError('No readable text was found in this PDF.')
    return text.strip()


def extract_docx_text(uploaded_file):
    try:
        uploaded_file.seek(0)
        document = Document(BytesIO(uploaded_file.read()))
        text = '\n'.join(paragraph.text for paragraph in document.paragraphs)
    except Exception as error:
        raise ResumeExtractionError('This DOCX could not be read. Please upload a valid DOCX document.') from error
    finally:
        uploaded_file.seek(0)

    if not text.strip():
        raise ResumeExtractionError('No readable text was found in this DOCX document.')
    return text.strip()


def extract_resume_text(uploaded_file):
    filename = uploaded_file.name.replace('\\', '/').lower()
    if filename.endswith('.pdf'):
        return extract_pdf_text(uploaded_file)
    if filename.endswith('.docx'):
        return extract_docx_text(uploaded_file)
    raise ResumeExtractionError('Only PDF and DOCX resume files are supported.')