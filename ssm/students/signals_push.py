from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from .models import BonafideRequest, LeaveRequest
from webpush import send_user_notification

@receiver(pre_save, sender=BonafideRequest)
def store_previous_status_bonafide(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_instance = BonafideRequest.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
        except BonafideRequest.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None

@receiver(post_save, sender=BonafideRequest)
def notify_bonafide_status_change(sender, instance, created, **kwargs):
    if created:
        return # Don't notify on creation (usually pending)
    
    old_status = getattr(instance, '_old_status', None)
    new_status = instance.status
    
    if old_status != new_status:
        # Try to resolve Django User from Student
        # Attempt 1: Direct attribute
        user = getattr(instance.student, 'user', None)
        
        # Attempt 2: Lookup by username (assuming roll_number == username)
        if not user:
            from django.contrib.auth.models import User
            user = User.objects.filter(username=instance.student.roll_number).first()

        if not user:
            print(f"WebPush: No Django User found for student {instance.student.roll_number}. Notification skipped.")
            return

        payload = {
            "head": "Bonafide Request Update",
            "body": f"Your request status has changed to: {new_status}",
            "icon": "/static/imgs/annamalai.png",
            "url": "/student/bonafide/" # Adjust URL as needed
        }
        
        try:
            send_user_notification(user=user, payload=payload, ttl=1000)
        except Exception as e:
            print(f"Failed to send push notification: {e}")

@receiver(pre_save, sender=LeaveRequest)
def store_previous_status_leave(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_instance = LeaveRequest.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
        except LeaveRequest.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None

@receiver(post_save, sender=LeaveRequest)
def notify_leave_status_change(sender, instance, created, **kwargs):
    if created:
        return

    old_status = getattr(instance, '_old_status', None)
    new_status = instance.status

    if old_status != new_status:
        # Try to resolve Django User from Student
        user = getattr(instance.student, 'user', None)
        
        if not user:
            from django.contrib.auth.models import User
            user = User.objects.filter(username=instance.student.roll_number).first()

        if not user:
            print(f"WebPush: No Django User found for student {instance.student.roll_number}. Notification skipped.")
            return

        payload = {
            "head": "Leave Request Update",
            "body": f"Your leave request status is now: {new_status}",
            "icon": "/static/imgs/annamalai.png",
            "url": "/student/leave/history/" 
        }

        try:
            send_user_notification(user=user, payload=payload, ttl=1000)
        except Exception as e:
            print(f"Failed to send push notification: {e}")


@receiver(pre_save)
def auto_compress_all_uploaded_files(sender, instance, **kwargs):
    """
    Globally intercept saves for all models in 'students' and 'staffs' apps.
    Automatically compress any newly uploaded image or PDF files on the fly.
    """
    if instance._meta.app_label in ['students', 'staffs']:
        from django.db.models import FileField
        from django.core.files.uploadedfile import UploadedFile
        from ssm.validators import compress_file

        for field in instance._meta.get_fields():
            if isinstance(field, FileField):
                file_attr = getattr(instance, field.name)
                # Check if it's a new upload (isinstance of UploadedFile)
                if file_attr and hasattr(file_attr, 'file') and isinstance(file_attr.file, UploadedFile):
                    compress_file(file_attr)

