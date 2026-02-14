from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.contrib import messages
from django.db.models import Q, Count, F
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required
from functools import wraps
import datetime
import csv
import json
import logging
from django.views.decorators.http import require_http_methods, require_POST

logger = logging.getLogger(__name__)

from .models import (
    Student, PersonalInfo, BankDetails, AcademicHistory, DiplomaDetails, UGDetails, PGDetails, PhDDetails,
    ScholarshipInfo, StudentDocuments, OtherDetails, Caste, StudentMarks, StudentAttendance,
    StudentSkill, StudentProject, LeaveRequest, StudentGPA, BonafideRequest
)
from . import ai_utils
from django.template.loader import get_template
from xhtml2pdf import pisa
# Import the caste data for the API
from .caste_data import CASTE_DATA
from .forms import (
    StudentForm, PersonalInfoForm, BankDetailsForm, AcademicHistoryForm,
    DiplomaDetailsForm, UGDetailsForm, PGDetailsForm, PhDDetailsForm,
    ScholarshipInfoForm, StudentDocumentsForm, OtherDetailsForm,
    StudentSkillForm, StudentProjectForm, LeaveRequestForm
)
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.conf import settings
import os


# --- Custom Decorator for Session-Based Login ---
def student_login_required(view_func):
    """
    Custom decorator to check if a student is logged in via session.
    If not, redirects to the login page.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if 'student_roll_number' not in request.session:
            return redirect('student_login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


from staffs.models import News

def prevhome(request): 
    # Redirect logged-in students directly to dashboard
    # if 'student_roll_number' in request.session:
    #    return redirect('student_dashboard')
    
    
    # Redirect logged-in staff directly to dashboard
    # if 'staff_id' in request.session:
    #    return redirect('staffs:staff_dashboard')

    # --- Mobile App Redirection Logic ---
    # 1. Detect if coming from TWA (Mobile App)
    if request.GET.get('source') == 'twa':
        request.session['is_mobile_app'] = True

    # 2. If valid mobile app session AND not explicitly asking for landing page
    if request.session.get('is_mobile_app') and not request.GET.get('show_landing'):
        # If logged in as student -> Dashboard
        if 'student_roll_number' in request.session:
            return redirect('student_dashboard')
        # If logged in as staff -> Staff Dashboard
        elif 'staff_id' in request.session:
            return redirect('staffs:staff_dashboard')
        # Else -> Login
        else:
            return redirect('student_login')
    # ------------------------------------
    
    # Fetch public news for the home page
    today = timezone.now().date()
    news_list = News.objects.filter(
        Q(is_active=True) & 
        (Q(start_date__isnull=True) | Q(start_date__lte=today)) & 
        (Q(end_date__isnull=True) | Q(end_date__gte=today))
    ).order_by('-date', '-id')
    return render(request, 'prevhome.html', {'news_list': news_list})



def registration_success(request): 
    return render(request, 'success.html')

def help_and_support(request):
    return render(request, 'studhelp.html')

from staffs.models import ExamSchedule, Timetable

def exam_timetable(request):
    if 'student_roll_number' not in request.session:
        return redirect('student_login')
    
    student = Student.objects.get(roll_number=request.session['student_roll_number'])
    schedule = ExamSchedule.objects.filter(semester=student.current_semester).order_by('date', 'session')
    
    return render(request, 'student_exam_schedule.html', {
        'student': student,
        'schedule': schedule
    })

def class_timetable(request):
    if 'student_roll_number' not in request.session:
        return redirect('student_login')
        
    student = Student.objects.get(roll_number=request.session['student_roll_number'])
    entries = Timetable.objects.filter(semester=student.current_semester)
    
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    timetable_data = {day: [None]*7 for day in days}
    
    for entry in entries:
        if 1 <= entry.period <= 7:
             timetable_data[entry.day][entry.period-1] = entry

    timetable_rows = []
    for day in days:
        timetable_rows.append((day, timetable_data[day]))
    
    return render(request, 'student_class_timetable.html', {
        'student': student,
        'timetable_rows': timetable_rows
    })
def service_unavailable(request):
    return render(request, 'service.html')


# --- API Views ---
def get_caste_data_api(request):
    """API to provide the initial caste data to the registration form."""
    return JsonResponse(CASTE_DATA)

@csrf_exempt
def register_student(request):
    """API view to handle the student profile completion (registration) form submission."""
    # Strict Session Check
    if 'student_roll_number' not in request.session:
         return JsonResponse({'error': 'Authentication required. Please log in.'}, status=401)

    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method is allowed'}, status=405)

    try:
        roll_number = request.session['student_roll_number']
        student = Student.objects.get(roll_number=roll_number)
        
        data = request.POST
        files = request.FILES
        
        # Helper to get instance or None (or create empty if OneToOne is strictly required to exist, but Forms handle None/New fine)
        # However, for Updates, we MUST pass instance if we want to update.
        # Since we use OneToOne, we can check if related obj exists.
        
        def get_instance(model_class):
            try:
                return model_class.objects.get(student=student)
            except model_class.DoesNotExist:
                return None

        # 1. Initialize all forms with instances
        student_form = StudentForm(data, instance=student)
        
        # Special check for password match is inside StudentForm.clean()
        # StudentForm expects 'password' field.

        personal_form = PersonalInfoForm(data, instance=get_instance(PersonalInfo))
        bank_form = BankDetailsForm(data, instance=get_instance(BankDetails))
        docs_form = StudentDocumentsForm(data, files, instance=get_instance(StudentDocuments))
        other_form = OtherDetailsForm(data, instance=get_instance(OtherDetails))

        # Conditional forms
        scholarship_form = ScholarshipInfoForm(data, instance=get_instance(ScholarshipInfo))
        academic_form = AcademicHistoryForm(data, instance=get_instance(AcademicHistory))
        diploma_form = DiplomaDetailsForm(data, instance=get_instance(DiplomaDetails))
        ug_form = UGDetailsForm(data, instance=get_instance(UGDetails))
        pg_form = PGDetailsForm(data, instance=get_instance(PGDetails))
        phd_form = PhDDetailsForm(data, instance=get_instance(PhDDetails))

        # 2. Collect forms to validate
        forms_to_validate = [student_form, personal_form, bank_form, docs_form, other_form, academic_form]
        
        # Add conditional forms based on logic
        if data.get('has_scholarship') == 'yes':
             forms_to_validate.append(scholarship_form)
        
        program_level = data.get('program_level')
        ug_entry_type = data.get('ug_entry_type')
        
        if program_level == 'UG' and ug_entry_type == 'Lateral':
            forms_to_validate.append(diploma_form)
        
        if program_level in ['PG', 'PHD']:
            forms_to_validate.append(ug_form) 
            if program_level == 'PHD':
                forms_to_validate.append(pg_form) 
        
        if program_level == 'PHD':
             forms_to_validate.append(phd_form)

        # 3. Check validity
        if all(f.is_valid() for f in forms_to_validate):
            with transaction.atomic():
                # Save Student (Updates existing)
                s = student_form.save() # This also sets the new password
                s.is_profile_complete = True
                s.is_password_changed = True
                s.save()

                # Handle Caste Logic
                caste_name = data.get('caste')
                if caste_name == 'Other':
                    caste_name = data.get('caste_other')
                
                caste_obj = None
                if caste_name and caste_name not in ['Not Applicable', '']:
                     caste_obj, _ = Caste.objects.get_or_create(name=caste_name)

                # Save Personal Info
                personal = personal_form.save(commit=False)
                personal.student = s
                personal.caste = caste_obj
                personal.save()

                # Save others
                def save_related(form_instance):
                    obj = form_instance.save(commit=False)
                    obj.student = s
                    obj.save()

                save_related(bank_form)
                save_related(docs_form)
                save_related(other_form)
                save_related(academic_form)

                if data.get('has_scholarship') == 'yes':
                    save_related(scholarship_form)
                
                if program_level == 'UG' and ug_entry_type == 'Lateral':
                    save_related(diploma_form)
                
                if program_level in ['PG', 'PHD']:
                    save_related(ug_form)
                    if program_level == 'PHD':
                        save_related(pg_form)
                
                if program_level == 'PHD':
                    save_related(phd_form)
            
            from staffs.utils import log_audit
            log_audit(request, 'update', actor_type='student', actor_id=student.roll_number, actor_name=student.student_name, object_type='Student', object_id=student.roll_number, message=f'Profile completed and password updated')

            print(f"DEBUG: Saved student {s.roll_number}. is_profile_complete={s.is_profile_complete}")
            return JsonResponse({'message': 'Profile Completed Successfully! Redirecting to Dashboard...'})
        
        else:
            # Collect and format errors
            error_messages = []
            for f in forms_to_validate:
                for field, errors in f.errors.items():
                    # For student form, we might get 'Roll Number already exists' if logic wasn't fixed, but we fixed forms.py
                    for error in errors:
                        error_messages.append(f"{field}: {error}")
            
            return JsonResponse({'error': " | ".join(error_messages)}, status=400)

    except Exception as e:
        print(f"Error during registration: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': f'An error occurred: {str(e)}'}, status=400)


# --- Authentication and Dashboard Views ---
# --- Authentication and Dashboard Views ---
def stdlogin(request):
    if request.method == 'POST':
        roll_number = request.POST.get('roll_number')
        password_from_form = request.POST.get('password')
        try:
            student = Student.objects.get(roll_number=roll_number)
            # Use the secure check_password method from your model
            if student.check_password(password_from_form):
                # Clear any existing staff session to prevent dual login
                if 'staff_id' in request.session:
                    del request.session['staff_id']
                
                request.session['student_roll_number'] = student.roll_number
                from staffs.utils import log_audit
                
                # Check if profile is complete - DEPRECATED: Redirecting inside dashboard now
                # if not student.is_profile_complete:
                #      return redirect('stdregister')
                
                log_audit(request, 'login', actor_type='student', actor_id=student.roll_number, actor_name=student.student_name, message='Student logged in')
                return redirect('student_dashboard')
            else:
                error = "Invalid credentials."
        except Student.DoesNotExist:
            error = "Invalid credentials."
        return render(request, 'stdlogin.html', {'error': error})
    return render(request, 'stdlogin.html')

@student_login_required
def stdregister(request): 
    # This is now the "Complete Profile" page
    roll_number = request.session.get('student_roll_number')
    student = get_object_or_404(Student, roll_number=roll_number)
    
    # Helper to safely get related objects
    def get_related_or_none(model_class, student_obj):
        try:
            return model_class.objects.get(student=student_obj)
        except model_class.DoesNotExist:
            return None

    context = {
        'student': student,
        'personal': get_related_or_none(PersonalInfo, student),
        'bank': get_related_or_none(BankDetails, student),
        'docs': get_related_or_none(StudentDocuments, student),
        'other': get_related_or_none(OtherDetails, student),
        'scholarship': get_related_or_none(ScholarshipInfo, student),
        'academic': get_related_or_none(AcademicHistory, student),
        'diploma': get_related_or_none(DiplomaDetails, student),
        'ug': get_related_or_none(UGDetails, student),
        'pg': get_related_or_none(PGDetails, student),
        'phd': get_related_or_none(PhDDetails, student),
    }

    return render(request, 'stdregister.html', context)

from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required

#@never_cache
#@login_required#(login_url='student_login')
@student_login_required
def student_dashboard(request):
    roll_number = request.session.get('student_roll_number')
    try:
        student = Student.objects.get(roll_number=roll_number)
    except Student.DoesNotExist:
        # Session could be stale or invalid
        request.session.flush()
        return redirect('student_login')
    
    # helper to safely get related objects
    from staffs.models import News
    def get_related_or_none(model_class, student_obj):
        try:
            return model_class.objects.get(student=student_obj)
        except model_class.DoesNotExist:
            return None

    # Fetch News
    # Fetch News
    today = timezone.now().date()
    news_list = News.objects.filter(
        Q(is_active=True) & 
        Q(target__in=['All', 'Student']) &
        (Q(start_date__isnull=True) | Q(start_date__lte=today)) & 
        (Q(end_date__isnull=True) | Q(end_date__gte=today))
    ).order_by('-date', '-id')

    # Calculate Attendance (Current Semester Only)
    total_classes = StudentAttendance.objects.filter(student=student, subject__semester=student.current_semester).count()
    present_classes = StudentAttendance.objects.filter(student=student, subject__semester=student.current_semester, status='Present').count()
    attendance_percentage = 0
    if total_classes > 0:
        attendance_percentage = round((present_classes / total_classes) * 100, 1)

    # Fetch GPA Data for Chart
    gpa_records = list(StudentGPA.objects.filter(student=student).order_by('semester'))
    
    # Check if current semester is in gpa_records
    existing_sems = [r.semester for r in gpa_records]
    if student.current_semester not in existing_sems:
        # Fetch current semester data manually
        from staffs.models import Subject
        from students.models import StudentMarks
        
        current_subs = Subject.objects.filter(semester=student.current_semester)
        subject_data = []
        for sub in current_subs:
            # Calculate Subject Attendance
            sub_total = StudentAttendance.objects.filter(student=student, subject=sub).count()
            sub_present = StudentAttendance.objects.filter(student=student, subject=sub, status='Present').count()
            sub_attn = round((sub_present / sub_total) * 100, 1) if sub_total > 0 else 0

            try:
                marks = StudentMarks.objects.get(student=student, subject=sub)
                subject_data.append({
                    'code': sub.code,
                    'name': sub.name,
                    'credits': sub.credits,
                    'test1_marks': marks.test1_marks,
                    'test2_marks': marks.test2_marks,
                    'internal_marks': marks.internal_marks,
                    'attendance_percentage': sub_attn,
                    'grade': 'N/A' # Not generated yet
                })
            except StudentMarks.DoesNotExist:
                subject_data.append({
                    'code': sub.code,
                    'name': sub.name,
                    'credits': sub.credits,
                    'attendance_percentage': sub_attn, 
                    'grade': 'N/A'
                })
        
        if subject_data:
            # Append a dict that mimics the structure needed by the template
            gpa_records.append({
                'semester': student.current_semester,
                'gpa': 0.0, # Placeholder
                'subject_data': subject_data
            })

    gpa_labels = [f"Sem {r.semester if isinstance(r, StudentGPA) else r.get('semester')}" for r in gpa_records]
    gpa_data = [r.gpa if isinstance(r, StudentGPA) else 0.0 for r in gpa_records]
    
    # Calculate CGPA
    # Filter only actual StudentGPA objects for calculation
    real_records = [r for r in gpa_records if isinstance(r, StudentGPA)]
    total_points = sum(r.gpa * r.total_credits for r in real_records)
    total_credits = sum(r.total_credits for r in real_records)
    cgpa = round(total_points / total_credits, 2) if total_credits > 0 else 0.0

    # Skills & Projects (New)
    skills = student.skills.all()
    projects = student.projects.all()

    # Leave Requests (New Widget)
    from students.models import LeaveRequest
    recent_leaves = LeaveRequest.objects.filter(student=student).order_by('-created_at')[:5]

    # Helper for calendar data
    calendar_data = get_attendance_calendar_data(student)

    context = {
        'student': student,
        'recent_leaves': recent_leaves,
        'news_list': news_list,
        'attendance_percentage': attendance_percentage,
        'gpa_labels': gpa_labels,
        'gpa_data': gpa_data,
        'cgpa': cgpa,
        'gpa_records': gpa_records,  # Added for History View
        'skills': skills,
        'projects': projects,

        'today': timezone.now().strftime('%A'),
        'calendar_data': calendar_data,
        'profile_completion_percentage': calculate_profile_completion(student),
        'is_profile_complete': student.is_profile_complete
    }
    
    # New Logic: If profile is incomplete, show the status page instead of dashboard
    print(f"DEBUG: Dashboard access for {student.roll_number}. is_profile_complete={student.is_profile_complete}")
    if not student.is_profile_complete:
         return render(request, 'student_profile_status.html', context)

    return render(request, 'stddash.html', context)

def calculate_profile_completion(student):
    """
    Calculates the percentage of the profile that is complete.
    Based on key fields in Student and related models.
    """
    total_fields = 0
    filled_fields = 0
    
    # helper
    def check_model_fields(model_instance, fields_to_check):
        nonlocal total_fields, filled_fields
        if not model_instance:
             total_fields += len(fields_to_check)
             return
        
        for field in fields_to_check:
            total_fields += 1
            val = getattr(model_instance, field, None)
            if val and str(val).strip(): # Check for non-empty
                filled_fields += 1
    
    # 1. Student Model (Core)
    check_model_fields(student, ['student_name', 'student_email', 'program_level', 'current_semester'])
    
    # 2. Personal Info
    try:
        p_info = getattr(student, 'personalinfo', None) # OneToOne related name default is lowercase modelname or defined? 
        # Models.py says 'personalinfo' (implied) or we need to check. Usually standard is lowercase.
        # Checking implementation: PersonalInfo.student = models.OneToOneField(..., related_name='personalinfo') (Assumption)
        # Actually standard Django default related_name is 'personalinfo' if class is PersonalInfo.
        # Let's rely on views.py logic using PersonalInfo.objects.get(student=student) usually.
        # But we passed `student` object. Let's try accessor.
        if not p_info:
             p_info = PersonalInfo.objects.filter(student=student).first()
        check_model_fields(p_info, ['date_of_birth', 'gender', 'student_mobile', 'father_name', 'father_mobile', 'present_address'])
    except:
        total_fields += 6 # Punishment for missing model
        
    # 3. Academic History
    try:
         acad = AcademicHistory.objects.filter(student=student).first()
         check_model_fields(acad, ['sslc_percentage', 'sslc_year_of_passing', 'hsc_percentage', 'hsc_year_of_passing'])
    except:
         total_fields += 4

    if total_fields == 0: return 0
    
    percentage = int((filled_fields / total_fields) * 100)
    return min(percentage, 100)

def get_attendance_calendar_data(student):
    """Helper to prepare attendance data for calendar."""
    from .models import StudentAttendance
    all_attendance = StudentAttendance.objects.filter(student=student).select_related('subject')
    calendar_data = {}
    
    for record in all_attendance:
        date_key = record.date.strftime('%Y-%m-%d')
        if date_key not in calendar_data:
            calendar_data[date_key] = {
                'present_count': 0,
                'absent_count': 0,
                'classes': []
            }
        
        calendar_data[date_key]['classes'].append({
            'subject': record.subject.code if record.subject else 'General',
            'status': record.status
        })
        
        if record.status == 'Present':
            calendar_data[date_key]['present_count'] += 1
        else:
            calendar_data[date_key]['absent_count'] += 1
            
    # Finalize colors
    final_calendar_data = {}
    for d, info in calendar_data.items():
        if info['present_count'] == 0 and info['absent_count'] > 0:
             dot_color = 'red' # Fully Absent
        elif info['present_count'] > 0 and info['absent_count'] > 0:
             dot_color = 'orange' # Partial
        else:
             dot_color = 'green' # All Present (or no classes?)
             
        final_calendar_data[d] = {
            'color': dot_color,
            'details': info['classes']
        }
    return final_calendar_data

@student_login_required
def student_profile(request):
    """
    Displays the full profile (bio-data) of the student.
    """
    roll_number = request.session.get('student_roll_number')
    student = get_object_or_404(Student, roll_number=roll_number)
    
    # Copy of the fetching logic from old dashboard
    from staffs.models import News
    def get_related_or_none(model_class, student_obj):
        try:
            return model_class.objects.get(student=student_obj)
        except model_class.DoesNotExist:
            return None

    context = {
        'student': student,
        'diploma': get_related_or_none(DiplomaDetails, student),
        'ug': get_related_or_none(UGDetails, student),
        'pg': get_related_or_none(PGDetails, student),
        'phd': get_related_or_none(PhDDetails, student),
        'other_details': get_related_or_none(OtherDetails, student),
    }
    return render(request, 'student_profile.html', context)


@student_login_required
def student_logout(request):
    roll_number = request.session.get('student_roll_number')
    if roll_number:
        from staffs.utils import log_audit
        log_audit(request, 'logout', actor_type='student', actor_id=roll_number, message='Student logged out')

    request.session.flush()
    try:
        del request.session['student_roll_number']
    except KeyError:
        pass
    return redirect('student_login')

from django.contrib import messages

@student_login_required
def student_editprofile(request):
    roll_number = request.session.get('student_roll_number')
    student = Student.objects.get(roll_number=roll_number)
    
    personal_info, _ = PersonalInfo.objects.get_or_create(student=student)
    student_docs, _ = StudentDocuments.objects.get_or_create(student=student)
    bank_details, _ = BankDetails.objects.get_or_create(student=student)
    other_details, _ = OtherDetails.objects.get_or_create(student=student)

    if request.method == 'POST':
        # Update student email
        student.student_email = request.POST.get('student_email')
        student.save()
        
        # Update personal info - contact numbers and addresses
        personal_info.student_mobile = request.POST.get('student_mobile')
        personal_info.father_mobile = request.POST.get('father_mobile')
        personal_info.mother_mobile = request.POST.get('mother_mobile')
        personal_info.parent_email = request.POST.get('parent_email')
        personal_info.present_address = request.POST.get('present_address')
        personal_info.permanent_address = request.POST.get('permanent_address')
        personal_info.save()
        
        # Update bank details
        bank_details.account_holder_name = request.POST.get('account_holder_name')
        bank_details.account_number = request.POST.get('account_number')
        bank_details.bank_name = request.POST.get('bank_name')
        bank_details.branch_name = request.POST.get('branch_name')
        bank_details.ifsc_code = request.POST.get('ifsc_code')
        bank_details.save()
        
        # Update document uploads
        if 'student_photo' in request.FILES:
            student_docs.student_photo = request.FILES['student_photo']
        if 'aadhaar_card' in request.FILES:
            student_docs.aadhaar_card = request.FILES['aadhaar_card']
        if 'community_certificate' in request.FILES:
            student_docs.community_certificate = request.FILES['community_certificate']
        if 'sslc_marksheet' in request.FILES:
            student_docs.sslc_marksheet = request.FILES['sslc_marksheet']
        if 'hsc_marksheet' in request.FILES:
            student_docs.hsc_marksheet = request.FILES['hsc_marksheet']
        if 'income_certificate' in request.FILES:
            student_docs.income_certificate = request.FILES['income_certificate']
        if 'bank_passbook' in request.FILES:
            student_docs.bank_passbook = request.FILES['bank_passbook']
        if 'driving_license' in request.FILES:
            student_docs.driving_license = request.FILES['driving_license']
        
        student_docs.save()
        
        from staffs.utils import log_audit
        log_audit(request, 'update', actor_type='student', actor_id=student.roll_number, actor_name=student.student_name, object_type='Student', object_id=student.roll_number, message='Updated profile/personal details')

        messages.success(request, 'Your profile has been updated successfully!')
        return redirect('student_dashboard')

    context = {
        'student': student,
        'personalinfo': personal_info,
        'studentdocuments': student_docs,
        'bankdetails': bank_details,
        'otherdetails': other_details,
        'skills': student.skills.all(),
        'projects': student.projects.all(),
    }
    return render(request, 'studedit.html', context)

# --- NEW PASSWORD RESET WORKFLOW (MOBILE & AADHAAR) ---

def password_reset_identify(request):
    """Step 1: User provides their Roll Number."""
    student = None
    if request.method == 'POST':
        roll_number = request.POST.get('roll_number')
        try:
            student = Student.objects.get(roll_number=roll_number)
            request.session['reset_student_pk'] = student.pk
            return redirect('password_reset_verify')
        except Student.DoesNotExist:
            messages.error(request, 'No student found with that Roll Number.')

    return render(request, 'p1.html', {'student': student})


def password_reset_verify(request):
    """Step 2: User verifies with Mobile and Aadhaar numbers OR requests OTP."""
    student_pk = request.session.get('reset_student_pk')
    if not student_pk:
        return redirect('password_reset_identify')

    try:
        student = Student.objects.get(pk=student_pk)
    except Student.DoesNotExist:
        return redirect('password_reset_identify')

    if request.method == 'POST':
        action = request.POST.get('action')
        mobile_number = request.POST.get('student_mobile')

        # --- OPTION 1: Email OTP (Requires Mobile + Email) ---
        if action == 'send_otp':
            email_address = request.POST.get('student_email')
            
            # Validation: Check if Mobile AND Email match
            if (hasattr(student, 'personalinfo') and
                student.personalinfo.student_mobile == mobile_number and 
                student.student_email == email_address):
                
                # Generate OTP
                import random
                otp = str(random.randint(100000, 999999))
                
                # Store in session with expiry
                request.session['reset_otp'] = otp
                request.session['reset_otp_expiry'] = (timezone.now() + datetime.timedelta(minutes=10)).isoformat()
                
                # Send Email
                from django.core.mail import send_mail
                from django.template.loader import render_to_string
                from django.utils.html import strip_tags
                
                # Render HTML content
                html_content = render_to_string('emails/password_reset_email.html', {
                    'otp': otp,
                    'student_name': student.student_name
                })
                plain_message = strip_tags(html_content) # Create text fallback

                try:
                    send_mail(
                            subject = "Password Reset OTP – Annamalai University - IT Department Student Portal",
                            message = plain_message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[student.student_email],
                        html_message=html_content,
                        fail_silently=False,
                    )
                    messages.success(request, f'OTP sent to registered email.')
                except Exception as e:
                    messages.error(request, f'Failed to send email: {str(e)}')
                
                return render(request, 'p2_otp.html', {
                    'email_mask': student.student_email
                })
            else:
                 messages.error(request, 'Mobile Number or Email Address does not match our records.')

        # --- OPTION 2: Legacy Mobile/Aadhaar (Requires Mobile + Aadhaar) ---
        elif action == 'verify_details':
            aadhaar_number = request.POST.get('aadhaar_number')

            if (hasattr(student, 'personalinfo') and
                student.personalinfo.student_mobile == mobile_number and 
                student.personalinfo.aadhaar_number == aadhaar_number):
                
                request.session['reset_verified'] = True
                return redirect('password_reset_confirm')
            else:
                messages.error(request, 'Mobile Number or Aadhaar Number does not match our records.')

    # Pass student to template to display their name
    return render(request, 'p2.html', {'student': student})


def password_reset_otp_verify(request):
    """Step 2.5: Verify the entered OTP."""
    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        session_otp = request.session.get('reset_otp')
        expiry_str = request.session.get('reset_otp_expiry')
        
        if not session_otp or not expiry_str:
            messages.error(request, 'No OTP found or session expired. Please request a new one.')
            return redirect('password_reset_verify') # Redirects back effectively re-rendering p2 or needing logic

        # Check expiry
        expiry_time = datetime.datetime.fromisoformat(expiry_str)       
        if timezone.now() > expiry_time:
            messages.error(request, 'OTP has expired. Please request a new one.')
            return redirect('password_reset_identify') # Or handle better re-flow

        if entered_otp == session_otp:
            # Success
            request.session['reset_verified'] = True
            # clear OTP session
            del request.session['reset_otp']
            del request.session['reset_otp_expiry']
            return redirect('password_reset_confirm')
        else:
            messages.error(request, 'Invalid OTP. Please try again.')
            # Re-render the OTP page
            # We need student email mask again, but student obj is in session PK
            student_pk = request.session.get('reset_student_pk')
            student = Student.objects.get(pk=student_pk)
            return render(request, 'p2_otp.html', {
                 'email_mask': student.student_email
            })
            
    return redirect('password_reset_identify')


def password_reset_confirm(request):
    """Step 3: If verified, the user sets a new password."""
    student_pk = request.session.get('reset_student_pk')
    is_verified = request.session.get('reset_verified')

    if not student_pk or not is_verified:
        return redirect('password_reset_identify')

    try:
        student = Student.objects.get(pk=student_pk)
    except Student.DoesNotExist:
        return redirect('password_reset_identify')

    if request.method == 'POST':
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if not password or password != confirm_password:
            messages.error(request, 'Passwords do not match or are empty.')
            return render(request, 'p3.html', {'student': student})

        student.set_password(password)
        student.save()

        # Cleanup Session
        keys_to_delete = ['reset_student_pk', 'reset_verified', 'reset_otp', 'reset_otp_expiry', 'student_roll_number']
        for key in keys_to_delete:
            if key in request.session:
                del request.session[key]
        
        # Log them in? Or make them log in again.
        # User requested manual login usually safer after reset, but previous code logged them in. 
        # Requirement: "Log them in manually" was in previous code.
        request.session['student_roll_number'] = student.roll_number
        
        messages.success(request, 'Your password has been reset successfully!')
        return redirect('student_login')
        
    return render(request, 'p3.html', {'student': student})


@student_login_required
def student_attendance(request):
    """Displays student's attendance data course-wise."""
    roll_number = request.session.get('student_roll_number')
    try:
        student = Student.objects.get(roll_number=roll_number)
    except Student.DoesNotExist:
        request.session.flush()
        return redirect('student_login')
    
    from staffs.models import Subject
    from .models import StudentAttendance
    
    subjects = Subject.objects.filter(semester=student.current_semester).order_by('code')
    
    theory_data = []
    lab_data = []
    
    # Chart Data Arrays
    chart_labels = []
    chart_present = []
    chart_absent = []
    
    total_classes_overall = 0
    present_total_overall = 0
    
    for subject in subjects:
        attendance_entries = StudentAttendance.objects.filter(
            student=student,
            subject=subject
        )
        total_classes = attendance_entries.count()
        present_count = attendance_entries.filter(status='Present').count()
        absent_count = attendance_entries.filter(status='Absent').count()
        
        if total_classes > 0:
            percentage = (present_count / total_classes) * 100
        else:
            percentage = 0
            
        subject_data = {
            'subject': subject,
            'total_classes': total_classes,
            'present': present_count,
            'absent': absent_count,
            'percentage': round(percentage, 1),
            'status_color': 'success' if percentage >= 75 else ('warning' if percentage >= 65 else 'danger')
        }
        
        if subject.subject_type == 'Theory':
            theory_data.append(subject_data)
        elif subject.subject_type == 'Lab':
            lab_data.append(subject_data)
            
        # Stats accumulation
        total_classes_overall += total_classes
        present_total_overall += present_count

        # Populate Chart Data
        chart_labels.append(subject.code)
        chart_present.append(present_count)
        chart_absent.append(absent_count)
    
    # Combined for charts/legacy support
    attendance_data = theory_data + lab_data

    # Overall Percentage
    if total_classes_overall > 0:
        overall_percentage = (present_total_overall / total_classes_overall) * 100
    else:
        overall_percentage = 0
        
    overall_stats = {
        'total_classes': total_classes_overall,
        'present_count': present_total_overall,
        'overall_percentage': round(overall_percentage, 1),
        'attendance_status': 'Great!' if overall_percentage >= 75 else ('Needs Improvement' if overall_percentage >= 65 else 'Critical')
    }

    # Use the helper for calendar data
    calendar_data = get_attendance_calendar_data(student)
    
    context = {
        'student': student,
        'attendance_data': attendance_data, # Restored for charts
        'theory_data': theory_data,
        'lab_data': lab_data,
        'overall_stats': overall_stats,
        'chart_data': {
            'labels': chart_labels, 
            'present': chart_present,
            'absent': chart_absent
        },
        'calendar_data': calendar_data
    }
    
    return render(request, 'student_attendance.html', context)


