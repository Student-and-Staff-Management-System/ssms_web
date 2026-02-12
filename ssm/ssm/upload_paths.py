"""
Helper functions for generating R2 upload paths.
Organizes files into per-student and per-staff folders.
"""
import os
from datetime import datetime


# ==========================================
# STUDENT FILE UPLOAD PATHS
# ==========================================

def student_photo_path(instance, filename):
    """Upload path for student profile photos."""
    ext = filename.split('.')[-1]
    return f'students/{instance.student.roll_number}/profile_photo.{ext}'


def student_certificate_path(instance, filename, cert_type):
    """Generic path for student certificates."""
    ext = filename.split('.')[-1]
    return f'students/{instance.student.roll_number}/{cert_type}.{ext}'


def community_certificate_path(instance, filename):
    return student_certificate_path(instance, filename, 'community_certificate')


def income_certificate_path(instance, filename):
    return student_certificate_path(instance, filename, 'income_certificate')


def first_graduate_certificate_path(instance, filename):
    return student_certificate_path(instance, filename, 'first_graduate_certificate')


def aadhaar_card_path(instance, filename):
    return student_certificate_path(instance, filename, 'aadhaar_card')


def sslc_marksheet_path(instance, filename):
    return student_certificate_path(instance, filename, 'sslc_marksheet')


def hsc_marksheet_path(instance, filename):
    return student_certificate_path(instance, filename, 'hsc_marksheet')


def bank_passbook_path(instance, filename):
    return student_certificate_path(instance, filename, 'bank_passbook')


def driving_license_path(instance, filename):
    return student_certificate_path(instance, filename, 'driving_license')


def student_id_card_path(instance, filename):
    return student_certificate_path(instance, filename, 'student_id_card')


def student_leave_document_path(instance, filename):
    """Upload path for student leave documents."""
    ext = filename.split('.')[-1]
    date_str = datetime.now().strftime('%Y%m%d')
    leave_type = instance.leave_type.lower().replace(' ', '_')
    return f'students/{instance.student.roll_number}/leave_{leave_type}_{date_str}.{ext}'


def result_screenshot_path(instance, filename):
    """Upload path for result screenshots."""
    ext = filename.split('.')[-1]
    date_str = datetime.now().strftime('%Y%m%d')
    subject_code = instance.subject.code.replace(' ', '_')
    return f'students/{instance.student.roll_number}/result_{subject_code}_{date_str}.{ext}'


def student_remark_evidence_path(instance, filename):
    """Upload path for student remark evidence documents."""
    ext = filename.split('.')[-1]
    date_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f'students/{instance.student.roll_number}/remarks/evidence_{date_str}.{ext}'


def student_remark_apology_path(instance, filename):
    """Upload path for student apology letters."""
    ext = filename.split('.')[-1]
    date_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f'students/{instance.student.roll_number}/remarks/apology_{date_str}.{ext}'


def news_documents_path(instance, filename):
    """Upload path for news/announcement documents."""
    ext = filename.split('.')[-1]
    date_str = datetime.now().strftime('%Y%m%d')
    # Sanitize filename
    safe_filename = filename.replace(' ', '_')
    return f'news/documents/{date_str}_{safe_filename}'


# ==========================================
# STAFF FILE UPLOAD PATHS
# ==========================================

def staff_photo_path(instance, filename):
    """Upload path for staff profile photos."""
    ext = filename.split('.')[-1]
    return f'staff/{instance.staff_id}/profile_photo.{ext}'


def staff_award_document_path(instance, filename):
    """Upload path for staff award/honour documents."""
    ext = filename.split('.')[-1]
    title_slug = instance.title[:30].replace(' ', '_').lower()
    year = instance.year or 'undated'
    return f'staff/{instance.staff.staff_id}/award_{title_slug}_{year}.{ext}'


def staff_seminar_document_path(instance, filename):
    """Upload path for staff seminar/workshop documents."""
    ext = filename.split('.')[-1]
    title_slug = instance.title[:30].replace(' ', '_').lower()
    year = instance.year or 'undated'
    return f'staff/{instance.staff.staff_id}/seminar_{title_slug}_{year}.{ext}'


def staff_student_guided_document_path(instance, filename):
    """Upload path for staff student guidance documents."""
    ext = filename.split('.')[-1]
    name_slug = instance.student_name[:20].replace(' ', '_').lower()
    degree = instance.degree_type.lower()
    return f'staff/{instance.staff.staff_id}/student_guided_{name_slug}_{degree}.{ext}'


def staff_leave_document_path(instance, filename):
    """Upload path for staff leave documents."""
    ext = filename.split('.')[-1]
    date_str = datetime.now().strftime('%Y%m%d')
    leave_type = instance.leave_type.lower().replace(' ', '_')
    return f'staff/{instance.staff.staff_id}/leave_{leave_type}_{date_str}.{ext}'


def staff_conference_document_path(instance, filename):
    """Upload path for staff conference documents."""
    ext = filename.split('.')[-1]
    title_slug = instance.title_of_paper[:30].replace(' ', '_').lower() if instance.title_of_paper else 'conference'
    year = instance.year_of_publication or 'undated'
    return f'staff/{instance.staff.staff_id}/conference_{title_slug}_{year}.{ext}'


def staff_journal_document_path(instance, filename):
    """Upload path for staff journal documents."""
    ext = filename.split('.')[-1]
    title_slug = instance.title_of_paper[:30].replace(' ', '_').lower()
    year = instance.published_year or 'undated'
    return f'staff/{instance.staff.staff_id}/journal_{title_slug}_{year}.{ext}'


def staff_book_document_path(instance, filename):
    """Upload path for staff book documents."""
    ext = filename.split('.')[-1]
    title_slug = instance.title_of_book[:30].replace(' ', '_').lower()
    year = instance.year_of_publication or 'undated'
    return f'staff/{instance.staff.staff_id}/book_{title_slug}_{year}.{ext}'
