import os
from django.conf import settings
from django.utils import timezone
from django.core.mail import send_mail



def log_audit(request, action, actor_type, actor_id, actor_name=None, object_type=None, object_id=None, message=None):
    """
    Logs an audit trail entry.
    """
    from .models import AuditLog

    # Get Client IP
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip_address = x_forwarded_for.split(',')[0]
    else:
        ip_address = request.META.get('REMOTE_ADDR')

    # Get User Agent
    user_agent = request.META.get('HTTP_USER_AGENT', '')

    AuditLog.objects.create(
        action=action,
        actor_type=actor_type,
        actor_id=actor_id or '',
        actor_name=actor_name or '',
        object_type=object_type or '',
        object_id=object_id or '',
        ip_address=ip_address,
        user_agent=user_agent,
        message=message or '',
        timestamp=timezone.now()
    )


def send_parent_notification_email(student, remark_types, staff_name):
    """
    Send email notification to parent about student discipline remarks.
    
    Args:
        student: Student object
        remark_types: List of remark type display names
        staff_name: Name of staff who recorded the remarks
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    import logging
    from django.template.loader import render_to_string
    from django.utils.html import strip_tags
    from django.core.mail import EmailMultiAlternatives

    logger = logging.getLogger(__name__)

    try:
        # Get parent email from student's personal info
        parent_email = None
        if hasattr(student, 'personalinfo') and student.personalinfo:
            parent_email = student.personalinfo.parent_email
        
        if not parent_email:
            logger.warning(f"No parent email found for student {student.roll_number}")
            return False
        
        # Prepare email content
        subject = f"Student Discipline Notification - {student.student_name}"
        
        # Context for the template
        context = {
            'student_name': student.student_name,
            'roll_number': student.roll_number,
            'program': student.program_level,
            'semester': student.current_semester,
            'remark_types': remark_types,
            'date': timezone.now().strftime('%d-%m-%Y'),
            'staff_name': staff_name,
        }

        # Render HTML content
        html_content = render_to_string('emails/student_remark_notification.html', context)
        # Create plain text alternative
        text_content = strip_tags(html_content)
        
        # Create Email object
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[parent_email]
        )
        email.attach_alternative(html_content, "text/html")
        
        # Send
        email.send(fail_silently=False)
        
        logger.info(f"Email sent successfully to {parent_email}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        return False

def send_attendance_deficit_email(student, month_name, percentage, total_hours, attended_hours, staff_name):
    """
    Send low attendance alert email.
    """
    import logging
    from django.template.loader import render_to_string
    from django.utils.html import strip_tags
    from django.core.mail import EmailMultiAlternatives

    logger = logging.getLogger(__name__)

    try:
        parent_email = None
        if hasattr(student, 'personalinfo') and student.personalinfo:
            parent_email = student.personalinfo.parent_email
        
        if not parent_email:
            return False

        subject = f"Low Attendance Alert - {student.student_name} - {month_name}"
        
        context = {
            'student_name': student.student_name,
            'roll_number': student.roll_number,
            'program': student.program_level,
            'semester': student.current_semester,
            'month_name': month_name,
            'percentage': percentage,
            'total_hours': total_hours,
            'attended_hours': attended_hours,
            'staff_name': staff_name,
        }

        html_content = render_to_string('emails/attendance_deficit_notification.html', context)
        text_content = strip_tags(html_content)

        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[parent_email]
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)
        return True

    except Exception as e:
        logger.error(f"Error sending attendance email: {e}")
        return False

# --- Push Notification Helper ---
def send_push_notification(student, title, body, url=None):
    """
    Sends a web push notification to a specific student using their roll number group.
    """
    try:
        from webpush import send_group_notification
        
        group_name = f"student_{student.roll_number}"
        payload = {
            "head": title,
            "title": title, # Redundant key for compatibility with some Service Workers
            "body": body,
            "icon": "https://res.cloudinary.com/deocom5lr/image/upload/v1754117176/annamalai_kuoh1j.png", 
            "url": url if url else "/students/dashboard/"
        }
        # TTL 86400 = 24 hours
        send_group_notification(group_name=group_name, payload=payload, ttl=86400)
        return True
    except Exception as e:
        print(f"Push Notification Failed for {student.roll_number}: {e}")
        return False

def send_staff_notification(staff, title, body, url=None):
    """
    Sends a web push notification to a specific staff member.
    """
    try:
        from webpush import send_group_notification
        
        group_name = f"staff_{staff.staff_id}"
        payload = {
            "head": title,
            "title": title,
            "body": body,
            "icon": "https://res.cloudinary.com/deocom5lr/image/upload/v1754117176/annamalai_kuoh1j.png",
            "url": url if url else "/staffs/"
        }
        send_group_notification(group_name=group_name, payload=payload, ttl=86400)
        return True
    except Exception as e:
        print(f"Push Notification Failed for Staff {staff.staff_id}: {e}")
        return False