@student_login_required
def student_marks(request):
    """Displays student's marks with pre-processed chart data."""
    roll_number = request.session.get('student_roll_number')
    try:
        student = Student.objects.get(roll_number=roll_number)
    except Student.DoesNotExist:
        request.session.flush()
        return redirect('student_login')
    
    from staffs.models import Subject
    from .models import StudentMarks
    
    subjects = Subject.objects.filter(semester=student.current_semester).order_by('code')
    
    marks_data = []
    
    # Chart Data Arrays
    radar_labels = []
    radar_test1 = []
    radar_test2 = []
    radar_internal = []
    
    has_any_data = False
    
    for subject in subjects:
        try:
            marks = StudentMarks.objects.get(student=student, subject=subject)
            
            # Normalize marks (None -> 0 for calculations)
            t1 = marks.test1_marks if marks.test1_marks is not None else 0
            t2 = marks.test2_marks if marks.test2_marks is not None else 0
            internal = marks.internal_marks if marks.internal_marks is not None else 0
            
            has_data = True
            has_any_data = True
            
            marks_data.append({
                'subject': {
                    'name': subject.name,
                    'code': subject.code,
                    'semester': subject.semester
                },
                'test1': marks.test1_marks, # Keep None for display as "-"
                'test2': marks.test2_marks,
                'internal': marks.internal_marks,
                'has_data': True
            })
            
            # Populate Chart Data
            radar_labels.append(subject.code)
            radar_test1.append(t1)
            radar_test2.append(t2)
            radar_internal.append(internal)
            
        except StudentMarks.DoesNotExist:
            marks_data.append({
                'subject': {
                    'name': subject.name,
                    'code': subject.code,
                    'semester': subject.semester
                },
                'test1': None,
                'test2': None,
                'internal': None,
                'has_data': False
            })
            # Still add label for radar to show missing subject gap
            radar_labels.append(subject.code)
            radar_test1.append(0)
            radar_test2.append(0)
            radar_internal.append(0)
    
    # Filter empty charts if essentially no data
    if not has_any_data:
        radar_labels = [] # Prevents empty chart rendering

    context = {
        'student': student,
        'marks_data': marks_data,
        'has_any_data': has_any_data,
        'chart_data': {
            'labels': radar_labels,
            'test1': radar_test1,
            'test2': radar_test2,
            'internal': radar_internal
        }
    }
    
    return render(request, 'student_marks.html', context)


