from io import BytesIO
from pathlib import PurePosixPath
import zipfile

from django.core.exceptions import ValidationError


MAX_RESUME_SIZE = 5 * 1024 * 1024
MAX_DOCX_UNCOMPRESSED_SIZE = 50 * 1024 * 1024


def validate_resume_file(uploaded_file):
    if uploaded_file.size > MAX_RESUME_SIZE:
        raise ValidationError('File size must be 5 MB or smaller.')

    extension = PurePosixPath(str(uploaded_file.name).replace('\\', '/')).suffix.lower()
    if extension not in {'.pdf', '.docx'}:
        raise ValidationError('Only PDF and DOCX resume files are supported.')

    try:
        uploaded_file.seek(0)
        if extension == '.pdf':
            is_valid = b'%PDF-' in uploaded_file.read(1024)
        else:
            with zipfile.ZipFile(BytesIO(uploaded_file.read())) as archive:
                names = set(archive.namelist())
                total_uncompressed_size = sum(item.file_size for item in archive.infolist())
                is_valid = (
                    '[Content_Types].xml' in names
                    and 'word/document.xml' in names
                    and total_uncompressed_size <= MAX_DOCX_UNCOMPRESSED_SIZE
                )
    except (OSError, ValueError, zipfile.BadZipFile, zipfile.LargeZipFile):
        is_valid = False
    finally:
        uploaded_file.seek(0)

    if not is_valid:
        raise ValidationError('The file content is not a valid PDF or DOCX document.')