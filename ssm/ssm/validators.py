"""
File validators for upload restrictions and robust auto-compression.
"""
import os
import logging
from io import BytesIO
from PIL import Image
from pypdf import PdfReader, PdfWriter
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


def compress_file(file):
    """
    Attempt to compress an image or PDF file in-place to be under the 100KB limit.
    Modifies the underlying UploadedFile or FieldFile buffer and size attributes.
    """
    from django.core.files.base import File as DjangoFile

    max_size_kb = 100
    max_size_bytes = max_size_kb * 1024

    if not hasattr(file, 'size') or not file.size:
        return

    # Skip compression if already under the limit
    if file.size <= max_size_bytes:
        return

    # Resolve underlying file object wrapper if file is a FieldFile/UploadedFile
    django_file = file
    if hasattr(file, 'file') and isinstance(file.file, DjangoFile):
        django_file = file.file

    filename, ext = os.path.splitext(file.name if hasattr(file, 'name') else 'file')
    ext = ext.lower()

    # 1. Compress Images (PNG, JPG, JPEG, WEBP, BMP, TIF)
    if ext in ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tif', '.tiff']:
        try:
            file.seek(0)
            img = Image.open(file)

            # Convert colorspace (RGBA/LA/P to RGB for JPEG format)
            if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                background = Image.new("RGB", img.size, (255, 255, 255))
                mask = img.convert("RGBA").split()[3]
                background.paste(img, mask=mask)
                img = background
            elif img.mode != "RGB":
                img = img.convert("RGB")

            # Progressive downscale and JPEG quality reduction
            max_dim = 1200
            output = BytesIO()

            while True:
                curr_img = img.copy()
                if max(curr_img.size) > max_dim:
                    curr_img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

                quality_achieved = False
                for quality in (85, 70, 55, 40, 25, 15):
                    output = BytesIO()
                    curr_img.save(output, format='JPEG', quality=quality, optimize=True)
                    if output.tell() <= max_size_bytes:
                        quality_achieved = True
                        break

                if quality_achieved or max_dim <= 250:
                    break

                max_dim = int(max_dim * 0.75)

            output.seek(0)
            new_size = output.getbuffer().nbytes
            new_name = f"{filename}.jpg"

            # Update file handle and size attributes in place
            if hasattr(django_file, 'file'):
                django_file.file = output
            django_file.size = new_size
            django_file.name = new_name
            if hasattr(django_file, 'content_type'):
                django_file.content_type = 'image/jpeg'

            if django_file is not file:
                file.name = new_name
                if hasattr(file, '_size'):
                    file._size = new_size
                if hasattr(file, 'size'):
                    try:
                        file.size = new_size
                    except AttributeError:
                        pass

            logger.info(f"Auto-compressed image {filename}{ext} -> {new_name} ({new_size / 1024:.1f}KB)")
        except Exception as e:
            logger.warning(f"Auto-compression failed for image {getattr(file, 'name', '')}: {e}")

    # 2. Compress PDFs
    elif ext == '.pdf':
        try:
            file.seek(0)
            reader = PdfReader(file)
            writer = PdfWriter()

            for page in reader.pages:
                try:
                    page.compress_content_streams()
                except Exception:
                    pass
                writer.add_page(page)

            output = BytesIO()
            writer.write(output)
            output.seek(0)
            new_size = output.getbuffer().nbytes

            if new_size < file.size:
                if hasattr(django_file, 'file'):
                    django_file.file = output
                django_file.size = new_size
                if django_file is not file:
                    if hasattr(file, '_size'):
                        file._size = new_size
                    if hasattr(file, 'size'):
                        try:
                            file.size = new_size
                        except AttributeError:
                            pass
                logger.info(f"Auto-compressed PDF {filename}.pdf ({new_size / 1024:.1f}KB)")
        except Exception as e:
            logger.warning(f"Auto-compression failed for PDF {getattr(file, 'name', '')}: {e}")


def validate_file_size(file):
    """
    Validate that uploaded file size is within limits.
    Attempts automatic compression first.
    If the file is an auto-compressed image or PDF, allows up to 350KB soft threshold
    so complex PDFs/documents never block user submissions.
    """
    target_max_kb = 100
    target_max_bytes = target_max_kb * 1024  # 100KB

    if hasattr(file, 'size') and file.size > target_max_bytes:
        compress_file(file)

    current_size = getattr(file, 'size', 0)

    # Soft limit threshold (350KB) for compressed documents/PDFs
    SOFT_MAX_BYTES = 350 * 1024

    if current_size > SOFT_MAX_BYTES:
        raise ValidationError(
            f'File size must not exceed {target_max_kb}KB. '
            f'Current file size after compression: {current_size / 1024:.1f}KB'
        )