@student_login_required
def export_student_marks_csv(request):
    """Export student marks to CSV."""
    import csv
    from django.http import HttpResponse
    from staffs.models import Subject
    from .models import StudentMarks

    roll_number = request.session.get('student_roll_number')
    student = Student.objects.get(roll_number=roll_number)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="Marks_{student.roll_number}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Subject Code', 'Subject Name', 'Test 1', 'Test 2', 'Internal'])
    
    subjects = Subject.objects.filter(semester=student.current_semester).order_by('code')
    
    for subject in subjects:
        try:
            marks = StudentMarks.objects.get(student=student, subject=subject)
            writer.writerow([
                subject.code,
                subject.name,
                marks.test1_marks if marks.test1_marks is not None else '-',
                marks.test2_marks if marks.test2_marks is not None else '-',
                marks.internal_marks if marks.internal_marks is not None else '-'
            ])
        except StudentMarks.DoesNotExist:
            writer.writerow([subject.code, subject.name, '-', '-', '-'])
            
    return response


@student_login_required
def cgpa_history(request):
    """
    Displays the detailed CGPA history of the student with visualizations and AI insights.
    """
    roll_number = request.session.get('student_roll_number')
    student = get_object_or_404(Student, roll_number=roll_number)

    # Fetch all stored GPA records
    gpa_records = StudentGPA.objects.filter(student=student).order_by('semester')

    # Prepare data for visualizations
    semesters = []
    gpas = []
    cgpas = []
    
    cumulative_points = 0
    cumulative_credits = 0
    
    detailed_history = []
    
    
    # For Analysis
    theory_points = []
    lab_points = []
    
    grade_points_map = {
        'O': 10, 'A+': 9, 'A': 8, 'B+': 7, 'B': 6, 'C': 5, 'RA': 0, 'AB': 0
    }

    for record in gpa_records:
        semesters.append(f"Sem {record.semester}")
        gpas.append(record.gpa)
        
        # Calculate running CGPA
        cumulative_points += (record.gpa * record.total_credits)
        cumulative_credits += record.total_credits
        
        current_cgpa = round(cumulative_points / cumulative_credits, 2) if cumulative_credits > 0 else 0.0
        cgpas.append(current_cgpa)
        
        subjects = record.subject_data if record.subject_data else []
        
        # Collect detailed stats
        for sub in subjects:
            grade = sub.get('grade')
            # Assuming subject code implies type or we just blindly trust specific naming if available
            # In absence of strict type in JSON, we rely on 'subject_type' field if we had it joined.
            # Since we store JSON, let's try to infer or just collect all.
            # For this 'standout' feature, we'll try to guess based on simple heuristic or just general stats.
            
            pts = grade_points_map.get(grade, 0)
            if 'LAB' in sub.get('name', '').upper() or 'PRACTICAL' in sub.get('name', '').upper():
                lab_points.append(pts)
            else:
                theory_points.append(pts)

        detailed_history.append({
            'semester': record.semester,
            'gpa': record.gpa,
            'cgpa': current_cgpa,
            'credits': record.total_credits,
            'subjects': subjects
        })

    # Summary Stats
    if gpas:
        max_gpa = max(gpas)
        min_gpa = min(gpas)
        avg_gpa = round(sum(gpas) / len(gpas), 2)
        latest_cgpa = cgpas[-1] if cgpas else 0.0
    else:
        max_gpa = min_gpa = avg_gpa = latest_cgpa = 0.0

    # --- AI Insights Logic ---
    insights = []
    
    # 1. Trend Analysis
    if len(gpas) >= 3:
        last_3 = gpas[-3:]
        if last_3[0] < last_3[1] < last_3[2]:
            insights.append("Your performance is on a consistent upward trajectory over the last 3 semesters. Keep it up!")
        elif last_3[0] > last_3[1] > last_3[2]:
            insights.append("We've noticed a slight dip in recent semesters. Consider focusing on core subjects.")
        elif max(last_3) - min(last_3) < 0.5:
            insights.append("You demonstrate remarkable consistency in your academic performance.")
    
    # 2. Strength Area
    avg_theory = sum(theory_points)/len(theory_points) if theory_points else 0
    avg_lab = sum(lab_points)/len(lab_points) if lab_points else 0
    
    if avg_lab > avg_theory + 1:
        insights.append("You show exceptional practical skills, consistently scoring higher in Laboratory courses.")
    elif avg_theory > avg_lab + 1:
        insights.append("Your theoretical understanding is your strong suit, outpacing your practical grades.")
    
    # 3. Peak
    if gpas:
        best_sem_idx = gpas.index(max(gpas))
        insights.append(f"Semester {detailed_history[best_sem_idx]['semester']} was your peak performance era so far.")

    if not insights:
        insights.append("Maintain your focus and continue working towards your academic goals.")

    context = {
        'student': student,
        'semesters': semesters,
        'gpas': gpas,
        'cgpas': cgpas,
        'detailed_history': detailed_history,
        'detailed_history': detailed_history,
        'insights': insights,
        'summary': {
            'max_gpa': max_gpa,
            'min_gpa': min_gpa,
            'avg_gpa': avg_gpa,
            'latest_cgpa': latest_cgpa
        }
    }
    return render(request, 'cgpa_history.html', context)

