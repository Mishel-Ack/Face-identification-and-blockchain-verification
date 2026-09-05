from pydantic import BaseModel, field_validator
from typing import List
import os

class PipelineRequest(BaseModel):
    """Validated request for /api/run_pipeline"""
    search_name: str = ""
    search_handle: str = ""
    search_location: str = ""
    search_occupation: str = ""
    search_education: str = ""
    search_website: str = ""
    keywords: str = "AI tech innovator"
    photo_notes: str = ""
    target_platforms: List[str] = []

    @field_validator('keywords', 'search_name', mode='before')
    @classmethod
    def sanitize_input(cls, v):
        """Remove dangerous characters"""
        if not v:
            return ""
        dangerous_chars = ['<', '>', ';', '--']
        if any(char in str(v) for char in dangerous_chars):
            raise ValueError('Invalid characters in input')
        return str(v).strip()

    @field_validator('search_website', mode='before')
    @classmethod
    def validate_url(cls, v):
        """Basic URL validation"""
        if v and not (str(v).startswith('http://') or str(v).startswith('https://')):
            raise ValueError('URL must start with http:// or https://')
        return str(v) if v else ""

class FileValidator:
    """Validate uploaded image files"""
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}
    ALLOWED_MIMETYPES = {'image/jpeg', 'image/png', 'image/gif', 'application/octet-stream'}

    @staticmethod
    def validate_file(file):
        """Validate file size, extension, and mimetype"""
        if not file or file.filename == '':
            raise ValueError('No file provided')

        # Check size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)

        if file_size > FileValidator.MAX_FILE_SIZE:
            raise ValueError(f'File too large ({file_size} bytes > {FileValidator.MAX_FILE_SIZE} bytes)')

        # Check extension
        ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
        if ext not in FileValidator.ALLOWED_EXTENSIONS:
            raise ValueError(f'Invalid file type: {ext}. Allowed: {FileValidator.ALLOWED_EXTENSIONS}')

        # Check mimetype if present
        if file.content_type and file.content_type not in FileValidator.ALLOWED_MIMETYPES:
            raise ValueError(f'Invalid MIME type: {file.content_type}')

        return True
