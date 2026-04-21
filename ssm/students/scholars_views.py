import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from students.models import (
    Student, ResearchScholarProfile, RACMember, ZerothReview, RCWReview,
    PersonalInfo, UGDetails, PGDetails, StudentDocuments, OtherDetails,
    ScholarshipInfo, ScholarAttendance, LeaveRequest, AcademicHistory
)
from students.forms import LeaveRequestForm
from staffs.models import Staff

def scholar_login(request):
    if request.method == 'POST':
        roll_number = request.POST.get('roll_number')
        password = request.POST.get('password')
        try:
            student = Student.objects.get(roll_number=roll_number, program_level='PHD')
            if student.check_password(password):
                request.session['student_roll_number'] = student.roll_number
                return redirect('scholar_dashboard')
            else:
                return render(request, 'scholars/scholar_login.html', {'error': 'Invalid credentials'})
        except Student.DoesNotExist:
            return render(request, 'scholars/scholar_login.html', {'error': 'Scholar not found'})
    return render(request, 'scholars/scholar_login.html')

def scholar_register_step1(request):
    staff_list = Staff.objects.filter(is_active=True).order_by('name')
    if request.method == 'POST':
        name = request.POST.get('student_name')
        admission_no = request.POST.get('admission_no')
        email = request.POST.get('student_email')
        password = request.POST.get('password')
        scholar_type = request.POST.get('scholar_type')
        admission_date = request.POST.get('admission_date')
        supervisor_id = request.POST.get('supervisor_id')
        admission_order_doc = request.FILES.get('admission_order_doc')

        if Student.objects.filter(roll_number=admission_no).exists():
            messages.error(request, "A student/scholar with this Admission No already exists.")
            return render(request, 'scholars/scholar_register_step1.html', {'staff_list': staff_list})

        # Create basic Student
        student = Student(
            roll_number=admission_no,
            student_name=name,
            student_email=email,
            program_level='PHD',
            is_profile_complete=False
        )
        student.set_password(password)
        student.save()

        # Create Profile
        supervisor = Staff.objects.filter(staff_id=supervisor_id).first() if supervisor_id else None
        ResearchScholarProfile.objects.create(
            student=student,
            scholar_type=scholar_type,
            admission_date=admission_date,
            admission_order_doc=admission_order_doc,
            supervisor=supervisor
        )
        # Empty ZerothReview creation to attach file paths later
        ZerothReview.objects.create(scholar=student)

        request.session['register_roll_number'] = student.roll_number
        return redirect('scholar_register_step2')

    return render(request, 'scholars/scholar_register_step1.html', {'staff_list': staff_list})