@student_login_required
def export_student_attendance_csv(request):
    """Export student attendance summary to CSV."""
    import csv
    from django.http import HttpResponse
    from staffs.models import Subject
    from .models import StudentAttendance
    
    roll_number = request.session.get('student_roll_number')
    student = Student.objects.get(roll_number=roll_number)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="Attendance_{student.roll_number}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Subject Code', 'Subject Name', 'Total Classes', 'Present', 'Absent', 'Percentage', 'Status'])
    
    subjects = Subject.objects.filter(semester=student.current_semester).order_by('code')
    
    for subject in subjects:
        attendance_entries = StudentAttendance.objects.filter(student=student, subject=subject)
        total = attendance_entries.count()
        present = attendance_entries.filter(status='Present').count()
        absent = attendance_entries.filter(status='Absent').count()
        
        percentage = (present / total * 100) if total > 0 else 0
        percentage_str = f"{percentage:.2f}%"
        
        status = 'Good' if percentage >= 75 else 'Average' if percentage >= 65 else 'Low'
        
        writer.writerow([
            subject.code,
            subject.name,
            total,
            present,
            absent,
            percentage_str,
            status
        ])
            
    return response


@student_login_required
def resume_builder(request):
    roll_number = request.session.get('student_roll_number')
    student = Student.objects.get(roll_number=roll_number)
    
    # Forms
    skill_form = StudentSkillForm()
    project_form = StudentProjectForm()

    if request.method == 'POST':
        if 'add_skill' in request.POST:
            skill_form = StudentSkillForm(request.POST)
            if skill_form.is_valid():
                skill = skill_form.save(commit=False)
                skill.student = student
                skill.save()
                messages.success(request, 'Skill added successfully!')
                return redirect('resume_builder')
        
        elif 'add_project' in request.POST:
            project_form = StudentProjectForm(request.POST)
            if project_form.is_valid():
                project = project_form.save(commit=False)
                project.student = student
                project.save()
                messages.success(request, 'Project added successfully!')
                return redirect('resume_builder')
                
        elif 'delete_skill' in request.POST:
            skill_id = request.POST.get('skill_id')
            StudentSkill.objects.filter(id=skill_id, student=student).delete()
            messages.success(request, 'Skill deleted.')
            return redirect('resume_builder')
            
        elif 'delete_project' in request.POST:
            project_id = request.POST.get('project_id')
            StudentProject.objects.filter(id=project_id, student=student).delete()
            messages.success(request, 'Project deleted.')
            return redirect('resume_builder')

    context = {
        'student': student,
        'skills': student.skills.all(),
        'projects': student.projects.all(),
        'skill_form': skill_form,
        'project_form': project_form,
    }
    return render(request, 'resume_builder.html', context)


