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
import logging
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)

from .models import (
    Student, PersonalInfo, BankDetails, AcademicHistory, DiplomaDetails, UGDetails, PGDetails, PhDDetails,
    ScholarshipInfo, StudentDocuments, OtherDetails, Caste, StudentMarks, StudentAttendance,
    StudentSkill, StudentProject, LeaveRequest
)
from . import ai_utils
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


def prevhome(request): 
    return render(request, 'prevhome.html')

def stdregister(request): 
    return render(request, 'stdregister.html')

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
    """API view to handle the student registration form submission."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method is allowed'}, status=405)

    # Validation via Django Forms
    try:
        data = request.POST
        files = request.FILES
        
        # 1. Initialize all forms
        student_form = StudentForm(data)
        personal_form = PersonalInfoForm(data)
        bank_form = BankDetailsForm(data)
        docs_form = StudentDocumentsForm(data, files)
        other_form = OtherDetailsForm(data)

        # Conditional forms
        scholarship_form = ScholarshipInfoForm(data)
        academic_form = AcademicHistoryForm(data)
        diploma_form = DiplomaDetailsForm(data)
        ug_form = UGDetailsForm(data)
        pg_form = PGDetailsForm(data)
        phd_form = PhDDetailsForm(data)

        # 2. Collect forms to validate
        forms_to_validate = [student_form, personal_form, bank_form, docs_form, other_form, academic_form]
        
        # Add conditional forms based on logic similar to original view
        if data.get('has_scholarship') == 'yes':
             forms_to_validate.append(scholarship_form)
        
        program_level = data.get('program_level')
        ug_entry_type = data.get('ug_entry_type')
        
        if program_level == 'UG' and ug_entry_type == 'Lateral':
            forms_to_validate.append(diploma_form)
        
        if program_level in ['PG', 'PHD']:
            forms_to_validate.append(ug_form) # PG students have UG details
            if program_level == 'PHD':
                forms_to_validate.append(pg_form) # PhD students have PG details
        
        if program_level == 'PHD':
             forms_to_validate.append(phd_form)

        # 3. Check validity
        if all(f.is_valid() for f in forms_to_validate):
            with transaction.atomic():
                # Save Student (Root)
                student = student_form.save()

                # Handle Caste Logic (Custom)
                caste_name = data.get('caste')
                if caste_name == 'Other':
                    caste_name = data.get('caste_other')
                
                caste_obj = None
                if caste_name and caste_name not in ['Not Applicable', '']:
                     # Caste is already imported at the top from .models
                     caste_obj, _ = Caste.objects.get_or_create(name=caste_name)

                # Save Personal Info
                personal = personal_form.save(commit=False)
                personal.student = student
                personal.caste = caste_obj
                personal.save()

                # Save others
                def save_related(form_instance):
                    obj = form_instance.save(commit=False)
                    obj.student = student
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
                    if program_level == 'PHD': # See logic note in plan, strictly following request handling
                        save_related(pg_form)
                
                if program_level == 'PHD':
                    save_related(phd_form)

            return JsonResponse({'message': 'Registration successful! Redirecting...'})
        
        else:
            # Collect and format errors
            error_messages = []
            for f in forms_to_validate:
                for field, errors in f.errors.items():
                    for error in errors:
                        error_messages.append(f"{field}: {error}")
            
            return JsonResponse({'error': " | ".join(error_messages)}, status=400)

    except Exception as e:
        print(f"Error during registration: {e}")
        return JsonResponse({'error': f'An error occurred: {str(e)}'}, status=400)


# --- Authentication and Dashboard Views ---
def stdlogin(request):
    if request.method == 'POST':
        roll_number = request.POST.get('roll_number')
        password_from_form = request.POST.get('password')
        try:
            student = Student.objects.get(roll_number=roll_number)
            # Use the secure check_password method from your model
            if student.check_password(password_from_form):
                request.session['student_roll_number'] = student.roll_number
                return redirect('student_dashboard')
            else:
                error = "Invalid credentials."
        except Student.DoesNotExist:
            error = "Invalid credentials."
        return render(request, 'stdlogin.html', {'error': error})
    return render(request, 'stdlogin.html')

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
    return render(request, 'stddash.html', context)

@student_login_required
def student_logout(request):
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

        messages.success(request, 'Your profile has been updated successfully!')
        return redirect('student_dashboard')

    context = {
        'student': student,
        'personalinfo': personal_info,
        'studentdocuments': student_docs,
        'bankdetails': bank_details,
        'otherdetails': other_details,
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
    """Step 2: User verifies with Mobile and Aadhaar numbers."""
    student_pk = request.session.get('reset_student_pk')
    if not student_pk:
        return redirect('password_reset_identify')

    try:
        student = Student.objects.get(pk=student_pk)
    except Student.DoesNotExist:
        return redirect('password_reset_identify')

    if request.method == 'POST':
        mobile_number = request.POST.get('student_mobile')
        aadhaar_number = request.POST.get('aadhaar_number')

        if (hasattr(student, 'personalinfo') and
            student.personalinfo.student_mobile == mobile_number and 
            student.personalinfo.aadhaar_number == aadhaar_number):
            
            request.session['reset_verified'] = True
            return redirect('password_reset_confirm')
        else:
            messages.error(request, 'The details you entered do not match our records.')

    # Pass student to template to display their name
    return render(request, 'p2.html', {'student': student})


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

        del request.session['reset_student_pk']
        del request.session['reset_verified']
        
        # Log them in manually by setting the session
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
    
    attendance_data = [] # Keeping this for legacy/chart compatibility if needed
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
            'percentage': round(percentage, 2),
            'status_color': 'success' if percentage >= 75 else 'warning' if percentage >= 65 else 'danger'
        }
        
        # Add to comprehensive list
        attendance_data.append(subject_data)
        
        # Split based on Type
        if subject.subject_type == 'Lab':
            lab_data.append(subject_data)
        else:
            theory_data.append(subject_data)
        
        # Populate Chart Data if classes exist
        if total_classes > 0:
            chart_labels.append(subject.code)
            chart_present.append(present_count)
            chart_absent.append(absent_count)
            
            total_classes_overall += total_classes
            present_total_overall += present_count

    # Overall Statistics
    overall_percentage = 0
    if total_classes_overall > 0:
        overall_percentage = round((present_total_overall / total_classes_overall) * 100, 2)

    context = {
        'student': student,
        'attendance_data': attendance_data, # Kept for backward compat if template uses it for iter
        'theory_data': theory_data,
        'lab_data': lab_data,
        'overall_stats': {
            'total_classes': total_classes_overall,
            'present_count': present_total_overall,
            'overall_percentage': overall_percentage,
            'attendance_status': 'Good' if overall_percentage >= 75 else 'Average' if overall_percentage >= 65 else 'Low'
        },
        'chart_data': {
            'labels': chart_labels,
            'present': chart_present,
            'absent': chart_absent
        }
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
        form = LeaveRequestForm(request.POST)
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