def scholar_register_step2(request):
    roll_number = request.session.get('register_roll_number')
    if not roll_number:
        return redirect('scholar_register_step1')
    
    student = get_object_or_404(Student, roll_number=roll_number)

    if request.method == 'POST':
        # Part 2 Registration -> Personal, Parents, UG, PG, Schooling details
        
        # 1. Personal & Parent Info
        PersonalInfo.objects.update_or_create(
            student=student,
            defaults={
                'gender': request.POST.get('gender', ''),
                'date_of_birth': request.POST.get('date_of_birth') or None,
                'student_mobile': request.POST.get('student_mobile', ''),
                'blood_group': request.POST.get('blood_group', ''),
                'aadhaar_number': request.POST.get('aadhaar_number', ''),
                'community': request.POST.get('community', ''),
                'caste_other': request.POST.get('caste_other', ''),
                'present_address': request.POST.get('present_address', ''),
                'permanent_address': request.POST.get('permanent_address', ''),
                'is_hosteler': request.POST.get('is_hosteler') == 'yes',
                'father_name': request.POST.get('father_name', ''),
                'father_mobile': request.POST.get('father_mobile', ''),
                'father_occupation': request.POST.get('father_occupation', ''),
                'mother_name': request.POST.get('mother_name', ''),
                'mother_mobile': request.POST.get('mother_mobile', ''),
                'mother_occupation': request.POST.get('mother_occupation', ''),
                'parent_annual_income': request.POST.get('parent_annual_income') or None,
            }
        )

        # Update PersonalInfo with Caste ForeignKey Logic (Synchronized with UG logic)
        p_info = PersonalInfo.objects.get(student=student)
        caste_name = request.POST.get('caste')
        if caste_name and caste_name not in ['Not Applicable', '']:
            from students.models import Caste
            caste_obj, _ = Caste.objects.get_or_create(name=caste_name)
            p_info.caste = caste_obj
            p_info.save()

        # 2. Academic History (SSLC/HSC)
        AcademicHistory.objects.update_or_create(
            student=student,
            defaults={
                'sslc_school_name': request.POST.get('sslc_school_name', ''),
                'sslc_percentage': request.POST.get('sslc_percentage') or None,
                'sslc_year_of_passing': request.POST.get('sslc_year_of_passing', ''),
                'hsc_school_name': request.POST.get('hsc_school_name', ''),
                'hsc_percentage': request.POST.get('hsc_percentage') or None,
                'hsc_year_of_passing': request.POST.get('hsc_year_of_passing', ''),
            }
        )

        # 3. UG & PG Details
        UGDetails.objects.update_or_create(
            student=student,
            defaults={
                'ug_course': request.POST.get('ug_course', ''),
                'ug_university': request.POST.get('ug_university', ''),
                'ug_year_of_passing': request.POST.get('ug_year_of_passing', ''),
            }
        )
        PGDetails.objects.update_or_create(
            student=student,
            defaults={
                'pg_course': request.POST.get('pg_course', ''),
                'pg_university': request.POST.get('pg_university', ''),
                'pg_year_of_passing': request.POST.get('pg_year_of_passing', ''),
            }
        )

        # 4. Student Documents
        docs, _ = StudentDocuments.objects.get_or_create(student=student)
        if request.FILES.get('student_photo'): docs.student_photo = request.FILES.get('student_photo')
        if request.FILES.get('aadhaar_card'): docs.aadhaar_card = request.FILES.get('aadhaar_card')
        if request.FILES.get('community_certificate'): docs.community_certificate = request.FILES.get('community_certificate')
        if request.FILES.get('sslc_marksheet'): docs.sslc_marksheet = request.FILES.get('sslc_marksheet')
        if request.FILES.get('hsc_marksheet'): docs.hsc_marksheet = request.FILES.get('hsc_marksheet')
        if request.FILES.get('income_certificate'): docs.income_certificate = request.FILES.get('income_certificate')
        if request.FILES.get('bank_passbook'): docs.bank_passbook = request.FILES.get('bank_passbook')
        if request.FILES.get('driving_license'): docs.driving_license = request.FILES.get('driving_license')
        docs.save()

        student.is_profile_complete = True
        student.save()
        
        # Clear session
        if 'register_roll_number' in request.session:
            del request.session['register_roll_number']
            
        messages.success(request, 'Registration complete. Your profile is now 100% complete. Please login.')
        return redirect('scholar_login')

    return render(request, 'scholars/scholar_register_step2.html', {'student': student})

def scholar_dashboard(request):
    roll_number = request.session.get('student_roll_number')
    if not roll_number:
        return redirect('scholar_login')
    
    student = get_object_or_404(Student, roll_number=roll_number, program_level='PHD')
    profile = getattr(student, 'scholar_profile', None)
    zeroth = getattr(student, 'zeroth_review', None)
    
    rac_members = student.rac_members.all()
    rcw_reviews = student.rcw_reviews.all()
    
    # Internal Staff for RAC member dropdown
    staff_list = Staff.objects.filter(is_active=True).order_by('name')

    # Attendance data
    today = datetime.date.today()
    today_attendance = student.scholar_attendance.filter(date=today).first()

    # Full history
    all_attendance = list(student.scholar_attendance.all())
    attendance_history = all_attendance[:30]   # Last 30 for the list

    # Aggregate stats
    total   = len(all_attendance)
    approved = sum(1 for a in all_attendance if a.status == 'Approved')
    rejected = sum(1 for a in all_attendance if a.status == 'Rejected')
    pending  = sum(1 for a in all_attendance if a.status == 'Pending')
    attendance_rate = round((approved / total * 100), 1) if total > 0 else 0

    # Last 30 days timeline for bar chart  (date label + status)
    import json
    timeline_labels = [a.date.strftime('%d %b') for a in reversed(attendance_history)]
    timeline_approved = [1 if a.status == 'Approved' else 0 for a in reversed(attendance_history)]
    timeline_rejected = [1 if a.status == 'Rejected' else 0 for a in reversed(attendance_history)]
    timeline_pending  = [1 if a.status == 'Pending'  else 0 for a in reversed(attendance_history)]

    # Sync with student_profile.html logic (profile completion)
    from .views import get_profile_completion_data
    completion_info = get_profile_completion_data(student)

    context = {
        'student': student,
        'profile': profile,
        'rac_members': rac_members,
        'zeroth': zeroth,
        'rcw_reviews': rcw_reviews,
        'staff_list': staff_list,
        'today_attendance': today_attendance,
        'attendance_history': attendance_history,
        # Stats
        'att_total': total,
        'att_approved': approved,
        'att_rejected': rejected,
        'att_pending': pending,
        'att_rate': attendance_rate,
        # Chart JSON
        'timeline_labels':   json.dumps(timeline_labels),
        'timeline_approved': json.dumps(timeline_approved),
        'timeline_rejected': json.dumps(timeline_rejected),
        'timeline_pending':  json.dumps(timeline_pending),
        # Profile Completion
        'profile_completion_percentage': completion_info['percentage'],
        'profile_missing_fields': completion_info['missing_fields'],
        # Portfolio Counts
        'conf_count': student.scholar_conferences.count(),
        'journ_count': student.scholar_journals.count(),
        'book_count': student.scholar_books.count(),
        'semi_count': student.scholar_seminars.count(),
        'award_count': student.scholar_awards.count(),
    }
    context['portfolio_total'] = context['conf_count'] + context['journ_count'] + context['book_count'] + context['semi_count'] + context['award_count']
    return render(request, 'scholars/scholar_dashboard.html', context)