@student_login_required
def generate_resume_pdf(request):
    roll_number = request.session.get('student_roll_number')
    student = Student.objects.get(roll_number=roll_number)
    
    # Fetch subjects for coursework section
    from staffs.models import Subject
    subjects = Subject.objects.filter(semester=student.current_semester)
    
    # Check for AI Data in Session
    ai_data = request.session.get('ai_resume_data', None)
    
    # If standard type requested, force ignore AI data
    if request.GET.get('type') == 'standard':
        ai_data = None
    
    # Gather all data
    context = {
        'student': student,
        'personal': getattr(student, 'personalinfo', None),
        'academic': getattr(student, 'academichistory', None),
        'diploma': getattr(student, 'diplomadetails', None),
        'ug': getattr(student, 'ugdetails', None),
        'pg': getattr(student, 'pgdetails', None),
        'phd': getattr(student, 'phddetails', None),
        'skills': student.skills.all(),
        'projects': student.projects.all(),
        'ai_data': ai_data,
        'other': getattr(student, 'otherdetails', None), 
        'coursework': subjects,
    }
    
    # 3. Create PDF
    template_path = 'resume_template.html'
    template = get_template(template_path)
    html = template.render(context)
    
    response = HttpResponse(content_type='application/pdf')
    # Custom filename: Name_rollnumber_Resume.pdf
    filename = f"{student.student_name.replace(' ', '_')}_{student.roll_number}_Resume.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    pisa_status = pisa.CreatePDF(
       html, dest=response
    )
    
    if pisa_status.err:
       return HttpResponse('We had some errors <pre>' + html + '</pre>')
    return response



