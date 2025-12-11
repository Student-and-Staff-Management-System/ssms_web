from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from functools import wraps

from .models import (
    Student, PersonalInfo, AcademicHistory, DiplomaDetails, UGDetails, PGDetails, 
    PhDDetails, ScholarshipInfo, StudentDocuments, BankDetails, OtherDetails, Caste
)
# Import the caste data for the API
from .caste_data import CASTE_DATA


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

def exam_timetable(request):
    return render(request, 'timetable.html')
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

    try:
        data = request.POST
        files = request.FILES
        
        # --- Create Student and Hash Password ---
        student = Student(
            roll_number=data.get('roll_number'),
            register_number=data.get('register_number'),
            student_name=data.get('student_name'),
            student_email=data.get('student_email'),
            program_level=data.get('program_level'),
            ug_entry_type=data.get('ug_entry_type') if data.get('program_level') == 'UG' else '',
            current_semester=data.get('current_semester') or 1  # Add semester, default to 1
        )
        # Use the secure password setting method from your model
        student.set_password(data.get('password')) 
        # The student object is now saved with a hashed password.

        # --- FIX: CORRECTLY HANDLE CASTE FOREIGN KEY ---
        caste_name = data.get('caste')
        caste_obj = None  # Default to None

        if caste_name and caste_name not in ['Other', 'Not Applicable', '']:
            # Find the Caste object by its NAME, not its ID.
            # This is the direct fix for the error in your screenshot.
            caste_obj, created = Caste.objects.get_or_create(name=caste_name)
        # --- END OF FIX ---

        PersonalInfo.objects.create(
            student=student,
            caste=caste_obj,  # Use the object we found, not the name string
            caste_other=data.get('caste_other'),
            emis_id=data.get('emis_id'),
            umis_id=data.get('umis_id'),
            abc_id=data.get('abc_id'),
            blood_group=data.get('blood_group'),
            date_of_birth=data.get('date_of_birth') or None,
            gender=data.get('gender'),
            community=data.get('community'),
            religion=data.get('religion'),
            aadhaar_number=data.get('aadhaar_number'), 
            permanent_address=data.get('permanent_address'),
            present_address=data.get('present_address'),
            student_mobile=data.get('student_mobile'),
            father_name=data.get('father_name'),
            father_occupation=data.get('father_occupation'),
            father_mobile=data.get('father_mobile'),
            mother_name=data.get('mother_name'),
            mother_occupation=data.get('mother_occupation'),
            mother_mobile=data.get('mother_mobile'),
            parent_annual_income=data.get('parent_annual_income') or None,
            has_scholarship=data.get('has_scholarship') == 'yes'
            # etc...
        )

        BankDetails.objects.create(
            student=student, 
            account_holder_name=data.get('account_holder_name'),
            account_number=data.get('account_number'),
            bank_name=data.get('bank_name'), 
            branch_name=data.get('branch_name'),
            ifsc_code=data.get('ifsc_code'),
        )
        


        if data.get('has_scholarship') == 'yes':
            ScholarshipInfo.objects.create(
                student=student,
                is_first_graduate='is_first_graduate' in data,
                sch_bcmbc='sch_bcmbc' in data, sch_postmetric='sch_postmetric' in data,
                sch_pm='sch_pm' in data, sch_govt='sch_govt' in data,
                sch_pudhumai='sch_pudhumai' in data, sch_tamizh='sch_tamizh' in data,
                sch_private='sch_private' in data,
                private_scholarship_name=data.get('private_scholarship_name')
            )

        AcademicHistory.objects.create(
            student=student, 
            sslc_register_number=data.get('sslc_register_number'),
            sslc_percentage=data.get('sslc_percentage') or None, 
            sslc_year_of_passing=data.get('sslc_year_of_passing'),
            sslc_school_name=data.get('sslc_school_name'), 
            sslc_school_address=data.get('sslc_school_address'),
            hsc_register_number=data.get('hsc_register_number'),
            hsc_percentage=data.get('hsc_percentage') or None, 
            hsc_year_of_passing=data.get('hsc_year_of_passing'),
            hsc_school_name=data.get('hsc_school_name'), 
            hsc_school_address=data.get('hsc_school_address'),
        )

        program_level = data.get('program_level')
        
        if program_level == 'UG' and data.get('ug_entry_type') == 'Lateral':
            DiplomaDetails.objects.create(
                student=student, 
                diploma_register_number=data.get('diploma_register_number'), 
                diploma_percentage=data.get('diploma_percentage') or None, 
                diploma_year_of_passing=data.get('diploma_year_of_passing'), 
                diploma_college_name=data.get('diploma_college_name'), 
                diploma_college_address=data.get('diploma_college_address')
            )

        if program_level in ['PG', 'PHD']:
            UGDetails.objects.create(student=student, ug_course=data.get('ug_course'), ug_university=data.get('ug_university'), ug_ogpa=data.get('ug_ogpa') or None, ug_year_of_passing=data.get('ug_year_of_passing'))
        
        if program_level in ['PG', 'PHD']:
             PGDetails.objects.create(student=student, pg_course=data.get('pg_course'), pg_university=data.get('pg_university'), pg_ogpa=data.get('pg_ogpa') or None, pg_year_of_passing=data.get('pg_year_of_passing'))
        
        if program_level == 'PHD':
            PhDDetails.objects.create(student=student, phd_specialization=data.get('phd_specialization'), phd_university=data.get('phd_university'), phd_year_of_joining=data.get('phd_year_of_joining'))

        StudentDocuments.objects.create(
            student=student, student_photo=files.get('student_photo'), student_id_card=files.get('student_id_card'),
            community_certificate=files.get('community_certificate'), aadhaar_card=files.get('aadhaar_card'),
            first_graduate_certificate=files.get('first_graduate_certificate'), sslc_marksheet=files.get('sslc_marksheet'),
            hsc_marksheet=files.get('hsc_marksheet'), income_certificate=files.get('income_certificate'),
            bank_passbook=files.get('bank_passbook'), driving_license=files.get('driving_license'),
        )
        
        OtherDetails.objects.create(
            student=student, ambition=data.get('ambition'), role_model=data.get('role_model'),
            hobbies=data.get('hobbies'), identification_marks=data.get('identification_marks'),
        )

  

        return JsonResponse({'message': 'Registration successful!'}, status=201)

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