@require_POST
def scholar_add_rac(request):
    roll_number = request.session.get('student_roll_number')
    if not roll_number:
        return redirect('scholar_login')
    
    student = get_object_or_404(Student, roll_number=roll_number)
    member_type = request.POST.get('member_type') # Internal or External
    
    if member_type == 'Internal':
        staff_id = request.POST.get('staff_id')
        staff = Staff.objects.filter(staff_id=staff_id).first()
        if staff:
            RACMember.objects.create(scholar=student, member_type='Internal', staff=staff)
    elif member_type == 'External':
        name = request.POST.get('external_name')
        designation = request.POST.get('external_designation')
        dept = request.POST.get('external_department')
        if name and dept:
            RACMember.objects.create(
                scholar=student, 
                member_type='External',
                external_name=name,
                external_designation=designation,
                external_department=dept
            )
            
    return redirect('scholar_dashboard')

@require_POST
def scholar_update_zeroth(request):
    roll_number = request.session.get('student_roll_number')
    if not roll_number:
        return redirect('scholar_login')
    
    student = get_object_or_404(Student, roll_number=roll_number)
    zeroth, _ = ZerothReview.objects.get_or_create(scholar=student)
    
    zeroth.tentative_title = request.POST.get('tentative_title', zeroth.tentative_title)
    zeroth.rcw001_subject = request.POST.get('rcw001_subject', zeroth.rcw001_subject)
    zeroth.rcw002_subject = request.POST.get('rcw002_subject', zeroth.rcw002_subject)
    zeroth.rcw003_subject = request.POST.get('rcw003_subject', zeroth.rcw003_subject)
    zeroth.rcw004_subject = request.POST.get('rcw004_subject', zeroth.rcw004_subject)
    
    if request.FILES.get('exam1_marksheet'):
        zeroth.exam1_marksheet = request.FILES.get('exam1_marksheet')
    if request.FILES.get('exam2_marksheet'):
        zeroth.exam2_marksheet = request.FILES.get('exam2_marksheet')
        
    zeroth.save()
    messages.success(request, "Zeroth Review details updated successfully.")
    return redirect('scholar_dashboard')

@require_POST
def scholar_add_rcw(request):
    roll_number = request.session.get('student_roll_number')
    if not roll_number:
        return redirect('scholar_login')
        
    student = get_object_or_404(Student, roll_number=roll_number)
    
    date = request.POST.get('date')
    time = request.POST.get('time')
    progress = request.POST.get('progress')
    document = request.FILES.get('document')
    
    if date and time and progress:
        RCWReview.objects.create(
            scholar=student,
            date=date,
            time=time,
            progress=progress,
            document=document
        )
        messages.success(request, "RCW Review added successfully.")
        
    return redirect('scholar_dashboard')