@require_http_methods(["POST"])
def ai_generate_resume(request):
    """
    Generate AI-enhanced resume content for the logged-in student.
    """
    # 1. Authentication check
    roll_number = request.session.get('student_roll_number')
    if not roll_number:
        return JsonResponse({
            'error': 'Authentication required',
            'message': 'Please log in to generate your resume.'
        }, status=401)
    
    try:
        student = Student.objects.select_related(
            'ugdetails', 'pgdetails', 'phddetails', 'personalinfo'
        ).prefetch_related(
            'skills', 'projects'
        ).get(roll_number=roll_number)
    except Student.DoesNotExist:
        return JsonResponse({
            'error': 'Student not found',
            'message': 'Your student profile could not be found.'
        }, status=404)
    
    # 2. Gather comprehensive student data
    try:
        student_data = _prepare_student_data(student)
    except Exception as e:
        logger.error(f"Error preparing student data for {roll_number}: {str(e)}")
        return JsonResponse({
            'error': 'Data preparation failed',
            'message': 'Unable to prepare your information. Please try again.'
        }, status=500)
    
    # 3. Check if minimum data exists
    if not student_data['department']:
        return JsonResponse({
            'error': 'Incomplete profile',
            'message': 'Please complete your academic information before generating a resume.'
        }, status=400)
    
    # 4. Call AI service
    logger.info(f"Generating AI resume for {student.student_name} ({roll_number})")
    ai_result = ai_utils.generate_resume_content(student_data)
    
    # 5. Handle AI service errors
    if 'error' in ai_result:
        logger.error(f"AI generation failed for {roll_number}: {ai_result['error']}")
        return JsonResponse({
            'error': 'AI generation failed',
            'message': ai_result['error'],
            'fallback': 'You can still download your resume with existing data.'
        }, status=500)
    
    # 6. Store in session with metadata
    request.session['ai_resume_data'] = {
        **ai_result,
        'generated_at': str(timezone.now()),
        'student_name': student.student_name,
        'version': '2.0'
    }
    request.session.modified = True
    
    # 7. Return success with preview data
    return JsonResponse({
        'success': True,
        'message': 'Resume generated successfully!',
        'data': {
            'summary_preview': ai_result.get('summary', '')[:150] + '...',
            'project_count': len(ai_result.get('projects_enhanced', [])),
            'skill_count': len(ai_result.get('hard_skills', [])),
            'generated_at': str(timezone.now())
        }
    })


