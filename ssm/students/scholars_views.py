import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from students.models import (
    Student, ResearchScholarProfile, RACMember, ZerothReview, RCWReview,
    PersonalInfo, UGDetails, PGDetails, StudentDocuments, OtherDetails,
    ScholarshipInfo, ScholarAttendance, LeaveRequest
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
        # Part 2 Registration -> Personal, UG, PG details
        # Similar logic to regular student
        PersonalInfo.objects.create(
            student=student,
            gender=request.POST.get('gender', ''),
            date_of_birth=request.POST.get('date_of_birth') or None,
            student_mobile=request.POST.get('student_mobile', ''),
            permanent_address=request.POST.get('permanent_address', '')
        )
        UGDetails.objects.create(
            student=student,
            ug_course=request.POST.get('ug_course', ''),
            ug_university=request.POST.get('ug_university', ''),
            ug_year_of_passing=request.POST.get('ug_year_of_passing', '')
        )
        PGDetails.objects.create(
            student=student,
            pg_course=request.POST.get('pg_course', ''),
            pg_university=request.POST.get('pg_university', ''),
            pg_year_of_passing=request.POST.get('pg_year_of_passing', '')
        )

        student.is_profile_complete = True
        student.save()
        messages.success(request, 'Registration complete. Please login.')
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
    }
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
    
    def get_related_or_none(model_class, student_obj):
        try:
            return model_class.objects.get(student=student_obj)
        except model_class.DoesNotExist:
            return None

    context = {
        'student': student,
        'profile': get_related_or_none(ResearchScholarProfile, student),
        'personalinfo': get_related_or_none(PersonalInfo, student),
        'ug': get_related_or_none(UGDetails, student),
        'pg': get_related_or_none(PGDetails, student),
    }
    return render(request, 'scholars/scholar_profile.html', context)


def scholar_edit_profile(request):
    roll_number = request.session.get('student_roll_number')
    if not roll_number:
        return redirect('scholar_login')

    student = get_object_or_404(Student, roll_number=roll_number, program_level='PHD')
    
    personal_info, _ = PersonalInfo.objects.get_or_create(student=student)
    student_docs, _ = StudentDocuments.objects.get_or_create(student=student)
    ug_details, _ = UGDetails.objects.get_or_create(student=student)
    pg_details, _ = PGDetails.objects.get_or_create(student=student)

    if request.method == 'POST':
        # Update student details
        student.student_email = request.POST.get('student_email')
        student.save()
        
        # Update personal info
        personal_info.student_mobile = request.POST.get('student_mobile')
        personal_info.father_name = request.POST.get('father_name')
        personal_info.father_mobile = request.POST.get('father_mobile')
        personal_info.mother_name = request.POST.get('mother_name')
        personal_info.mother_mobile = request.POST.get('mother_mobile')
        personal_info.present_address = request.POST.get('present_address')
        personal_info.permanent_address = request.POST.get('permanent_address')
        personal_info.date_of_birth = request.POST.get('date_of_birth') or None
        personal_info.save()

        # Update UG & PG
        ug_details.ug_course = request.POST.get('ug_course', '')
        ug_details.ug_university = request.POST.get('ug_university', '')
        ug_details.ug_year_of_passing = request.POST.get('ug_year_of_passing', '')
        ug_details.save()

        pg_details.pg_course = request.POST.get('pg_course', '')
        pg_details.pg_university = request.POST.get('pg_university', '')
        pg_details.pg_year_of_passing = request.POST.get('pg_year_of_passing', '')
        pg_details.save()

        # Update document uploads
        if 'student_photo' in request.FILES:
            student_docs.student_photo = request.FILES['student_photo']
        if 'student_id_card' in request.FILES:
            student_docs.student_id_card = request.FILES['student_id_card']
        if 'aadhaar_card' in request.FILES:
            student_docs.aadhaar_card = request.FILES['aadhaar_card']
        if 'community_certificate' in request.FILES:
            student_docs.community_certificate = request.FILES['community_certificate']
        if 'sslc_marksheet' in request.FILES:
            student_docs.sslc_marksheet = request.FILES['sslc_marksheet']
        if 'hsc_marksheet' in request.FILES:
            student_docs.hsc_marksheet = request.FILES['hsc_marksheet']
            
        student_docs.save()

        messages.success(request, 'Your Scholar Profile has been updated successfully!')
        return redirect('scholar_profile')

    context = {
        'student': student,
        'personalinfo': personal_info,
        'ug': ug_details,
        'pg': pg_details,
        'studentdocuments': student_docs,
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