def scholar_profile(request):
    roll_number = request.session.get('student_roll_number')
    if not roll_number:
        return redirect('scholar_login')
    
    student = get_object_or_404(Student, roll_number=roll_number, program_level='PHD')

    from django.db.models import Sum
    from students.models import (
        AcademicHistory, StudentDocuments, StudentSkill, StudentProject, 
        ResearchScholarProfile, PersonalInfo, UGDetails, PGDetails
    )

    def get_related_or_none(model_class, student_obj):
        try:
            return model_class.objects.get(student=student_obj)
        except model_class.DoesNotExist:
            return None

    # Sync with student_profile.html logic (profile completion)
    from .views import get_profile_completion_data

    completion_info = get_profile_completion_data(student)

    context = {
        'student': student,
        'profile': get_related_or_none(ResearchScholarProfile, student),
        'personalinfo': get_related_or_none(PersonalInfo, student),
        'academichistory': get_related_or_none(AcademicHistory, student),
        'studentdocuments': get_related_or_none(StudentDocuments, student),
        'ug': get_related_or_none(UGDetails, student),
        'pg': get_related_or_none(PGDetails, student),
        'skills': student.skills.all(),
        'projects': student.projects.all(),
        'profile_completion_percentage': completion_info['percentage'],
        'profile_missing_fields': completion_info['missing_fields'],
    }
    return render(request, 'scholars/scholar_profile.html', context)


def scholar_edit_profile(request):
    roll_number = request.session.get('student_roll_number')
    if not roll_number:
        return redirect('scholar_login')

    student = get_object_or_404(Student, roll_number=roll_number, program_level='PHD')
    
    # Sync all student-related models
    personal_info, _ = PersonalInfo.objects.get_or_create(student=student)
    student_docs, _ = StudentDocuments.objects.get_or_create(student=student)
    academic_history, _ = AcademicHistory.objects.get_or_create(student=student)
    ug_details, _ = UGDetails.objects.get_or_create(student=student)
    pg_details, _ = PGDetails.objects.get_or_create(student=student)

    if request.method == 'POST':
        # 1. Update basic student details
        student.student_email = request.POST.get('student_email')
        student.save()
        
        # 2. Update personal info (Synchronized with studedit.html)
        personal_info.student_mobile = request.POST.get('student_mobile')
        personal_info.gender = request.POST.get('gender')
        personal_info.date_of_birth = request.POST.get('date_of_birth') or None
        personal_info.blood_group = request.POST.get('blood_group')
        personal_info.community = request.POST.get('community')
        
        # Handle Caste ForeignKey (Synchronized with UG logic)
        caste_name = request.POST.get('caste')
        if caste_name and caste_name not in ['Not Applicable', '']:
            from students.models import Caste
            caste_obj, _ = Caste.objects.get_or_create(name=caste_name)
            personal_info.caste = caste_obj
            
        personal_info.caste_other = request.POST.get('caste_other')
        
        personal_info.aadhaar_number = request.POST.get('aadhaar_number')
        personal_info.present_address = request.POST.get('present_address')
        personal_info.permanent_address = request.POST.get('permanent_address')
        personal_info.is_hosteler = (request.POST.get('is_hosteler') == 'yes')
        
        # Parent Details
        personal_info.father_name = request.POST.get('father_name')
        personal_info.father_mobile = request.POST.get('father_mobile')
        personal_info.father_occupation = request.POST.get('father_occupation')
        personal_info.mother_name = request.POST.get('mother_name')
        personal_info.mother_mobile = request.POST.get('mother_mobile')
        personal_info.mother_occupation = request.POST.get('mother_occupation')
        
        income = request.POST.get('parent_annual_income')
        personal_info.parent_annual_income = int(income) if income and income.isdigit() else None
        
        personal_info.save()

        # 3. Update Academic History (SSLC/HSC)
        academic_history.sslc_school_name = request.POST.get('sslc_school_name')
        academic_history.sslc_percentage = request.POST.get('sslc_percentage') or None
        academic_history.sslc_year_of_passing = request.POST.get('sslc_year_of_passing')
        
        academic_history.hsc_school_name = request.POST.get('hsc_school_name')
        academic_history.hsc_percentage = request.POST.get('hsc_percentage') or None
        academic_history.hsc_year_of_passing = request.POST.get('hsc_year_of_passing')
        academic_history.save()

        # 4. Update UG & PG (RS Specific)
        ug_details.ug_course = request.POST.get('ug_course', '')
        ug_details.ug_university = request.POST.get('ug_university', '')
        ug_details.ug_year_of_passing = request.POST.get('ug_year_of_passing', '')
        ug_details.save()

        pg_details.pg_course = request.POST.get('pg_course', '')
        pg_details.pg_university = request.POST.get('pg_university', '')
        pg_details.pg_year_of_passing = request.POST.get('pg_year_of_passing', '')
        pg_details.save()

        # 5. Update document uploads
        from ssm.upload_paths import student_photo_path # ensure paths are available if needed, but FielField handles it
        files = request.FILES
        if 'student_photo' in files: student_docs.student_photo = files['student_photo']
        if 'student_id_card' in files: student_docs.student_id_card = files['student_id_card']
        if 'aadhaar_card' in files: student_docs.aadhaar_card = files['aadhaar_card']
        if 'community_certificate' in files: student_docs.community_certificate = files['community_certificate']
        if 'sslc_marksheet' in files: student_docs.sslc_marksheet = files['sslc_marksheet']
        if 'hsc_marksheet' in files: student_docs.hsc_marksheet = files['hsc_marksheet']
        if 'income_certificate' in files: student_docs.income_certificate = files['income_certificate']
        if 'bank_passbook' in files: student_docs.bank_passbook = files['bank_passbook']
        if 'driving_license' in files: student_docs.driving_license = files['driving_license']
            
        student_docs.save()

        messages.success(request, 'Your research scholar profile has been updated successfully!')
        return redirect('scholar_profile')

    context = {
        'student': student,
        'personalinfo': personal_info,
        'academichistory': academic_history,
        'ug': ug_details,
        'pg': pg_details,
        'studentdocuments': student_docs,
        'skills': student.skills.all(),
        'projects': student.projects.all(),
    }
    return render(request, 'scholars/scholar_edit_profile.html', context)