def _prepare_student_data(student):
    """
    Extract and structure all relevant student data for AI processing.
    """
    # Get skills with proficiency levels
    skills = []
    for skill in student.skills.all():
        skill_str = skill.skill_name
        if skill.proficiency:
            skill_str += f" ({skill.proficiency})"
        skills.append(skill_str)
    
    # Get projects with full details
    projects = []
    for project in student.projects.all():
        projects.append({
            'title': project.title,
            'role': project.role or 'Developer',
            'description': project.description,
            'technologies': project.technologies or '',
            'link': project.link if hasattr(project, 'link') else None
        })
    
    # Determine department/specialization
    department = _get_student_department(student)
    
    return {
        'name': student.student_name,
        'email': student.student_email,
        'degree': student.program_level,
        'department': department,
        'skills': skills,
        'projects': projects,
        'joining_year': student.joining_year if hasattr(student, 'joining_year') else None
    }


def _get_student_department(student):
    """
    Extract department/specialization based on program level.
    """
    if student.program_level == 'UG' and hasattr(student, 'ugdetails'):
        return student.ugdetails.ug_course or 'Engineering'
    elif student.program_level == 'PG' and hasattr(student, 'pgdetails'):
        return student.pgdetails.pg_course or 'Postgraduate Studies'
    elif student.program_level == 'PHD' and hasattr(student, 'phddetails'):
        return student.phddetails.phd_specialization or 'Doctoral Research'
    return 'Engineering'  # Fallback


@require_http_methods(["POST"])
def clear_ai_resume(request):
    """
    Clear AI-generated resume data from session.
    """
    if 'ai_resume_data' in request.session:
        del request.session['ai_resume_data']
        request.session.modified = True
        return JsonResponse({'success': True, 'message': 'AI resume data cleared.'})
    
    return JsonResponse({'success': False, 'message': 'No AI resume data to clear.'})


@student_login_required
def bonafide_list(request):
    """Lists student's bonafide requests."""
    roll_number = request.session.get('student_roll_number')
    student = Student.objects.get(roll_number=roll_number)
    
    requests = BonafideRequest.objects.filter(student=student).order_by('-created_at')

    # Count for visual limit display & check
    now = timezone.now()
    start_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_count = BonafideRequest.objects.filter(
        student=student,
        created_at__gte=start_month
    ).count()
    limit = 2
    
    # Handle New Request Submission (if done from this page)
    # Handle New Request Submission (if done from this page)
    if request.method == 'POST':
        reason = request.POST.get('reason')
        if not reason:
             messages.error(request, 'Reason is required.')
        else:
            # Unlimited requests
            BonafideRequest.objects.create(student=student, reason=reason)
            messages.success(request, 'Bonafide Request submitted successfully to Office!')
            return redirect('bonafide_list')

    return render(request, 'bonafide_list.html', {
        'requests': requests, 
        'student': student,
        'monthly_count': monthly_count,
        'limit': limit
    })

@student_login_required
def download_bonafide(request, request_id):
    """Generates PDF for approved bona fide certificate."""
    roll_number = request.session.get('student_roll_number')
    student = Student.objects.get(roll_number=roll_number)
    
    bonafide = get_object_or_404(BonafideRequest, id=request_id, student=student)
    
    if bonafide.status not in ['Signed', 'Collected', 'Ready for Collection']:
        messages.error(request, 'Certificate is not ready for download yet.')
        return redirect('bonafide_list')
        
    template_path = 'bonafide_certificate_pdf.html'
    context = {
        'bonafide': bonafide,
        'student': student,
        'date': timezone.now()
    }
    
    response = HttpResponse(content_type='application/pdf')
    filename = f"Bonafide_{student.roll_number}_{bonafide.id}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    template = get_template(template_path)
    html = template.render(context)
    
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
       return HttpResponse('We had some errors <pre>' + html + '</pre>')
    return response
    

@require_http_methods(["GET"])
def get_ai_resume_status(request):
    """
    Check if AI-generated resume exists in session.
    """
    ai_data = request.session.get('ai_resume_data')
    
    if ai_data:
        return JsonResponse({
            'exists': True,
            'generated_at': ai_data.get('generated_at'),
            'version': ai_data.get('version'),
            'preview': {
                'summary': ai_data.get('summary', '')[:100] + '...',
                'project_count': len(ai_data.get('projects_enhanced', [])),
                'skill_count': len(ai_data.get('hard_skills', []))
            }
        })
    
    return JsonResponse({'exists': False})

# --- Leave Request Views ---

@student_login_required
def apply_leave(request):
    roll_number = request.session.get('student_roll_number')
    student = Student.objects.get(roll_number=roll_number)
    
    if request.method == 'POST':
        form = LeaveRequestForm(request.POST, request.FILES)
        if form.is_valid():
            leave_request = form.save(commit=False)
            leave_request.student = student
            leave_request.save()
            messages.success(request, 'Leave request submitted successfully!')
            return redirect('leave_history')
    else:
        form = LeaveRequestForm()
    
    return render(request, 'leave_apply.html', {'form': form, 'student': student})

@student_login_required
def leave_history(request):
    roll_number = request.session.get('student_roll_number')
    student = Student.objects.get(roll_number=roll_number)
    
    # Fetch all requests ordered by latest first
    leaves = LeaveRequest.objects.filter(student=student).order_by('-created_at')
    
    return render(request, 'leave_list.html', {'student': student, 'leaves': leaves})

