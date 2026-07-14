"""
File validators for upload restrictions.
"""
import os
from io import BytesIO
from PIL import Image
from pypdf import PdfReader, PdfWriter
from django.core.exceptions import ValidationError


def compress_file(file):
    """
    Attempt to compress an image or PDF file in-place to be under 100KB.
    """
    from django.core.files.base import File as DjangoFile
    
    max_size_kb = 100
    max_size_bytes = max_size_kb * 1024
    
    # Resolve the underlying UploadedFile wrapper if file is a FieldFile
    django_file = file
    if hasattr(file, 'file') and isinstance(file.file, DjangoFile):
        django_file = file.file

    filename, ext = os.path.splitext(file.name)
    ext = ext.lower()
    
    # 1. Compress Images (PNG, JPG, JPEG, WEBP)
    if ext in ['.jpg', '.jpeg', '.png', '.webp']:
        try:
            file.seek(0)
            img = Image.open(file)
            
            # Handle transparency (RGBA / LA / Palette with transparency) for JPEG conversion
            if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                background = Image.new("RGB", img.size, (255, 255, 255))
                mask = img.convert("RGBA").split()[3]
                background.paste(img, mask=mask)
                img = background
            elif img.mode != "RGB":
                img = img.convert("RGB")
                
            output = BytesIO()
            quality = 80
            img.save(output, format='JPEG', quality=quality)
            
            # Progressively reduce quality to fit within 100KB
            while output.tell() > max_size_bytes and quality > 30:
                output = BytesIO()
                quality -= 10
                img.save(output, format='JPEG', quality=quality)
                
            # If still too large, downscale the resolution
            if output.tell() > max_size_bytes:
                width, height = img.size
                img = img.resize((int(width * 0.75), int(height * 0.75)), Image.Resampling.LANCZOS)
                output = BytesIO()
                img.save(output, format='JPEG', quality=50)
                
            output.seek(0)
            new_size = output.getbuffer().nbytes
            
            # Update the inner UploadedFile in place
            django_file.file = output
            django_file.size = new_size
            django_file.name = f"{filename}.jpg"
            if hasattr(django_file, 'content_type'):
                django_file.content_type = 'image/jpeg'
            
            # Update the outer FieldFile wrapper if applicable
            if django_file is not file:
                file.name = f"{filename}.jpg"
                if hasattr(file, '_size'):
                    file._size = new_size
        except Exception as e:
            print(f"Auto-compression failed for image {file.name}: {e}")

    # 2. Compress PDFs
    elif ext == '.pdf':
        try:
            file.seek(0)
            reader = PdfReader(file)
            writer = PdfWriter()
            
            for page in reader.pages:
                page.compress_content_streams()
                writer.add_page(page)
                
            output = BytesIO()
            writer.write(output)
            output.seek(0)
            new_size = output.getbuffer().nbytes
            
            # Update the file object in place if it actually got smaller
            if new_size < file.size:
                django_file.file = output
                django_file.size = new_size
                if django_file is not file:
                    if hasattr(file, '_size'):
                        file._size = new_size
        except Exception as e:
            print(f"Auto-compression failed for PDF {file.name}: {e}")


def validate_file_size(file):
    """
    Validate that uploaded file is not larger than 100KB.
    If the file is an image or PDF and is larger than 100KB,
    attempt to compress it in-place first.
    """
    max_size_kb = 100
    max_size_bytes = max_size_kb * 1024  # 100KB = 102400 bytes
    
    # Compress first if it's over the limit
    if file.size > max_size_bytes:
        compress_file(file)
        
    # Raise validation error if it still exceeds the limit
    if file.size > max_size_bytes:
        raise ValidationError(
            f'File size must not exceed {max_size_kb}KB. '
            f'Current file size: {file.size / 1024:.1f}KB'
        )