@require_POST
def scholar_attendance_submit(request):
    roll_number = request.session.get('student_roll_number')
    if not roll_number:
        return redirect('scholar_login')

    student = get_object_or_404(Student, roll_number=roll_number, program_level='PHD')
    
    # Check if already marked for today
    today = datetime.date.today()
    if ScholarAttendance.objects.filter(scholar=student, date=today).exists():
        messages.error(request, "You have already submitted attendance for today.")
    else:
        ScholarAttendance.objects.create(scholar=student, date=today)
        messages.success(request, "Attendance submitted successfully for today. Pending Approval.")
        
        # Email Notification to Supervisor
        profile = getattr(student, 'scholar_profile', None)
        if profile and profile.supervisor and profile.supervisor.email:
            try:
                from django.core.mail import send_mail
                from django.conf import settings
                subject = f"New Attendance Request - {student.student_name}"
                message = f"Dear {profile.supervisor.name},\n\nYour assigned Research Scholar {student.student_name} ({student.roll_number}) has submitted their attendance for {today.strftime('%d %B %Y')}.\n\nPlease log in to your staff portal to approve or reject the attendance.\n\nThank you,\nAnnamalai University SSMSystem"
                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [profile.supervisor.email], fail_silently=True)
            except Exception as e:
                pass

    return redirect('scholar_dashboard')
def scholar_apply_leave(request):
    roll_number = request.session.get('student_roll_number')
    if not roll_number:
        return redirect('scholar_login')

    student = get_object_or_404(Student, roll_number=roll_number, program_level='PHD')
    profile = getattr(student, 'scholar_profile', None)

    if request.method == 'POST':
        form = LeaveRequestForm(request.POST, request.FILES)
        if form.is_valid():
            leave_request = form.save(commit=False)
            leave_request.student = student
            leave_request.status = 'Pending Guide'   # RS leaves go to Guide, not Class Incharge
            leave_request.save()

            try:
                from django.core.mail import send_mail
                from django.conf import settings
                if profile and profile.supervisor and profile.supervisor.email:
                    subject = "Leave Request - " + student.student_name + " (" + student.roll_number + ")"
                    body = (
                        "Dear " + profile.supervisor.name + ",\n\n"
                        "Research Scholar " + student.student_name + " (" + student.roll_number + ") has submitted "
                        "a leave request.\n\n"
                        "Type: " + leave_request.get_leave_type_display() + "\n"
                        "From: " + leave_request.start_date.strftime('%d %B %Y') + "\n"
                        "To:   " + leave_request.end_date.strftime('%d %B %Y') + "\n"
                        "Reason: " + leave_request.reason + "\n\n"
                        "Please log in to the staff portal to review.\n\nAnnamalai University SSMSystem"
                    )
                    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [profile.supervisor.email], fail_silently=True)
            except Exception:
                pass

            messages.success(request, 'Leave request submitted successfully!')
            return redirect('scholar_leave_history')
    else:
        form = LeaveRequestForm()

    return render(request, 'scholars/scholar_leave_apply.html', {
        'form': form,
        'student': student,
        'profile': profile,
    })