@student_login_required
def request_bonafide(request):
    roll_number = request.session.get('student_roll_number')
    student = Student.objects.get(roll_number=roll_number)

    if request.method == 'POST':
        bonafide_type = request.POST.get('bonafide_type')
        
        # Construct the final reason string based on type
        final_reason = bonafide_type
        
        if bonafide_type == 'Educational Loan':
            bank = request.POST.get('bank_name', '').strip()
            branch = request.POST.get('branch_name', '').strip()
            if bank and branch:
                final_reason = f"Educational Loan - Bank: {bank}, Branch: {branch}"
            else:
                 messages.error(request, 'Bank and Branch names are required for Educational Loan.')
                 return redirect('bonafide_list')
        
        elif bonafide_type == 'Other':
            custom_reason = request.POST.get('custom_reason', '').strip()
            if custom_reason:
                final_reason = custom_reason
            else:
                messages.error(request, 'Please specify the reason.')
                return redirect('bonafide_list')
        
        if not final_reason:
             messages.error(request, 'Reason is required.')
             return redirect('bonafide_list')
        
        # Unlimited requests
        BonafideRequest.objects.create(student=student, reason=final_reason, status='Pending Office Approval')
        messages.success(request, 'Bonafide Request submitted successfully to Office!')
        return redirect('bonafide_list')
    
    return redirect('bonafide_list')

def upload_result(request):
    """Allows students to upload result screenshots for their current semester subjects."""
    if 'student_roll_number' not in request.session:
        return redirect('student_login')
    
    student = Student.objects.get(roll_number=request.session['student_roll_number'])
    
    # Fetch subjects for the student's current semester
    from staffs.models import Subject
    from django.shortcuts import get_object_or_404
    from .models import ResultScreenshot
    from django.contrib import messages
    subjects = Subject.objects.filter(semester=student.current_semester)
    
    if request.method == 'POST':
        subject_id = request.POST.get('subject')
        screenshot = request.FILES.get('screenshot')
        
        if subject_id and screenshot:
            subject = get_object_or_404(Subject, id=subject_id)
            
            # Save the screenshot
            ResultScreenshot.objects.create(student=student, subject=subject, screenshot=screenshot)
            
            messages.success(request, 'Result screenshot uploaded successfully.')
            return redirect('upload_result')
        else:
            messages.error(request, 'Please select a subject and upload a file.')
            
    return render(request, 'student/upload_result.html', {'subjects': subjects})


# --- GPA Calculator Views ---

@student_login_required
def gpa_calculator(request):
    """Renders the GPA Calculator page."""
    roll_number = request.session.get('student_roll_number')
    student = Student.objects.get(roll_number=roll_number)
    
    # Fetch existing GPA records
    gpa_records = StudentGPA.objects.filter(student=student).order_by('semester')
    
    context = {
        'student': student,
        'gpa_records': gpa_records,
        'range_8': range(1, 9)
    }
    return render(request, 'gpa_calculator.html', context)


@student_login_required
@require_http_methods(["POST"])
def extract_grades_api(request):
    """API to extract grades from uploaded image using Gemini."""
    try:
        if 'result_image' not in request.FILES:
            return JsonResponse({'error': 'No image uploaded'}, status=400)
        
        image_file = request.FILES['result_image']
        
        # Call AI Utility (API Key handled by env)
        extraction_result = ai_utils.extract_grades_from_image(image_file)
        
        if 'error' in extraction_result:
            return JsonResponse({'error': extraction_result['error']}, status=500)
            
        return JsonResponse(extraction_result)

    except Exception as e:
        logger.error(f"GPA Extraction Error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@student_login_required
@require_http_methods(["POST"])
def save_gpa_api(request):
    """API to save calculated GPA for a semester."""
    try:
        roll_number = request.session.get('student_roll_number')
        student = Student.objects.get(roll_number=roll_number)
        
        data = json.loads(request.body)
        semester = int(data.get('semester'))
        gpa = float(data.get('gpa'))
        total_credits = float(data.get('total_credits', 0))
        subject_data = data.get('subject_data', []) # Function to store subject details

        # Update or Create Record
        record, created = StudentGPA.objects.update_or_create(
            student=student,
            semester=semester,
            defaults={
                'gpa': gpa,
                'total_credits': total_credits,
                'subject_data': subject_data
            }
        )
        
        return JsonResponse({
            'success': True, 
            'message': f"GPA for Sem {semester} saved successfully!",
            'cgpa': calculate_cgpa(student) # Return updated CGPA
        })

    except Exception as e:
        logger.error(f"Save GPA Error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@student_login_required
@require_http_methods(["GET"])
def get_gpa_data(request):
    """API to fetch stored GPA and Subject Data for a specific semester."""
    try:
        roll_number = request.session.get('student_roll_number')
        student = Student.objects.get(roll_number=roll_number)
        semester = request.GET.get('semester')
        
        if not semester:
            return JsonResponse({'error': 'Semester required'}, status=400)

        record = StudentGPA.objects.filter(student=student, semester=semester).first()
        
        if record:
            return JsonResponse({
                'found': True,
                'gpa': record.gpa,
                'total_credits': record.total_credits,
                'subject_data': record.subject_data or []
            })
        else:
            return JsonResponse({'found': False})

    except Exception as e:
        logger.error(f"Fetch GPA Data Error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

def calculate_cgpa(student):
    """Helper to calculate CGPA from stored records."""
    records = StudentGPA.objects.filter(student=student)
    if not records.exists():
        return 0.0
        
    total_points = sum(r.gpa * r.total_credits for r in records)
    total_credits = sum(r.total_credits for r in records)
    
    if total_credits == 0:
        return 0.0
        
    return round(total_points / total_credits, 2)

# --- Skills & Projects APIs ---

@require_POST
@student_login_required
def add_skill_api(request):
    try:
        data = json.loads(request.body)
        skill_name = data.get('skill_name')
        proficiency = data.get('proficiency', 'Intermediate')
        
        if not skill_name:
             return JsonResponse({'success': False, 'error': 'Skill name is required'})

        roll_number = request.session.get('student_roll_number')
        student = Student.objects.get(roll_number=roll_number)
        
        skill = StudentSkill.objects.create(
            student=student, 
            skill_name=skill_name,
            proficiency=proficiency
        )
        return JsonResponse({'success': True, 'id': skill.id})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@require_POST
@student_login_required
def delete_skill_api(request):
    try:
        data = json.loads(request.body)
        skill_id = data.get('skill_id')
        
        roll_number = request.session.get('student_roll_number')
        student = Student.objects.get(roll_number=roll_number)
        
        StudentSkill.objects.filter(id=skill_id, student=student).delete()
        return JsonResponse({'success': True})
    except Exception as e:
         return JsonResponse({'success': False, 'error': str(e)})

# Force Server Reload

@require_POST
@student_login_required
def add_project_api(request):
    try:
        data = json.loads(request.body)
        title = data.get('title')
        description = data.get('description')
        role = data.get('role', '')
        link = data.get('link', '')
        
        if not title or not description:
             return JsonResponse({'success': False, 'error': 'Title and Description are required'})

        roll_number = request.session.get('student_roll_number')
        student = Student.objects.get(roll_number=roll_number)
        
        project = StudentProject.objects.create(
            student=student, 
            title=title,
            description=description,
            role=role,
            project_link=link
        )
        return JsonResponse({'success': True, 'id': project.id})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@require_POST
@student_login_required
def delete_project_api(request):
    try:
        data = json.loads(request.body)
        project_id = data.get('project_id')
        
        roll_number = request.session.get('student_roll_number')
        student = Student.objects.get(roll_number=roll_number)
        
        StudentProject.objects.filter(id=project_id, student=student).delete()
        return JsonResponse({'success': True})
    except Exception as e:
         return JsonResponse({'success': False, 'error': str(e)})