from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from .models import Staff
from students.models import BonafideRequest

def generate_bonafide_request_pdf(request, request_id):
    """Renders the printable Bonafide Certificate template."""
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')
        
    bonafide_req = get_object_or_404(BonafideRequest, id=request_id)
    student = bonafide_req.student
    
    # Calculate Year from Semester (1,2->I; 3,4->II, etc.)
    import math
    current_year_val = math.ceil(student.current_semester / 2)

    # Calculate Academic Year (e.g., 2025-26)
    from datetime import datetime
    current_date = datetime.now()
    this_year = current_date.year
    if current_date.month > 5: # Academic year starts roughly in June
        academic_year = f"{this_year} - {this_year - 1999}" # 2025 - 26
    else:
        academic_year = f"{this_year - 1} - {this_year - 2000}" # 2024 - 25

    # Semester/Year Roman Numerals
    def to_roman(n):
        val = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
        syb = ["M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I"]
        roman_num = ''
        i = 0
        while n > 0:
            for _ in range(n // val[i]):
                roman_num += syb[i]
                n -= val[i]
            i += 1
        return roman_num

    current_year_roman = to_roman(current_year_val)
    current_semester_roman = to_roman(student.current_semester)
    
    # Get Father Name safely
    father_name = ""
    try:
        if hasattr(student, 'personalinfo'):
            father_name = student.personalinfo.father_name
    except Exception:
        pass

    context = {
        'student': student,
        'father_name': father_name,
        'bonafide_request': bonafide_req,
        'date': current_date,
        'academic_year': academic_year,
        'current_year_roman': current_year_roman,
        'current_semester_roman': current_semester_roman,
    }
    
    return render(request, 'staff/bonafide/certificate_print.html', context)

def hod_bonafide_list(request):
    """
    HOD View: Lists pending requests. actions: Approve / Reject.
    Strict role checks are initially disabled to ensure access.
    """
    print("DEBUG: Entered hod_bonafide_list")
    if 'staff_id' not in request.session:
        print("DEBUG: No staff_id in session, redirecting to login")
        return redirect('staffs:stafflogin')

    try:
        staff = Staff.objects.get(staff_id=request.session['staff_id'])
        print(f"DEBUG: Staff found: {staff.name} ({staff.role})")
    except Staff.DoesNotExist:
        print("DEBUG: Staff.DoesNotExist")
        return redirect('staffs:stafflogin')

    # POST: Handle Actions
    if request.method == 'POST':
        action = request.POST.get('action')
        req_id = request.POST.get('request_id')
        rejection_reason = request.POST.get('rejection_reason', '')

        bonafide_req = get_object_or_404(BonafideRequest, id=req_id)

        if action == 'approve':
            if bonafide_req.status == 'Pending HOD Approval':
                bonafide_req.status = 'Approved by HOD'
            bonafide_req.save()
            messages.success(request, f"Approved request for {bonafide_req.student.student_name}.")
            # Notify Student
            from .utils import send_push_notification
            send_push_notification(bonafide_req.student, "Bonafide Request Approved ✅", "Your request has been signed by HOD.")
            
            # --- EMAIL NOTIFICATION ---
            try:
                from django.core.mail import send_mail
                from django.conf import settings
                from django.template.loader import render_to_string
                from django.utils.html import strip_tags
                subject = "Bonafide Request Approved"
                message = f"Hello {bonafide_req.student.student_name},\n\nYour Bonafide Request has been signed by the HOD.\n\nLogin to the portal to view the details."
                if bonafide_req.student.student_email:
                    html_message = render_to_string('emails/bonafide_status.html', {'student_name': bonafide_req.student.student_name, 'message': "Your Bonafide Request has been signed by the HOD."})
                    send_mail(subject, strip_tags(message), settings.DEFAULT_FROM_EMAIL, [bonafide_req.student.student_email], html_message=html_message, fail_silently=True)
            except Exception as e:
                print(f"Error sending bonafide email: {e}")
            # ---------------------------
        
        elif action == 'reject':
            bonafide_req.status = 'Rejected'
            bonafide_req.rejection_reason = rejection_reason
            bonafide_req.save()
            messages.warning(request, f"Rejected request for {bonafide_req.student.student_name}.")
            # Notify Student
            from .utils import send_push_notification
            send_push_notification(bonafide_req.student, "Bonafide Request Rejected ❌", f"Reason: {rejection_reason}")
            
            # --- EMAIL NOTIFICATION ---
            try:
                from django.core.mail import send_mail
                from django.conf import settings
                subject = "Bonafide Request Rejected"
                message = f"Hello {bonafide_req.student.student_name},\n\nYour Bonafide Request has been rejected.\n\nReason: {rejection_reason}\n\nLogin to the portal to view the details."
                if bonafide_req.student.student_email:
                    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [bonafide_req.student.student_email], fail_silently=True)
            except Exception as e:
                print(f"Error sending bonafide email: {e}")
            # ---------------------------

        elif action == 'mark_collected':
             bonafide_req.status = 'Collected'
             bonafide_req.save()
             messages.success(request, "Marked as Collected.")
             
             # --- EMAIL NOTIFICATION ---
             try:
                 from django.core.mail import send_mail
                 from django.conf import settings
                 subject = "Bonafide Certificate Collected"
                 message = f"Hello {bonafide_req.student.student_name},\n\nYour Bonafide Certificate has been marked as Collected.\n\nLogin to the portal to view the details."
                 if bonafide_req.student.student_email:
                     send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [bonafide_req.student.student_email], fail_silently=True)
             except Exception as e:
                 print(f"Error sending bonafide email: {e}")
             # ---------------------------

        return redirect('staffs:hod_manage_bonafide')

    # GET: List Data
    pending_requests = BonafideRequest.objects.filter(status__in=['Pending HOD Approval', 'Waiting for HOD Sign']).order_by('-created_at')
    # Approved requests now visible to HOD for printing/issuing
    approved_requests = BonafideRequest.objects.filter(status='Approved by HOD').order_by('-updated_at')
    history_requests = BonafideRequest.objects.exclude(status__in=['Pending HOD Approval', 'Approved by HOD']).order_by('-updated_at')[:20]

    context = {
        'staff': staff,
        'pending_requests': pending_requests,
        'approved_requests': approved_requests,
        'history_requests': history_requests,
    }
    return render(request, 'staff/bonafide/hod_list.html', context)