def scholar_leave_history(request):
    roll_number = request.session.get('student_roll_number')
    if not roll_number:
        return redirect('scholar_login')

    student = get_object_or_404(Student, roll_number=roll_number, program_level='PHD')
    profile = getattr(student, 'scholar_profile', None)
    leaves = LeaveRequest.objects.filter(student=student).order_by('-created_at')

    leaves_list = list(leaves)
    return render(request, 'scholars/scholar_leave_history.html', {
        'student': student,
        'profile': profile,
        'leaves': leaves,
        'approved_count': sum(1 for l in leaves_list if l.status == 'Approved'),
        'rejected_count': sum(1 for l in leaves_list if l.status == 'Rejected'),
        'pending_count':  sum(1 for l in leaves_list if l.status == 'Pending Guide'),
    })


from staffs.models import ConferenceParticipation, JournalPublication, BookPublication, StaffSeminar, StaffAwardHonour

def scholar_portfolio(request):
    roll_number = request.session.get('student_roll_number')
    if not roll_number: return redirect('scholar_login')
    
    student = get_object_or_404(Student, roll_number=roll_number, program_level='PHD')
    
    conferences = student.scholar_conferences.all().order_by('-year_of_publication', '-created_at')
    journals = student.scholar_journals.all().order_by('-published_year', '-created_at')
    books = student.scholar_books.all().order_by('-year_of_publication', '-created_at')
    seminars = student.scholar_seminars.all().order_by('-year', '-order')
    awards = student.scholar_awards.all().order_by('-year', '-order')
    
    return render(request, 'scholars/scholar_portfolio.html', {
        'student': student,
        'conferences': conferences,
        'journals': journals,
        'books': books,
        'seminars': seminars,
        'awards': awards,
    })

def scholar_portfolio_add(request, form_type):
    roll_number = request.session.get('student_roll_number')
    if not roll_number: return redirect('scholar_login')
    
    student = get_object_or_404(Student, roll_number=roll_number, program_level='PHD')
    staff_list = Staff.objects.filter(is_active=True).order_by('name')
    
    if request.method == 'POST':
        staff_ids = request.POST.getlist('staff_ids')
        if not staff_ids:
            messages.error(request, "Please select at least one Faculty member.")
            return redirect(request.path)
            
        if form_type == 'conference':
            item = ConferenceParticipation(student=student)
            item.participation_type = request.POST.get('participation_type', 'Presented')
            item.national_international = request.POST.get('national_international', 'National')
            item.author_name = request.POST.get('author_name', '').strip()
            item.year_of_publication = request.POST.get('year_of_publication', '').strip()
            item.title_of_paper = request.POST.get('title_of_paper', '').strip()
            item.title_of_proceedings = request.POST.get('title_of_proceedings', '').strip()
            item.date_from = request.POST.get('date_from') or None
            item.date_to = request.POST.get('date_to') or None
            item.location = request.POST.get('location', '').strip()
            item.page_numbers_from = request.POST.get('page_numbers_from', '').strip()
            item.page_numbers_to = request.POST.get('page_numbers_to', '').strip()
            item.place_of_publication = request.POST.get('place_of_publication', '').strip()
            item.publisher_proceedings = request.POST.get('publisher_proceedings', '').strip()
            if 'supporting_document' in request.FILES: item.supporting_document = request.FILES['supporting_document']
            item.save()
            item.staff.set(staff_ids)
            messages.success(request, "Conference added.")
        
        elif form_type == 'journal':
            item = JournalPublication(student=student)
            item.national_international = request.POST.get('national_international', 'National')
            item.published_month = request.POST.get('published_month', '').strip()
            item.published_year = request.POST.get('published_year', '').strip()
            item.author_name = request.POST.get('author_name', '').strip()
            item.title_of_paper = request.POST.get('title_of_paper', '').strip()
            item.journal_name = request.POST.get('journal_name', '').strip()
            item.volume_number = request.POST.get('volume_number', '').strip()
            item.issue_number = request.POST.get('issue_number', '').strip()
            item.year_of_publication_doi = request.POST.get('year_of_publication_doi', '').strip()
            item.page_numbers_from = request.POST.get('page_numbers_from', '').strip()
            item.page_numbers_to = request.POST.get('page_numbers_to', '').strip()
            if 'supporting_document' in request.FILES: item.supporting_document = request.FILES['supporting_document']
            item.save()
            item.staff.set(staff_ids)
            messages.success(request, "Journal added.")
            
        elif form_type == 'book':
            item = BookPublication(student=student)
            item.type = request.POST.get('type', 'Book')
            item.author_name = request.POST.get('author_name', '').strip()
            item.title_of_book = request.POST.get('title_of_book', '').strip()
            item.publisher_name = request.POST.get('publisher_name', '').strip()
            item.publisher_address = request.POST.get('publisher_address', '').strip()
            item.isbn_issn_number = request.POST.get('isbn_issn_number', '').strip()
            item.page_numbers_from = request.POST.get('page_numbers_from', '').strip()
            item.page_numbers_to = request.POST.get('page_numbers_to', '').strip()
            item.month_of_publication = request.POST.get('month_of_publication', '').strip()
            item.year_of_publication = request.POST.get('year_of_publication', '').strip()
            item.url_address = request.POST.get('url_address', '').strip()
            if 'supporting_document' in request.FILES: item.supporting_document = request.FILES['supporting_document']
            item.save()
            item.staff.set(staff_ids)
            messages.success(request, "Book added.")
            
        elif form_type == 'seminar':
            item = StaffSeminar(student=student)
            item.title = request.POST.get('title', '').strip()
            item.event_type = request.POST.get('event_type', 'Seminar')
            item.venue_or_description = request.POST.get('venue_or_description', '').strip()
            item.date_from = request.POST.get('date_from') or None
            item.date_to = request.POST.get('date_to') or None
            item.year = request.POST.get('year', '').strip()
            if 'supporting_document' in request.FILES: item.supporting_document = request.FILES['supporting_document']
            item.save()
            item.staff.set(staff_ids)
            messages.success(request, "Seminar added.")
            
        elif form_type == 'award':
            item = StaffAwardHonour(student=student)
            item.title = request.POST.get('title', '').strip()
            item.category = request.POST.get('category', 'Award')
            item.awarded_by = request.POST.get('awarded_by', '').strip()
            item.year = request.POST.get('year', '').strip()
            item.description = request.POST.get('description', '').strip()
            if 'supporting_document' in request.FILES: item.supporting_document = request.FILES['supporting_document']
            item.save()
            item.staff.set(staff_ids)
            messages.success(request, "Award added.")
            
        return redirect('scholar_portfolio')
            
    title_map = {
        'conference': 'Add Conference',
        'journal': 'Add Journal',
        'book': 'Add Book',
        'seminar': 'Add Seminar',
        'award': 'Add Award',
    }
    
    return render(request, 'scholars/scholar_portfolio_form.html', {
        'student': student,
        'staff_list': staff_list,
        'form_type': form_type,
        'title': title_map.get(form_type, 'Add Item'),
    })