def office_bonafide_list(request):
    """
    Office View: Lists requests with new workflow:
    Pending -> Waiting for HOD Sign -> Signed -> Collected
    """
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')

    try:
        staff = Staff.objects.get(staff_id=request.session['staff_id'])
    except Staff.DoesNotExist:
        return redirect('staffs:stafflogin')

    # POST: Handle Actions
    if request.method == 'POST':
        action = request.POST.get('action')
        req_id = request.POST.get('request_id')
        rejection_reason = request.POST.get('rejection_reason', '')
        
        # Handle Bulk Print
        # Handle Bulk Print
        if action == 'bulk_print':
             waiting_requests = BonafideRequest.objects.filter(status='Waiting for HOD Sign')
             
             if waiting_requests.exists():
                 from datetime import datetime
                 import math
                 
                 current_date = datetime.now()
                 this_year = current_date.year
                 if current_date.month > 5:
                    base_academic_year = f"{this_year} - {this_year - 1999}"
                 else:
                    base_academic_year = f"{this_year - 1} - {this_year - 2000}"

                 def to_roman(n):
                    val = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
                    syb = ["M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I"]
                    roman_num = ''
                    i = 0
                    while n > 0:
                        for _ in range(n // val[i]):
                            roman_num += syb[i]
                            n -= val[i]
                        i += 1
                    return roman_num

                 bulk_data = []
                 for req in waiting_requests:
                     student = req.student
                     current_year_val = math.ceil(student.current_semester / 2)
                     
                     # Get Father Name safely
                     father_name = ""
                     try:
                         if hasattr(student, 'personalinfo'):
                             father_name = student.personalinfo.father_name
                     except Exception:
                         pass

                     bulk_data.append({
                         'student': student,
                         'bonafide_request': req,
                         'father_name': father_name,
                         'current_year_roman': to_roman(current_year_val),
                         'current_semester_roman': to_roman(student.current_semester),
                         'academic_year': base_academic_year
                     })

                 context = {
                     'bulk_data': bulk_data,
                     'date': current_date
                 }
                 return render(request, 'staff/bonafide/certificate_bulk_print.html', context)
             else:
                 messages.warning(request, "No requests waiting for signature.")
                 return redirect('staffs:office_manage_bonafide')

        # Request-specific actions
        bonafide_req = get_object_or_404(BonafideRequest, id=req_id)

        if action == 'approve':
             # PENDING -> WAITING FOR HOD SIGN
             bonafide_req.status = 'Waiting for HOD Sign'
             bonafide_req.save()
             messages.success(request, f"Approved request for {bonafide_req.student.student_name}. Moved to Waiting List.")
             # Notify Student
             from .utils import send_push_notification
             send_push_notification(bonafide_req.student, "Bonafide Request Update", "Your request is processed and waiting for HOD signature.")
             
             # --- EMAIL NOTIFICATION ---
             try:
                 from django.core.mail import send_mail
                 from django.conf import settings
                 from django.template.loader import render_to_string
                 from django.utils.html import strip_tags
                 subject = "Bonafide Request Update"
                 message = f"Hello {bonafide_req.student.student_name},\n\nYour Bonafide Request has been processed by the Office and is waiting for the HOD's signature.\n\nLogin to the portal to view the details."
                 if bonafide_req.student.student_email:
                     html_message = render_to_string('emails/bonafide_status.html', {'student_name': bonafide_req.student.student_name, 'message': "Your Bonafide Request has been processed by the Office and is waiting for the HOD's signature."})
                     send_mail(subject, strip_tags(message), settings.DEFAULT_FROM_EMAIL, [bonafide_req.student.student_email], html_message=html_message, fail_silently=True)
             except Exception as e:
                 print(f"Error sending bonafide email: {e}")
             # ---------------------------

        elif action == 'reject':
            bonafide_req.status = 'Rejected'
            bonafide_req.rejection_reason = rejection_reason
            bonafide_req.save()
            messages.warning(request, f"Rejected request for {bonafide_req.student.student_name}.")
            # Notify Student
            from .utils import send_push_notification
            send_push_notification(bonafide_req.student, "Bonafide Request Rejected ❌", f"Reason: {rejection_reason}")
            
            # --- EMAIL NOTIFICATION ---
            try:
                from django.core.mail import send_mail
                from django.conf import settings
                subject = "Bonafide Request Rejected"
                message = f"Hello {bonafide_req.student.student_name},\n\nYour Bonafide Request has been rejected.\n\nReason: {rejection_reason}\n\nLogin to the portal to view the details."
                if bonafide_req.student.student_email:
                    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [bonafide_req.student.student_email], fail_silently=True)
            except Exception as e:
                print(f"Error sending bonafide email: {e}")
            # ---------------------------

        elif action == 'mark_signed':
            # WAITING -> SIGNED (Ready for Collection)
            bonafide_req.status = 'Signed'
            bonafide_req.save()
            messages.success(request, "Marked as Signed & Ready for Collection.")
            # Notify Student
            from .utils import send_push_notification
            send_push_notification(bonafide_req.student, "Bonafide Certificate Ready! 📜", "Your certificate is signed and ready for collection.")
            
            # --- EMAIL NOTIFICATION ---
            try:
                from django.core.mail import send_mail
                from django.conf import settings
                from django.template.loader import render_to_string
                from django.utils.html import strip_tags
                subject = "Bonafide Certificate Ready"
                message = f"Hello {bonafide_req.student.student_name},\n\nYour Bonafide Certificate is signed and ready for collection at the Department Office.\n\nLogin to the portal to view the details."
                if bonafide_req.student.student_email:
                    html_message = render_to_string('emails/bonafide_status.html', {'student_name': bonafide_req.student.student_name, 'message': "Your Bonafide Certificate is signed and ready for collection at the Department Office."})
                    send_mail(subject, strip_tags(message), settings.DEFAULT_FROM_EMAIL, [bonafide_req.student.student_email], html_message=html_message, fail_silently=True)
            except Exception as e:
                print(f"Error sending bonafide email: {e}")
            # ---------------------------
        
        elif action == 'mark_collected':
             # SIGNED -> COLLECTED
             bonafide_req.status = 'Collected'
             bonafide_req.save()
             messages.success(request, "Marked as Collected.")
             
             # --- EMAIL NOTIFICATION ---
             try:
                 from django.core.mail import send_mail
                 from django.conf import settings
                 subject = "Bonafide Certificate Collected"
                 message = f"Hello {bonafide_req.student.student_name},\n\nYour Bonafide Certificate has been marked as Collected.\n\nLogin to the portal to view the details."
                 if bonafide_req.student.student_email:
                     send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [bonafide_req.student.student_email], fail_silently=True)
             except Exception as e:
                 print(f"Error sending bonafide email: {e}")
             # ---------------------------

        return redirect('staffs:office_manage_bonafide')

    # GET: List Data
    
    # 1. Pending Approval
    pending_requests = BonafideRequest.objects.filter(status='Pending Office Approval').order_by('created_at')
    
    # 2. Waiting for HOD Sign (Approved by Office, waiting for print/sign)
    # Include 'Approved by HOD' for legacy/transition support if any exists
    waiting_requests = BonafideRequest.objects.filter(status__in=['Waiting for HOD Sign', 'Approved by HOD']).order_by('updated_at')
    
    # 3. Ready for Collection (Signed)
    # Include 'Ready for Collection' for legacy/transition support
    ready_requests = BonafideRequest.objects.filter(status__in=['Signed', 'Ready for Collection']).order_by('updated_at')
    
    # 4. History
    # 4. History (Handovered)
    completed_requests = BonafideRequest.objects.filter(status='Collected').order_by('-updated_at')[:20]
    
    # 5. Rejected History
    rejected_requests = BonafideRequest.objects.filter(status='Rejected').order_by('-updated_at')[:20]

    context = {
        'staff': staff,
        'pending_requests': pending_requests,
        'waiting_requests': waiting_requests,
        'ready_requests': ready_requests,
        'completed_requests': completed_requests,
        'rejected_requests': rejected_requests,
    }
    return render(request, 'staff/bonafide/office_list.html', context)