def scholar_portfolio_edit(request, form_type, pk):
    roll_number = request.session.get('student_roll_number')
    if not roll_number: return redirect('scholar_login')
    
    student = get_object_or_404(Student, roll_number=roll_number, program_level='PHD')
    staff_list = Staff.objects.filter(is_active=True).order_by('name')
    
    model_map = {
        'conference': ConferenceParticipation,
        'journal': JournalPublication,
        'book': BookPublication,
        'seminar': StaffSeminar,
        'award': StaffAwardHonour,
    }
    ModelClass = model_map.get(form_type)
    if not ModelClass: return redirect('scholar_portfolio')
    
    item = get_object_or_404(ModelClass, pk=pk, student=student)
    
    if request.method == 'POST':
        staff_ids = request.POST.getlist('staff_ids')
        if staff_ids:
            item.staff.set(staff_ids)
            
        if form_type == 'conference':
            item.participation_type = request.POST.get('participation_type', 'Presented')
            item.national_international = request.POST.get('national_international', 'National')
            item.author_name = request.POST.get('author_name', '').strip()
            item.year_of_publication = request.POST.get('year_of_publication', '').strip()
            item.title_of_paper = request.POST.get('title_of_paper', '').strip()
            item.title_of_proceedings = request.POST.get('title_of_proceedings', '').strip()
            item.date_from = request.POST.get('date_from') or None
            item.date_to = request.POST.get('date_to') or None
            item.location = request.POST.get('location', '').strip()
            item.page_numbers_from = request.POST.get('page_numbers_from', '').strip()
            item.page_numbers_to = request.POST.get('page_numbers_to', '').strip()
            item.place_of_publication = request.POST.get('place_of_publication', '').strip()
            item.publisher_proceedings = request.POST.get('publisher_proceedings', '').strip()
            if 'supporting_document' in request.FILES: item.supporting_document = request.FILES['supporting_document']
            item.save()
            messages.success(request, "Conference updated.")
        
        elif form_type == 'journal':
            item.national_international = request.POST.get('national_international', 'National')
            item.published_month = request.POST.get('published_month', '').strip()
            item.published_year = request.POST.get('published_year', '').strip()
            item.author_name = request.POST.get('author_name', '').strip()
            item.title_of_paper = request.POST.get('title_of_paper', '').strip()
            item.journal_name = request.POST.get('journal_name', '').strip()
            item.volume_number = request.POST.get('volume_number', '').strip()
            item.issue_number = request.POST.get('issue_number', '').strip()
            item.year_of_publication_doi = request.POST.get('year_of_publication_doi', '').strip()
            item.page_numbers_from = request.POST.get('page_numbers_from', '').strip()
            item.page_numbers_to = request.POST.get('page_numbers_to', '').strip()
            if 'supporting_document' in request.FILES: item.supporting_document = request.FILES['supporting_document']
            item.save()
            messages.success(request, "Journal updated.")
            
        elif form_type == 'book':
            item.type = request.POST.get('type', 'Book')
            item.author_name = request.POST.get('author_name', '').strip()
            item.title_of_book = request.POST.get('title_of_book', '').strip()
            item.publisher_name = request.POST.get('publisher_name', '').strip()
            item.publisher_address = request.POST.get('publisher_address', '').strip()
            item.isbn_issn_number = request.POST.get('isbn_issn_number', '').strip()
            item.page_numbers_from = request.POST.get('page_numbers_from', '').strip()
            item.page_numbers_to = request.POST.get('page_numbers_to', '').strip()
            item.month_of_publication = request.POST.get('month_of_publication', '').strip()
            item.year_of_publication = request.POST.get('year_of_publication', '').strip()
            item.url_address = request.POST.get('url_address', '').strip()
            if 'supporting_document' in request.FILES: item.supporting_document = request.FILES['supporting_document']
            item.save()
            messages.success(request, "Book updated.")
            
        elif form_type == 'seminar':
            item.title = request.POST.get('title', '').strip()
            item.event_type = request.POST.get('event_type', 'Seminar')
            item.venue_or_description = request.POST.get('venue_or_description', '').strip()
            item.date_from = request.POST.get('date_from') or None
            item.date_to = request.POST.get('date_to') or None
            item.year = request.POST.get('year', '').strip()
            if 'supporting_document' in request.FILES: item.supporting_document = request.FILES['supporting_document']
            item.save()
            messages.success(request, "Seminar updated.")
            
        elif form_type == 'award':
            item.title = request.POST.get('title', '').strip()
            item.category = request.POST.get('category', 'Award')
            item.awarded_by = request.POST.get('awarded_by', '').strip()
            item.year = request.POST.get('year', '').strip()
            item.description = request.POST.get('description', '').strip()
            if 'supporting_document' in request.FILES: item.supporting_document = request.FILES['supporting_document']
            item.save()
            messages.success(request, "Award updated.")
            
        return redirect('scholar_portfolio')
            
    title_map = {
        'conference': 'Edit Conference',
        'journal': 'Edit Journal',
        'book': 'Edit Book',
        'seminar': 'Edit Seminar',
        'award': 'Edit Award',
    }
    
    return render(request, 'scholars/scholar_portfolio_form.html', {
        'student': student,
        'staff_list': staff_list,
        'form_type': form_type,
        'item': item,
        'title': title_map.get(form_type, 'Edit Item'),
    })

def scholar_portfolio_delete(request, form_type, pk):
    roll_number = request.session.get('student_roll_number')
    if not roll_number: return redirect('scholar_login')
    
    student = get_object_or_404(Student, roll_number=roll_number, program_level='PHD')
    
    model_map = {
        'conference': ConferenceParticipation,
        'journal': JournalPublication,
        'book': BookPublication,
        'seminar': StaffSeminar,
        'award': StaffAwardHonour,
    }
    ModelClass = model_map.get(form_type)
    if ModelClass:
        get_object_or_404(ModelClass, pk=pk, student=student).delete()
        messages.success(request, "Entry deleted.")
        
    return redirect('scholar_portfolio')

