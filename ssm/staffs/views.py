from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
import random
import string

from .models import Staff, Subject, ExamSchedule, Timetable, StaffPublication, StaffAwardHonour, StaffSeminar, StaffStudentGuided, AuditLog, Lab, AdminSettings, ClassMapping
from students.models import Student, ResearchScholarProfile, ScholarAttendance
from django.db.models import Q, Case, When
from django.db import transaction

def stafflogin(request):
    """Handles staff login."""
    if 'staff_id' in request.session:
        return redirect('staffs:staff_dashboard')

    if request.method == 'POST':
        staff_id = request.POST.get('staff_id')
        password = request.POST.get('password')
        if staff_id:
            staff_id = staff_id.strip().upper()
        try:
            staff = Staff.objects.get(staff_id=staff_id)
            if staff.check_password(password):
                # Clear any existing student session to prevent dual login
                if 'student_roll_number' in request.session:
                    del request.session['student_roll_number']
                
                request.session['staff_id'] = staff.staff_id
                from .utils import log_audit
                log_audit(request, 'login', actor_type='staff', actor_id=staff.staff_id, actor_name=staff.name, message='Staff logged in')
                # First login / incomplete profile should go to registration page
                # with preloaded identity details for completion.
                if not staff.is_profile_complete:
                    request.session['onboarding_staff_id'] = staff.staff_id
                    messages.info(request, 'Please complete your profile before accessing dashboard.')
                    return redirect('staffs:staff_register')
                return redirect('staffs:staff_dashboard')
            else:
                messages.error(request, 'Invalid Staff ID or Password.')
        except Staff.DoesNotExist:
            messages.error(request, 'Invalid Staff ID or Password.')
            
    return render(request, 'staff/stafflogin.html')


def staff_dashboard(request):
    """Displays the staff dashboard. Requires login."""
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')
    
    try:
        staff = Staff.objects.get(staff_id=request.session['staff_id'])
    except Staff.DoesNotExist:
        request.session.flush()
        return redirect('staffs:stafflogin')

    student_count = Student.objects.count()
    all_assigned_roles = staff.get_roles_list()
    req_active_role = request.GET.get('active_role')
    if req_active_role and req_active_role in all_assigned_roles:
        active_role = req_active_role
        request.session['active_role'] = active_role
    else:
        active_role = request.session.get('active_role')
        if not active_role or active_role not in all_assigned_roles:
            active_role = staff.role

    if active_role == 'Class Incharge':
        template_name = 'staff/staffdash_class.html'
        if staff.assigned_semester:
            student_qs = Student.objects.filter(current_semester=staff.assigned_semester)
            if staff.assigned_batch in ['A', 'B']:
                student_qs = student_qs.filter(lab_batch=staff.assigned_batch)
            student_count = student_qs.count()
        else:
            student_count = 0 
    elif active_role == 'Course Incharge':
        template_name = 'staff/staffdash_course.html'
    elif active_role == 'Scholarship Officer':
        template_name = 'staff/staffdash_scholarship.html'
    elif active_role == 'Office Staff':
        template_name = 'staff/staffdash_office.html'
    elif active_role == 'Technical Officer':
        template_name = 'staff/staffdash_technical.html'
    elif active_role in ['HOD', 'Admin'] or (staff.is_staff_admin and active_role not in ['Course Incharge', 'Class Incharge', 'Scholarship Officer', 'Office Staff', 'Technical Officer']):
        template_name = 'staff/staffdash_hod.html'
    else:
        template_name = 'staff/staffdash_course.html'
        
    print(f"DEBUG: staff_dashboard - Active Role: '{active_role}' -> Template: '{template_name}'")
        
    assigned_subjects = []
    _completion_data = get_staff_profile_completion_data(staff)
    if not staff.is_profile_complete:
        template_name = 'staff/staff_profile_status.html'

    else:
        assigned_subjects = staff.get_teaching_subjects()
        for subj in assigned_subjects:
            if subj.staff == staff:
                if not subj.staff_batch_b or subj.staff_batch_b == staff:
                    subj.dashboard_batch = 'Both'
                else:
                    subj.dashboard_batch = 'A'
            elif subj.staff_batch_b == staff:
                subj.dashboard_batch = 'B'
            else:
                subj.dashboard_batch = 'None'
        
    # Calculate pending leaves for notification badge
    from students.models import LeaveRequest, BonafideRequest, ScholarshipInfo
    from staffs.models import StaffLeaveRequest, News
    pending_leaves_count = 0
    pending_staff_leaves_count = 0
    pending_bonafide_count = 0
    pending_portfolio_count = 0
    
    # Fetch News
    # Fetch News
    today = timezone.now().date()
    # Office staff usually don't need general student news unless specified, but keeping simple for now
    news_list = News.objects.filter(
        Q(is_active=True) & 
        Q(target__in=['All', 'Staff', 'Student']) &
        (Q(start_date__isnull=True) | Q(start_date__lte=today)) & 
        (Q(end_date__isnull=True) | Q(end_date__gte=today))
    ).order_by('-date', '-id')
    
    if staff.is_staff_admin:
        pending_leaves_count = LeaveRequest.objects.filter(status='Pending HOD').count()
        pending_staff_leaves_count = StaffLeaveRequest.objects.filter(status='Pending').count()
        # HOD sees requests waiting for sign
        pending_bonafide_count = BonafideRequest.objects.filter(status__in=['Pending HOD Approval', 'Waiting for HOD Sign']).count()
        from .models import StaffPastDesignation
        pending_portfolio_count = StaffPastDesignation.objects.filter(approval_status='Pending').count()
    elif staff.role == 'Office Staff':
         from students.models import DocumentRequest
         # Office Staff sees all active requests not yet collected/rejected
         pending_bonafide_count = BonafideRequest.objects.filter(
             status__in=[
                 'Pending Office Approval', 
                 'Approved by HOD', 
                 'Waiting for HOD Sign', 
                 'Signed', 
                 'Ready for Collection'
             ]
         ).count()
         # Fetch recent active requests for the dashboard widget
         recent_bonafide_requests = BonafideRequest.objects.select_related('student').exclude(status__in=['Rejected', 'Collected']).order_by('-updated_at')[:5]
         
         pending_doc_count = DocumentRequest.objects.filter(status='Pending').count()
         unreturned_doc_count = DocumentRequest.objects.filter(status='Collected (Not Returned)').count()
         recent_doc_requests = DocumentRequest.objects.select_related('student').order_by('-updated_at')[:5]

         # Ensure other counts are 0
         pending_leaves_count = 0
         pending_staff_leaves_count = 0
    elif staff.has_role('Class Incharge') and staff.assigned_semester:
        leave_qs = LeaveRequest.objects.filter(
            status='Pending Class Incharge',
            student__current_semester=staff.assigned_semester
        )
        if staff.assigned_batch in ['A', 'B']:
            leave_qs = leave_qs.filter(student__lab_batch=staff.assigned_batch)
        pending_leaves_count = leave_qs.count()

    # Scholarship Officer Specific Logic
    scholarship_students = []
    selected_scholarship = request.GET.get('scholarship_type')
    
    if staff.role == 'Scholarship Officer' or staff.role == 'Office Staff':
        scholarship_qs = ScholarshipInfo.objects.select_related('student')
        
        SCHOLARSHIP_MAPPING = {
            'First Graduate': 'is_first_graduate',
            'BC/MBC': 'sch_bcmbc',
            'Postmatric': 'sch_postmetric',
            'PM': 'sch_pm',
            'Govt': 'sch_govt',
            'Pudhumai Penn': 'sch_pudhumai',
            'Tamizh Puthalvan': 'sch_tamizh',
            'Private': 'sch_private'
        }

        if selected_scholarship and selected_scholarship in SCHOLARSHIP_MAPPING:
             field_name = SCHOLARSHIP_MAPPING[selected_scholarship]
             filter_kwargs = {field_name: True}
             scholarship_qs = scholarship_qs.filter(**filter_kwargs)
        
        # Determine strict list of scholarship students (those who have AT LEAST ONE scholarship)
        elif not selected_scholarship:
             scholarship_qs = scholarship_qs.filter(
                 Q(is_first_graduate=True) | 
                 Q(sch_bcmbc=True) | 
                 Q(sch_postmetric=True) | 
                 Q(sch_pm=True) | 
                 Q(sch_govt=True) |
                 Q(sch_pudhumai=True) |
                 Q(sch_tamizh=True) |
                 Q(sch_private=True)
             )

        scholarship_students = scholarship_qs


    # ── Research Scholar (RS) data ──────────────────────────────────────────
    from students.models import ResearchScholarProfile, ScholarAttendance, LeaveRequest, PhDProgress
    
    if staff.is_staff_admin:
        # HOD / Admin sees all scholars and all pending requests
        rs_scholars = Student.objects.filter(program_level='PHD').select_related('scholar_profile', 'phd_progress')
        rs_pending_leaves = LeaveRequest.objects.filter(student__program_level='PHD', status='Pending Guide').count()
        rs_pending_attendance = ScholarAttendance.objects.filter(scholar__program_level='PHD', status='Pending').count()
    else:
        # Other staff see only their assigned scholars
        rs_scholars = Student.objects.filter(scholar_profile__supervisor=staff, program_level='PHD').select_related('scholar_profile', 'phd_progress')
        rs_ids = rs_scholars.values_list('pk', flat=True)
        rs_pending_leaves = LeaveRequest.objects.filter(student_id__in=rs_ids, status='Pending Guide').count() if rs_scholars.exists() else 0
        rs_pending_attendance = ScholarAttendance.objects.filter(scholar_id__in=rs_ids, status='Pending').count() if rs_scholars.exists() else 0

    # Ensure phd_progress records exist for all scholars
    for s in rs_scholars:
        if not hasattr(s, 'phd_progress') or s.phd_progress is None:
            PhDProgress.objects.get_or_create(scholar=s)

    rs_count = rs_scholars.count()
    assigned_labs = staff.assigned_labs.all()
    
    # Guided Students stats
    guided_students_qs = staff.student_guided_list.all()
    guided_phd_completed = guided_students_qs.filter(degree_type='PhD', status='Completed').count()
    guided_phd_ongoing = guided_students_qs.filter(degree_type='PhD', status='Ongoing').count()
    guided_pg_completed = guided_students_qs.filter(degree_type='PG', status='Completed').count()
    guided_pg_ongoing = guided_students_qs.filter(degree_type='PG', status='Ongoing').count()
    guided_students_list = guided_students_qs.filter(status='Completed')
    
    total_completed = guided_phd_completed + guided_pg_completed
    total_ongoing = guided_phd_ongoing + guided_pg_ongoing
    total_all = total_completed + total_ongoing
    if total_all > 0:
        guided_success_rate = int((total_completed / total_all) * 100)
    else:
        guided_success_rate = 0
    guided_offset = round(150.8 - (guided_success_rate / 100) * 150.8, 1)
    
    # ── Today's Class Schedule ─────────────────────────────────────────────
    import datetime
    from students.models import StudentAttendance

    today_date_obj = timezone.now().date()
    today_date = today_date_obj.strftime('%Y-%m-%d')
    today_weekday = today_date_obj.strftime('%A')  # 'Monday', 'Tuesday' etc.
    today_schedule = []
    unmarked_done_count = 0

    if today_weekday in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
        today_tt_entries = Timetable.objects.filter(
            staff=staff, day=today_weekday
        ).select_related('subject').order_by('period')
        
        # Pre-fetch attendance records for today to check status per subject & period
        subject_ids = [e.subject.id for e in today_tt_entries if e.subject]
        attendance_records = StudentAttendance.objects.filter(
            date=today_date_obj,
            subject_id__in=subject_ids
        ).values('subject_id', 'time')
        
        attendance_set = set()
        for rec in attendance_records:
            attendance_set.add((rec['subject_id'], rec['time']))

        # Define period time slots matching official system timetable
        PERIOD_TIMES = {
            1: ('08:30', '09:30'),
            2: ('09:30', '10:30'),
            3: ('10:40', '11:40'),
            4: ('11:40', '12:40'),
            5: ('13:30', '14:30'),
            6: ('14:30', '15:30'),
            7: ('15:30', '16:30'),
        }
        now_time = timezone.now().time()
        seen_periods = set()
        for entry in today_tt_entries:
            if entry.period in seen_periods:
                continue
            seen_periods.add(entry.period)
            times = PERIOD_TIMES.get(entry.period, ('--', '--'))
            start_t = None
            try:
                start_t = datetime.time(int(times[0][:2]), int(times[0][3:]))
                end_t   = datetime.time(int(times[1][:2]), int(times[1][3:]))
                if now_time < start_t:
                    status = 'upcoming'
                elif start_t <= now_time <= end_t:
                    status = 'ongoing'
                else:
                    status = 'done'
            except Exception:
                status = 'upcoming'

            # Check if attendance has been marked for this slot/subject
            is_marked = False
            if entry.subject:
                if (entry.subject.id, start_t) in attendance_set:
                    is_marked = True
                elif (entry.subject.id, None) in attendance_set:
                    is_marked = True
                elif any(rec_s_id == entry.subject.id for (rec_s_id, rec_time) in attendance_set if rec_time is None):
                    is_marked = True

            if status == 'done' and not is_marked:
                unmarked_done_count += 1

            today_schedule.append({
                'period': entry.period,
                'subject': entry.subject,
                'batch': entry.batch,
                'semester': entry.semester,
                'start': times[0],
                'end': times[1],
                'status': status,
                'is_marked': is_marked,
            })

    has_unmarked_done = (unmarked_done_count > 0)

    # Dynamic Sarcastic / Emotional Mood Text Generator based on Class Count & Day
    import random
    class_count = len(today_schedule)
    if today_weekday in ['Saturday', 'Sunday']:
        schedule_mood_text = random.choice([
            "Weekend vibes! Zero classes, zero stress 🌅",
            "It's the weekend! Time to recharge 🔋",
            "No alarm clocks needed today ☕"
        ])
    elif class_count == 0:
        schedule_mood_text = random.choice([
            "Zero classes today! Time to pretend you're working on research ☕",
            "No classes today! Your vocal cords send their regards 💃",
            "Empty schedule! Enjoy the quiet before the storm 🌴",
            "No teaching today! Catch up on coffee & grading ☕"
        ])
    elif class_count == 1:
        schedule_mood_text = random.choice([
            "Just 1 class! Barely a warm-up, grab another coffee ☕",
            "Only 1 hour today! Easy money 🚀",
            "1 class on duty. Light work, heavy relaxation 🎧",
            "Just 1 class! Smooth sailing today ⛵"
        ])
    elif class_count == 2:
        schedule_mood_text = random.choice([
            "2 classes today. Perfectly balanced, as all things should be ⚖️",
            "2 hours today. Light work, max energy ⚡",
            "2 classes on deck. A piece of cake 🍰"
        ])
    elif class_count == 3:
        schedule_mood_text = random.choice([
            "3 classes today. Solid shift! Stay hydrated 💧",
            "3 hours on duty. Moderate effort, maximum impact 🔥",
            "3 classes lined up. In the zone today 🎯"
        ])
    elif class_count == 4:
        schedule_mood_text = random.choice([
            "4 classes today! Throat lozenges required by 3 PM 🗣️",
            "4 hours of teaching... Stay strong, soldier! 🫡",
            "4 classes today. Coffee level: Emergency ☕⚡",
            "4 classes on deck! Deep breath, you got this 💪"
        ])
    else:  # 5+ classes
        if today_weekday == 'Monday':
            schedule_mood_text = random.choice([
                "Monday AND 5 classes?! Someone's testing your patience 😭",
                "5 classes on a Monday?! Heavy marathon day 🏃‍♂️💨",
                "5 hours straight on Monday... Coffee level: CRITICAL ☕🔥"
            ])
        elif today_weekday == 'Friday':
            schedule_mood_text = random.choice([
                "5 classes on a Friday?! Absolute cruelty! 😮‍💨",
                "5 classes today, but weekend is right after! Finish strong 🏁",
                "5 hours today... Friday boss battle unlocked 🎮"
            ])
        else:
            schedule_mood_text = random.choice([
                "5 classes?! Who scheduled this marathon?! 🏃‍♂️💨",
                "5 hours today... May the caffeine be with you 🦸",
                "5 classes today. Survival mode: ACTIVATED 🚨",
                "5 hours straight... Press F for your vocal cords 🫡",
                "5 classes today! Heavy duty shift in progress 🏋️"
            ])

    # ────────────────────────────────────────────────────────────────────────
    dashboard_context = {
        'staff': staff, 
        'student_count': student_count,
        'subjects': assigned_subjects,
        'assigned_subjects': assigned_subjects, # For HOD dashboard compatibility
        'pending_leaves_count': pending_leaves_count,
        'pending_staff_leaves_count': pending_staff_leaves_count,
        'pending_bonafide_count': pending_bonafide_count,
        'pending_doc_count': locals().get('pending_doc_count', 0),
        'unreturned_doc_count': locals().get('unreturned_doc_count', 0),
        'recent_doc_requests': locals().get('recent_doc_requests', []),
        'pending_portfolio_count': pending_portfolio_count,
        'recent_bonafide_requests': locals().get('recent_bonafide_requests', []),
        'news_list': news_list,
        'scholarship_students': scholarship_students,
        'selected_scholarship': selected_scholarship,
        'profile_completion_percentage': _completion_data['percentage'],
        'profile_missing_fields': _completion_data['missing_fields'],
        # Research Scholar Context
        'rs_count': rs_count,
        'rs_pending_leaves': rs_pending_leaves,
        'rs_pending_attendance': rs_pending_attendance,
        'rs_scholars': rs_scholars,
        'assigned_labs': assigned_labs,
        'assigned_dept_tasks': staff.assigned_department_tasks.all().order_by('task_number'),
        # Guided Students
        'guided_phd_completed': guided_phd_completed,
        'guided_phd_ongoing': guided_phd_ongoing,
        'guided_pg_completed': guided_pg_completed,
        'guided_pg_ongoing': guided_pg_ongoing,
        'guided_students_list': guided_students_list,
        'guided_success_rate': guided_success_rate,
        'guided_offset': guided_offset,
        # Today's Schedule
        'today_schedule': today_schedule,
        'today_weekday': today_weekday,
        'today_date': today_date,
        'schedule_mood_text': schedule_mood_text,
        'unmarked_done_count': unmarked_done_count,
        'has_unmarked_done': has_unmarked_done,
        'all_assigned_roles': all_assigned_roles,
        'active_role': active_role,
    }
    dashboard_context.update(_get_portfolio_summary_stats(staff))
    return render(request, template_name, dashboard_context)

def get_staff_profile_completion_data(staff):
    """
    Returns a dict with:
      - 'percentage': int (0-100)
      - 'missing_fields': list of human-readable field names that are empty
    """
    total_fields = 0
    filled_fields = 0
    missing_fields = []

    FIELD_LABELS = {
        'name': 'Full Name',
        'email': 'Email Address',
        'mobile_number': 'Mobile Number',
        'date_of_birth': 'Date of Birth',
        'date_of_joining': 'Date of Joining',
        'address': 'Address',
        'salutation': 'Salutation',
    }

    def check_fields(model_instance, fields_to_check):
        nonlocal total_fields, filled_fields
        if not model_instance:
            total_fields += len(fields_to_check)
            for f in fields_to_check:
                missing_fields.append(FIELD_LABELS.get(f, f.replace('_', ' ').title()))
            return
        for field in fields_to_check:
            total_fields += 1
            val = getattr(model_instance, field, None)
            if val and str(val).strip():
                filled_fields += 1
            else:
                missing_fields.append(FIELD_LABELS.get(field, field.replace('_', ' ').title()))

    if staff.role in ['Office Staff', 'Technical Officer']:
        if not staff.is_profile_complete:
            staff.is_profile_complete = True
            staff.save(update_fields=['is_profile_complete'])
        return {
            'percentage': 100,
            'missing_fields': [],
        }

    # Check basic fields
    check_fields(staff, ['name', 'email', 'mobile_number', 'date_of_birth', 'date_of_joining', 'address', 'salutation'])

    basic_total = total_fields
    basic_filled = filled_fields
    basic_percentage = int((basic_filled / basic_total) * 100) if basic_total > 0 else 0

    # Auto-update status based ONLY on basic onboarding fields completion
    if basic_percentage == 100 and not staff.is_profile_complete:
        staff.is_profile_complete = True
        staff.save(update_fields=['is_profile_complete'])
    elif basic_percentage < 100 and staff.is_profile_complete:
        staff.is_profile_complete = False
        staff.save(update_fields=['is_profile_complete'])

    # Qualifications
    total_fields += 1
    if staff.qualifications.exists():
        filled_fields += 1
    else:
        missing_fields.append('Qualifications (At least 1)')

    # Past Designations (Optional based on typical needs, but part of profile completion)
    total_fields += 1
    if staff.past_designations.exists() or staff.designation: # Either past designation or current designation filled
        filled_fields += 1
    else:
        missing_fields.append('Designation History (At least 1)')

    percentage = int((filled_fields / total_fields) * 100) if total_fields > 0 else 0

    return {
        'percentage': min(percentage, 100),
        'missing_fields': missing_fields,
    }

def staff_logout(request):
    """Logs the staff member out."""
    staff_id = request.session.get('staff_id')
    staff_name = ''
    if staff_id:
        try:
            s = Staff.objects.get(staff_id=staff_id)
            staff_name = s.name
        except Staff.DoesNotExist:
            pass
        from .utils import log_audit
        log_audit(request, 'logout', actor_type='staff', actor_id=staff_id or '', actor_name=staff_name, message='Staff logged out')
    try:
        request.session.flush() # Securely clears the entire session
    except KeyError:
        pass
    messages.success(request, "You have been successfully logged out.")
    return redirect('staffs:stafflogin')

from .forms import StaffRegistrationForm

def staff_register(request):
    from django.shortcuts import get_object_or_404
    onboarding_staff_id = request.session.get('onboarding_staff_id')
    if not onboarding_staff_id:
        messages.error(request, "Access Denied: Please log in first.")
        return redirect('staffs:stafflogin')
        
    staff = get_object_or_404(Staff, staff_id=onboarding_staff_id)
    
    if request.method == 'POST':
        salutation = request.POST.get('salutation')
        initial = request.POST.get('initial')
        email = request.POST.get('email')
        password = request.POST.get('password')
        photo = request.FILES.get('photo')
        
        dob_str = request.POST.get('date_of_birth')
        doj_str = request.POST.get('date_of_joining')
        mobile_number = request.POST.get('mobile_number')
        address = request.POST.get('address')
        specialization = request.POST.get('specialization')
        
        if staff.role == 'Office Staff' and not specialization:
            specialization = 'General Administration'
        elif staff.role == 'Technical Officer' and not specialization:
            specialization = 'Technical Support & Lab Management'

        # Validation
        if not email or not dob_str or not doj_str or not mobile_number or not address or (staff.role not in ['Office Staff', 'Technical Officer'] and not specialization):
            messages.error(request, "All required fields must be filled out.")
            return render(request, 'staff/staffreg.html', {'staff': staff})
            
        # Unique email exclusion
        if Staff.objects.filter(email=email).exclude(staff_id=staff.staff_id).exists():
            messages.error(request, "This email is already registered.")
            return render(request, 'staff/staffreg.html', {'staff': staff})
            
        if password and len(password) < 6:
            messages.error(request, "Password must be at least 6 characters long.")
            return render(request, 'staff/staffreg.html', {'staff': staff})
            
        import datetime
        try:
            dob = datetime.datetime.strptime(dob_str, '%Y-%m-%d').date()
            doj = datetime.datetime.strptime(doj_str, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, "Invalid date format.")
            return render(request, 'staff/staffreg.html', {'staff': staff})
            
        age = (datetime.date.today() - dob).days / 365.25
        if age < 18:
            messages.error(request, "Staff must be at least 18 years old.")
            return render(request, 'staff/staffreg.html', {'staff': staff})
            
        if doj < dob:
            messages.error(request, "Date of Joining cannot be before Date of Birth.")
            return render(request, 'staff/staffreg.html', {'staff': staff})
            
        import re
        if not re.match(r'^\d{10}$', mobile_number):
            messages.error(request, "Mobile number must be exactly 10 digits.")
            return render(request, 'staff/staffreg.html', {'staff': staff})
            
        # Update and complete profile
        staff.salutation = salutation
        staff.initial = initial
        staff.email = email
        if password:
            staff.set_password(password)
        if photo:
            staff.photo = photo
            
        staff.date_of_birth = dob
        staff.date_of_joining = doj
        staff.mobile_number = mobile_number
        staff.address = address
        staff.specialization = specialization
            
        staff.is_profile_complete = True
        staff.save()
        
        # Log audit
        from .utils import log_audit
        log_audit(
            request, 'update',
            actor_type='staff',
            actor_id=staff.staff_id,
            actor_name=staff.name,
            object_type='Staff',
            object_id=staff.staff_id,
            message='Staff onboarding profile completed'
        )
        
        # Log staff in by keeping staff_id in session and removing onboarding
        request.session['staff_id'] = staff.staff_id
        request.session.pop('onboarding_staff_id', None)
        
        messages.success(request, f"Welcome {staff.name}! Your profile is now complete.")
        return redirect('staffs:staff_dashboard')
        
    return render(request, 'staff/staffreg.html', {'staff': staff})


def generate_staff(request):
    """
    Admin-only helper: generate temporary credentials for a staff record
    using Staff ID + Name, then force profile completion on first login.
    """
    if not request.user.is_authenticated or not request.user.is_superuser:
        messages.error(request, "Access Denied: This page is available only in Admin Dashboard.")
        return redirect('/admin/')

    import csv
    from django.http import HttpResponse

    def next_temp_email(staff_id):
        base_email = f"{staff_id.lower()}@temp.staff.local"
        email_candidate = base_email
        suffix = 1
        while Staff.objects.filter(email=email_candidate).exclude(staff_id=staff_id).exists():
            suffix += 1
            email_candidate = f"{staff_id.lower()}{suffix}@temp.staff.local"
        return email_candidate

    OFFICE_DUTIES = {'Office Staff', 'Bonafide Issuing', 'Marksheet & Document Requests', 'Scholarship Management'}

    def upsert_staff_identity(staff_id, name, roles=None):
        if not roles:
            roles = ['Course Incharge']
        roles_list = list(roles) if isinstance(roles, list) else [roles]
        
        has_office_duty = any(r in OFFICE_DUTIES for r in roles_list)
        if has_office_duty:
            primary_role = 'Office Staff'
            sec_roles = [r for r in roles_list if r != 'Office Staff']
            secondary_roles_str = ", ".join(sec_roles)
        else:
            primary_role = roles_list[0]
            secondary_roles_str = ", ".join(roles_list[1:]) if len(roles_list) > 1 else ""

        roles_set = set(roles_list)
        email_candidate = next_temp_email(staff_id)
        is_office = ('Office Staff' in roles_set or has_office_duty)

        defaults = {
            'name': name,
            'email': email_candidate,
            'role': primary_role,
            'secondary_roles': secondary_roles_str,
            'is_scholarship_officer': ('Scholarship Officer' in roles_set or 'Scholarship Management' in roles_set),
            'is_timetable_incharge': 'Timetable Incharge' in roles_set,
            'is_admin': 'HOD' in roles_set,
            'salutation': 'Mr.' if is_office else 'Dr.',
            'designation': 'Office Assistant' if is_office else 'Assistant Professor',
            'qualification': 'Graduate' if is_office else 'Ph.D.',
            'specialization': 'General Administration' if is_office else 'Information Technology',
            'department': 'Information Technology',
            'is_profile_complete': False,
        }
        staff_obj, created = Staff.objects.get_or_create(staff_id=staff_id, defaults=defaults)
        if not created:
            staff_obj.role = primary_role
            staff_obj.secondary_roles = secondary_roles_str
            if 'Scholarship Officer' in roles_set or 'Scholarship Management' in roles_set:
                staff_obj.is_scholarship_officer = True
            if 'Timetable Incharge' in roles_set:
                staff_obj.is_timetable_incharge = True
            if 'HOD' in roles_set:
                staff_obj.is_admin = True
            if staff_obj.name != name:
                staff_obj.name = name
            staff_obj.save()
        return staff_obj, created

    if request.method == 'POST':
        action = request.POST.get('action', 'preview_bulk')
        staff_roles = request.POST.getlist('staff_roles')
        if not staff_roles:
            single_role = request.POST.get('staff_role', 'Course Incharge')
            staff_roles = [single_role]

        if action == 'preview_bulk':
            bulk_input = (request.POST.get('bulk_input') or '').strip()
            if not bulk_input:
                messages.error(request, "Please enter at least one 'StaffID, Name' row.")
                return render(request, 'staff/generate_staff.html', {'staff_role': staff_roles[0], 'staff_roles': staff_roles})

            preview_list = []
            lines = [line.strip() for line in bulk_input.splitlines() if line.strip()]
            for idx, line in enumerate(lines, start=1):
                if ',' not in line:
                    messages.error(request, f"Row {idx} invalid. Use format: STAFF_ID, Staff Name")
                    return render(request, 'staff/generate_staff.html', {'staff_role': staff_roles[0], 'staff_roles': staff_roles})
                raw_id, raw_name = line.split(',', 1)
                staff_id = raw_id.strip()
                name = raw_name.strip()
                if not staff_id or not name:
                    messages.error(request, f"Row {idx} invalid. Staff ID and Name are required.")
                    return render(request, 'staff/generate_staff.html', {'staff_role': staff_roles[0], 'staff_roles': staff_roles})
                exists = Staff.objects.filter(staff_id=staff_id).exists()
                preview_list.append({'staff_id': staff_id, 'name': name, 'exists': exists})

            return render(request, 'staff/generate_staff.html', {
                'show_preview': True,
                'preview_list': preview_list,
                'bulk_input': bulk_input,
                'staff_role': staff_roles[0],
                'staff_roles': staff_roles,
            })

        if action == 'generate_bulk':
            selected_entries = request.POST.getlist('selected_entries')
            if not selected_entries:
                messages.error(request, "No staff selected for generation.")
                return redirect('staffs:generate_staff')

            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="generated_staff_credentials.csv"'
            writer = csv.writer(response)
            writer.writerow(['Staff ID', 'Name', 'Primary Role', 'All Roles', 'Temp Password'])

            with transaction.atomic():
                for entry in selected_entries:
                    try:
                        staff_id, name = entry.split('||', 1)
                    except ValueError:
                        continue

                    already_exists = Staff.objects.filter(staff_id=staff_id).exists()
                    staff_obj, _ = upsert_staff_identity(staff_id, name, roles=staff_roles)
                    if already_exists:
                        pass_label = "Existing Password"
                    else:
                        temp_pass = "Tmp" + ''.join(random.choices(string.digits, k=5))
                        staff_obj.set_password(temp_pass)
                        staff_obj.save(update_fields=['password'])
                        pass_label = temp_pass
                    writer.writerow([staff_id, name, staff_obj.role, ", ".join(staff_obj.get_roles_list()), pass_label])

            response.set_cookie('download_complete', 'true', max_age=20)
            return response

        if action == 'generate_single':
            staff_id = (request.POST.get('single_staff_id') or '').strip()
            name = (request.POST.get('single_name') or '').strip()
            if not staff_id or not name:
                messages.error(request, "Staff ID and Name are required.")
                return redirect('staffs:generate_staff')

            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="generated_staff_{staff_id}.csv"'
            writer = csv.writer(response)
            writer.writerow(['Staff ID', 'Name', 'Primary Role', 'All Roles', 'Temp Password'])

            with transaction.atomic():
                staff_obj, _ = upsert_staff_identity(staff_id, name, roles=staff_roles)
                temp_pass = "Tmp" + ''.join(random.choices(string.digits, k=5))
                staff_obj.set_password(temp_pass)
                staff_obj.save(update_fields=['password'])
                writer.writerow([staff_id, name, staff_obj.role, ", ".join(staff_obj.get_roles_list()), temp_pass])

            response.set_cookie('download_complete', 'true', max_age=20)
            return response

    return render(request, 'staff/generate_staff.html')


def student_list(request):
    """Displays a list of students with search functionality for staff."""
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')

    query = request.GET.get('q')
    semester = request.GET.get('semester')
    start_roll = request.GET.get('start_roll')
    end_roll = request.GET.get('end_roll')
    
    students = Student.objects.all().select_related('studentdocuments')

    # Restrict view for Class Incharge
    try:
        current_staff = Staff.objects.get(staff_id=request.session['staff_id'])
        if current_staff.has_role('Class Incharge') and current_staff.assigned_semester:
            students = students.filter(current_semester=current_staff.assigned_semester)
            if current_staff.assigned_batch in ['A', 'B']:
                students = students.filter(lab_batch=current_staff.assigned_batch)
            # Override semester filter to be the assigned one (or hide the filter in template)
            semester = str(current_staff.assigned_semester) 
    except Staff.DoesNotExist:
        pass

    if query:
        students = students.filter(
            Q(student_name__icontains=query) | 
            Q(roll_number__icontains=query) |
            Q(student_email__icontains=query)
        )
    
    if semester:
        try:
            semester_num = int(semester)
            if semester_num >= 9:
                students = students.filter(current_semester__gte=9)
            else:
                students = students.filter(current_semester=semester_num)
        except ValueError:
            pass  # ignore invalid semester input

    if start_roll:
        students = students.filter(roll_number__gte=start_roll)
    if end_roll:
        students = students.filter(roll_number__lte=end_roll)

    # Compute profile completion for each student
    from students.views import get_profile_completion_data
    students_with_completion = []
    for s in students:
        comp = get_profile_completion_data(s)
        students_with_completion.append({
            'student': s,
            'completion_pct': comp['percentage'],
            'missing_fields': comp['missing_fields'],
        })

    if request.GET.get('export') == 'csv':
        import csv
        from django.http import HttpResponse
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="student_directory.csv"'
        writer = csv.writer(response)
        
        # CSV Headers
        writer.writerow([
            'Roll Number', 
            'Register Number', 
            'Student Name', 
            'Student Email', 
            'Program Level', 
            'Current Semester', 
            'Starting Year (Joining Year)', 
            'Ending Year', 
            'Status',
            'Missing Details'
        ])
        
        # Map existing students by roll_number for fast lookup
        existing_map = {}
        for item in students_with_completion:
            s = item['student']
            existing_map[s.roll_number] = item
 
        # Determine sequence if start_roll and end_roll are numeric
        try:
            start_int = int(start_roll) if start_roll else None
            end_int = int(end_roll) if end_roll else None
            is_range = (start_int is not None and end_int is not None)
        except (ValueError, TypeError):
            is_range = False
 
        if is_range and start_int <= end_int:
            # Generate all roll numbers in the sequence preserving string length
            length = len(start_roll)
            sequence_rolls = [str(x).zfill(length) for x in range(start_int, end_int + 1)]
            
            for r_num in sequence_rolls:
                if r_num in existing_map:
                    item = existing_map[r_num]
                    s = item['student']
                    pct = item['completion_pct']
                    if s.is_password_changed:
                        status_str = f"Registered ({pct}%)"
                    elif s.password and s.password.strip() != "":
                        status_str = "Not Registered (Password Generated)"
                    else:
                        status_str = "No Password Generated"
                    
                    missing_str = ", ".join(item['missing_fields'])
                    writer.writerow([
                        f'="{s.roll_number}"',
                        f'="{s.register_number}"' if s.register_number else '',
                        s.student_name,
                        s.student_email or '',
                        s.program_level,
                        s.current_semester,
                        s.joining_year or '',
                        s.ending_year or '',
                        status_str,
                        missing_str
                    ])
                else:
                    # In-between roll number not in DB
                    writer.writerow([
                        f'="{r_num}"',
                        '',
                        'Not Found (Not Generated)',
                        '',
                        '',
                        '',
                        '',
                        '',
                        'No Password Generated',
                        'Not Found'
                    ])
        else:
            # Fallback: Just output existing filtered records
            for item in students_with_completion:
                s = item['student']
                pct = item['completion_pct']
                if s.is_password_changed:
                    status_str = f"Registered ({pct}%)"
                elif s.password and s.password.strip() != "":
                    status_str = "Not Registered (Password Generated)"
                else:
                    status_str = "No Password Generated"
                
                missing_str = ", ".join(item['missing_fields'])
                writer.writerow([
                    f'="{s.roll_number}"',
                    f'="{s.register_number}"' if s.register_number else '',
                    s.student_name,
                    s.student_email or '',
                    s.program_level,
                    s.current_semester,
                    s.joining_year or '',
                    s.ending_year or '',
                    status_str,
                    missing_str
                ])
            
        return response

    return render(request, 'studlist.html', {
        'students_with_completion': students_with_completion,
        'query': query,
        'selected_semester': semester,
        'start_roll': start_roll,
        'end_roll': end_roll
    })


def student_detail(request, roll_number):
    """Displays complete details of a single student."""
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')

    student = get_object_or_404(Student, roll_number=roll_number)
    
    # helper to get object or None
    def get_or_none(model, **kwargs):
        try:
            return model.objects.get(**kwargs)
        except model.DoesNotExist:
            return None

    # Importing models inside function to avoid circular imports if any, 
    # but preferably they should be at top. Let's assume they are available or import them.
    from students.models import (
        PersonalInfo, AcademicHistory, DiplomaDetails, UGDetails, PGDetails, 
        PhDDetails, ScholarshipInfo, StudentDocuments, BankDetails, OtherDetails,
        StudentGPA 
    )

    from students.views import get_profile_completion_data
    _comp = get_profile_completion_data(student)

    context = {
        'student': student,
        'personal_info': get_or_none(PersonalInfo, student=student),
        'academic_history': get_or_none(AcademicHistory, student=student),
        'gpa_records': StudentGPA.objects.filter(student=student).order_by('semester'), # Added history
        'diploma_details': get_or_none(DiplomaDetails, student=student),
        'ug_details': get_or_none(UGDetails, student=student),
        'pg_details': get_or_none(PGDetails, student=student),
        'phd_details': get_or_none(PhDDetails, student=student),
        'scholarship_info': get_or_none(ScholarshipInfo, student=student),
        'bank_details': get_or_none(BankDetails, student=student),
        'docs': get_or_none(StudentDocuments, student=student),
        'other_details': get_or_none(OtherDetails, student=student),
        'profile_completion_percentage': _comp['percentage'],
        'profile_missing_fields': _comp['missing_fields'],
    }

    return render(request, 'staff/stud_detail.html', context)

def manage_semesters(request):
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')
    
    selected_semester = request.GET.get('semester')
    students = []
    
    if request.method == 'POST':
        student_ids = request.POST.getlist('student_ids')
        action = request.POST.get('action')

        if student_ids and action:
            from django.db.models import F
            
            if action == 'promote':
                # Loop through students to archive data individually BEFORE promoting
                count = 0
                for roll in student_ids:
                    try:
                        student = Student.objects.get(roll_number=roll)
                        if student.current_semester <= 8:
                            # ARCHIVE DATA FIRST
                            archive_semester_data(student)
                            
                            # PROMOTE
                            student.current_semester += 1
                            student.save()
                            count += 1
                    except Student.DoesNotExist:
                        continue
                        
                messages.success(request, f"Successfully promoted {count} students and archived their semester data.")
            
            elif action == 'demote':
                # Only demote if current_semester > 1.
                Student.objects.filter(roll_number__in=student_ids, current_semester__gt=1).update(current_semester=F('current_semester') - 1)
                messages.success(request, f"Successfully demoted selected students.")
                
            return redirect(f"{request.path}?semester={selected_semester}") # Stay on same page
        else:
            messages.warning(request, "No students selected or invalid action.")

    display_semester_selector = True
    header_text = "Filter by Current Semester"

    # Restrict for Class Incharge
def manage_subjects(request):
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')
    
    # Check if HOD
    try:
        current_staff = Staff.objects.get(staff_id=request.session['staff_id'])
        if not current_staff.is_staff_admin:
             messages.error(request, "Access Denied: Only HOD can manage courses.")
             return redirect('staffs:staff_dashboard')
    except Staff.DoesNotExist:
         return redirect('staffs:stafflogin')

    from .models import Subject, ClassMapping, Lab # Import locally to avoid circularity if any

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add_subject':
            name = request.POST.get('name')
            code = request.POST.get('code')
            semester = request.POST.get('semester')
            subject_type = request.POST.get('type', 'Theory')
            location_name = request.POST.get('location_name', '').strip()
            
            if name and code and semester:
                Subject.objects.create(
                    name=name, 
                    code=code, 
                    semester=semester, 
                    subject_type=subject_type,
                    location_name=location_name or None
                )
                messages.success(request, f"{subject_type} '{name}' added successfully.")
            else:
                 messages.error(request, "All fields are required to add a subject.")
                 
        elif action == 'assign_staff':
            subject_id = request.POST.get('subject_id')
            staff_id = request.POST.get('staff_id')
            staff_batch_b_id = request.POST.get('staff_batch_b_id')
            location_name = request.POST.get('location_name', '').strip()
            
            if subject_id:
                subject = get_object_or_404(Subject, id=subject_id)
                allowed = True
                staff_member = None
                staff_batch_b_member = None
                
                # Resolve Batch A / Both Staff
                if staff_id:
                    staff_member = get_object_or_404(Staff, staff_id=staff_id)
                    # Limit Check for Batch A Staff
                    existing_assignments = Subject.objects.filter(staff=staff_member, semester=subject.semester).exclude(code=subject.code)
                    existing_b_assignments = Subject.objects.filter(staff_batch_b=staff_member, semester=subject.semester).exclude(code=subject.code)
                    
                    if subject.subject_type == 'Theory':
                        existing_theory = (existing_assignments.filter(subject_type='Theory') | existing_b_assignments.filter(subject_type='Theory')).first()
                        if existing_theory:
                            messages.error(request, f"Cannot assign Batch A: {staff_member.name} already handles a Theory subject in Sem {subject.semester} ({existing_theory.code}). Limit: 1 Theory + 1 Lab.")
                            allowed = False
                    elif subject.subject_type == 'Lab':
                        existing_lab = (existing_assignments.filter(subject_type='Lab') | existing_b_assignments.filter(subject_type='Lab')).first()
                        if existing_lab:
                            messages.error(request, f"Cannot assign Batch A: {staff_member.name} already handles a Lab in Sem {subject.semester} ({existing_lab.code}). Limit: 1 Theory + 1 Lab.")
                            allowed = False
                
                # Resolve Batch B Staff (if specified and different from Batch A)
                if staff_batch_b_id and staff_batch_b_id != staff_id:
                    staff_batch_b_member = get_object_or_404(Staff, staff_id=staff_batch_b_id)
                    # Limit Check for Batch B Staff
                    existing_assignments = Subject.objects.filter(staff=staff_batch_b_member, semester=subject.semester).exclude(code=subject.code)
                    existing_b_assignments = Subject.objects.filter(staff_batch_b=staff_batch_b_member, semester=subject.semester).exclude(code=subject.code)
                    
                    if subject.subject_type == 'Theory':
                        existing_theory = (existing_assignments.filter(subject_type='Theory') | existing_b_assignments.filter(subject_type='Theory')).first()
                        if existing_theory:
                            messages.error(request, f"Cannot assign Batch B: {staff_batch_b_member.name} already handles a Theory subject in Sem {subject.semester} ({existing_theory.code}). Limit: 1 Theory + 1 Lab.")
                            allowed = False
                    elif subject.subject_type == 'Lab':
                        existing_lab = (existing_assignments.filter(subject_type='Lab') | existing_b_assignments.filter(subject_type='Lab')).first()
                        if existing_lab:
                            messages.error(request, f"Cannot assign Batch B: {staff_batch_b_member.name} already handles a Lab in Sem {subject.semester} ({existing_lab.code}). Limit: 1 Theory + 1 Lab.")
                            allowed = False

                if allowed:
                    subject.staff = staff_member
                    subject.staff_batch_b = staff_batch_b_member
                    subject.assigned_batch = 'Both' # Standard default
                    if location_name:
                        subject.location_name = location_name
                    subject.save()
                    
                    if staff_member and staff_batch_b_member:
                        messages.success(request, f"Assigned {staff_member.name} (Batch A) and {staff_batch_b_member.name} (Batch B) to {subject.name}.")
                    elif staff_member:
                        messages.success(request, f"Assigned {staff_member.name} to {subject.name} (Both Batches).")
                    elif staff_batch_b_member:
                        messages.success(request, f"Assigned {staff_batch_b_member.name} to {subject.name} (Batch B only).")
                    else:
                        messages.success(request, f"Updated assignment for {subject.name}.")

        elif action == 'delete_subject':
            subject_id = request.POST.get('subject_id')
            if subject_id:
                subject = get_object_or_404(Subject, id=subject_id)
                name = subject.name
                subject.delete()
                messages.success(request, f"Subject '{name}' deleted successfully.")

        return redirect('staffs:manage_subjects')

    # Group subjects by semester
    subjects = Subject.objects.all().order_by('semester', 'code')
    staff_members = Staff.objects.all().order_by('name')
    class_mappings = ClassMapping.objects.all().order_by('semester', 'class_name')
    labs = Lab.objects.all().order_by('name')
    
    # Organize into a dict for easier template iteration: { 1: [subj1, subj2], 2: [...] }
    subjects_by_sem = {}
    for i in range(1, 9):
        subjects_by_sem[i] = []
        
    for subj in subjects:
        if subj.semester in subjects_by_sem:
            subjects_by_sem[subj.semester].append(subj)
            
    return render(request, 'staff/manage_subjects.html', {
        'subjects_by_sem': subjects_by_sem,
        'staff_members': staff_members,
        'class_mappings': class_mappings,
        'labs': labs,
        'current_staff': current_staff
    })


def hod_live_class_visualisation(request):
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')
    try:
        staff = Staff.objects.get(staff_id=request.session['staff_id'])
    except Staff.DoesNotExist:
        return redirect('staffs:stafflogin')

    if staff.role not in ['HOD', 'Technical Officer', 'Office Staff'] and not staff.is_admin:
        messages.error(request, "Access Denied: You do not have permission to view Live Class Visualisation.")
        return redirect('staffs:staff_dashboard')

    now = timezone.localtime(timezone.now())
    day_name = now.strftime('%A') # e.g. "Monday"
    current_time_str = now.strftime('%I:%M %p')
    
    hour = now.hour
    minute = now.minute
    total_minutes = hour * 60 + minute

    # Official System Timetable Period Timings (in minutes from midnight)
    # P1: 08:30 (510) - 09:30 (570)
    # P2: 09:30 (570) - 10:30 (630)
    # Tea Break: 10:30 - 10:40
    # P3: 10:40 (640) - 11:40 (700)
    # P4: 11:40 (700) - 12:40 (760)
    # Lunch Break: 12:40 - 13:30
    # P5: 13:30 (810) - 14:30 (870)
    # P6: 14:30 (870) - 15:30 (930)
    # P7: 15:30 (930) - 16:30 (990)
    
    current_period = None
    if 510 <= total_minutes < 570:
        current_period = 1
    elif 570 <= total_minutes < 630:
        current_period = 2
    elif 640 <= total_minutes < 700:
        current_period = 3
    elif 700 <= total_minutes < 760:
        current_period = 4
    elif 810 <= total_minutes < 870:
        current_period = 5
    elif 870 <= total_minutes < 930:
        current_period = 6
    elif 930 <= total_minutes < 990:
        current_period = 7

    # Optional manual period selector override via query string (e.g. ?period=3)
    requested_period = request.GET.get('period')
    if requested_period and requested_period.isdigit():
        current_period = int(requested_period)

    class_mappings = list(ClassMapping.objects.all().order_by('semester', 'class_name'))
    labs = list(Lab.objects.all().select_related('staff').order_by('name'))

    timetable_today = list(Timetable.objects.filter(day=day_name).select_related('subject', 'subject__staff', 'subject__staff_batch_b', 'staff'))
    if not timetable_today:
        timetable_today = list(Timetable.objects.all().select_related('subject', 'subject__staff', 'subject__staff_batch_b', 'staff'))

    period_map = {p: [] for p in range(1, 8)}
    for entry in timetable_today:
        if 1 <= entry.period <= 7:
            period_map[entry.period].append(entry)

    # Active period to showcase: if outside working hours, default to P3 or period with entries
    active_period = current_period
    if not active_period:
        for p in range(1, 8):
            if period_map[p]:
                active_period = p
                break
        if not active_period:
            active_period = 3

    current_entries = period_map.get(active_period, [])
    room_cards = []

    # 1. Process Classrooms
    for idx, cm in enumerate(class_mappings):
        live_entry = None
        next_entry = None
        
        # Match by subject location name or classroom FK first
        for e in current_entries:
            if e.subject:
                sub_loc = (e.subject.location_name or '').lower()
                rm_name = (cm.room_name or '').lower()
                cls_name = (cm.class_name or '').lower()
                if (rm_name and rm_name in sub_loc) or (cls_name and cls_name in sub_loc) or (getattr(e.subject, 'classroom_id', None) == cm.id):
                    live_entry = e
                    break

        # Fallback 1: Match by semester
        if not live_entry and cm.semester:
            for e in current_entries:
                if e.semester == cm.semester:
                    live_entry = e
                    break

        # Fallback 2: Match any Theory subject in active period
        if not live_entry:
            theory_entries = [e for e in current_entries if e.subject and e.subject.subject_type == 'Theory']
            if theory_entries:
                live_entry = theory_entries[idx % len(theory_entries)]

        # Fallback 3: Any entry in active period
        if not live_entry and current_entries:
            live_entry = current_entries[idx % len(current_entries)]

        next_p = (active_period % 7) + 1
        next_entries = period_map.get(next_p, [])
        if next_entries:
            next_entry = next_entries[0]

        status = 'LIVE' if (live_entry and live_entry.subject) else 'VACANT'
        status_display = '🔴 LIVE NOW' if status == 'LIVE' else '🟢 VACANT'

        day_schedule = []
        for p in range(1, 8):
            p_list = period_map.get(p, [])
            p_sub = None
            p_staff = None
            for e in p_list:
                if e.subject:
                    sub_loc = (e.subject.location_name or '').lower()
                    if (cm.room_name.lower() in sub_loc) or (cm.class_name.lower() in sub_loc) or (cm.semester and e.semester == cm.semester) or (e.subject.subject_type == 'Theory'):
                        p_sub = e.subject
                        p_staff = e.staff or e.subject.staff
                        break
            if not p_sub and p_list:
                p_sub = p_list[0].subject
                p_staff = p_list[0].staff or (p_sub.staff if p_sub else None)

            day_schedule.append({
                'period': p,
                'is_current': p == active_period,
                'subject': p_sub,
                'staff': p_staff,
            })

        room_cards.append({
            'id': f'class-{cm.id}',
            'type': 'Classroom',
            'title': cm.class_name,
            'room_name': cm.room_name,
            'semester': cm.semester or (live_entry.semester if live_entry else None),
            'incharge': None,
            'status': status,
            'status_display': status_display,
            'live_entry': live_entry,
            'next_entry': next_entry,
            'day_schedule': day_schedule,
        })

    # 2. Process Laboratories
    for idx, lab in enumerate(labs):
        live_entry = None
        next_entry = None

        for e in current_entries:
            if e.subject:
                sub_loc = (e.subject.location_name or '').lower()
                l_name = lab.name.lower()
                l_short = (lab.short_name or '').lower()
                if (l_name and l_name in sub_loc) or (l_short and l_short in sub_loc) or (getattr(e.subject, 'lab_id', None) == lab.id):
                    live_entry = e
                    break

        if not live_entry:
            lab_entries = [e for e in current_entries if e.subject and e.subject.subject_type == 'Lab']
            if lab_entries:
                live_entry = lab_entries[idx % len(lab_entries)]

        next_p = (active_period % 7) + 1
        next_entries = period_map.get(next_p, [])
        if next_entries:
            next_entry = next_entries[0]

        status = 'LIVE' if (live_entry and live_entry.subject) else 'VACANT'
        status_display = '🔴 LIVE NOW' if status == 'LIVE' else '🟢 VACANT'

        day_schedule = []
        for p in range(1, 8):
            p_list = period_map.get(p, [])
            p_sub = None
            p_staff = None
            for e in p_list:
                if e.subject:
                    sub_loc = (e.subject.location_name or '').lower()
                    if (lab.name.lower() in sub_loc) or (lab.short_name and lab.short_name.lower() in sub_loc) or (e.subject.subject_type == 'Lab'):
                        p_sub = e.subject
                        p_staff = e.staff or e.subject.staff
                        break
            if not p_sub and p_list:
                p_sub = p_list[0].subject
                p_staff = p_list[0].staff or (p_sub.staff if p_sub else None)

            day_schedule.append({
                'period': p,
                'is_current': p == active_period,
                'subject': p_sub,
                'staff': p_staff,
            })

        room_cards.append({
            'id': f'lab-{lab.id}',
            'type': 'Lab',
            'title': lab.name,
            'room_name': lab.short_name,
            'semester': live_entry.semester if live_entry else None,
            'incharge': lab.staff,
            'status': status,
            'status_display': status_display,
            'live_entry': live_entry,
            'next_entry': next_entry,
            'day_schedule': day_schedule,
        })

    total_rooms = len(room_cards)
    live_count = sum(1 for r in room_cards if r['status'] == 'LIVE')
    vacant_count = total_rooms - live_count
    classroom_count = sum(1 for r in room_cards if r['type'] == 'Classroom')
    lab_count = sum(1 for r in room_cards if r['type'] == 'Lab')

    return render(request, 'staff/live_class_visualisation.html', {
        'staff': staff,
        'day_name': day_name,
        'current_time_str': current_time_str,
        'current_period': active_period,
        'room_cards': room_cards,
        'total_rooms': total_rooms,
        'live_count': live_count,
        'vacant_count': vacant_count,
        'classroom_count': classroom_count,
        'lab_count': lab_count,
    })


def manage_marks(request, subject_id):
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')

    from .models import Subject


    subject = get_object_or_404(Subject, id=subject_id)
    current_staff = get_object_or_404(Staff, staff_id=request.session['staff_id'])

    # Access Control: HOD or Assigned Staff
    if not current_staff.is_staff_admin and subject.staff != current_staff:
        messages.error(request, "Access Denied: You are not assigned to this subject.")
        return redirect('staffs:staff_dashboard')

    # Basic Access Control completed.

    from django.db.models import Q
    # Fetch students who are CURRENTLY in this semester OR have GPA data for this semester
    students = Student.objects.filter(
        Q(current_semester=subject.semester) | 
        Q(gpa_records__semester=subject.semester)
    ).distinct().order_by('roll_number')

    # Import StudentMarks locally to ensure it is available
    from students.models import StudentMarks

    if request.method == 'POST':
        for student in students:
            test1 = request.POST.get(f'test1_{student.roll_number}')
            test2 = request.POST.get(f'test2_{student.roll_number}')
            internal = request.POST.get(f'internal_{student.roll_number}')
            
            # Clean empty strings to None
            test1 = int(test1) if test1 else None
            test2 = int(test2) if test2 else None
            internal = int(internal) if internal else None

            # Update or Create marks
            StudentMarks.objects.update_or_create(
                student=student, 
                subject=subject,
                defaults={
                    'test1_marks': test1,
                    'test2_marks': test2,
                    'internal_marks': internal
                }
            )
        messages.success(request, "Marks updated successfully.")
        return redirect('staffs:manage_marks', subject_id=subject.id)
    
    # Determine if read-only
    # HOD can view all, but should only edit if they are the assigned staff
    is_readonly = False
    if current_staff.is_staff_admin and subject.staff != current_staff:
        is_readonly = True

    # Pre-fetch existing marks for display
    student_marks_map = {}
    marks_entries = StudentMarks.objects.filter(subject=subject, student__in=students)
    for entry in marks_entries:
        student_marks_map[entry.student.roll_number] = entry

    # Correlation Logic: Fetch Claimed Grades from StudentGPA
    from students.models import StudentGPA
    claimed_grades_map = {}
    
    # Fetch GPA records for this semester for these students
    gpa_records = StudentGPA.objects.filter(student__in=students, semester=subject.semester)
    
    for record in gpa_records:
        if record.subject_data:
            # Find the grade for this specific subject
            for sub_data in record.subject_data:
                # Match by Code (Case insensitive comparison just in case)
                if sub_data.get('code', '').strip().upper() == subject.code.strip().upper():
                    grade = sub_data.get('grade', '-')
                    code = sub_data.get('code', '')
                    if grade:
                        claimed_grades_map[record.student.roll_number] = {
                            'grade': grade,
                            'code': code
                        }
                    break

    return render(request, 'staff/manage_marks.html', {
        'subject': subject,
        'students': students,
        'student_marks_map': student_marks_map,
        'claimed_grades_map': claimed_grades_map,
        'is_readonly': is_readonly
    })

def manage_attendance(request, subject_id):
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')
    
    from .models import Subject, Timetable
    from students.models import StudentAttendance
    import datetime
    import calendar
    from django.urls import reverse

    subject = get_object_or_404(Subject, id=subject_id)
    current_staff = get_object_or_404(Staff, staff_id=request.session['staff_id'])

    # --- Date Handling (Current Selected Date) ---
    date_str = request.GET.get('date')
    if date_str:
        try:
            date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
             date_obj = datetime.date.today()
    else:
        date_obj = datetime.date.today()

    # Check for Substitution
    from .models import ClassSubstitutionRequest
    is_substitute = ClassSubstitutionRequest.objects.filter(
        substitute=current_staff,
        subject=subject,
        date=date_obj,
        status='Approved'
    ).exists()

    # Access Control
    if not current_staff.is_staff_admin and subject.staff != current_staff and not is_substitute:
        messages.error(request, "Access Denied: You are not assigned to this subject.")
        return redirect('staffs:staff_dashboard')

    formatted_date = date_obj.strftime('%Y-%m-%d')
    students = Student.objects.filter(current_semester=subject.semester).order_by('roll_number')

    # Determine if read-only
    is_readonly = False
    if current_staff.is_staff_admin and subject.staff != current_staff and not is_substitute:
        is_readonly = True

    # --- POST Handler (Saving Attendance) ---
    today_date = datetime.date.today()
    now_time = datetime.datetime.now().time()

    is_upcoming = False
    upcoming_reason = ""
    if date_obj > today_date:
        is_upcoming = True
        upcoming_reason = f"Attendance cannot be marked for future date ({date_obj.strftime('%d-%b-%Y')})."

    if request.method == 'POST':
        if is_readonly or is_upcoming:
             reason = upcoming_reason if is_upcoming else "Read-only access: Cannot save attendance."
             messages.error(request, reason)
             return redirect(request.path + f"?date={formatted_date}")

        post_date_str = request.POST.get('attendance_date')
        if post_date_str:
             try:
                save_date = datetime.datetime.strptime(post_date_str, '%Y-%m-%d').date()
             except ValueError:
                save_date = date_obj
        else:
            save_date = date_obj

        # Additional check on post save_date
        if save_date > today_date:
            messages.error(request, f"Attendance cannot be marked for future date ({save_date.strftime('%d-%b-%Y')}).")
            return redirect(request.path + f"?date={save_date.strftime('%Y-%m-%d')}")

        # VALIDATION: Check Timetable
        day_name = save_date.strftime('%A')
        has_timetable = Timetable.objects.filter(semester=subject.semester, subject=subject, day=day_name).exists()
        
        is_extra_class = request.POST.get('is_extra_class')
        
        if not has_timetable and not is_extra_class:
             messages.error(request, f"Attendance cannot be marked for {formatted_date} ({day_name}). {subject.code} is not scheduled in the timetable. Check 'Extra / Special Class' to proceed.")
             return redirect(request.path + f"?date={save_date.strftime('%Y-%m-%d')}")

        # Save Logic
        class_time_str = request.POST.get('class_time')
        end_time_str = request.POST.get('end_time')
        class_time = None
        end_time = None

        if class_time_str:
            try:
                class_time = datetime.datetime.strptime(class_time_str, '%H:%M').time()
            except ValueError:
                class_time = None
        
        if end_time_str:
            try:
                end_time = datetime.datetime.strptime(end_time_str, '%H:%M').time()
            except ValueError:
                end_time = None

        count_present = 0
        count_absent = 0
        for student in students:
            status = request.POST.get(f'status_{student.roll_number}')
            if status in ['Present', 'Absent']:
                StudentAttendance.objects.update_or_create(
                    student=student, 
                    subject=subject, 
                    date=save_date,
                    time=class_time,
                    defaults={
                        'status': status,
                        'end_time': end_time
                    }
                )
                if status == 'Present': count_present += 1
                elif status == 'Absent': count_absent += 1
            else:
                # If unmarked or cleared, delete existing attendance record for this student/date/time
                StudentAttendance.objects.filter(
                    student=student,
                    subject=subject,
                    date=save_date,
                    time=class_time
                ).delete()
        
        time_msg = ""
        if class_time:
            time_msg = f" at {class_time.strftime('%I:%M %p')}"
            if end_time:
                time_msg += f" - {end_time.strftime('%I:%M %p')}"

        if count_present == 0 and count_absent == 0:
            messages.success(request, f"Attendance cleared for {save_date.strftime('%d-%b-%Y')} ({day_name}){time_msg}.")
        else:
            messages.success(request, f"Attendance saved for {save_date.strftime('%d-%b-%Y')} ({day_name}){time_msg}. {count_present} Present, {count_absent} Absent.")
        
        redirect_url = reverse('staffs:manage_attendance', kwargs={'subject_id': subject.id}) + f"?date={save_date.strftime('%Y-%m-%d')}"
        if class_time_str:
            redirect_url += f"&time={class_time_str}"
        if end_time_str:
            redirect_url += f"&end_time={end_time_str}"
        return redirect(redirect_url)

    # --- Fetch Data for List View (Selected Date) ---
    prefill_time = request.GET.get('time', '')
    prefill_end_time = request.GET.get('end_time', '')

    # Determine Timetable period for this subject on date_obj's weekday
    day_name = date_obj.strftime('%A')
    PERIOD_TIMES = {
        1: ('08:30', '09:30'),
        2: ('09:30', '10:30'),
        3: ('10:40', '11:40'),
        4: ('11:40', '12:40'),
        5: ('13:30', '14:30'),
        6: ('14:30', '15:30'),
        7: ('15:30', '16:30'),
    }
    tt_entries = Timetable.objects.filter(subject=subject, day=day_name).order_by('period')
    today_periods = []
    current_period = None

    for entry in tt_entries:
        times = PERIOD_TIMES.get(entry.period, ('--', '--'))
        start_str, end_str = times
        try:
            start_t = datetime.datetime.strptime(start_str, '%H:%M').time()
        except ValueError:
            start_t = None

        is_p_marked = False
        if start_t:
            is_p_marked = StudentAttendance.objects.filter(subject=subject, date=date_obj, time=start_t).exists()
        if not is_p_marked:
            is_p_marked = StudentAttendance.objects.filter(subject=subject, date=date_obj, time__isnull=True).exists()

        is_p_future_date = (date_obj > today_date)
        if is_p_marked:
            p_badge = "✓ Marked"
            p_class = "marked"
        elif is_p_future_date:
            p_badge = "🔒 Upcoming"
            p_class = "upcoming"
        elif date_obj == today_date and start_t and start_t > now_time:
            p_badge = "🕒 Scheduled"
            p_class = "unmarked"
        else:
            p_badge = "⚠️ Unmarked"
            p_class = "unmarked"

        is_sel = (prefill_time == start_str)
        p_info = {
            'period': entry.period,
            'badge': f"P{entry.period}",
            'label': f"P{entry.period} ({start_str}–{end_str})",
            'start': start_str,
            'end': end_str,
            'is_selected': is_sel,
            'status_badge': p_badge,
            'status_class': p_class,
            'url': f"?date={formatted_date}&time={start_str}&end_time={end_str}"
        }
        today_periods.append(p_info)
        if is_sel:
            current_period = p_info

    if not current_period and prefill_time:
        for p in today_periods:
            if p['start'] == prefill_time:
                p['is_selected'] = True
                current_period = p
                break
        if not current_period:
            current_period = {
                'period': None,
                'badge': 'Extra',
                'label': f"Extra Class ({prefill_time}–{prefill_end_time or '--'})",
                'start': prefill_time,
                'end': prefill_end_time or '--',
                'is_selected': True,
                'status_badge': '',
                'status_class': ''
            }
    elif not current_period and today_periods:
        today_periods[0]['is_selected'] = True
        current_period = today_periods[0]
        prefill_time = current_period['start']
        prefill_end_time = current_period['end']

    if is_upcoming:
        is_readonly = True

    # Fetch Attendance Records
    attendance_map = {}
    class_time_obj = None
    if prefill_time:
        try:
            class_time_obj = datetime.datetime.strptime(prefill_time, '%H:%M').time()
        except ValueError:
            class_time_obj = None

    attendance_qs = StudentAttendance.objects.filter(subject=subject, date=date_obj, student__in=students)
    if class_time_obj:
        attendance_qs = attendance_qs.filter(Q(time=class_time_obj) | Q(time__isnull=True))

    attendance_map = {entry.student.roll_number: entry.status for entry in attendance_qs}

    prev_day = (date_obj - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    next_day = (date_obj + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    today_date_str = datetime.date.today().strftime('%Y-%m-%d')

    return render(request, 'staff/manage_attendance.html', {
        'subject': subject,
        'students': students,
        'attendance_map': attendance_map,
        'current_date': formatted_date,
        'is_readonly': is_readonly,
        'is_upcoming': is_upcoming,
        'upcoming_reason': upcoming_reason,
        'prefill_time': prefill_time,
        'prefill_end_time': prefill_end_time,
        'current_period': current_period,
        'today_periods': today_periods,
        'day_name': day_name,
        'prev_day': prev_day,
        'next_day': next_day,
        'today_date': today_date_str,
    })


def attendance_calendar(request, subject_id):
    """Separate dedicated view for the Monthly Attendance Calendar."""
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')
    
    from .models import Subject, Timetable, ClassSubstitutionRequest
    from students.models import StudentAttendance
    import datetime
    import calendar
    from django.urls import reverse

    subject = get_object_or_404(Subject, id=subject_id)
    current_staff = get_object_or_404(Staff, staff_id=request.session['staff_id'])

    # Access Control
    is_substitute = ClassSubstitutionRequest.objects.filter(
        substitute=current_staff,
        subject=subject,
        status='Approved'
    ).exists()

    if not current_staff.is_staff_admin and subject.staff != current_staff and not is_substitute:
        messages.error(request, "Access Denied: You are not assigned to this subject.")
        return redirect('staffs:staff_dashboard')

    date_str = request.GET.get('date')
    if date_str:
        try:
            date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            date_obj = datetime.date.today()
    else:
        date_obj = datetime.date.today()

    cal_year = date_obj.year
    cal_month = date_obj.month
    today_date = datetime.date.today()
    now_time = datetime.datetime.now().time()
    
    cal = calendar.Calendar(firstweekday=0) # 0 = Monday
    month_days = cal.monthdatescalendar(cal_year, cal_month)
    
    PERIOD_TIMES = {
        1: ('08:30', '09:30'),
        2: ('09:30', '10:30'),
        3: ('10:40', '11:40'),
        4: ('11:40', '12:40'),
        5: ('13:30', '14:30'),
        6: ('14:30', '15:30'),
        7: ('15:30', '16:30'),
    }

    timetable_entries = Timetable.objects.filter(subject=subject).order_by('period')
    timetable_map = {}
    for entry in timetable_entries:
        if entry.day not in timetable_map:
            timetable_map[entry.day] = []
        timetable_map[entry.day].append(entry.period)
    
    # Fetch all Attendance records for this month with date and time
    attendance_records = StudentAttendance.objects.filter(
        subject=subject, 
        date__year=cal_year, 
        date__month=cal_month
    ).values('date', 'time').distinct()

    marked_slots = set()
    marked_dates = set()
    for rec in attendance_records:
        marked_dates.add(rec['date'])
        marked_slots.add((rec['date'], rec['time']))

    calendar_rows = []
    for week in month_days:
        week_data = []
        for day in week:
            is_current_month = (day.month == cal_month)
            day_classes = []
            day_has_unmarked = False
            day_has_marked = False
            
            day_name = day.strftime('%A')
            if day_name in timetable_map:
                for period_num in timetable_map[day_name]:
                    times = PERIOD_TIMES.get(period_num, ('--', '--'))
                    start_str, end_str = times
                    
                    try:
                        start_t = datetime.time(int(start_str[:2]), int(start_str[3:]))
                        end_t   = datetime.time(int(end_str[:2]), int(end_str[3:]))
                    except Exception:
                        start_t = None
                        end_t   = None

                    is_marked = False
                    if (day, start_t) in marked_slots or (day, None) in marked_slots:
                        is_marked = True

                    if is_marked:
                        p_status = 'marked'
                        p_title = f'Period {period_num}: Attendance Recorded'
                        day_has_marked = True
                    elif day < today_date or (day == today_date and end_t and now_time > end_t):
                        p_status = 'unmarked'
                        p_title = f'Period {period_num}: Class Done • Attendance Not Marked'
                        day_has_unmarked = True
                    else:
                        p_status = 'future'
                        p_title = f'Period {period_num}: Scheduled Class'

                    day_classes.append({
                        'period': period_num,
                        'start': start_str,
                        'end': end_str,
                        'status_class': p_status,
                        'status_title': p_title,
                        'url': reverse('staffs:manage_attendance', kwargs={'subject_id': subject.id}) + f"?date={day.strftime('%Y-%m-%d')}&time={start_str}&end_time={end_str}"
                    })

            # Overall day status indicator dot
            if day_has_unmarked:
                status_class = "pending" # Needs attention
            elif day_has_marked:
                status_class = "recorded" # All marked
            elif day_classes:
                status_class = "future"
            else:
                status_class = "empty"

            week_data.append({
                'date': day,
                'day_num': day.day,
                'is_current_month': is_current_month,
                'is_selected': (day == date_obj),
                'is_today': (day == today_date),
                'classes': day_classes,
                'status_class': status_class,
                'url': reverse('staffs:manage_attendance', kwargs={'subject_id': subject.id}) + f"?date={day.strftime('%Y-%m-%d')}"
            })
        calendar_rows.append(week_data)

    if cal_month == 1:
        prev_date = datetime.date(cal_year - 1, 12, 1)
    else:
        prev_date = datetime.date(cal_year, cal_month - 1, 1)

    if cal_month == 12:
        next_date = datetime.date(cal_year + 1, 1, 1)
    else:
        next_date = datetime.date(cal_year, cal_month + 1, 1)

    return render(request, 'staff/attendance_calendar.html', {
        'subject': subject,
        'calendar_rows': calendar_rows,
        'month_name': calendar.month_name[cal_month],
        'year': cal_year,
        'prev_month_url': f"?date={prev_date.strftime('%Y-%m-%d')}",
        'next_month_url': f"?date={next_date.strftime('%Y-%m-%d')}",
        'current_date': date_obj.strftime('%Y-%m-%d'),
    })


def overall_attendance_calendar(request):
    """Monthly Overall Attendance Calendar showing all assigned subjects for the logged-in staff."""
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')

    from .models import Subject, Timetable, ClassSubstitutionRequest
    from students.models import StudentAttendance
    import datetime
    import calendar
    from django.urls import reverse

    current_staff = get_object_or_404(Staff, staff_id=request.session['staff_id'])
    assigned_subjects = current_staff.get_teaching_subjects()

    selected_subject_id = request.GET.get('subject_id')
    selected_subject = None
    if selected_subject_id and selected_subject_id != 'all':
        try:
            selected_subject = Subject.objects.get(id=selected_subject_id)
            if selected_subject not in assigned_subjects and not current_staff.is_staff_admin:
                selected_subject = None
        except (Subject.DoesNotExist, ValueError):
            selected_subject = None

    subjects_to_include = [selected_subject] if selected_subject else list(assigned_subjects)

    date_str = request.GET.get('date')
    if date_str:
        try:
            date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            date_obj = datetime.date.today()
    else:
        date_obj = datetime.date.today()

    cal_year = date_obj.year
    cal_month = date_obj.month
    today_date = datetime.date.today()
    now_time = datetime.datetime.now().time()

    cal = calendar.Calendar(firstweekday=0) # 0 = Monday
    month_days = cal.monthdatescalendar(cal_year, cal_month)

    PERIOD_TIMES = {
        1: ('08:30', '09:30'),
        2: ('09:30', '10:30'),
        3: ('10:40', '11:40'),
        4: ('11:40', '12:40'),
        5: ('13:30', '14:30'),
        6: ('14:30', '15:30'),
        7: ('15:30', '16:30'),
    }

    timetable_entries = Timetable.objects.filter(subject__in=subjects_to_include).select_related('subject').order_by('day', 'period')
    timetable_map = {}
    for entry in timetable_entries:
        if entry.day not in timetable_map:
            timetable_map[entry.day] = []
        if not any(item['period'] == entry.period and item['subject'].id == entry.subject.id for item in timetable_map[entry.day]):
            timetable_map[entry.day].append({
                'period': entry.period,
                'subject': entry.subject,
                'batch': entry.batch,
            })

    attendance_records = StudentAttendance.objects.filter(
        subject__in=subjects_to_include,
        date__year=cal_year,
        date__month=cal_month
    ).values('subject_id', 'date', 'time').distinct()

    marked_slots = set()
    for rec in attendance_records:
        marked_slots.add((rec['subject_id'], rec['date'], rec['time']))

    calendar_rows = []
    for week in month_days:
        week_data = []
        for day in week:
            is_current_month = (day.month == cal_month)
            day_classes = []
            day_has_unmarked = False
            day_has_marked = False

            day_name = day.strftime('%A')
            if day_name in timetable_map:
                sorted_entries = sorted(timetable_map[day_name], key=lambda x: x['period'])
                for item in sorted_entries:
                    period_num = item['period']
                    subj = item['subject']
                    times = PERIOD_TIMES.get(period_num, ('--', '--'))
                    start_str, end_str = times

                    try:
                        start_t = datetime.time(int(start_str[:2]), int(start_str[3:]))
                        end_t   = datetime.time(int(end_str[:2]), int(end_str[3:]))
                    except Exception:
                        start_t = None
                        end_t   = None

                    is_marked = False
                    if (subj.id, day, start_t) in marked_slots or (subj.id, day, None) in marked_slots:
                        is_marked = True

                    subj_badge = subj.code or subj.name[:6]

                    if is_marked:
                        p_status = 'marked'
                        p_title = f'Period {period_num} ({subj.name}): Attendance Recorded'
                        day_has_marked = True
                    elif day < today_date or (day == today_date and end_t and now_time > end_t):
                        p_status = 'unmarked'
                        p_title = f'Period {period_num} ({subj.name}): Class Done • Attendance Not Marked'
                        day_has_unmarked = True
                    else:
                        p_status = 'future'
                        p_title = f'Period {period_num} ({subj.name}): Scheduled Class'

                    day_classes.append({
                        'period': period_num,
                        'subject_id': subj.id,
                        'subject_badge': subj_badge,
                        'subject_name': subj.name,
                        'start': start_str,
                        'end': end_str,
                        'status_class': p_status,
                        'status_title': p_title,
                        'url': reverse('staffs:manage_attendance', kwargs={'subject_id': subj.id}) + f"?date={day.strftime('%Y-%m-%d')}&time={start_str}&end_time={end_str}"
                    })

            if day_has_unmarked:
                status_class = "pending"
            elif day_has_marked:
                status_class = "recorded"
            elif day_classes:
                status_class = "future"
            else:
                status_class = "empty"

            first_class_url = day_classes[0]['url'] if day_classes else (
                reverse('staffs:manage_attendance', kwargs={'subject_id': subjects_to_include[0].id}) + f"?date={day.strftime('%Y-%m-%d')}"
                if subjects_to_include else reverse('staffs:staff_dashboard')
            )

            week_data.append({
                'date': day,
                'day_num': day.day,
                'is_current_month': is_current_month,
                'is_selected': (day == date_obj),
                'is_today': (day == today_date),
                'classes': day_classes,
                'status_class': status_class,
                'url': first_class_url
            })
        calendar_rows.append(week_data)

    if cal_month == 1:
        prev_date = datetime.date(cal_year - 1, 12, 1)
    else:
        prev_date = datetime.date(cal_year, cal_month - 1, 1)

    if cal_month == 12:
        next_date = datetime.date(cal_year + 1, 1, 1)
    else:
        next_date = datetime.date(cal_year, cal_month + 1, 1)

    subj_param = f"&subject_id={selected_subject.id}" if selected_subject else "&subject_id=all"

    return render(request, 'staff/overall_attendance_calendar.html', {
        'assigned_subjects': assigned_subjects,
        'selected_subject': selected_subject,
        'calendar_rows': calendar_rows,
        'month_name': calendar.month_name[cal_month],
        'year': cal_year,
        'prev_month_url': f"?date={prev_date.strftime('%Y-%m-%d')}{subj_param}",
        'next_month_url': f"?date={next_date.strftime('%Y-%m-%d')}{subj_param}",
        'current_date': date_obj.strftime('%Y-%m-%d'),
        'is_overall': True,
    })

def attendance_report(request, subject_id):
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')
        
    from .models import Subject
    from students.models import StudentAttendance
    from django.db.models import Count, Q
    import datetime
    import calendar

    subject = get_object_or_404(Subject, id=subject_id)
    current_staff = get_object_or_404(Staff, staff_id=request.session['staff_id'])

    # Access Control
    if not current_staff.is_staff_admin and subject.staff != current_staff:
        messages.error(request, "Access Denied: You are not assigned to this subject.")
        return redirect('staffs:staff_dashboard')

    students = Student.objects.filter(current_semester=subject.semester).order_by('roll_number')
    
    # Filter Parameters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    search_query = request.GET.get('q')
    status_filter = request.GET.get('status')
    export_csv = request.GET.get('export')
    
    attendance_qs = StudentAttendance.objects.filter(subject=subject)
    
    # Date Filtering
    if start_date and end_date:
        attendance_qs = attendance_qs.filter(date__range=[start_date, end_date])
    
    # Calculate attendance summary
    summary_data = []
    
    # Get total working days (unique dates with attendance for this subject within filter)
    working_dates_qs = attendance_qs.values_list('date', flat=True).distinct().order_by('date')
    working_dates = list(working_dates_qs)
    total_dates = len(working_dates)
    
    # Filter Students if searching
    if search_query:
        students = students.filter(Q(student_name__icontains=search_query) | Q(roll_number__icontains=search_query))

    # Calculate stats
    total_percentage_sum = 0
    count_safe = 0      # >= 75%
    count_warning = 0   # 60-75%
    count_critical = 0  # < 60%
    
    class_total_students = Student.objects.filter(current_semester=subject.semester).count()

    for student in students:
        student_attendance = attendance_qs.filter(student=student)
        present_count = student_attendance.filter(status='Present').count()
        absent_count = student_attendance.filter(status='Absent').count()
        
        percentage = (present_count / total_dates * 100) if total_dates > 0 else 0
        total_percentage_sum += percentage

        # Determine Category
        if percentage >= 75:
            category = 'safe'
            count_safe += 1
        elif 60 <= percentage < 75:
            category = 'warning'
            count_warning += 1
        else:
            category = 'critical'
            count_critical += 1

        # Filter Logic
        if status_filter == 'safe' and category != 'safe':
            continue
        if status_filter == 'warning' and category != 'warning':
            continue
        if status_filter == 'critical' and category != 'critical':
            continue

        summary_data.append({
            'student': student,
            'present': present_count,
            'absent': absent_count,
            'percentage': round(percentage, 2),
            'category': category
        })

    # Calculate Class Average
    avg_attendance = (total_percentage_sum / len(students)) if len(students) > 0 else 0

    # EXPORT CSV LOGIC
    if export_csv:
        import csv
        from django.http import HttpResponse

        response = HttpResponse(content_type='text/csv')
        filename = f"Attendance_{subject.code}"
        if start_date and end_date:
            filename += f"_{start_date}_to_{end_date}"
        else:
            filename += "_Overall"
        filename += ".csv"
            
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)
        writer.writerow(['Roll Number', 'Student Name', 'Percentage', 'Status'])

        for data in summary_data:
            status_label = "Safe"
            if data['category'] == 'warning': status_label = "Warning"
            if data['category'] == 'critical': status_label = "Critical"
            
            writer.writerow([
                f'="{data["student"].roll_number}"', 
                data['student'].student_name, 
                f"{data['percentage']}%",
                status_label
            ])
        
        return response

    return render(request, 'staff/attendance_report.html', {
        'subject': subject,
        'summary_data': summary_data,
        'total_working_days': total_dates,
        'working_dates': working_dates,
        'current_staff': current_staff,
        # Stats
        'stats': {
            'total_students': class_total_students,
            'avg_attendance': round(avg_attendance, 1),
            'safe': count_safe,
            'warning': count_warning,
            'critical': count_critical,
        },
        # Filters context to keep form filled
        'filters': {
            'start_date': start_date,
            'end_date': end_date,
            'q': search_query,
            'status': status_filter
        }
    })



def export_marks_csv(request, subject_id):
    """Exports student marks for a specific subject to CSV."""
    import csv
    from django.http import HttpResponse
    from .models import Subject
    from students.models import StudentMarks

    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')

    subject = get_object_or_404(Subject, id=subject_id)
    students = Student.objects.filter(current_semester=subject.semester).order_by('roll_number')

    # Prepare CSV response
    response = HttpResponse(content_type='text/csv')
    filename = f"{subject.code}_marks.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    # Fetch all marks for efficiency
    marks_entries = StudentMarks.objects.filter(subject=subject) # Keep queryset for checking existence
    marks_map = {m.student.roll_number: m for m in marks_entries}

    # Determine which columns have data
    has_test1 = any(m.test1_marks is not None for m in marks_entries)
    has_test2 = any(m.test2_marks is not None for m in marks_entries)
    has_internal = any(m.internal_marks is not None for m in marks_entries)

    # Dynamic Header
    header = ['Roll Number', 'Student Name']
    if has_test1: header.append('Test 1')
    if has_test2: header.append('Test 2')
    if has_internal: header.append('Internal')
    # Removed Total as requested ("remove totals")
    
    writer = csv.writer(response)
    writer.writerow(header)

    for student in students:
        marks = marks_map.get(student.roll_number)
        
        # Last 3 digits of roll number, clean number (no quote requested: "and ` in roll no, just number is")
        roll_short = student.roll_number[-3:] if len(student.roll_number) >= 3 else student.roll_number
        if roll_short.isdigit():
             # If it's a pure number, Excel might strip leading zeros. 
             # User said "just number is", implying they don't want the quote hack. 
             # We will just write the string. Excel handles CSV digits as numbers usually (stripping 0).
             # If they want to keep 023 as 023 without quote, it's tricky in CSV for Excel.
             # But "just number is" suggests removing the quote wrapper.
             pass
        
        row = [roll_short, student.student_name]

        if has_test1:
             row.append(marks.test1_marks if marks and marks.test1_marks is not None else '')
        if has_test2:
             row.append(marks.test2_marks if marks and marks.test2_marks is not None else '')
        if has_internal:
             row.append(marks.internal_marks if marks and marks.internal_marks is not None else '')
        
        writer.writerow(row)

    return response

def staff_list(request):
    """Displays a list of staff members with search functionality."""
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')

    # Basic Check: Is this restricted to HOD? 
    # User request: "in hod dashboard i want staff directory"
    # Assuming visible to all staff (like student directory) but definitely HOD.
    # Let's verify HOD just in case, or leave it open to all staff like student list.
    # Given the prompt context "in hod dashboard", I'll make it accessible to logged in staff 
    # but primarily promoted for HOD. 
    
    query = request.GET.get('q')
    department = request.GET.get('department') # Optional filter
    
    staff_members = Staff.objects.all().order_by('name')

    if query:
        staff_members = staff_members.filter(
            Q(name__icontains=query) | 
            Q(staff_id__icontains=query) |
            Q(email__icontains=query)
        )
    
    if department:
        staff_members = staff_members.filter(department__icontains=department)

    logged_in_staff = get_object_or_404(Staff, staff_id=request.session['staff_id'])
    return render(request, 'staff/stafflist.html', {
        'staff_members': staff_members,
        'query': query,
        'departments': Staff.objects.values_list('department', flat=True).distinct(),
        'logged_in_staff': logged_in_staff,
    })
def passed_out_batches(request):
    """View to list batches (Ending Years) of passed out students."""
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')
        
    staff = Staff.objects.get(staff_id=request.session['staff_id'])
    
    # Simple access check: Only HOD should ideally access this, but can be open to staff
    if not staff.is_staff_admin:
         messages.error(request, "Access Restricted to HOD / Admin.")
         return redirect('staffs:staff_dashboard')

    # Get distinct ending years
    batches = Student.objects.values_list('ending_year', flat=True).distinct().order_by('-ending_year')
    # Filter out None and future years if needed, though user might want to see upcoming
    batches = [year for year in batches if year is not None]

    return render(request, 'staff/passed_out_batches.html', {'batches': batches, 'staff': staff})

def batch_students(request, year):
    """View to list students of a specific passed out batch."""
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')
    
    staff = Staff.objects.get(staff_id=request.session['staff_id'])
    
    students = Student.objects.filter(ending_year=year).order_by('roll_number')
    
    return render(request, 'staff/batch_students.html', {
        'year': year, 
        'students': students, 
        'student_count': students.count(),
        'staff': staff
    })

def exam_schedule(request):
    """View to display exam schedule."""
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')
        
    staff = Staff.objects.get(staff_id=request.session['staff_id'])
    
    # Get semester from GET request or default to 1
    selected_semester = request.GET.get('semester', 1)
    try:
        selected_semester = int(selected_semester)
    except ValueError:
        selected_semester = 1
        
    schedule = ExamSchedule.objects.filter(semester=selected_semester).order_by('date')
    
    return render(request, 'staff/exam_schedule.html', {
        'staff': staff,
        'schedule': schedule,
        'selected_semester': selected_semester,
        'semesters': range(1, 9)
    })

def timetable(request):
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')
        
    staff = Staff.objects.get(staff_id=request.session['staff_id'])
    if staff.is_staff_admin or staff.is_timetable_incharge:
        return hod_published_timetables(request)
    
    selected_semester = request.GET.get('semester', 1)
    try:
        selected_semester = int(selected_semester)
    except ValueError:
        selected_semester = 1
        
    selected_academic_year = request.GET.get('academic_year', '2026-2027').strip()
    existing_years = list(Timetable.objects.values_list('academic_year', flat=True).distinct())
    default_years = ['2026-2027', '2025-2026', '2024-2025', '2023-2024', '2022-2023']
    available_academic_years = sorted(list(set(default_years + [y for y in existing_years if y])), reverse=True)
    if selected_academic_year not in available_academic_years:
        selected_academic_year = '2026-2027'

    # Fetch timetable entries for selected semester & academic year
    entries = Timetable.objects.filter(academic_year=selected_academic_year, semester=selected_semester)
    
    # Structure data for the template: { 'Day': { periods... } }
    # Or just pass entries and let template handle filtering, but structured is better
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    timetable_data = {day: [None]*7 for day in days} # 7 Periods
    
    class BatchBlock:
        def __init__(self, e1, e2):
            self.is_batch = True
            self.A = e1 if e1.batch == 'A' else e2
            self.B = e2 if e2.batch == 'B' else e1
            self.staff = None

            class DummySubj:
                id = 'BATCHED'
                subject_type = 'Lab'
                code = e1.subject.code if e1.subject and e2.subject and e1.subject.id == e2.subject.id else "LAB"
                name = e1.subject.name if e1.subject and e2.subject and e1.subject.id == e2.subject.id else "Lab Session"

            self.subject = DummySubj()
            
    for entry in entries:
        if 1 <= entry.period <= 7:
            curr = timetable_data[entry.day][entry.period-1]
            if curr is None:
                timetable_data[entry.day][entry.period-1] = entry
            elif getattr(curr, 'is_batch', False):
                # Keep the first complete batch-pair representation for this slot.
                continue
            elif curr.batch in ['A', 'B'] and entry.batch in ['A', 'B'] and curr.batch != entry.batch:
                timetable_data[entry.day][entry.period-1] = BatchBlock(curr, entry)
            elif curr.batch == 'All' and entry.batch in ['A', 'B']:
                # Prefer explicit split-batch data over an older 'All' row.
                timetable_data[entry.day][entry.period-1] = entry
            elif curr.batch in ['A', 'B'] and entry.batch == 'All':
                # Keep batch entry; it better represents LAB_SESSION slots.
                continue
            else:
                timetable_data[entry.day][entry.period-1] = entry

    # Convert to list of tuples for template iteration: [('Monday', [p1, p2...]), ...]
    timetable_rows = []
    for day in days:
        timetable_rows.append((day, timetable_data[day]))
             
    return render(request, 'staff/timetable.html', {
        'staff': staff,
        'timetable_rows': timetable_rows,
        'selected_semester': selected_semester,
        'selected_academic_year': selected_academic_year,
        'available_academic_years': available_academic_years,
        'semesters': range(1, 9)
    })

def assign_lab_batches(request):
    """View to assign students to Batch A or Batch B."""
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')
        
    staff = Staff.objects.get(staff_id=request.session['staff_id'])
    
    if not staff.is_staff_admin and not staff.is_timetable_incharge:
        messages.error(request, "Access Denied: Only HOD or Timetable Incharge can assign batches.")
        return redirect('staffs:staff_dashboard')

    from students.models import Student
    from django.db import transaction

    selected_semester = request.POST.get('semester') or request.GET.get('semester') or 1
    try:
        selected_semester = int(selected_semester)
    except (ValueError, TypeError):
        selected_semester = 1

    if request.method == 'POST':
        students = list(Student.objects.filter(current_semester=selected_semester).exclude(program_level='PHD'))
        rep_a_count = 0
        rep_b_count = 0
        
        for student in students:
            is_rep = request.POST.get(f'rep_{student.roll_number}') == 'true'
            batch_val = request.POST.get(f'batch_{student.roll_number}', '').strip() or None
            if is_rep:
                if batch_val == 'A':
                    rep_a_count += 1
                elif batch_val == 'B':
                    rep_b_count += 1
                else:
                    messages.error(request, f"Error: {student.student_name} ({student.roll_number}) is selected as Class Representative but is not assigned to Batch A or B.")
                    return redirect(f'/staffs/assign-batches/?semester={selected_semester}')

        if rep_a_count > 2 or rep_b_count > 2:
            messages.error(request, "Error: Batch A or B cannot have more than 2 Class Representatives.")
            return redirect(f'/staffs/assign-batches/?semester={selected_semester}')

        with transaction.atomic():
            for student in students:
                batch_val = request.POST.get(f'batch_{student.roll_number}', '').strip() or None
                is_rep = request.POST.get(f'rep_{student.roll_number}') == 'true'
                student.lab_batch = batch_val
                student.is_class_representative = is_rep
                student.save(update_fields=['lab_batch', 'is_class_representative'])

        messages.success(request, f'Lab batches & Representatives updated successfully for Semester {selected_semester}.')
        return redirect(f'/staffs/assign-batches/?semester={selected_semester}')

    students_list = Student.objects.filter(current_semester=selected_semester).exclude(program_level='PHD').order_by('roll_number')
    phd_student = Student.objects.filter(current_semester=selected_semester, program_level='PHD').first()
    batch_a_students = [s for s in students_list if s.lab_batch == 'A']
    batch_b_students = [s for s in students_list if s.lab_batch == 'B']
    unassigned_students = [s for s in students_list if not s.lab_batch]

    return render(request, 'staff/assign_batches.html', {
        'staff': staff,
        'selected_semester': selected_semester,
        'students_list': students_list,
        'students': students_list,
        'batch_a_students': batch_a_students,
        'batch_b_students': batch_b_students,
        'unassigned_students': unassigned_students,
        'phd_student': phd_student,
        'semesters': range(1, 9),
    })

def edit_timetable(request, semester):
    """View to edit weekly timetable. Restricted to HOD."""
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')
        
    staff = Staff.objects.get(staff_id=request.session['staff_id'])
    
    if not staff.is_staff_admin and not staff.is_timetable_incharge:
        messages.error(request, 'Access Denied: Only HOD or Timetable Incharge can edit the timetable.')
        return redirect('staffs:timetable')
        
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    periods = range(1, 8)
    
    from .models import Subject
    # Get all subjects for this semester to populate dropdowns
    subjects = Subject.objects.filter(semester=semester)
    # Get all active staff to populate dropdowns
    all_staff = Staff.objects.filter(is_active=True).order_by('name')
    
    selected_academic_year = request.GET.get('academic_year') or request.POST.get('academic_year') or '2026-2027'
    selected_academic_year = selected_academic_year.strip()
    existing_years = list(Timetable.objects.values_list('academic_year', flat=True).distinct())
    default_years = ['2026-2027', '2025-2026', '2024-2025', '2023-2024', '2022-2023']
    available_academic_years = sorted(list(set(default_years + [y for y in existing_years if y])), reverse=True)
    if selected_academic_year not in available_academic_years:
        selected_academic_year = '2026-2027'

    # Check current batch mode
    current_batch = request.GET.get('batch', 'All')
    if request.method == 'POST':
        current_batch = request.POST.get('current_batch', 'All')
    if current_batch not in ['All', 'A', 'B']:
        current_batch = 'All'
        
    if request.method == 'POST':
        from .utils import send_staff_notification
        from django.db import transaction
        VIRTUAL_SLOTS = ['LAB_SESSION', 'PLACEMENT', 'LIBRARY']
        MORNING_LAB_BLOCKS = [(1, 2, 3), (2, 3, 4)]
        AFTERNOON_LAB_BLOCK = (5, 6, 7)
        
        lab_subject_ids = set(str(sid) for sid in Subject.objects.filter(semester=semester, subject_type='Lab').values_list('id', flat=True))

        def is_3hr_lab(val):
            if not val:
                return False
            return val == 'LAB_SESSION' or val in lab_subject_ids

        # Pre-parse form input into a grid dictionary
        post_grid = {}
        for day in days:
            post_grid[day] = {}
            for period in periods:
                post_grid[day][period] = (request.POST.get(f'subject_{day}_{period}') or '').strip()

        # Apply 3-hour propagation for 3-hour labs (explicit Lab subject or LAB_SESSION)
        for day in days:
            # Morning Lab Block 1: P1 -> P1, P2, P3
            if is_3hr_lab(post_grid[day][1]):
                if not post_grid[day][2] or is_3hr_lab(post_grid[day][2]):
                    post_grid[day][2] = post_grid[day][1]
                if not post_grid[day][3] or is_3hr_lab(post_grid[day][3]):
                    post_grid[day][3] = post_grid[day][1]

            # Morning Lab Block 2: P2 -> P2, P3, P4
            elif is_3hr_lab(post_grid[day][2]):
                if not post_grid[day][3] or is_3hr_lab(post_grid[day][3]):
                    post_grid[day][3] = post_grid[day][2]
                if not post_grid[day][4] or is_3hr_lab(post_grid[day][4]):
                    post_grid[day][4] = post_grid[day][2]

            # Afternoon Lab Block: P5 -> P5, P6, P7
            if is_3hr_lab(post_grid[day][5]):
                if not post_grid[day][6] or is_3hr_lab(post_grid[day][6]):
                    post_grid[day][6] = post_grid[day][5]
                if not post_grid[day][7] or is_3hr_lab(post_grid[day][7]):
                    post_grid[day][7] = post_grid[day][5]

        with transaction.atomic():
            for day in days:
                for period in periods:
                    sub_val = post_grid[day][period]
                    lab_a_val = request.POST.get(f'lab_a_{day}_{period}')
                    lab_b_val = request.POST.get(f'lab_b_{day}_{period}')
                    
                    if sub_val == 'LAB_SESSION' and (not lab_a_val or not lab_b_val):
                        related_periods = []
                        for block in MORNING_LAB_BLOCKS + [AFTERNOON_LAB_BLOCK]:
                            if period in block:
                                related_periods = block
                                break
                        for p in related_periods:
                            if not lab_a_val:
                                lab_a_val = request.POST.get(f'lab_a_{day}_{p}') or lab_a_val
                            if not lab_b_val:
                                lab_b_val = request.POST.get(f'lab_b_{day}_{p}') or lab_b_val
                    
                    # Fetch existing entries for all batches for this academic year
                    entries = list(Timetable.objects.filter(academic_year=selected_academic_year, semester=semester, day=day, period=period))
                    
                    # Helper to manage creation/update of a batch entry
                    def handle_batch_entry(batch_val, subj_id, virtual_sub=None):
                        batch_entry = next((e for e in entries if e.batch == batch_val), None)
                        
                        if virtual_sub:
                            b_subject = None
                            b_staff = None
                        else:
                            b_subject = Subject.objects.filter(id=subj_id).first() if subj_id else None
                            b_staff = b_subject.staff if b_subject else None

                        if not b_subject and not virtual_sub:
                            if batch_entry and batch_entry.pk is not None:
                                if batch_entry.staff:
                                    send_staff_notification(batch_entry.staff, "📅 Timetable Updated", f"You have been removed from {day} Period {period}.", url="/staffs/my-timetable/")
                                batch_entry.delete()
                            return
                        
                        if batch_entry:
                            changed = False
                            old_staff = batch_entry.staff
                            if batch_entry.subject != b_subject:
                                batch_entry.subject = b_subject
                                changed = True
                            if batch_entry.staff != b_staff:
                                batch_entry.staff = b_staff
                                changed = True
                            
                            if changed:
                                batch_entry.save()
                                if b_staff and old_staff != b_staff:
                                    send_staff_notification(b_staff, "📅 Timetable Updated", f"You've been assigned {b_subject.code if b_subject else 'a class'} on {day} Period {period} (Batch {batch_val}).", url="/staffs/my-timetable/")
                                if old_staff and old_staff != b_staff:
                                    send_staff_notification(old_staff, "📅 Timetable Updated", f"You are no longer assigned to {day} Period {period} (Batch {batch_val}).", url="/staffs/my-timetable/")
                        else:
                            try:
                                new_entry = Timetable.objects.create(
                                    academic_year=selected_academic_year,
                                    semester=semester,
                                    day=day,
                                    period=period,
                                    subject=b_subject,
                                    staff=b_staff,
                                    batch=batch_val
                                )
                                if b_staff:
                                    send_staff_notification(b_staff, "📅 Timetable Assigned", f"You have been assigned {b_subject.code if b_subject else 'a class'} on {day} Period {period} (Batch {batch_val}).", url="/staffs/my-timetable/")
                            except IntegrityError:
                                pass

                    if current_batch == 'All':
                        if sub_val == 'LAB_SESSION':
                            if not lab_a_val and not lab_b_val and any(e.batch in ['A', 'B'] for e in entries):
                                continue

                            for entry in entries:
                                if entry.batch == 'All' and entry.pk is not None:
                                    if entry.staff:
                                        send_staff_notification(entry.staff, "📅 Timetable Updated", f"You have been removed from {day} Period {period}.", url="/staffs/my-timetable/")
                                    entry.delete()
                            
                            handle_batch_entry('A', lab_a_val)
                            handle_batch_entry('B', lab_b_val)
                        else:
                            for entry in entries:
                                if entry.batch in ['A', 'B'] and entry.pk is not None:
                                    if entry.staff:
                                        send_staff_notification(entry.staff, "📅 Timetable Updated", f"You have been removed from {day} Period {period} (Batch {entry.batch}).", url="/staffs/my-timetable/")
                                    entry.delete()
                            
                            if not sub_val:
                                for entry in entries:
                                    if entry.pk is not None:
                                        if entry.staff:
                                            send_staff_notification(entry.staff, "📅 Timetable Updated", f"You have been removed from {day} Period {period}.", url="/staffs/my-timetable/")
                                        entry.delete()
                            else:
                                virt_lbl = sub_val if sub_val in VIRTUAL_SLOTS else None
                                subj_id_to_use = None if virt_lbl else sub_val
                                handle_batch_entry('All', subj_id_to_use, virtual_sub=virt_lbl)
                                
                    else:
                        if not sub_val:
                            for entry in entries:
                                if entry.batch == current_batch and entry.pk is not None:
                                    if entry.staff:
                                        send_staff_notification(entry.staff, "📅 Timetable Updated", f"You have been removed from {day} Period {period} (Batch {current_batch}).", url="/staffs/my-timetable/")
                                    entry.delete()
                        else:
                            virt_lbl = sub_val if sub_val in VIRTUAL_SLOTS else None
                            subj_id_to_use = None if virt_lbl else sub_val
                            
                            b_subject = Subject.objects.filter(id=subj_id_to_use).first() if subj_id_to_use else None
                            b_staff = b_subject.staff if b_subject else None
                            
                            all_entry = next((e for e in entries if e.batch == 'All'), None)
                            if all_entry:
                                other_batch = 'B' if current_batch == 'A' else 'A'
                                Timetable.objects.create(
                                    academic_year=selected_academic_year,
                                    semester=semester,
                                    day=day,
                                    period=period,
                                    subject=all_entry.subject,
                                    staff=all_entry.staff,
                                    batch=other_batch
                                )
                                all_entry.delete()
                                
                            Timetable.objects.update_or_create(
                                academic_year=selected_academic_year,
                                semester=semester,
                                day=day,
                                period=period,
                                batch=current_batch,
                                defaults={'subject': b_subject, 'staff': b_staff}
                            )
                                
        # Create/update version snapshot for historical archive
        create_timetable_version_snapshot(
            academic_year=selected_academic_year,
            semester=semester,
            staff_user=staff,
            version_name=f"Updated Schedule (Sem {semester})"
        )

        messages.success(request, f'Timetable for Academic Year {selected_academic_year} Semester {semester} updated successfully.')
        return redirect(f'/staffs/hod/published-timetables/?semester={semester}&academic_year={selected_academic_year}&tab=edit')
        
    # GET Request: Fetch timetable entries for selected semester & academic year
    entries = Timetable.objects.filter(academic_year=selected_academic_year, semester=semester).select_related('subject', 'staff')
    timetable_data = {day: [None]*7 for day in days}
    
    class BatchBlock:
        def __init__(self, e1, e2):
            self.is_batch = True
            self.A = e1 if e1.batch == 'A' else e2
            self.B = e2 if e2.batch == 'B' else e1
            self.staff = None
            class DummySubj:
                id = 'LAB_SESSION'
                subject_type = 'Lab'
                code = e1.subject.code if e1.subject and e2.subject and e1.subject.id == e2.subject.id else "LAB"
                name = e1.subject.name if e1.subject and e2.subject and e1.subject.id == e2.subject.id else "Lab Session"
            self.subject = DummySubj()

    if current_batch == 'All':
        for entry in entries:
            if 1 <= entry.period <= 7:
                curr = timetable_data[entry.day][entry.period-1]
                if curr is None:
                    timetable_data[entry.day][entry.period-1] = entry
                elif getattr(curr, 'is_batch', False):
                    continue
                elif curr.batch in ['A', 'B'] and entry.batch in ['A', 'B'] and curr.batch != entry.batch:
                    timetable_data[entry.day][entry.period-1] = BatchBlock(curr, entry)
                elif curr.batch == 'All' and entry.batch in ['A', 'B']:
                    timetable_data[entry.day][entry.period-1] = entry
                elif curr.batch in ['A', 'B'] and entry.batch == 'All':
                    continue
                else:
                    timetable_data[entry.day][entry.period-1] = entry
    else:
        for entry in entries:
            if 1 <= entry.period <= 7:
                curr = timetable_data[entry.day][entry.period-1]
                if entry.batch == current_batch:
                    timetable_data[entry.day][entry.period-1] = entry
                elif entry.batch == 'All':
                    if curr is None or curr.batch != current_batch:
                        timetable_data[entry.day][entry.period-1] = entry

    timetable_rows = []
    for day in days:
        timetable_rows.append((day, timetable_data[day]))
        
    import json as _json
    # Build faculty occupancy map for conflict detection across ALL semesters for the selected academic year
    all_academic_entries = Timetable.objects.filter(
        academic_year=selected_academic_year
    ).select_related('staff', 'subject', 'subject__staff', 'subject__staff_batch_b')

    faculty_occupancy = {}
    for entry in all_academic_entries:
        staff_ids = set()
        if entry.staff_id:
            staff_ids.add(entry.staff_id)
        if entry.subject:
            if entry.subject.staff_id:
                staff_ids.add(entry.subject.staff_id)
            if entry.subject.staff_batch_b_id:
                staff_ids.add(entry.subject.staff_batch_b_id)
                
        for sid in staff_ids:
            key = f"{entry.day}_{entry.period}_{sid}"
            if key not in faculty_occupancy:
                faculty_occupancy[key] = []
            faculty_occupancy[key].append({
                'semester': entry.semester,
                'subject_code': entry.subject.code if entry.subject else 'Class',
                'subject_name': entry.subject.name if entry.subject else '',
                'staff_name': entry.staff.name if entry.staff else (entry.subject.staff.name if entry.subject and entry.subject.staff else ''),
                'batch': entry.batch
            })

    subject_staff_map = {}
    for subj in subjects:
        target_hours = 3 if subj.subject_type == 'Lab' else getattr(subj, 'credits', 3)
        if target_hours <= 0:
            target_hours = 3 if subj.subject_type == 'Lab' else 4

        subject_staff_map[str(subj.id)] = {
            'id': subj.id,
            'code': subj.code,
            'name': subj.name,
            'type': subj.subject_type,
            'credits': getattr(subj, 'credits', 3),
            'target_hours': target_hours,
            'staff_id': subj.staff.staff_id if subj.staff else None,
            'staff': subj.staff.name if subj.staff else '—',
            'staff_b_id': subj.staff_batch_b.staff_id if subj.staff_batch_b else None,
            'staff_b': subj.staff_batch_b.name if subj.staff_batch_b else '—',
            'location': subj.get_location_display() if hasattr(subj, 'get_location_display') else ''
        }
    
    return render(request, 'staff/edit_timetable.html', {
        'staff': staff,
        'semester': semester,
        'timetable_rows': timetable_rows,
        'subjects': subjects,
        'subject_staff_map_json': _json.dumps(subject_staff_map),
        'faculty_occupancy_json': _json.dumps(faculty_occupancy),
        'current_batch': current_batch,
        'selected_academic_year': selected_academic_year,
        'available_academic_years': available_academic_years,
    })

import json as _json_module

def create_timetable_version_snapshot(academic_year, semester, staff_user, from_date_val=None, to_date_val=None, version_name_val=None, version_name=None):
    """
    Saves a published/updated timetable snapshot forever in PublishedTimetableVersion.
    """
    from .models import Timetable, PublishedTimetableVersion
    import datetime
    from django.core.serializers.json import DjangoJSONEncoder

    entries = Timetable.objects.filter(academic_year=academic_year, semester=semester).select_related('subject', 'staff')
    if not entries.exists():
        return None

    if not from_date_val:
        first_with_from = entries.filter(from_date__isnull=False).first()
        from_date_val = first_with_from.from_date if first_with_from else datetime.date.today()
    if not to_date_val:
        first_with_to = entries.filter(to_date__isnull=False).first()
        to_date_val = first_with_to.to_date if first_with_to else (from_date_val + datetime.timedelta(days=150))

    version_name_to_use = version_name or version_name_val
    if not version_name_to_use:
        version_count = PublishedTimetableVersion.objects.filter(academic_year=academic_year, semester=semester).count() + 1
        version_name_to_use = f"v{version_count}.0"

    version_name_final = str(version_name_to_use or "Published Version")

    snapshot_list = []
    for e in entries:
        snapshot_list.append({
            'day': e.day,
            'period': e.period,
            'batch': e.batch,
            'subject_code': e.subject.code if e.subject else '',
            'subject_name': e.subject.name if e.subject else '',
            'subject_type': e.subject.subject_type if e.subject else '',
            'staff_name': e.staff.name if e.staff else '',
            'staff_id': e.staff.staff_id if e.staff else '',
            'location_name': e.subject.get_location_display() if (e.subject and hasattr(e.subject, 'get_location_display')) else ''
        })

    json_payload = _json_module.dumps(snapshot_list, cls=DjangoJSONEncoder)

    PublishedTimetableVersion.objects.filter(academic_year=academic_year, semester=semester).update(is_active=False)
    entries.update(from_date=from_date_val, to_date=to_date_val)

    ver_obj = PublishedTimetableVersion.objects.create(
        academic_year=academic_year,
        semester=semester,
        version_name=version_name_final,
        from_date=from_date_val,
        to_date=to_date_val,
        published_by=staff_user,
        is_active=True,
        timetable_data_json=json_payload
    )
    return ver_obj


def parse_snapshot_grid(snapshot_json):
    """
    Parses a snapshot JSON into 5-day x 7-period rows for template rendering, supporting split batches (A/B).
    """
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    grid = {day: [None]*7 for day in days}
    try:
        data = _json_module.loads(snapshot_json)
        for item in data:
            d = item.get('day')
            p = item.get('period')
            if d in grid and 1 <= p <= 7:
                curr = grid[d][p - 1]
                batch = item.get('batch', 'All')

                if curr is None:
                    if batch in ['A', 'B']:
                        grid[d][p - 1] = {
                            'is_batch': True,
                            'A': item if batch == 'A' else None,
                            'B': item if batch == 'B' else None
                        }
                    else:
                        grid[d][p - 1] = item
                elif isinstance(curr, dict) and curr.get('is_batch'):
                    if batch == 'A':
                        curr['A'] = item
                    elif batch == 'B':
                        curr['B'] = item
                elif isinstance(curr, dict) and curr.get('batch') in ['A', 'B'] and batch in ['A', 'B'] and curr.get('batch') != batch:
                    old_item = curr
                    grid[d][p - 1] = {
                        'is_batch': True,
                        'A': old_item if old_item.get('batch') == 'A' else item,
                        'B': item if batch == 'B' else old_item
                    }
                else:
                    grid[d][p - 1] = item
    except Exception:
        pass
    return [(d, grid[d]) for d in days]


def hod_published_timetables(request):
    """
    Dedicated view for HOD & Timetable Incharges to view all saved and published timetables
    across academic years, semesters (1-8), and batches (All, Batch A, Batch B), along with assigned staff breakdowns
    and historical saved versions with effective from/to dates.
    """
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')
        
    staff = Staff.objects.get(staff_id=request.session['staff_id'])
    
    if not staff.is_staff_admin and not staff.is_timetable_incharge:
        messages.error(request, "Access Denied: Only HOD or Timetable Incharge can view Master Published Timetables.")
        return redirect('staffs:staff_dashboard')

    import datetime
    from .models import PublishedTimetableVersion

    selected_academic_year = request.GET.get('academic_year', '2026-2027').strip()
    existing_years = list(Timetable.objects.values_list('academic_year', flat=True).distinct())
    default_years = ['2026-2027', '2025-2026', '2024-2025', '2023-2024', '2022-2023']
    available_academic_years = sorted(list(set(default_years + [y for y in existing_years if y])), reverse=True)
    if selected_academic_year not in available_academic_years:
        selected_academic_year = '2026-2027'

    selected_semester = request.GET.get('semester', 1)
    try:
        selected_semester = int(selected_semester)
        if selected_semester < 1 or selected_semester > 8:
            selected_semester = 1
    except (ValueError, TypeError):
        selected_semester = 1

    selected_batch = request.GET.get('batch', 'All')
    if selected_batch not in ['All', 'A', 'B']:
        selected_batch = 'All'

    active_tab = request.GET.get('tab', 'master')

    # Handle POST Actions (Effect Dates, Timetable Grid Save, Batch Assignment)
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'set_effect_dates':
            from_date_str = request.POST.get('from_date')
            to_date_str = request.POST.get('to_date')
            from_date_val = None
            to_date_val = None
            if from_date_str:
                try:
                    from_date_val = datetime.datetime.strptime(from_date_str, '%Y-%m-%d').date()
                except ValueError:
                    pass
            if to_date_str:
                try:
                    to_date_val = datetime.datetime.strptime(to_date_str, '%Y-%m-%d').date()
                except ValueError:
                    pass

            if from_date_val and to_date_val:
                ver_obj = create_timetable_version_snapshot(
                    academic_year=selected_academic_year,
                    semester=selected_semester,
                    staff_user=staff,
                    from_date_val=from_date_val,
                    to_date_val=to_date_val,
                    version_name_val=f"Effective Period ({from_date_val.strftime('%d-%b')} to {to_date_val.strftime('%d-%b-%Y')})"
                )
                messages.success(request, f"Effective Date Range saved for Semester {selected_semester}: From {from_date_val.strftime('%d-%b-%Y')} to {to_date_val.strftime('%d-%b-%Y')}.")
                return redirect(f"/staffs/hod/published-timetables/?academic_year={selected_academic_year}&semester={selected_semester}&tab=master")

        elif action == 'assign_batches':
            from students.models import Student
            from django.db import transaction
            
            students = list(Student.objects.filter(current_semester=selected_semester).exclude(program_level='PHD'))
            rep_a_count = 0
            rep_b_count = 0
            
            for student in students:
                is_rep = request.POST.get(f'rep_{student.roll_number}') == 'true'
                batch_val = request.POST.get(f'batch_{student.roll_number}', '').strip() or None
                if is_rep:
                    if batch_val == 'A':
                        rep_a_count += 1
                    elif batch_val == 'B':
                        rep_b_count += 1
                    else:
                        messages.error(request, f"Error: {student.student_name} ({student.roll_number}) is selected as Class Representative but is not assigned to Batch A or B.")
                        return redirect(f'/staffs/hod/published-timetables/?academic_year={selected_academic_year}&semester={selected_semester}&tab=batches')

            if rep_a_count > 2 or rep_b_count > 2:
                messages.error(request, "Error: Batch A or B cannot have more than 2 Class Representatives.")
                return redirect(f'/staffs/hod/published-timetables/?academic_year={selected_academic_year}&semester={selected_semester}&tab=batches')

            with transaction.atomic():
                for student in students:
                    batch_val = request.POST.get(f'batch_{student.roll_number}', '').strip() or None
                    is_rep = request.POST.get(f'rep_{student.roll_number}') == 'true'
                    student.lab_batch = batch_val
                    student.is_class_representative = is_rep
                    student.save(update_fields=['lab_batch', 'is_class_representative'])

            messages.success(request, f'Lab batches & Representatives updated successfully for Semester {selected_semester}.')
            return redirect(f'/staffs/hod/published-timetables/?academic_year={selected_academic_year}&semester={selected_semester}&tab=batches')

    # Semester Summary Cards for selected academic year (Sem 1 to 8)
    semesters_summary = []
    for sem in range(1, 9):
        sem_entries = Timetable.objects.filter(academic_year=selected_academic_year, semester=sem)
        total_slots = sem_entries.count()
        is_pub = sem_entries.filter(is_published=True).exists() if total_slots > 0 else False
        assigned_faculty_count = sem_entries.filter(staff__isnull=False).values('staff').distinct().count()
        subject_count = Subject.objects.filter(semester=sem).count()
        
        semesters_summary.append({
            'semester': sem,
            'total_slots': total_slots,
            'is_published': is_pub,
            'assigned_faculty_count': assigned_faculty_count,
            'subject_count': subject_count,
            'is_selected': (sem == selected_semester)
        })

    # Fetch entries for selected academic year and semester
    entries = Timetable.objects.filter(academic_year=selected_academic_year, semester=selected_semester).select_related('subject', 'staff')
    semester_is_published = entries.filter(is_published=True).exists() if entries.exists() else False

    # Fetch previous timetable versions saved forever
    previous_versions_qs = PublishedTimetableVersion.objects.filter(
        academic_year=selected_academic_year,
        semester=selected_semester
    ).select_related('published_by').order_by('-published_at')

    previous_timetable_versions = []
    for ver in previous_versions_qs:
        ver.grid_rows = parse_snapshot_grid(ver.timetable_data_json)
        previous_timetable_versions.append(ver)

    active_ver = previous_versions_qs.filter(is_active=True).first() or previous_versions_qs.first()
    current_from_date = active_ver.from_date if (active_ver and active_ver.from_date) else datetime.date.today()
    current_to_date = active_ver.to_date if (active_ver and active_ver.to_date) else (current_from_date + datetime.timedelta(days=150))

    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    timetable_data = {day: [None]*7 for day in days}

    class BatchBlock:
        def __init__(self, e1, e2):
            self.is_batch = True
            self.A = e1 if e1.batch == 'A' else e2
            self.B = e2 if e2.batch == 'B' else e1
            self.staff = None
            class DummySubj:
                id = 'BATCHED'
                subject_type = 'Lab'
                code = e1.subject.code if e1.subject and e2.subject and e1.subject.id == e2.subject.id else "LAB"
                name = e1.subject.name if e1.subject and e2.subject and e1.subject.id == e2.subject.id else "Lab Session"
            self.subject = DummySubj()

    if selected_batch == 'All':
        for entry in entries:
            if 1 <= entry.period <= 7:
                curr = timetable_data[entry.day][entry.period-1]
                if curr is None:
                    timetable_data[entry.day][entry.period-1] = entry
                elif getattr(curr, 'is_batch', False):
                    continue
                elif curr.batch in ['A', 'B'] and entry.batch in ['A', 'B'] and curr.batch != entry.batch:
                    timetable_data[entry.day][entry.period-1] = BatchBlock(curr, entry)
                elif curr.batch == 'All' and entry.batch in ['A', 'B']:
                    timetable_data[entry.day][entry.period-1] = entry
                elif curr.batch in ['A', 'B'] and entry.batch == 'All':
                    continue
                else:
                    timetable_data[entry.day][entry.period-1] = entry
    else:
        for entry in entries:
            if 1 <= entry.period <= 7:
                curr = timetable_data[entry.day][entry.period-1]
                if entry.batch == selected_batch:
                    timetable_data[entry.day][entry.period-1] = entry
                elif entry.batch == 'All':
                    if curr is None or curr.batch != selected_batch:
                        timetable_data[entry.day][entry.period-1] = entry

    def build_row_cells(periods):
        period_to_col = {0: 0, 1: 1, 2: 3, 3: 4, 4: 6, 5: 7, 6: 8}
        col_to_period = {v: k for k, v in period_to_col.items()}
        break_cols = {2: 'TEA', 5: 'LUNCH'}
        total_cols = 9

        cells = []
        for col in range(total_cols):
            if col in break_cols:
                cells.append({'type': 'break', 'label': break_cols[col], 'skip': False})
            else:
                p_idx = col_to_period[col]
                cells.append({'type': 'period', 'entry': periods[p_idx], 'colspan': 1, 'skip': False})

        i = 0
        while i < total_cols:
            if cells[i].get('type') == 'period' and not cells[i].get('skip'):
                entry = cells[i]['entry']
                if entry and getattr(entry, 'subject', None):
                    j = i + 1
                    span = 1
                    while j < total_cols:
                        c = cells[j]
                        if c['type'] == 'break':
                            if j + 1 < total_cols and cells[j+1].get('type') == 'period':
                                next_e = cells[j+1]['entry']
                                if next_e and getattr(next_e, 'subject', None) and getattr(next_e.subject, 'id', None) == getattr(entry.subject, 'id', None):
                                    c['skip'] = True
                                    cells[j+1]['skip'] = True
                                    span += 2
                                    j += 2
                                    continue
                            break
                        elif c['type'] == 'period':
                            next_e = c['entry']
                            if next_e and getattr(next_e, 'subject', None) and getattr(next_e.subject, 'id', None) == getattr(entry.subject, 'id', None):
                                c['skip'] = True
                                span += 1
                                j += 1
                                continue
                            break
                        j += 1
                    cells[i]['colspan'] = span
            i += 1
        return cells

    timetable_rows = [(day, build_row_cells(timetable_data[day])) for day in days]

    # Build Course & Assigned Staff Allocation List for this semester
    subjects = Subject.objects.filter(semester=selected_semester).select_related('staff')
    subject_allocation_list = []
    
    for subj in subjects:
        subj_entries = entries.filter(subject=subj)
        periods_count = subj_entries.count()
        
        assigned_staff_set = set()
        if subj.staff:
            assigned_staff_set.add(subj.staff)
        for e in subj_entries:
            if e.staff:
                assigned_staff_set.add(e.staff)
                
        schedule_details = []
        for e in subj_entries.order_by('day', 'period'):
            schedule_details.append(f"{e.day[:3]} P{e.period} ({e.batch})")
            
        subject_allocation_list.append({
            'subject': subj,
            'assigned_staff_list': list(assigned_staff_set),
            'primary_staff': subj.staff,
            'periods_count': periods_count,
            'schedule_summary': ", ".join(schedule_details) if schedule_details else "Not Scheduled",
            'is_assigned': len(assigned_staff_set) > 0
        })

    # Build context for Tab 2: Interactive Editor
    subjects_list = list(Subject.objects.filter(semester=selected_semester).order_by('code'))
    all_staff = Staff.objects.filter(is_active=True).order_by('name')

    # Build faculty occupancy map for conflict detection across ALL semesters for the selected academic year
    all_academic_entries = Timetable.objects.filter(
        academic_year=selected_academic_year
    ).select_related('staff', 'subject', 'subject__staff', 'subject__staff_batch_b')

    faculty_occupancy = {}
    for entry in all_academic_entries:
        staff_ids = set()
        if entry.staff_id:
            staff_ids.add(entry.staff_id)
        if entry.subject:
            if entry.subject.staff_id:
                staff_ids.add(entry.subject.staff_id)
            if entry.subject.staff_batch_b_id:
                staff_ids.add(entry.subject.staff_batch_b_id)
                
        for sid in staff_ids:
            key = f"{entry.day}_{entry.period}_{sid}"
            if key not in faculty_occupancy:
                faculty_occupancy[key] = []
            faculty_occupancy[key].append({
                'semester': entry.semester,
                'subject_code': entry.subject.code if entry.subject else 'Class',
                'subject_name': entry.subject.name if entry.subject else '',
                'staff_name': entry.staff.name if entry.staff else (entry.subject.staff.name if entry.subject and entry.subject.staff else ''),
                'batch': entry.batch
            })

    subject_staff_map = {}
    for subj in subjects_list:
        target_hours = 3 if subj.subject_type == 'Lab' else getattr(subj, 'credits', 3)
        if target_hours <= 0:
            target_hours = 3 if subj.subject_type == 'Lab' else 4

        subject_staff_map[str(subj.id)] = {
            'id': subj.id,
            'code': subj.code,
            'name': subj.name,
            'type': subj.subject_type,
            'credits': getattr(subj, 'credits', 3),
            'target_hours': target_hours,
            'staff_id': subj.staff.staff_id if subj.staff else None,
            'staff': subj.staff.name if subj.staff else '—',
            'staff_b_id': subj.staff_batch_b.staff_id if subj.staff_batch_b else None,
            'staff_b': subj.staff_batch_b.name if subj.staff_batch_b else '—',
            'location': subj.get_location_display() if hasattr(subj, 'get_location_display') else ''
        }

    edit_timetable_data = {day: [None]*7 for day in days}
    for entry in entries:
        if 1 <= entry.period <= 7:
            curr = edit_timetable_data[entry.day][entry.period-1]
            if curr is None or entry.batch == 'All':
                edit_timetable_data[entry.day][entry.period-1] = entry
    edit_timetable_rows = [(day, edit_timetable_data[day]) for day in days]

    # Build context for Tab 3: Lab Batch Assignments
    from students.models import Student
    students_list = Student.objects.filter(current_semester=selected_semester).exclude(program_level='PHD').order_by('roll_number')
    batch_a_students = [s for s in students_list if s.lab_batch == 'A']
    batch_b_students = [s for s in students_list if s.lab_batch == 'B']
    unassigned_students = [s for s in students_list if not s.lab_batch]

    return render(request, 'staff/hod_published_timetables.html', {
        'staff': staff,
        'selected_semester': selected_semester,
        'selected_batch': selected_batch,
        'selected_academic_year': selected_academic_year,
        'available_academic_years': available_academic_years,
        'semesters_summary': semesters_summary,
        'timetable_rows': timetable_rows,
        'semester_is_published': semester_is_published,
        'subject_allocation_list': subject_allocation_list,
        'total_entries_count': entries.count(),
        'semesters': range(1, 9),
        'previous_timetable_versions': previous_timetable_versions,
        'current_from_date': current_from_date,
        'current_to_date': current_to_date,
        'active_tab': active_tab,
        'subjects_list': subjects_list,
        'all_staff': all_staff,
        'subject_staff_map_json': _json_module.dumps(subject_staff_map),
        'faculty_occupancy_json': _json_module.dumps(faculty_occupancy),
        'edit_timetable_rows': edit_timetable_rows,
        'students_list': students_list,
        'batch_a_students': batch_a_students,
        'batch_b_students': batch_b_students,
        'unassigned_students': unassigned_students,
    })

def toggle_publish_timetable(request, semester):
    """View to publish or unpublish all timetable slots for a semester in a specific academic year. Restricted to HOD / Timetable Incharge."""
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')
        
    staff = Staff.objects.get(staff_id=request.session['staff_id'])
    
    if not staff.is_staff_admin and not staff.is_timetable_incharge:
        messages.error(request, "Access Denied: Only HOD or Timetable Incharge can publish/unpublish timetables.")
        return redirect('staffs:staff_dashboard')
        
    academic_year = request.GET.get('academic_year', '2026-2027').strip()
    entries = Timetable.objects.filter(academic_year=academic_year, semester=semester)
    if not entries.exists():
        messages.error(request, f"No timetable entries found for Academic Year {academic_year} Semester {semester} to publish.")
        return redirect(f'/staffs/hod/published-timetables/?academic_year={academic_year}&semester={semester}')
        
    currently_published = entries.filter(is_published=True).exists()
    new_state = not currently_published
    entries.update(is_published=new_state)
    
    if new_state:
        # Create published snapshot saved forever
        create_timetable_version_snapshot(
            academic_year=academic_year,
            semester=semester,
            staff_user=staff,
            version_name=f"Published Master Timetable (Sem {semester})"
        )

    state_str = "Published & Saved Forever" if new_state else "Unpublished (Draft)"
    messages.success(request, f"Timetable for Academic Year {academic_year} Semester {semester} is now {state_str}.")
    
    next_url = request.META.get('HTTP_REFERER') or f'/staffs/hod/published-timetables/?academic_year={academic_year}&semester={semester}'
    return redirect(next_url)

def my_timetable(request):
    """
    Displays only the timetable periods assigned to the currently logged-in staff.
    Each entry is annotated with is_mine=True so the template can highlight them.
    """
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')

    import datetime

    staff = Staff.objects.get(staff_id=request.session['staff_id'])

    # Only fetch entries assigned to this staff member
    entries = Timetable.objects.filter(staff=staff).select_related('subject')

    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']

    # Build a grid: day → list of 7 slots (None or entry)
    timetable_data = {day: [None] * 7 for day in days}

    for entry in entries:
        if 1 <= entry.period <= 7:
            # Annotate entry so template can colour it
            entry.is_mine = True
            timetable_data[entry.day][entry.period - 1] = entry

    timetable_rows = [(day, timetable_data[day]) for day in days]

    today_name = datetime.date.today().strftime('%A')  # e.g. "Monday"
    has_entries = entries.exists()

    return render(request, 'staff/my_timetable.html', {
        'staff': staff,
        'timetable_rows': timetable_rows,
        'today_name': today_name,
        'has_entries': has_entries,
    })


def risk_students(request):
    """
    Dedicated view to display students at risk (Low Attendance / Low Marks).
    """
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')
    
    staff = Staff.objects.get(staff_id=request.session['staff_id'])
    
    # Imports
    from .utils import get_risk_metrics
    from .models import Subject
    
    risk_insights = []
    subjects_to_analyze = []

    if staff.is_staff_admin:
        # HOD sees all subjects
        subjects_to_analyze = Subject.objects.all().order_by('semester', 'code')
    
    elif staff.role == 'Class Incharge' and staff.assigned_semester:
        # Class Incharge sees subjects they teach + ALL subjects in their assigned semester
        teaching_subjects = staff.get_teaching_subjects()
        semester_subjects = Subject.objects.filter(semester=staff.assigned_semester)
        subjects_to_analyze = (teaching_subjects | semester_subjects).distinct().order_by('semester', 'code')
        
    else:
        # Regular Staff / Course Incharge
        subjects_to_analyze = staff.get_teaching_subjects().order_by('semester', 'code')

    # Process Risk Metrics
    for subject in subjects_to_analyze:
        risks = get_risk_metrics(subject)
        if risks:
            risk_insights.append({
                'subject': subject,
                'students': risks
            })
            
    return render(request, 'staff/risk_students.html', {
        'staff': staff,
        'risk_insights': risk_insights
    })

def export_risk_list(request, subject_id):
    """
    Exports the list of risk students for a specific subject to CSV.
    """
    import csv
    from django.http import HttpResponse
    from .models import Subject
    from .utils import get_risk_metrics

    # Check Login
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')

    staff = Staff.objects.get(staff_id=request.session['staff_id'])
    subject = get_object_or_404(Subject, id=subject_id)

    # Access Control Check (Basic) - Reusing logic:
    # HOD can access all. Staff can access if assigned.
    # We can be slightly lenient or strict. Optimally, check usage.
    # Allowing if staff is HOD OR if subject is in staff.subjects.all()
    # (Or if Class Incharge and subject in semester... simpler to stick to "can view risk page logic")
    
    can_access = False
    if staff.is_staff_admin:
        can_access = True
    elif staff.role == 'Class Incharge' and staff.assigned_semester:
        # Allow if subject is in their assigned semester OR if they teach it
        if subject.semester == staff.assigned_semester or subject in staff.get_teaching_subjects():
            can_access = True
    else:
        if subject in staff.get_teaching_subjects():
            can_access = True
            
    # If HOD, access is True. If strict access needed:
    if not can_access and not staff.is_staff_admin:
         messages.error(request, "Access Denied.")
         return redirect('staffs:risk_students')

    # Get Data
    risks = get_risk_metrics(subject)
    
    # Prepare CSV
    filename = f"Risk_Report_{subject.code}_Sem{subject.semester}.csv"
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    # Context Header
    writer.writerow([f"Subject: {subject.name} ({subject.code})", f"Semester: {subject.semester}"])
    writer.writerow([]) # Blank line
    
    # Table Header
    writer.writerow(['Roll Number', 'Student Name', 'Attendance %', 'Internal Marks', 'Risk Factors'])
    
    for student_data in risks:
        # Data structure from get_risk_metrics: 
        # {'name': ..., 'roll_number': ..., 'attendance_percentage': ..., 'internal_marks': ..., 'risk_factors': [...]}
        
        row = [
            student_data['roll_number'],
            f"{student_data['name']} (Sem {student_data['current_semester']})",
            f"{student_data['attendance_percentage']}%",
            student_data['internal_marks'],
            ", ".join(student_data['risk_factors'])
        ]
        writer.writerow(row)
        
    return response


def view_leave_requests(request):
    """View to list pending leave requests."""
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')
        
    staff = Staff.objects.get(staff_id=request.session['staff_id'])
    from students.models import LeaveRequest
    
    # Filter requests based on role
    if staff.has_role('Class Incharge') and staff.assigned_semester:
        # Class Incharge sees 'Pending Class Incharge' for their semester/batch
        leave_qs = LeaveRequest.objects.filter(
            status='Pending Class Incharge',
            student__current_semester=staff.assigned_semester
        )
        if staff.assigned_batch in ['A', 'B']:
            leave_qs = leave_qs.filter(student__lab_batch=staff.assigned_batch)
        leave_requests = leave_qs.order_by('created_at')
    elif staff.is_staff_admin:
        # HOD sees 'Pending HOD' (approved by Class Incharge)
        leave_requests = LeaveRequest.objects.filter(
            status='Pending HOD'
        ).order_by('created_at')
    else:
        leave_requests = LeaveRequest.objects.none()

    return render(request, 'staff/staff_leave_list.html', {
        'staff': staff,
        'leave_requests': leave_requests
    })

def update_leave_status(request, request_id):
    """View to approve or reject a leave request."""
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')
    
    if request.method == 'POST':
        from students.models import LeaveRequest
        leave_request = get_object_or_404(LeaveRequest, id=request_id)
        
        action = request.POST.get('action')
        reason = request.POST.get('rejection_reason', '')
        
        staff = Staff.objects.get(staff_id=request.session['staff_id'])
        
        if action == 'approve':
            if staff.role == 'Class Incharge':
                 leave_request.status = 'Pending HOD'
                 messages.success(request, f"Leave forwarded to HOD for {leave_request.student.student_name}.")
                 # Notify Student
                 from .utils import send_push_notification
                 send_push_notification(leave_request.student, "Leave Request Update", f"Forwarded to HOD by {staff.name}")
                 
                 # --- EMAIL NOTIFICATION ---
                 try:
                     from django.core.mail import send_mail
                     from django.conf import settings
                     from django.template.loader import render_to_string
                     from django.utils.html import strip_tags
                     subject = "Leave Request Status Update"
                     message = f"Hello {leave_request.student.student_name},\n\nYour leave request has been forwarded to the HOD by your Class Incharge ({staff.name}).\n\nLogin to the portal to check further updates."
                     if leave_request.student.student_email:
                         html_message = render_to_string('emails/leave_status.html', {'student_name': leave_request.student.student_name, 'message': f"Your leave request has been forwarded to the HOD by your Class Incharge ({staff.name})."})
                         send_mail(subject, strip_tags(message), settings.DEFAULT_FROM_EMAIL, [leave_request.student.student_email], html_message=html_message, fail_silently=True)
                 except Exception as e:
                     print(f"Error sending leave email: {e}")
                 # ---------------------------

            elif staff.is_staff_admin:
                leave_request.status = 'Approved'
                messages.success(request, f"Leave approved for {leave_request.student.student_name}.")
                # Notify Student
                from .utils import send_push_notification, send_staff_notification
                send_push_notification(leave_request.student, "Leave Approved ✅", f"Your leave request has been approved by HOD.")
                
                # --- EMAIL NOTIFICATION ---
                try:
                    from django.core.mail import send_mail
                    from django.conf import settings
                    from django.template.loader import render_to_string
                    from django.utils.html import strip_tags
                    subject = "Leave Request Approved"
                    message = f"Hello {leave_request.student.student_name},\n\nYour leave request has been approved by the HOD.\n\nLogin to the portal to view the details."
                    if leave_request.student.student_email:
                        html_message = render_to_string('emails/leave_status.html', {'student_name': leave_request.student.student_name, 'message': "Your leave request has been approved by the HOD."})
                        send_mail(subject, strip_tags(message), settings.DEFAULT_FROM_EMAIL, [leave_request.student.student_email], html_message=html_message, fail_silently=True)
                except Exception as e:
                    print(f"Error sending leave email: {e}")
                # ---------------------------
                
                # Notify Class Incharges
                from django.db.models import Q
                ci_qs = Staff.objects.filter(assigned_semester=leave_request.student.current_semester).filter(
                    Q(role='Class Incharge') | Q(secondary_roles__icontains='Class Incharge')
                )
                if leave_request.student.lab_batch:
                    ci_batch = ci_qs.filter(assigned_batch=leave_request.student.lab_batch)
                    if ci_batch.exists():
                        class_incharges = ci_batch
                    else:
                        class_incharges = ci_qs.filter(Q(assigned_batch='All') | Q(assigned_batch__isnull=True) | Q(assigned_batch=''))
                else:
                    class_incharges = ci_qs
                for ci in class_incharges:
                    send_staff_notification(ci, "Student Leave Approved", f"{leave_request.student.student_name} (Sem {leave_request.student.current_semester}) leave approved.", url="/staffs/view_leave_requests/")
                
        elif action == 'reject':
            leave_request.status = 'Rejected'
            leave_request.rejection_reason = reason
            leave_request.rejected_by = f"{staff.name} ({staff.role})"
            messages.warning(request, f"Leave rejected for {leave_request.student.student_name}.")
            # Notify Student
            from .utils import send_push_notification
            send_push_notification(leave_request.student, "Leave Rejected ❌", f"Reason: {reason}")
            
            # --- EMAIL NOTIFICATION ---
            try:
                from django.core.mail import send_mail
                from django.conf import settings
                from django.template.loader import render_to_string
                from django.utils.html import strip_tags
                subject = "Leave Request Rejected"
                message = f"Hello {leave_request.student.student_name},\n\nYour leave request has been rejected by {staff.name} ({staff.role}).\n\nReason: {reason}\n\nLogin to the portal to view the details."
                if leave_request.student.student_email:
                    html_message = render_to_string('emails/leave_status.html', {'student_name': leave_request.student.student_name, 'message': f"Your leave request has been rejected by {staff.name} ({staff.role}).\nReason: {reason}"})
                    send_mail(subject, strip_tags(message), settings.DEFAULT_FROM_EMAIL, [leave_request.student.student_email], html_message=html_message, fail_silently=True)
            except Exception as e:
                print(f"Error sending leave email: {e}")
            # ---------------------------
        
        leave_request.save()
        
    return redirect('staffs:view_leave_requests')

# --- Staff Leave System (Staff -> HOD) ---

def staff_apply_leave(request):
    """View for staff to apply for leave."""
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')
    
    staff = Staff.objects.get(staff_id=request.session['staff_id'])
    from .forms import StaffLeaveRequestForm
    from .models import StaffLeaveRequest
    
    if request.method == 'POST':
        form = StaffLeaveRequestForm(request.POST, staff=staff)
        if form.is_valid():
            leave_request = form.save(commit=False)
            leave_request.staff = staff
            leave_request.save()
            messages.success(request, 'Leave request submitted to HOD.')
            return redirect('staffs:staff_leave_history')
    else:
        form = StaffLeaveRequestForm(staff=staff)
    
    # Calculate Leave Balances
    import datetime
    today = datetime.date.today()
    ay_start = datetime.date(today.year, 1, 1)
    
    def get_leave_status(leave_code, limit):
        leaves = StaffLeaveRequest.objects.filter(
            staff=staff,
            leave_type=leave_code,
            status='Approved',
            start_date__gte=ay_start
        ).order_by('start_date')
        
        used = 0
        dates = []
        for l in leaves:
            d = (l.end_date - l.start_date).days + 1
            used += d
            dates.append({'start': l.start_date, 'end': l.end_date, 'days': d})
            
        balance = max(0, limit - used)
        return used, balance, dates

    cl_used, cl_balance, cl_dates = get_leave_status('CL', 12)
    rh_used, rh_balance, rh_dates = get_leave_status('Religious', 3)
    special_used, special_balance, special_dates = get_leave_status('Special', 15)
        
    return render(request, 'staff/apply_leave.html', {
        'form': form, 
        'staff': staff,
        'cl_balance': cl_balance,
        'cl_used': cl_used,
        'cl_taken_dates': cl_dates,
        'rh_balance': rh_balance,
        'rh_used': rh_used,
        'special_balance': special_balance,
        'special_used': special_used,
    })

def staff_leave_history(request):
    """View for staff to see their leave history."""
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')
        
    staff = Staff.objects.get(staff_id=request.session['staff_id'])
    from .models import StaffLeaveRequest
    
    leaves = StaffLeaveRequest.objects.filter(staff=staff).order_by('-created_at')
    
    return render(request, 'staff/my_leave_history.html', {'staff': staff, 'leaves': leaves})

def hod_leave_dashboard(request):
    """HOD view to see all staff leave requests."""
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')
        
    current_staff = Staff.objects.get(staff_id=request.session['staff_id'])
    
    # Strictly for HOD
    if not current_staff.is_staff_admin:
        messages.error(request, "Access Restricted to HOD.")
        return redirect('staffs:staff_dashboard')
        
    from .models import StaffLeaveRequest
    
    # pending requests
    pending_leaves = StaffLeaveRequest.objects.filter(status='Pending').order_by('created_at')
    
    return render(request, 'staff/hod_leave_dashboard.html', {
        'staff': current_staff,
        'leave_requests': pending_leaves
    })

def hod_update_leave_status(request, request_id):
    """HOD action to approve/reject staff leave."""
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')
        
    if request.method == 'POST':
        from .models import StaffLeaveRequest
        leave_request = get_object_or_404(StaffLeaveRequest, id=request_id)
        
        # Verify HOD access again for security
        current_staff = Staff.objects.get(staff_id=request.session['staff_id'])
        if not current_staff.is_staff_admin:
             messages.error(request, "Unauthorized action.")
             return redirect('staffs:staff_dashboard')

        action = request.POST.get('action')
        reason = request.POST.get('rejection_reason', '')
        
        if action == 'approve':
            leave_request.status = 'Approved'
            messages.success(request, f"Approved leave for {leave_request.staff.name}.")
            # Notify Staff
            from .utils import send_staff_notification
            send_staff_notification(leave_request.staff, "Leave Approved ✅", "Your leave request has been approved by HOD.", url="/staffs/leave/history/")
            
        elif action == 'reject':
            leave_request.status = 'Rejected'
            leave_request.rejection_reason = reason
            messages.warning(request, f"Rejected leave for {leave_request.staff.name}.")
            # Notify Staff
            from .utils import send_staff_notification
            send_staff_notification(leave_request.staff, "Leave Rejected ❌", f"Reason: {reason}", url="/staffs/leave/history/")
        
        leave_request.save()
        
    return redirect('staffs:hod_leave_dashboard')

def admin_portal_login(request):
    """Auto-login HOD to Django Admin Portal."""
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')

    try:
        staff = Staff.objects.get(staff_id=request.session['staff_id'])
    except Staff.DoesNotExist:
        return redirect('staffs:stafflogin')

    if not staff.is_staff_admin:
        messages.error(request, "Access Denied: Only HOD and Admin can access Admin Portal.")
        return redirect('staffs:staff_dashboard')

    from django.contrib.auth.models import User
    from django.contrib.auth import login

    # Find or Create User for HOD
    # We use staff.email or staff.staff_id as username
    user_qs = User.objects.filter(email=staff.email)
    
    if user_qs.exists():
        user = user_qs.first()
        # Ensure permissions
        if not user.is_staff or not user.is_superuser:
            user.is_staff = True
            user.is_superuser = True
            user.save()
    else:
        # Create new superuser
        username = staff.staff_id.replace(" ", "") # accurate username
        user = User.objects.create_user(username=username, email=staff.email, password=staff.password)
        user.first_name = staff.name
        user.is_staff = True
        user.is_superuser = True
        user.save()

    # Log in the user
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    
    return redirect('/admin/')


def create_superuser(request):
    """View to manually create a superuser."""
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')
        
    try:
        staff = Staff.objects.get(staff_id=request.session['staff_id'])
    except Staff.DoesNotExist:
        return redirect('staffs:stafflogin')

    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        if not username or not email or not password:
            messages.error(request, "All fields are required.")
        else:
            from django.contrib.auth.models import User
            if User.objects.filter(username=username).exists():
                messages.error(request, "Username already exists.")
            else:
                try:
                    User.objects.create_superuser(username=username, email=email, password=password)
                    messages.success(request, f"Superuser '{username}' created successfully.")
                    # return redirect('staffs:stafflogin') # Stay on page or redirect? User probably wants to stay or go to admin.
                except Exception as e:
                    messages.error(request, f"Error creating superuser: {str(e)}")
                    
    return render(request, 'staff/create_superuser.html', {'staff': staff})


def scholarship_manager(request):
    """Dedicated page for managing scholarships with advanced multi-combination filtering, approval POST actions, and export."""
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')
        
    try:
        staff = Staff.objects.get(staff_id=request.session['staff_id'])
    except Staff.DoesNotExist:
        return redirect('staffs:stafflogin')
        
    if staff.role != 'Scholarship Officer' and staff.role != 'Office Staff' and not staff.is_scholarship_officer:
        messages.error(request, "Access restricted to Scholarship Officer or Office Staff.")
        return redirect('staffs:staff_dashboard')
        
    from students.models import Student, ScholarshipInfo, PersonalInfo, ScholarshipApplication, SCHOLARSHIP_TYPE_CHOICES
    from django.db.models import Q
    import csv
    from django.http import HttpResponse

    # --- Handle POST Actions (Approval, Disbursement, Rejection) ---
    if request.method == 'POST':
        action = request.POST.get('action')
        app_id = request.POST.get('app_id')
        sch_app = get_object_or_404(ScholarshipApplication, id=app_id)

        if action == 'approve':
            sch_app.status = 'Verified & Recommended'
            sch_app.verified_at = timezone.now()
            remarks = request.POST.get('office_remarks', '').strip()
            if remarks:
                sch_app.office_remarks = remarks
            sch_app.save()

            # Sync to student's ScholarshipInfo record
            sch_info, _ = ScholarshipInfo.objects.get_or_create(student=sch_app.student)
            stype = sch_app.scholarship_type
            if stype == 'FG': sch_info.is_first_graduate = True
            elif stype == 'BCMBC': sch_info.sch_bcmbc = True
            elif stype == 'POSTMATRIC': sch_info.sch_postmetric = True
            elif stype == 'PM': sch_info.sch_pm = True
            elif stype == 'GOVT_7_5': sch_info.sch_govt = True; sch_info.is_7_5_reservation = True
            elif stype == 'PUDHUMAI': sch_info.sch_pudhumai = True
            elif stype == 'TAMIZH': sch_info.sch_tamizh = True
            elif stype == 'PRIVATE':
                sch_info.sch_private = True
                if sch_app.private_scholarship_name:
                    sch_info.private_scholarship_name = sch_app.private_scholarship_name
            sch_info.save()

            messages.success(request, f"Scholarship application for {sch_app.student.student_name} ({sch_app.get_scholarship_type_display()}) verified & recommended to Govt portal!")

        elif action == 'disburse':
            sch_app.status = 'Govt Sanctioned / Availed'
            sch_app.disbursed_at = timezone.now()
            remarks = request.POST.get('office_remarks', '').strip()
            if remarks:
                sch_app.office_remarks = remarks
            sch_app.save()

            messages.info(request, f"Scholarship status updated to Govt Sanctioned / Availed for {sch_app.student.student_name}.")

        elif action == 'reject':
            reason = request.POST.get('rejection_reason', '').strip()
            sch_app.status = 'Rejected / Ineligible'
            sch_app.rejection_reason = reason or 'Application rejected or ineligible.'
            sch_app.save()

            messages.warning(request, f"Scholarship record for {sch_app.student.student_name} marked as Rejected / Ineligible.")

        return redirect('staffs:scholarship_manager')

    # Base Applications QuerySet
    app_qs = ScholarshipApplication.objects.select_related('student', 'student__scholarshipinfo', 'student__personalinfo').all()

    # --- Multi-Combination Filtering ---
    # 1. Multi-Select Scholarship Types
    sel_types = request.GET.getlist('scholarship_types')
    if not sel_types:
        single_type = request.GET.get('scholarship_type')
        if single_type:
            sel_types = [single_type]

    if sel_types and '' not in sel_types:
        app_qs = app_qs.filter(scholarship_type__in=sel_types)

    # 2. Application Status
    app_status = request.GET.get('status')
    if app_status:
        app_qs = app_qs.filter(status=app_status)

    # 3. Program Level
    program = request.GET.get('program_level')
    if program:
        app_qs = app_qs.filter(student__program_level=program)

    # 4. Semester
    semester = request.GET.get('semester')
    if semester:
        app_qs = app_qs.filter(student__current_semester=semester)

    # 5. Gender
    gender = request.GET.get('gender')
    if gender:
        app_qs = app_qs.filter(student__personalinfo__gender=gender)

    # 6. Community
    community = request.GET.get('community')
    if community:
        app_qs = app_qs.filter(student__personalinfo__community=community)

    # 7. Max Income Filter
    max_income = request.GET.get('max_income')
    if max_income:
        try:
            app_qs = app_qs.filter(annual_income__lte=int(max_income))
        except ValueError:
            pass

    # 8. Hosteller vs Day Scholar
    hostel_status = request.GET.get('is_hosteler')
    if hostel_status == 'yes':
        app_qs = app_qs.filter(student__personalinfo__is_hosteler=True)
    elif hostel_status == 'no':
        app_qs = app_qs.filter(student__personalinfo__is_hosteler=False)

    # 9. 7.5% Govt School Quota
    is_7_5 = request.GET.get('is_7_5')
    if is_7_5 == 'yes':
        app_qs = app_qs.filter(Q(scholarship_type='GOVT_7_5') | Q(student__scholarshipinfo__is_7_5_reservation=True))

    # 10. First Graduate
    is_fg = request.GET.get('is_fg')
    if is_fg == 'yes':
        app_qs = app_qs.filter(Q(scholarship_type='FG') | Q(student__scholarshipinfo__is_first_graduate=True))

    # 11. Search Query (Name, Roll, App No)
    q = request.GET.get('q', '').strip()
    if q:
        app_qs = app_qs.filter(
            Q(student__student_name__icontains=q) |
            Q(student__roll_number__icontains=q) |
            Q(application_no__icontains=q)
        )

    # --- Export to CSV ---
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="scholarship_applications_audit.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'Roll Number', 'Student Name', 'Program', 'Semester', 'Community', 'Gender',
            'Scholarship Scheme', 'App Ref No', 'Annual Income', 'Bank Account', 'IFSC', 'Status', 'Applied Date'
        ])

        for app in app_qs:
            comm = 'N/A'
            gen = 'N/A'
            try:
                comm = app.student.personalinfo.community
                gen = app.student.personalinfo.gender
            except PersonalInfo.DoesNotExist:
                pass

            writer.writerow([
                app.student.roll_number,
                app.student.student_name,
                app.student.program_level,
                app.student.current_semester,
                comm,
                gen,
                app.get_scholarship_type_display(),
                app.application_no or 'N/A',
                app.annual_income or 'N/A',
                app.bank_account_no or 'N/A',
                app.bank_ifsc or 'N/A',
                app.status,
                app.applied_at.strftime('%Y-%m-%d')
            ])
        return response

    # Stats counters for header tiles
    all_apps = ScholarshipApplication.objects.all()
    pending_count = all_apps.filter(status='Pending Office Verification').count()
    approved_count = all_apps.filter(status='Verified & Recommended').count()
    disbursed_count = all_apps.filter(status='Govt Sanctioned / Amount Received').count()
    not_received_count = all_apps.filter(status='Not Received / Pending Govt').count()
    rejected_count = all_apps.filter(status='Rejected / Ineligible').count()

    context = {
        'staff': staff,
        'applications': app_qs,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'disbursed_count': disbursed_count,
        'not_received_count': not_received_count,
        'rejected_count': rejected_count,
        'type_choices': SCHOLARSHIP_TYPE_CHOICES,
        'filters': {
            'scholarship_types': sel_types,
            'scholarship_type': request.GET.get('scholarship_type', ''),
            'status': app_status,
            'program_level': program,
            'semester': semester,
            'gender': gender,
            'community': community,
            'max_income': max_income,
            'is_hosteler': hostel_status,
            'is_7_5': is_7_5,
            'is_fg': is_fg,
            'q': q,
        }
    }
    return render(request, 'staff/scholarship_manager.html', context)


def manage_substitutions(request):
    """View for staff to request substitutes for their classes on a specific date."""
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')
    
    staff = Staff.objects.get(staff_id=request.session['staff_id'])
    from .models import Timetable, ClassSubstitutionRequest, Subject
    import datetime
    
    date_str = request.GET.get('date', datetime.date.today().strftime('%Y-%m-%d'))
    try:
        selected_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        selected_date = datetime.date.today()
        
    day_name = selected_date.strftime('%A')
    
    # Get regular classes
    my_timetable = Timetable.objects.filter(staff=staff, day=day_name).order_by('period')
    
    # Get existing requests for this date
    existing_requests = ClassSubstitutionRequest.objects.filter(requester=staff, date=selected_date)
    existing_requests_dict = {req.period: req for req in existing_requests}
    
    # Combine data
    classes_data = []
    for entry in my_timetable:
        classes_data.append({
            'period': entry.period,
            'subject': entry.subject,
            'request': existing_requests_dict.get(entry.period)
        })
        
    other_staff = Staff.objects.filter(is_active=True).exclude(staff_id=staff.staff_id).order_by('name')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'request_substitute':
            period = int(request.POST.get('period'))
            substitute_id = request.POST.get('substitute_id')
            subject_id = request.POST.get('subject_id')
            
            substitute = get_object_or_404(Staff, staff_id=substitute_id)
            subject = get_object_or_404(Subject, id=subject_id)
            
            # Create or update request
            ClassSubstitutionRequest.objects.update_or_create(
                requester=staff,
                date=selected_date,
                period=period,
                defaults={
                    'substitute': substitute,
                    'subject': subject,
                    'status': 'Pending'
                }
            )
            from django.conf import settings
            from django.core.mail import send_mail
            messages.success(request, f"Alternate request sent to {substitute.name}.")
            # Notify Substitute
            from .utils import send_staff_notification
            send_staff_notification(substitute, "📅 Alternate Request", f"{staff.name} requested you to act as alternate for Period {period} on {selected_date}.", url="/staffs/substitutions/incoming/")
            send_mail(
                "Class Alternate Request",
                f"Hello {substitute.name},\n\n{staff.name} has requested you to cover their class on {selected_date}, Period {period}.\n\nPlease log in to accept or reject this request.\n\nLink: http://127.0.0.1:8000/staffs/substitutions/incoming/",
                settings.DEFAULT_FROM_EMAIL,
                [substitute.email],
                fail_silently=True
            )
            
            return redirect(f'/staffs/substitutions/manage/?date={selected_date}')
            
        elif action == 'cancel_request':
            req_id = request.POST.get('request_id')
            req = get_object_or_404(ClassSubstitutionRequest, id=req_id, requester=staff)
            req.delete()
            messages.success(request, "Alternate request cancelled.")
            return redirect(f'/staffs/substitutions/manage/?date={selected_date}')
            
    return render(request, 'staff/manage_substitutions.html', {
        'staff': staff,
        'selected_date': selected_date,
        'classes_data': classes_data,
        'other_staff': other_staff
    })

def incoming_substitutions(request):
    """View for substitute staff to see incoming requests and accept/reject."""
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')
        
    staff = Staff.objects.get(staff_id=request.session['staff_id'])
    from .models import ClassSubstitutionRequest
    
    incoming_requests = ClassSubstitutionRequest.objects.filter(substitute=staff, status='Pending').order_by('date', 'period')
    history = ClassSubstitutionRequest.objects.filter(substitute=staff).exclude(status='Pending').order_by('-date', 'period')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        req_id = request.POST.get('request_id')
        req = get_object_or_404(ClassSubstitutionRequest, id=req_id, substitute=staff)
        
        from .utils import send_staff_notification
        from django.conf import settings
        from django.core.mail import send_mail
        
        if action == 'accept':
            req.status = 'Approved'
            req.save()
            messages.success(request, f"You have accepted the alternate request for Period {req.period} on {req.date}.")
            send_staff_notification(req.requester, "✅ Alternate Accepted", f"{staff.name} accepted your request for Period {req.period} on {req.date}.", url="/staffs/substitutions/manage/")
            send_mail(
                "Alternate Request Accepted",
                f"Hello {req.requester.name},\n\n{staff.name} has accepted your alternate request for {req.date}, Period {req.period}.",
                settings.DEFAULT_FROM_EMAIL,
                [req.requester.email],
                fail_silently=True
            )

        elif action == 'reject':
            req.status = 'Rejected'
            req.rejection_reason = request.POST.get('rejection_reason', '')
            req.save()
            messages.success(request, f"You have rejected the alternate request for Period {req.period} on {req.date}.")
            send_staff_notification(req.requester, "❌ Alternate Rejected", f"{staff.name} rejected your request for Period {req.period} on {req.date}.", url="/staffs/substitutions/manage/")
            send_mail(
                "Alternate Request Rejected",
                f"Hello {req.requester.name},\n\n{staff.name} has rejected your alternate request for {req.date}, Period {req.period}.\nReason: {req.rejection_reason}\n\nPlease request another staff member.",
                settings.DEFAULT_FROM_EMAIL,
                [req.requester.email],
                fail_silently=True
            )
            
        return redirect('staffs:incoming_substitutions')
        
    return render(request, 'staff/incoming_substitutions.html', {
        'staff': staff,
        'incoming_requests': incoming_requests,
        'history': history
    })

def assigned_substitutions(request):
    """View assigned substitution classes for the logged-in staff."""
    import datetime
    from .models import ClassSubstitutionRequest
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')

    staff = get_object_or_404(Staff, staff_id=request.session['staff_id'])
    
    today = datetime.date.today()
    # Get all approved requests where this staff is the substitute
    assigned_classes = ClassSubstitutionRequest.objects.filter(
        substitute=staff,
        status='Approved'
    ).order_by('-date', 'period') # Newest first

    return render(request, 'staff/assigned_substitutions.html', {
        'staff': staff,
        'assigned_classes': assigned_classes,
        'today': today
    })

def _get_portfolio_summary_stats(staff):
    import datetime
    # Dynamic Visual Stats Calculations
    all_confs = staff.conferences.all()
    conf_attended_national = all_confs.filter(participation_type='Attended', national_international='National').count()
    conf_attended_international = all_confs.filter(participation_type='Attended', national_international='International').count()
    conf_conducted_national = all_confs.filter(participation_type='Presented', national_international='National').count()
    conf_conducted_international = all_confs.filter(participation_type='Presented', national_international='International').count()
    conf_total = all_confs.count()

    all_sems = staff.seminar_list.all()
    seminars_attended = all_sems.filter(event_type='Seminar', participation_role='Attended').exclude(title__icontains='symposi').count()
    seminars_conducted = all_sems.filter(event_type='Seminar', participation_role='Conducted').exclude(title__icontains='symposi').count()
    seminars_total = seminars_attended + seminars_conducted
    
    symposia_attended = all_sems.filter(title__icontains='symposi', participation_role='Attended').count()
    symposia_conducted = all_sems.filter(title__icontains='symposi', participation_role='Conducted').count()
    symposia_total = symposia_attended + symposia_conducted
    
    workshops_attended = all_sems.filter(event_type='Workshop', participation_role='Attended').count()
    workshops_conducted = all_sems.filter(event_type='Workshop', participation_role='Conducted').count()
    workshops_total = workshops_attended + workshops_conducted

    students_guided = staff.student_guided_list.all()
    pg_completed = students_guided.filter(degree_type='PG', status='Completed').count()
    pg_ongoing = students_guided.filter(degree_type='PG', status='Ongoing').count()
    
    guided_phd_completed = students_guided.filter(degree_type='PhD', status='Completed').count()
    guided_phd_ongoing = students_guided.filter(degree_type='PhD', status='Ongoing').count()
    active_phd = staff.supervised_scholars.filter(status='Ongoing').count()
    phd_completed = guided_phd_completed
    phd_ongoing = guided_phd_ongoing + active_phd

    # Calculate Guidance Percentages
    pg_total = pg_completed + pg_ongoing
    pg_completed_pct = round((pg_completed / pg_total * 100)) if pg_total > 0 else 0
    pg_ongoing_pct = round((pg_ongoing / pg_total * 100)) if pg_total > 0 else 0
    
    phd_total = phd_completed + phd_ongoing
    phd_completed_pct = round((phd_completed / phd_total * 100)) if phd_total > 0 else 0
    phd_ongoing_pct = round((phd_ongoing / phd_total * 100)) if phd_total > 0 else 0

    # Publication & Indexing Stats
    journals = staff.journals.all()
    journals_count = journals.count()
    scopus_count = journals.filter(is_scopus=True).count()
    wos_count = journals.filter(is_wos=True).count()
    sci_count = journals.filter(is_sci=True).count()
    scie_count = journals.filter(is_scie=True).count()
    ugc_count = journals.filter(is_ugc=True).count()

    books_count = staff.books.count()
    total_publications = journals_count + conf_conducted_national + conf_conducted_international + books_count

    # Patents & Research Projects
    patents = staff.patents.all()
    patents_count = patents.count()
    patents_granted = patents.filter(status='Granted').count()
    patents_published = patents.filter(status='Published').count()
    patents_applied = patents.filter(status='Applied').count()

    research_projects = staff.research_projects.all()
    projects_count = research_projects.count()
    projects_active = research_projects.filter(status='Ongoing').count()
    projects_completed = research_projects.filter(status='Completed').count()

    # Academic & Professional Stats
    qualifications_count = staff.qualifications.count()
    highest_qual = staff.qualifications.order_by('-year_completed').first()
    highest_degree_name = highest_qual.degree if highest_qual else "Faculty"

    awards_count = staff.award_list.count()
    memberships_count = staff.memberships.count()

    # Calculated Service / Experience (Years & Months)
    experience_years = 0
    experience_months = 0
    if staff.date_of_joining:
        today = datetime.date.today()
        total_months = (today.year - staff.date_of_joining.year) * 12 + (today.month - staff.date_of_joining.month)
        experience_years = max(0, total_months // 12)
        experience_months = max(0, total_months % 12)

    _comp = get_staff_profile_completion_data(staff)
    profile_completion_percentage = _comp['percentage']

    return {
        'conf_total': conf_total,
        'conf_attended_national': conf_attended_national,
        'conf_attended_international': conf_attended_international,
        'conf_conducted_national': conf_conducted_national,
        'conf_conducted_international': conf_conducted_international,
        'conf_attended_total': conf_attended_national + conf_attended_international,
        'conf_conducted_total': conf_conducted_national + conf_conducted_international,
        'seminars_total': seminars_total,
        'seminars_attended': seminars_attended,
        'seminars_conducted': seminars_conducted,
        'symposia_total': symposia_total,
        'symposia_attended': symposia_attended,
        'symposia_conducted': symposia_conducted,
        'workshops_total': workshops_total,
        'workshops_attended': workshops_attended,
        'workshops_conducted': workshops_conducted,
        'pg_completed': pg_completed,
        'pg_ongoing': pg_ongoing,
        'pg_total': pg_total,
        'phd_completed': phd_completed,
        'phd_ongoing': phd_ongoing,
        'phd_total': phd_total,
        'scholars_guided_total': phd_total + pg_total,
        'scholars_completed_total': phd_completed + pg_completed,
        'scholars_ongoing_total': phd_ongoing + pg_ongoing,
        'pg_completed_pct': pg_completed_pct,
        'pg_ongoing_pct': pg_ongoing_pct,
        'phd_completed_pct': phd_completed_pct,
        'phd_ongoing_pct': phd_ongoing_pct,
        'journals_count': journals_count,
        'scopus_count': scopus_count,
        'wos_count': wos_count,
        'sci_count': sci_count,
        'scie_count': scie_count,
        'sci_scie_total': sci_count + scie_count,
        'ugc_count': ugc_count,
        'books_count': books_count,
        'total_publications': total_publications,
        'patents_count': patents_count,
        'patents_granted': patents_granted,
        'patents_published': patents_published,
        'patents_applied': patents_applied,
        'projects_count': projects_count,
        'projects_active': projects_active,
        'projects_completed': projects_completed,
        'qualifications_count': qualifications_count,
        'highest_degree_name': highest_degree_name,
        'awards_count': awards_count,
        'memberships_count': memberships_count,
        'experience_years': experience_years,
        'experience_months': experience_months,
        'profile_completion_percentage': profile_completion_percentage,
    }

def staff_profile(request):
    """View to display the logged-in staff's profile."""
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')

    try:
        staff = Staff.objects.get(staff_id=request.session['staff_id'])
    except Staff.DoesNotExist:
        return redirect('staffs:stafflogin')

    ctx = {'staff': staff, 'is_own_profile': True}
    ctx.update(_get_portfolio_summary_stats(staff))
    return render(request, 'staff/profile.html', ctx)

def view_faculty_profile(request, staff_id):
    """View to display a specific faculty member's profile, visible to other staff (e.g., HOD)."""
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')

    try:
        viewer = Staff.objects.get(staff_id=request.session['staff_id'])
    except Staff.DoesNotExist:
        return redirect('staffs:stafflogin')

    target_staff = get_object_or_404(Staff, staff_id=staff_id)

    ctx = {
        'staff': target_staff,
        'viewer': viewer,
        'is_own_profile': (viewer.staff_id == target_staff.staff_id)
    }
    ctx.update(_get_portfolio_summary_stats(target_staff))
    return render(request, 'staff/profile.html', ctx)


def staff_edit_profile(request):
    """View to edit staff professional profile."""
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')

    staff = get_object_or_404(Staff, staff_id=request.session['staff_id'])

    if request.method == 'POST':
        staff.address = request.POST.get('address', '')
        staff.mobile_number = request.POST.get('mobile_number', '') or None
        staff.blood_group = request.POST.get('blood_group', '') or None
        staff.gender = request.POST.get('gender', '') or None
        dob = request.POST.get('date_of_birth')
        staff.date_of_birth = dob if dob else None
        doj = request.POST.get('date_of_joining')
        staff.date_of_joining = doj if doj else None
        staff.specialization = request.POST.get('specialization', '')

        # Profile Picture Upload/Clear
        clear_photo = request.POST.get('clear_photo') == 'true'
        if clear_photo:
            if staff.photo:
                try:
                    staff.photo.delete(save=False)
                except Exception as e:
                    print(f"Error deleting old photo: {e}")
            staff.photo = None
        else:
            photo = request.FILES.get('photo')
            if photo:
                from django.core.exceptions import ValidationError
                from ssm.validators import validate_file_size
                try:
                    validate_file_size(photo)
                    if staff.photo:
                        try:
                            staff.photo.delete(save=False)
                        except Exception as e:
                            print(f"Error deleting old photo: {e}")
                    staff.photo = photo
                except ValidationError as e:
                    messages.error(request, f"Profile Picture: {e.message}")
                    return render(request, 'staff/staff_edit_profile.html', {'staff': staff})

        # Joining/Onboarding Documents
        joining_order = request.FILES.get('joining_order')
        if joining_order:
            staff.joining_order = joining_order
        appointment_order = request.FILES.get('appointment_order')
        if appointment_order:
            staff.appointment_order = appointment_order
        board_order = request.FILES.get('board_order')
        if board_order:
            staff.board_order = board_order
        joining_letter = request.FILES.get('joining_letter')
        if joining_letter:
            staff.joining_letter = joining_letter
        sslc_marksheet = request.FILES.get('sslc_marksheet')
        if sslc_marksheet:
            staff.sslc_marksheet = sslc_marksheet
        hsc_marksheet = request.FILES.get('hsc_marksheet')
        if hsc_marksheet:
            staff.hsc_marksheet = hsc_marksheet

        # New Fields
        staff.research_interests = request.POST.get('research_interests', '')
        staff.google_scholar_link = request.POST.get('google_scholar_link', '') or None
        staff.linkedin_link = request.POST.get('linkedin_link', '') or None
        staff.orcid_link = request.POST.get('orcid_link', '') or None
        staff.research_gate_link = request.POST.get('research_gate_link', '') or None

        staff.save()
        from .utils import log_audit
        log_audit(request, 'update', actor_type='staff', actor_id=staff.staff_id, actor_name=staff.name, object_type='Staff', object_id=staff.staff_id, message='Updated profile details')
        messages.success(request, "Profile updated successfully.")
        return redirect('staffs:staff_profile')

    return render(request, 'staff/staff_edit_profile.html', {'staff': staff})

def _get_staff_for_portfolio(request):
    """Helper to get logged-in staff for portfolio views."""
    if 'staff_id' not in request.session:
        return None
    try:
        return get_object_or_404(Staff, staff_id=request.session['staff_id'])
    except Exception:
        return None


def staff_portfolio(request):
    """View to manage staff publications, awards, honours, and research guidance."""
    staff = _get_staff_for_portfolio(request)
    if not staff:
        return redirect('staffs:stafflogin')

    if staff.role == 'Office Staff':
        messages.info(request, "Portfolio management is applicable only for teaching faculty.")
        return redirect('staffs:staff_profile')

    publications = staff.publication_list.all().order_by('-year', '-id')
    awards = staff.award_list.all().order_by('-year', '-id')
    students_guided = staff.student_guided_list.all().order_by('-year', '-id')
    
    # Combined Seminars, Workshops, Conferences & Symposia + FDP & Trainings
    all_seminar_entries = list(staff.seminar_list.all().order_by('-date_from', '-year', '-id'))

    academic_types = {'Conference', 'Seminar', 'Workshop', 'Symposia'}
    training_types = {'FDP', 'STTP', 'Summer/Winter School', 'Orientation Programme', 'Refresher Course / Training', 'Summer/Winter Orientation'}

    academic_events_attended = [e for e in all_seminar_entries if e.event_type in academic_types and e.participation_role == 'Attended']
    academic_events_conducted = [e for e in all_seminar_entries if e.event_type in academic_types and e.participation_role == 'Conducted']

    training_events_attended = [e for e in all_seminar_entries if e.event_type in training_types and e.participation_role == 'Attended']
    training_events_conducted = [e for e in all_seminar_entries if e.event_type in training_types and e.participation_role == 'Conducted']

    # Segregated breakdown counts for Academic & Training events
    academic_attended_counts = {
        'seminars': sum(1 for e in academic_events_attended if e.event_type == 'Seminar'),
        'workshops': sum(1 for e in academic_events_attended if e.event_type == 'Workshop'),
        'conferences': sum(1 for e in academic_events_attended if e.event_type == 'Conference'),
        'symposia': sum(1 for e in academic_events_attended if e.event_type == 'Symposia'),
    }
    academic_conducted_counts = {
        'seminars': sum(1 for e in academic_events_conducted if e.event_type == 'Seminar'),
        'workshops': sum(1 for e in academic_events_conducted if e.event_type == 'Workshop'),
        'conferences': sum(1 for e in academic_events_conducted if e.event_type == 'Conference'),
        'symposia': sum(1 for e in academic_events_conducted if e.event_type == 'Symposia'),
    }

    training_attended_counts = {
        'fdp': sum(1 for e in training_events_attended if e.event_type == 'FDP'),
        'sttp': sum(1 for e in training_events_attended if e.event_type == 'STTP'),
        'school': sum(1 for e in training_events_attended if 'School' in e.event_type),
        'orientation_refresher': sum(1 for e in training_events_attended if any(k in e.event_type for k in ['Orientation', 'Refresher'])),
    }
    training_conducted_counts = {
        'fdp': sum(1 for e in training_events_conducted if e.event_type == 'FDP'),
        'sttp': sum(1 for e in training_events_conducted if e.event_type == 'STTP'),
        'school': sum(1 for e in training_events_conducted if 'School' in e.event_type),
        'orientation_refresher': sum(1 for e in training_events_conducted if any(k in e.event_type for k in ['Orientation', 'Refresher'])),
    }

    # Legacy models
    conferences = staff.conferences.filter(participation_type='Presented').order_by('-year_of_publication', '-created_at')
    attended_conferences = staff.conferences.filter(participation_type='Attended').order_by('-year_of_publication', '-created_at')
    journals = staff.journals.all().order_by('-published_year', '-created_at')
    books = staff.books.all().order_by('-year_of_publication', '-created_at')
    
    qualifications = staff.qualifications.all().order_by('-year_completed', '-id')
    designations = staff.past_designations.filter(is_additional=False).order_by('-from_date', '-id')
    additional_posts = staff.past_designations.filter(is_additional=True).order_by('-from_date', '-id')
    memberships = staff.memberships.all().order_by('-year', '-id')
    patents = staff.patents.all().order_by('-application_year', '-created_at')
    research_projects = staff.research_projects.all().order_by('-start_date', '-id')

    # Dynamic PhD Scholar Guidance — auto-fetched from ResearchScholarProfile.supervisor FK
    from students.models import PhDProgress
    stage_map = dict(PhDProgress.CURRENT_STAGE_CHOICES)

    supervised_scholars_raw = staff.supervised_scholars.select_related(
        'student', 'student__phd_progress', 'student__personalinfo'
    ).all()

    phd_scholars_data = []
    for profile in supervised_scholars_raw:
        student = profile.student
        try:
            progress = student.phd_progress
            current_stage_key = progress.current_stage
            current_stage_label = stage_map.get(current_stage_key, current_stage_key)
            stats = progress.progress_stats
        except AttributeError:
            progress = None
            current_stage_key = 'RAC_REVIEW'
            current_stage_label = 'RAC Review'
            stats = {}

        photo = None
        if hasattr(student, 'studentdocuments') and student.studentdocuments and student.studentdocuments.student_photo:
            photo = student.studentdocuments.student_photo

        phd_scholars_data.append({
            'profile': profile,
            'student': student,
            'name': student.student_name,
            'roll_number': student.roll_number,
            'photo': photo,
            'scholar_type': profile.scholar_type or 'PhD Scholar',
            'admission_date': profile.admission_date,
            'completion_year': profile.completion_year,
            'status': profile.status,
            'current_stage_label': current_stage_label,
            'stats': stats,
            'overall_percent': stats.get('overall_percent', 0),
            'is_completed': (current_stage_key == 'COMPLETED' or profile.status == 'Completed'),
        })

    ctx = {
        'staff': staff,
        'publications': publications,
        'awards': awards,
        'seminars': all_seminar_entries,
        'academic_events_attended': academic_events_attended,
        'academic_events_conducted': academic_events_conducted,
        'training_events_attended': training_events_attended,
        'training_events_conducted': training_events_conducted,
        'academic_attended_counts': academic_attended_counts,
        'academic_conducted_counts': academic_conducted_counts,
        'training_attended_counts': training_attended_counts,
        'training_conducted_counts': training_conducted_counts,
        'students_guided': students_guided,
        'phd_scholars': phd_scholars_data,
        'conferences': conferences,
        'attended_conferences': attended_conferences,
        'journals': journals,
        'books': books,
        'qualifications': qualifications,
        'designations': designations,
        'additional_posts': additional_posts,
        'memberships': memberships,
        'patents': patents,
        'research_projects': research_projects,
    }
    ctx.update(_get_portfolio_summary_stats(staff))
    return render(request, 'staff/staff_portfolio.html', ctx)


def generate_biodata_pdf(request):
    """View to generate a printable PDF of a staff member's biodata."""
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')

    target_staff_id = request.GET.get('staff_id')
    try:
        if target_staff_id:
            staff = Staff.objects.get(staff_id=target_staff_id)
        else:
            staff = Staff.objects.get(staff_id=request.session['staff_id'])
    except Staff.DoesNotExist:
        return redirect('staffs:stafflogin')

    publications = staff.publication_list.all()
    awards = staff.award_list.all()
    seminars = staff.seminar_list.all()
    students_guided = staff.student_guided_list.all()
    
    # New Models
    conferences = staff.conferences.all().order_by('-year_of_publication', '-created_at')
    journals = staff.journals.all().order_by('-published_year', '-created_at')
    books = staff.books.all().order_by('-year_of_publication', '-created_at')
    
    qualifications = staff.qualifications.all().order_by('-year_completed')
    designations = staff.past_designations.all()
    memberships = staff.memberships.all()
    patents = staff.patents.all().order_by('-application_year', '-created_at')
    research_projects = staff.research_projects.all()

    # Dynamic PhD Scholar Guidance
    from students.models import PhDProgress
    stage_map = dict(PhDProgress.CURRENT_STAGE_CHOICES)

    supervised_scholars_raw = staff.supervised_scholars.select_related(
        'student', 'student__phd_progress', 'student__personalinfo'
    ).all()

    phd_scholars_data = []
    for profile in supervised_scholars_raw:
        student = profile.student
        try:
            progress = student.phd_progress
            current_stage_key = progress.current_stage
            current_stage_label = stage_map.get(current_stage_key, current_stage_key)
        except AttributeError:
            current_stage_label = 'RAC Review'

        phd_scholars_data.append({
            'roll_number': student.roll_number,
            'name': student.student_name,
            'scholar_type': profile.get_scholar_type_display() if hasattr(profile, 'get_scholar_type_display') else profile.scholar_type,
            'admission_date': profile.admission_date,
            'status': profile.status,
            'current_stage_label': current_stage_label,
        })

    context = {
        'staff': staff,
        'publications': publications,
        'awards': awards,
        'seminars': seminars,
        'students_guided': students_guided,
        'phd_scholars': phd_scholars_data,
        'conferences': conferences,
        'journals': journals,
        'books': books,
        'qualifications': qualifications,
        'designations': designations,
        'memberships': memberships,
        'patents': patents,
        'research_projects': research_projects,
    }

    from django.template.loader import get_template
    from django.http import HttpResponse
    from xhtml2pdf import pisa

    template_path = 'staff/staff_biodata_template.html'
    template = get_template(template_path)
    html = template.render(context)

    response = HttpResponse(content_type='application/pdf')
    filename = f"{staff.name.replace(' ', '_')}_BioData.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('We had some errors <pre>' + html + '</pre>')
    return response


def portfolio_add_publication(request):
    staff = _get_staff_for_portfolio(request)
    if not staff:
        return redirect('staffs:stafflogin')
    if request.method == 'POST':
        StaffPublication.objects.create(
            staff=staff,
            title=request.POST.get('title', '').strip(),
            venue_or_journal=request.POST.get('venue_or_journal', '').strip(),
            year=request.POST.get('year', '').strip(),
            pub_type=request.POST.get('pub_type', 'Journal'),
        )
        from .utils import log_audit
        log_audit(request, 'create', actor_type='staff', actor_id=staff.staff_id, actor_name=staff.name, object_type='Publication', message='Added new publication')
        messages.success(request, "Publication added.")
        return redirect('staffs:staff_portfolio')
    return render(request, 'staff/portfolio_form.html', {
        'staff': staff, 'form_type': 'publication', 'item': None, 'title': 'Add Publication',
    })


def portfolio_edit_publication(request, pk):
    staff = _get_staff_for_portfolio(request)
    if not staff:
        return redirect('staffs:stafflogin')
    item = get_object_or_404(StaffPublication, pk=pk, staff=staff)
    if request.method == 'POST':
        item.title = request.POST.get('title', '').strip()
        item.venue_or_journal = request.POST.get('venue_or_journal', '').strip()
        item.year = request.POST.get('year', '').strip()
        item.pub_type = request.POST.get('pub_type', 'Journal')
        item.save()
        from .utils import log_audit
        log_audit(request, 'update', actor_type='staff', actor_id=staff.staff_id, actor_name=staff.name, object_type='Publication', object_id=str(item.pk), message='Updated publication')
        messages.success(request, "Publication updated.")
        return redirect('staffs:staff_portfolio')
    return render(request, 'staff/portfolio_form.html', {
        'staff': staff, 'form_type': 'publication', 'item': item, 'title': 'Edit Publication',
    })


def portfolio_delete_publication(request, pk):
    staff = _get_staff_for_portfolio(request)
    if not staff:
        return redirect('staffs:stafflogin')
    item = get_object_or_404(StaffPublication, pk=pk, staff=staff)
    if request.method == 'POST':
        item.delete()
        from .utils import log_audit
        log_audit(request, 'delete', actor_type='staff', actor_id=staff.staff_id, actor_name=staff.name, object_type='Publication', object_id=str(pk), message='Deleted publication')
        messages.success(request, "Publication removed.")
        return redirect('staffs:staff_portfolio')
    return render(request, 'staff/portfolio_confirm_delete.html', {
        'staff': staff, 'item': item, 'item_label': item.title, 'cancel_url': 'staffs:staff_portfolio',
    })


def portfolio_add_award(request):
    staff = _get_staff_for_portfolio(request)
    if not staff:
        return redirect('staffs:stafflogin')
    if request.method == 'POST':
        item = StaffAwardHonour.objects.create(
            title=request.POST.get('title', '').strip(),
            awarded_by=request.POST.get('awarded_by', '').strip(),
            description=request.POST.get('description', '').strip(),
            year=request.POST.get('year', '').strip(),
            category=request.POST.get('category', 'Award'),
            supporting_document=request.FILES.get('supporting_document'),
        )
        item.staff.add(staff)
        from .utils import log_audit
        log_audit(request, 'create', actor_type='staff', actor_id=staff.staff_id, actor_name=staff.name, object_type='Award', message='Added new award/honour')
        messages.success(request, "Entry added.")
        return redirect('staffs:staff_portfolio')
    return render(request, 'staff/portfolio_form.html', {
        'staff': staff, 'form_type': 'award', 'item': None, 'title': 'Add Award / Honour / Membership',
    })


def portfolio_edit_award(request, pk):
    staff = _get_staff_for_portfolio(request)
    if not staff:
        return redirect('staffs:stafflogin')
    item = get_object_or_404(StaffAwardHonour, pk=pk, staff=staff)
    if request.method == 'POST':
        item.title = request.POST.get('title', '').strip()
        item.awarded_by = request.POST.get('awarded_by', '').strip()
        item.description = request.POST.get('description', '').strip()
        item.year = request.POST.get('year', '').strip()
        item.category = request.POST.get('category', 'Award')
        if 'supporting_document' in request.FILES:
            item.supporting_document = request.FILES['supporting_document']
        item.save()
        from .utils import log_audit
        log_audit(request, 'update', actor_type='staff', actor_id=staff.staff_id, actor_name=staff.name, object_type='Award', object_id=str(item.pk), message='Updated award/honour')
        messages.success(request, "Entry updated.")
        return redirect('staffs:staff_portfolio')
    return render(request, 'staff/portfolio_form.html', {
        'staff': staff, 'form_type': 'award', 'item': item, 'title': 'Edit Award / Honour / Membership',
    })


def portfolio_add_seminar(request):
    staff = _get_staff_for_portfolio(request)
    if not staff:
        return redirect('staffs:stafflogin')
    if request.method == 'POST':
        sem = StaffSeminar(
            title=request.POST.get('title', '').strip(),
            event_type=request.POST.get('event_type', 'Seminar'),
            venue_or_description=request.POST.get('venue_or_description', '').strip(),
            organized_by=request.POST.get('organized_by', '').strip(),
            sponsoring_agency=request.POST.get('sponsoring_agency', '').strip(),
            national_international=request.POST.get('national_international', 'National'),
            proceedings_title=request.POST.get('proceedings_title', '').strip(),
            date_from=request.POST.get('date_from') or None,
            date_to=request.POST.get('date_to') or None,
            year=request.POST.get('year', '').strip(),
            supporting_document=request.FILES.get('supporting_document'),
            order_certificate=request.FILES.get('order_certificate'),
            mode=request.POST.get('mode', 'Offline'),
            participation_role=request.POST.get('participation_role', 'Attended'),
        )
        sem._temp_staff_id = staff.staff_id
        sem.save()
        
        # Link co-authors
        co_authors = request.POST.getlist('co_authors')
        selected_staffs = [staff]
        for cid in co_authors:
            if cid != staff.staff_id:
                try:
                    co_staff = Staff.objects.get(staff_id=cid)
                    selected_staffs.append(co_staff)
                except Staff.DoesNotExist:
                    pass
        sem.staff.set(selected_staffs)
        
        from .utils import log_audit
        log_audit(request, 'create', actor_type='staff', actor_id=staff.staff_id, actor_name=staff.name, object_type='Seminar', message='Added new seminar/workshop/event entry')
        messages.success(request, "Event entry added successfully.")
        return redirect('staffs:staff_portfolio')
        
    all_staffs = Staff.objects.all().order_by('name')
    initial_event_type = request.GET.get('event_type', 'Seminar')
    return render(request, 'staff/portfolio_form.html', {
        'staff': staff, 'form_type': 'seminar', 'item': None, 'title': 'Add Seminar / Workshop / Conference / Symposia / Training', 'all_staffs': all_staffs, 'initial_event_type': initial_event_type,
    })


def portfolio_edit_seminar(request, pk):
    staff = _get_staff_for_portfolio(request)
    if not staff:
        return redirect('staffs:stafflogin')
    sem = get_object_or_404(StaffSeminar, pk=pk)
    if request.method == 'POST':
        sem.title = request.POST.get('title', '').strip()
        sem.event_type = request.POST.get('event_type', 'Seminar')
        sem.venue_or_description = request.POST.get('venue_or_description', '').strip()
        sem.organized_by = request.POST.get('organized_by', '').strip()
        sem.sponsoring_agency = request.POST.get('sponsoring_agency', '').strip()
        sem.national_international = request.POST.get('national_international', 'National')
        sem.proceedings_title = request.POST.get('proceedings_title', '').strip()
        sem.date_from = request.POST.get('date_from') or None
        sem.date_to = request.POST.get('date_to') or None
        sem.year = request.POST.get('year', '').strip()
        sem.mode = request.POST.get('mode', 'Offline')
        sem.participation_role = request.POST.get('participation_role', 'Attended')
        
        if 'supporting_document' in request.FILES:
            sem.supporting_document = request.FILES['supporting_document']
        if 'order_certificate' in request.FILES:
            sem.order_certificate = request.FILES['order_certificate']
            
        sem.save()
        
        co_authors = request.POST.getlist('co_authors')
        selected_staffs = [staff]
        for cid in co_authors:
            if cid != staff.staff_id:
                try:
                    co_staff = Staff.objects.get(staff_id=cid)
                    selected_staffs.append(co_staff)
                except Staff.DoesNotExist:
                    pass
        sem.staff.set(selected_staffs)
        
        from .utils import log_audit
        log_audit(request, 'update', actor_type='staff', actor_id=staff.staff_id, actor_name=staff.name, object_type='Seminar', object_id=str(sem.pk), message='Updated seminar/event entry')
        messages.success(request, "Event entry updated successfully.")
        return redirect('staffs:staff_portfolio')
        
    all_staffs = Staff.objects.all().order_by('name')
    return render(request, 'staff/portfolio_form.html', {
        'staff': staff, 'form_type': 'seminar', 'item': sem, 'title': 'Edit Event Entry', 'all_staffs': all_staffs,
    })

# --- New Portfolio Views (Conferences, Journals, Books) ---

def _get_guided_scholars_for_staff(staff):
    """
    Helper to fetch ONLY students/scholars guided by or assigned to this staff member:
    1. Current & Completed PhD Scholars supervised by staff (ResearchScholarProfile).
    2. PhD Scholars where staff is a RAC Committee Member (RACMember).
    3. All Guided Students recorded in StaffStudentGuided (both Previous and Current PG/PhD).
    """
    from students.models import Student, ResearchScholarProfile, RACMember
    from django.db.models import Q
    guided_scholars = []
    seen_pks = set()

    # 1. PhD Scholars supervised by this staff (Current & Completed)
    for profile in staff.supervised_scholars.select_related('student').all():
        student = profile.student
        if student and student.pk not in seen_pks:
            seen_pks.add(student.pk)
            guided_scholars.append({
                'pk': student.pk,
                'student_name': student.student_name,
                'roll_number': student.roll_number or '',
                'type': f"PhD Scholar ({profile.status})",
                'status': profile.status
            })

    # 2. PhD Scholars where staff is a RAC Committee Member
    rac_memberships = RACMember.objects.filter(staff=staff).select_related('scholar')
    for rac in rac_memberships:
        student = rac.scholar
        if student and student.pk not in seen_pks:
            seen_pks.add(student.pk)
            status = 'Ongoing'
            if hasattr(student, 'scholar_profile') and student.scholar_profile:
                status = student.scholar_profile.status
            guided_scholars.append({
                'pk': student.pk,
                'student_name': student.student_name,
                'roll_number': student.roll_number or '',
                'type': f"PhD Scholar (RAC Member - {status})",
                'status': status
            })

    # 3. Students guided by this staff (from StaffStudentGuided - Previous & Current)
    for g in staff.student_guided_list.all():
        stu_match = None
        if g.roll_number and g.roll_number.strip():
            stu_match = Student.objects.filter(roll_number__iexact=g.roll_number.strip()).first()
        if not stu_match and g.student_name and g.student_name.strip():
            stu_match = Student.objects.filter(student_name__iexact=g.student_name.strip()).first()

        if stu_match and g.roll_number and g.roll_number.strip() and stu_match.roll_number != g.roll_number.strip():
            if not Student.objects.filter(roll_number__iexact=g.roll_number.strip()).exclude(pk=stu_match.pk).exists():
                stu_match.roll_number = g.roll_number.strip()
                stu_match.save()

        # If no Student object exists yet for this guided student, get or create a lightweight Student record
        if not stu_match:
            roll_val = g.roll_number.strip() if (g.roll_number and g.roll_number.strip()) else f"GS{g.pk:04d}"
            stu_match, _ = Student.objects.get_or_create(
                roll_number=roll_val,
                defaults={
                    'student_name': g.student_name.strip() if g.student_name else 'Guided Student',
                    'current_semester': 8 if g.degree_type == 'PG' else 10,
                    'program_level': g.degree_type or 'PG',
                }
            )

        if stu_match and stu_match.pk not in seen_pks:
            seen_pks.add(stu_match.pk)
            spec_str = f" - {g.specialization}" if g.specialization else ""
            guided_scholars.append({
                'pk': stu_match.pk,
                'student_name': stu_match.student_name,
                'roll_number': g.roll_number.strip() if (g.roll_number and g.roll_number.strip()) else (stu_match.roll_number or ''),
                'type': f"{g.degree_type}{spec_str} ({g.status})",
                'status': g.status
            })

    return guided_scholars

def _save_item_students(item, request):
    co_students = request.POST.getlist('co_students') or request.POST.getlist('student') or request.POST.getlist('students')
    selected_students = []
    from students.models import Student
    for sid in co_students:
        if sid:
            try:
                stu = Student.objects.get(pk=sid)
                if stu not in selected_students:
                    selected_students.append(stu)
            except (Student.DoesNotExist, ValueError):
                pass
    item.student = selected_students[0] if selected_students else None
    item.save()
    if hasattr(item, 'students'):
        item.students.set(selected_students)

def _get_item_student_pks(item):
    if not item:
        return set()
    if hasattr(item, 'students') and item.students.exists():
        return set(item.students.values_list('pk', flat=True))
    if item.student:
        return {item.student.pk}
    return set()

def portfolio_add_conference(request):
    staff = _get_staff_for_portfolio(request)
    if not staff: return redirect('staffs:stafflogin')
    
    if request.method == 'POST':
        from .models import ConferenceParticipation
        item = ConferenceParticipation(
            participation_type=request.POST.get('participation_type', 'Presented'),
            national_international=request.POST.get('national_international', 'National'),
            year_of_publication=request.POST.get('year_of_publication', ''),
            title_of_paper=request.POST.get('title_of_paper', ''),
            title_of_proceedings=request.POST.get('title_of_proceedings', ''),
            date_from=request.POST.get('date_from') or None,
            date_to=request.POST.get('date_to') or None,
            location=request.POST.get('location', ''),
            page_numbers_from=request.POST.get('page_numbers_from', ''),
            page_numbers_to=request.POST.get('page_numbers_to', ''),
            place_of_publication=request.POST.get('place_of_publication', ''),
            publisher_proceedings=request.POST.get('publisher_proceedings', ''),
            supporting_document=request.FILES.get('supporting_document'),
        )
        item._temp_staff_id = staff.staff_id
        item.save()
        _save_item_students(item, request)
        
        # Link co-authors and auto-generate author_name
        co_authors = request.POST.getlist('co_authors')
        selected_staffs = [staff]
        for cid in co_authors:
            if cid != staff.staff_id:
                try:
                    co_staff = Staff.objects.get(staff_id=cid)
                    selected_staffs.append(co_staff)
                except Staff.DoesNotExist:
                    pass
        item.author_name = ", ".join([f"{s.salutation} {s.name}".strip() for s in selected_staffs])
        item.save()
        item.staff.set(selected_staffs)
        
        messages.success(request, "Conference entry added successfully.")
        return redirect('staffs:staff_portfolio')
    
    all_staffs = Staff.objects.all().order_by('name')
    guided_scholars = _get_guided_scholars_for_staff(staff)
    return render(request, 'staff/portfolio_form.html', {
        'staff': staff, 'form_type': 'conference', 'item': None, 'title': 'Add Conference Participation', 'all_staffs': all_staffs, 'guided_scholars': guided_scholars, 'item_student_pks': set(),
    })

def portfolio_add_journal(request):
    staff = _get_staff_for_portfolio(request)
    if not staff: return redirect('staffs:stafflogin')

    if request.method == 'POST':
        from .models import JournalPublication
        item = JournalPublication(
            national_international=request.POST.get('national_international', 'National'),
            published_month=request.POST.get('published_month', ''),
            published_year=request.POST.get('published_year', ''),
            title_of_paper=request.POST.get('title_of_paper', ''),
            journal_name=request.POST.get('journal_name', ''),
            volume_number=request.POST.get('volume_number', ''),
            issue_number=request.POST.get('issue_number', ''),
            year_of_publication_doi=request.POST.get('year_of_publication_doi', ''),
            page_numbers_from=request.POST.get('page_numbers_from', ''),
            page_numbers_to=request.POST.get('page_numbers_to', ''),
            is_scopus=request.POST.get('is_scopus') == 'on',
            is_wos=request.POST.get('is_wos') == 'on',
            is_sci=request.POST.get('is_sci') == 'on',
            is_scie=request.POST.get('is_scie') == 'on',
            is_ugc=request.POST.get('is_ugc') == 'on',
            supporting_document=request.FILES.get('supporting_document'),
        )
        item._temp_staff_id = staff.staff_id
        item.save()
        _save_item_students(item, request)
        
        # Link co-authors and auto-generate author_name
        co_authors = request.POST.getlist('co_authors')
        selected_staffs = [staff]
        for cid in co_authors:
            if cid != staff.staff_id:
                try:
                    co_staff = Staff.objects.get(staff_id=cid)
                    selected_staffs.append(co_staff)
                except Staff.DoesNotExist:
                    pass
        item.author_name = ", ".join([f"{s.salutation} {s.name}".strip() for s in selected_staffs])
        item.save()
        item.staff.set(selected_staffs)
                
        messages.success(request, "Journal publication added successfully.")
        return redirect('staffs:staff_portfolio')
    
    all_staffs = Staff.objects.all().order_by('name')
    guided_scholars = _get_guided_scholars_for_staff(staff)
    return render(request, 'staff/portfolio_form.html', {
        'staff': staff, 'form_type': 'journal', 'item': None, 'title': 'Add Journal Publication', 'all_staffs': all_staffs, 'guided_scholars': guided_scholars, 'item_student_pks': set(),
    })

def portfolio_add_book(request):
    staff = _get_staff_for_portfolio(request)
    if not staff: return redirect('staffs:stafflogin')

    if request.method == 'POST':
        from .models import BookPublication
        item = BookPublication(
            type=request.POST.get('type', 'Book'),
            title_of_book=request.POST.get('title_of_book', ''),
            publisher_name=request.POST.get('publisher_name', ''),
            publisher_address=request.POST.get('publisher_address', ''),
            isbn_issn_number=request.POST.get('isbn_issn_number', ''),
            page_numbers_from=request.POST.get('page_numbers_from', ''),
            page_numbers_to=request.POST.get('page_numbers_to', ''),
            month_of_publication=request.POST.get('month_of_publication', ''),
            year_of_publication=request.POST.get('year_of_publication', ''),
            url_address=request.POST.get('url_address') or None,
            supporting_document=request.FILES.get('supporting_document'),
        )
        item._temp_staff_id = staff.staff_id
        item.save()
        _save_item_students(item, request)
        
        # Link co-authors and auto-generate author_name
        co_authors = request.POST.getlist('co_authors')
        selected_staffs = [staff]
        for cid in co_authors:
            if cid != staff.staff_id:
                try:
                    co_staff = Staff.objects.get(staff_id=cid)
                    selected_staffs.append(co_staff)
                except Staff.DoesNotExist:
                    pass
        item.author_name = ", ".join([f"{s.salutation} {s.name}".strip() for s in selected_staffs])
        item.save()
        item.staff.set(selected_staffs)
                
        messages.success(request, "Book/Article entry added successfully.")
        return redirect('staffs:staff_portfolio')
    
    all_staffs = Staff.objects.all().order_by('name')
    guided_scholars = _get_guided_scholars_for_staff(staff)
    return render(request, 'staff/portfolio_form.html', {
        'staff': staff, 'form_type': 'book', 'item': None, 'title': 'Add Book / Article', 'all_staffs': all_staffs, 'guided_scholars': guided_scholars, 'item_student_pks': set(),
    })

from .forms import StaffQualificationForm, StaffPastDesignationForm, StaffMembershipForm, StaffResearchProjectForm

def portfolio_add_research_project(request):
    staff = _get_staff_for_portfolio(request)
    if not staff: return redirect('staffs:stafflogin')
    
    if request.method == 'POST':
        form = StaffResearchProjectForm(request.POST, request.FILES)
        if form.is_valid():
            project = form.save(commit=False)
            project.staff = staff
            project.save()
            messages.success(request, "Research Project added successfully.")
            return redirect('staffs:staff_portfolio')
    else:
        form = StaffResearchProjectForm()
        
    return render(request, 'staff/portfolio_generic_form.html', {
        'staff': staff, 'form': form, 'title': 'Add Research Project'
    })

def portfolio_edit_research_project(request, pk):
    from .models import StaffResearchProject
    staff = _get_staff_for_portfolio(request)
    if not staff: return redirect('staffs:stafflogin')
    item = get_object_or_404(StaffResearchProject, pk=pk, staff=staff)
    if request.method == 'POST':
        form = StaffResearchProjectForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, "Research Project updated successfully.")
            return redirect('staffs:staff_portfolio')
    else:
        form = StaffResearchProjectForm(instance=item)
    return render(request, 'staff/portfolio_generic_form.html', {
        'staff': staff, 'form': form, 'title': 'Edit Research Project'
    })

def portfolio_add_qualification(request):
    staff = _get_staff_for_portfolio(request)
    if not staff: return redirect('staffs:stafflogin')
    
    if request.method == 'POST':
        form = StaffQualificationForm(request.POST, request.FILES)
        if form.is_valid():
            qual = form.save(commit=False)
            qual.staff = staff
            qual.approval_status = 'Approved'
            qual.save()
            messages.success(request, "Qualification added successfully.")
            return redirect('staffs:staff_portfolio')
    else:
        form = StaffQualificationForm()
        
    return render(request, 'staff/portfolio_generic_form.html', {
        'staff': staff, 'form': form, 'title': 'Add Qualification'
    })

def portfolio_edit_qualification(request, pk):
    from .models import StaffQualification
    staff = _get_staff_for_portfolio(request)
    if not staff: return redirect('staffs:stafflogin')
    item = get_object_or_404(StaffQualification, pk=pk, staff=staff)
    if request.method == 'POST':
        form = StaffQualificationForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            qual = form.save(commit=False)
            qual.approval_status = 'Approved'
            qual.save()
            messages.success(request, "Qualification updated.")
            return redirect('staffs:staff_portfolio')
    else:
        form = StaffQualificationForm(instance=item)
    return render(request, 'staff/portfolio_generic_form.html', {
        'staff': staff, 'form': form, 'title': 'Edit Qualification'
    })

def sync_staff_additional_designation(staff_member):
    """
    Sync both primary designation and additional posts based on approved Present designations.
    """
    # 1. Sync Primary Designation (is_additional=False)
    latest_present_primary = staff_member.past_designations.filter(
        approval_status='Approved',
        to_date__isnull=True,
        is_additional=False
    ).order_by('-from_date', '-id').first()

    if latest_present_primary:
        staff_member.designation = latest_present_primary.designation
    else:
        staff_member.designation = ''  # No approved present designation → clear it

    # 2. Sync Additional Designation (is_additional=True)
    latest_present_additional = staff_member.past_designations.filter(
        approval_status='Approved',
        to_date__isnull=True,
        is_additional=True
    ).order_by('-from_date', '-id').first()

    if latest_present_additional:
        staff_member.additional_designation = latest_present_additional.designation
    else:
        staff_member.additional_designation = None

    staff_member.save(update_fields=['designation', 'additional_designation'])


def portfolio_add_designation(request):
    staff = _get_staff_for_portfolio(request)
    if not staff: return redirect('staffs:stafflogin')
    is_additional = request.GET.get('type') == 'additional'
    if request.method == 'POST':
        form = StaffPastDesignationForm(request.POST, request.FILES)
        if form.is_valid():
            des = form.save(commit=False)
            des.staff = staff
            des.approval_status = 'Pending' if not des.to_date else 'Approved'
            des.is_additional = is_additional
            des.save()
            sync_staff_additional_designation(staff)
            messages.success(request, "Designation added.")
            return redirect('staffs:staff_portfolio')
    else:
        initial_data = {}
        if request.GET.get('type') == 'additional':
            initial_data['is_present'] = True
        form = StaffPastDesignationForm(initial=initial_data)
    
    title = 'Add Additional Post' if request.GET.get('type') == 'additional' else 'Add Designation'
    return render(request, 'staff/portfolio_generic_form.html', {
        'staff': staff, 'form': form, 'title': title
    })

def portfolio_edit_designation(request, pk):
    from .models import StaffPastDesignation
    staff = _get_staff_for_portfolio(request)
    if not staff: return redirect('staffs:stafflogin')
    item = get_object_or_404(StaffPastDesignation, pk=pk, staff=staff)
    if request.method == 'POST':
        form = StaffPastDesignationForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            des = form.save(commit=False)
            des.approval_status = 'Pending' if not des.to_date else 'Approved'
            des.save()
            sync_staff_additional_designation(staff)
            messages.success(request, "Designation updated.")
            return redirect('staffs:staff_portfolio')
    else:
        form = StaffPastDesignationForm(instance=item)
    return render(request, 'staff/portfolio_generic_form.html', {
        'staff': staff, 'form': form, 'title': 'Edit Designation'
    })

def portfolio_add_membership(request):
    staff = _get_staff_for_portfolio(request)
    if not staff: return redirect('staffs:stafflogin')
    if request.method == 'POST':
        form = StaffMembershipForm(request.POST, request.FILES)
        if form.is_valid():
            mem = form.save(commit=False)
            mem.staff = staff
            mem.save()
            messages.success(request, "Membership added.")
            return redirect('staffs:staff_portfolio')
    else:
        form = StaffMembershipForm()
    return render(request, 'staff/portfolio_generic_form.html', {
        'staff': staff, 'form': form, 'title': 'Add Membership'
    })

def portfolio_edit_membership(request, pk):
    from .models import StaffMembership
    staff = _get_staff_for_portfolio(request)
    if not staff: return redirect('staffs:stafflogin')
    item = get_object_or_404(StaffMembership, pk=pk, staff=staff)
    if request.method == 'POST':
        form = StaffMembershipForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, "Membership updated.")
            return redirect('staffs:staff_portfolio')
    else:
        form = StaffMembershipForm(instance=item)
    return render(request, 'staff/portfolio_generic_form.html', {
        'staff': staff, 'form': form, 'title': 'Edit Membership'
    })


def portfolio_delete_entry(request, model_name, pk):
    staff = _get_staff_for_portfolio(request)
    if not staff: return redirect('staffs:stafflogin')
    
    from .models import ConferenceParticipation, JournalPublication, BookPublication, StaffAwardHonour, StaffSeminar, StaffStudentGuided, StaffPublication, StaffQualification, StaffPastDesignation, StaffMembership, StaffPatent, StaffResearchProject
    
    model_map = {
        'conference': ConferenceParticipation,
        'journal': JournalPublication,
        'book': BookPublication,
        'award': StaffAwardHonour,
        'seminar': StaffSeminar,
        'student_guided': StaffStudentGuided,
        'qualification': StaffQualification,
        'designation': StaffPastDesignation,
        'membership': StaffMembership,
        'patent': StaffPatent,
        'research_project': StaffResearchProject,
    }
    
    ModelClass = model_map.get(model_name)
    if ModelClass:
        item = get_object_or_404(ModelClass, pk=pk, staff=staff)
        if model_name in ['journal', 'book', 'conference', 'seminar', 'patent'] and item.staff.count() > 1:
            item.staff.remove(staff)
        else:
            item.delete()
        if model_name == 'designation':
            sync_staff_additional_designation(staff)
        messages.success(request, "Entry deleted.")
    
    return redirect('staffs:staff_portfolio')

def portfolio_add_patent(request):
    staff = _get_staff_for_portfolio(request)
    if not staff: return redirect('staffs:stafflogin')

    if request.method == 'POST':
        from .models import StaffPatent
        item = StaffPatent(
            title=request.POST.get('title', '').strip(),
            application_number=request.POST.get('application_number', '').strip(),
            patent_type=request.POST.get('patent_type', 'Indian'),
            status=request.POST.get('status', 'Applied'),
            application_year=request.POST.get('application_year', '').strip(),
            grant_year=request.POST.get('grant_year', '').strip(),
            funding_agency=request.POST.get('funding_agency', '').strip(),
            description=request.POST.get('description', '').strip(),
        )
        if 'supporting_document' in request.FILES:
            item.supporting_document = request.FILES['supporting_document']
        item._temp_staff_id = staff.staff_id
        item.save()
        _save_item_students(item, request)
        
        # Link co-inventors and auto-generate inventors field
        co_authors = request.POST.getlist('co_authors')
        selected_staffs = [staff]
        for cid in co_authors:
            if cid != staff.staff_id:
                try:
                    co_staff = Staff.objects.get(staff_id=cid)
                    selected_staffs.append(co_staff)
                except Staff.DoesNotExist:
                    pass
        item.inventors = ", ".join([f"{s.salutation} {s.name}".strip() for s in selected_staffs])
        item.save()
        item.staff.set(selected_staffs)
        
        messages.success(request, "Patent added successfully.")
        return redirect('staffs:staff_portfolio')
    
    all_staffs = Staff.objects.all().order_by('name')
    guided_scholars = _get_guided_scholars_for_staff(staff)
    return render(request, 'staff/portfolio_form.html', {
        'staff': staff, 'form_type': 'patent', 'item': None, 'title': 'Add Patent', 'all_staffs': all_staffs, 'guided_scholars': guided_scholars, 'item_student_pks': set(),
    })


def portfolio_edit_patent(request, pk):
    staff = _get_staff_for_portfolio(request)
    if not staff: return redirect('staffs:stafflogin')

    from .models import StaffPatent
    item = get_object_or_404(StaffPatent, pk=pk, staff=staff)

    if request.method == 'POST':
        item.title = request.POST.get('title', '').strip()
        item.application_number = request.POST.get('application_number', '').strip()
        item.patent_type = request.POST.get('patent_type', 'Indian')
        item.status = request.POST.get('status', 'Applied')
        item.application_year = request.POST.get('application_year', '').strip()
        item.grant_year = request.POST.get('grant_year', '').strip()
        item.funding_agency = request.POST.get('funding_agency', '').strip()
        item.description = request.POST.get('description', '').strip()

        if 'supporting_document' in request.FILES:
            item.supporting_document = request.FILES['supporting_document']
        item._temp_staff_id = staff.staff_id
        item.save()
        _save_item_students(item, request)
        
        # Update co-inventors and inventors field
        co_authors = request.POST.getlist('co_authors')
        selected_staffs = [staff]
        for cid in co_authors:
            if cid != staff.staff_id:
                try:
                    co_staff = Staff.objects.get(staff_id=cid)
                    selected_staffs.append(co_staff)
                except Staff.DoesNotExist:
                    pass
        item.inventors = ", ".join([f"{s.salutation} {s.name}".strip() for s in selected_staffs])
        item.save()
        item.staff.set(selected_staffs)
        
        messages.success(request, "Patent updated successfully.")
        return redirect('staffs:staff_portfolio')

    all_staffs = Staff.objects.all().order_by('name')
    guided_scholars = _get_guided_scholars_for_staff(staff)
    return render(request, 'staff/portfolio_form.html', {
        'staff': staff, 'form_type': 'patent', 'item': item, 'title': 'Edit Patent', 'all_staffs': all_staffs, 'guided_scholars': guided_scholars, 'item_student_pks': _get_item_student_pks(item),
    })


def portfolio_edit_conference(request, pk):
    staff = _get_staff_for_portfolio(request)
    if not staff:
        return redirect('staffs:stafflogin')
    
    from .models import ConferenceParticipation
    item = get_object_or_404(ConferenceParticipation, pk=pk, staff=staff)
    
    if request.method == 'POST':
        item.participation_type = request.POST.get('participation_type', 'Presented')
        item.national_international = request.POST.get('national_international', 'National')
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
        
        if 'supporting_document' in request.FILES:
            item.supporting_document = request.FILES['supporting_document']
            
        item._temp_staff_id = staff.staff_id
        item.save()
        _save_item_students(item, request)
        
        # Link co-authors and auto-generate author_name
        co_authors = request.POST.getlist('co_authors')
        selected_staffs = [staff]
        for cid in co_authors:
            if cid != staff.staff_id:
                try:
                    co_staff = Staff.objects.get(staff_id=cid)
                    selected_staffs.append(co_staff)
                except Staff.DoesNotExist:
                    pass
        item.author_name = ", ".join([f"{s.salutation} {s.name}".strip() for s in selected_staffs])
        item.save()
        item.staff.set(selected_staffs)
        
        from .utils import log_audit
        log_audit(request, 'update', actor_type='staff', actor_id=staff.staff_id, actor_name=staff.name, 
                  object_type='Conference', object_id=str(item.pk), message='Updated conference entry')
        messages.success(request, "Conference entry updated successfully.")
        return redirect('staffs:staff_portfolio')
    
    all_staffs = Staff.objects.all().order_by('name')
    guided_scholars = _get_guided_scholars_for_staff(staff)
    return render(request, 'staff/portfolio_form.html', {
        'staff': staff, 'form_type': 'conference', 'item': item, 'title': 'Edit Conference Participation', 'all_staffs': all_staffs, 'guided_scholars': guided_scholars, 'item_student_pks': _get_item_student_pks(item),
    })


def portfolio_edit_journal(request, pk):
    staff = _get_staff_for_portfolio(request)
    if not staff:
        return redirect('staffs:stafflogin')
    
    from .models import JournalPublication
    item = get_object_or_404(JournalPublication, pk=pk, staff=staff)
    
    if request.method == 'POST':
        item.national_international = request.POST.get('national_international', 'National')
        item.published_month = request.POST.get('published_month', '').strip()
        item.published_year = request.POST.get('published_year', '').strip()
        item.title_of_paper = request.POST.get('title_of_paper', '').strip()
        item.journal_name = request.POST.get('journal_name', '').strip()
        item.volume_number = request.POST.get('volume_number', '').strip()
        item.issue_number = request.POST.get('issue_number', '').strip()
        item.year_of_publication_doi = request.POST.get('year_of_publication_doi', '').strip()
        item.page_numbers_from = request.POST.get('page_numbers_from', '').strip()
        item.page_numbers_to = request.POST.get('page_numbers_to', '').strip()
        item.is_scopus = request.POST.get('is_scopus') == 'on'
        item.is_wos = request.POST.get('is_wos') == 'on'
        item.is_sci = request.POST.get('is_sci') == 'on'
        item.is_scie = request.POST.get('is_scie') == 'on'
        item.is_ugc = request.POST.get('is_ugc') == 'on'
        
        if 'supporting_document' in request.FILES:
            item.supporting_document = request.FILES['supporting_document']

        item._temp_staff_id = staff.staff_id
        item.save()
        _save_item_students(item, request)
        
        # Update ManyToMany co-authors and auto-generate author_name
        co_authors = request.POST.getlist('co_authors')
        selected_staffs = [staff]
        for cid in co_authors:
            if cid != staff.staff_id:
                try:
                    co_staff = Staff.objects.get(staff_id=cid)
                    selected_staffs.append(co_staff)
                except Staff.DoesNotExist:
                    pass
        item.author_name = ", ".join([f"{s.salutation} {s.name}".strip() for s in selected_staffs])
        item.save()
        item.staff.set(selected_staffs)
        
        from .utils import log_audit
        log_audit(request, 'update', actor_type='staff', actor_id=staff.staff_id, actor_name=staff.name, 
                  object_type='Journal', object_id=str(item.pk), message='Updated journal publication')
        messages.success(request, "Journal publication updated successfully.")
        return redirect('staffs:staff_portfolio')
    
    all_staffs = Staff.objects.all().order_by('name')
    guided_scholars = _get_guided_scholars_for_staff(staff)
    return render(request, 'staff/portfolio_form.html', {
        'staff': staff, 'form_type': 'journal', 'item': item, 'title': 'Edit Journal Publication', 'all_staffs': all_staffs, 'guided_scholars': guided_scholars, 'item_student_pks': _get_item_student_pks(item),
    })


def portfolio_edit_book(request, pk):
    staff = _get_staff_for_portfolio(request)
    if not staff:
        return redirect('staffs:stafflogin')
    
    from .models import BookPublication
    item = get_object_or_404(BookPublication, pk=pk, staff=staff)
    
    if request.method == 'POST':
        item.type = request.POST.get('type', 'Book')
        item.title_of_book = request.POST.get('title_of_book', '').strip()
        item.publisher_name = request.POST.get('publisher_name', '').strip()
        item.publisher_address = request.POST.get('publisher_address', '').strip()
        item.isbn_issn_number = request.POST.get('isbn_issn_number', '').strip()
        item.page_numbers_from = request.POST.get('page_numbers_from', '').strip()
        item.page_numbers_to = request.POST.get('page_numbers_to', '').strip()
        item.month_of_publication = request.POST.get('month_of_publication', '').strip()
        item.year_of_publication = request.POST.get('year_of_publication', '').strip()
        item.url_address = request.POST.get('url_address') or None
        
        if 'supporting_document' in request.FILES:
            item.supporting_document = request.FILES['supporting_document']

        item._temp_staff_id = staff.staff_id
        item.save()
        _save_item_students(item, request)
        
        # Update ManyToMany co-authors and auto-generate author_name
        co_authors = request.POST.getlist('co_authors')
        selected_staffs = [staff]
        for cid in co_authors:
            if cid != staff.staff_id:
                try:
                    co_staff = Staff.objects.get(staff_id=cid)
                    selected_staffs.append(co_staff)
                except Staff.DoesNotExist:
                    pass
        item.author_name = ", ".join([f"{s.salutation} {s.name}".strip() for s in selected_staffs])
        item.save()
        item.staff.set(selected_staffs)
        
        from .utils import log_audit
        log_audit(request, 'update', actor_type='staff', actor_id=staff.staff_id, actor_name=staff.name, 
                  object_type='Book', object_id=str(item.pk), message='Updated book/article entry')
        messages.success(request, "Book/Article entry updated successfully.")
        return redirect('staffs:staff_portfolio')
    
    all_staffs = Staff.objects.all().order_by('name')
    guided_scholars = _get_guided_scholars_for_staff(staff)
    return render(request, 'staff/portfolio_form.html', {
        'staff': staff, 'form_type': 'book', 'item': item, 'title': 'Edit Book / Popular Article', 'all_staffs': all_staffs, 'guided_scholars': guided_scholars, 'item_student_pks': _get_item_student_pks(item),
    })



def portfolio_edit_seminar(request, pk):
    staff = _get_staff_for_portfolio(request)
    if not staff:
        return redirect('staffs:stafflogin')
    item = get_object_or_404(StaffSeminar, pk=pk, staff=staff)
    if request.method == 'POST':
        item.title = request.POST.get('title', '').strip()
        item.event_type = request.POST.get('event_type', 'Seminar')
        item.venue_or_description = request.POST.get('venue_or_description', '').strip()
        item.organized_by = request.POST.get('organized_by', '').strip()
        item.date_from = request.POST.get('date_from') or None
        item.date_to = request.POST.get('date_to') or None
        item.year = request.POST.get('year', '').strip()
        item.mode = request.POST.get('mode', 'Offline')
        item.participation_role = request.POST.get('participation_role', 'Attended')
        if 'supporting_document' in request.FILES:
            item.supporting_document = request.FILES['supporting_document']
        if 'order_certificate' in request.FILES:
            item.order_certificate = request.FILES['order_certificate']
        item._temp_staff_id = staff.staff_id
        item.save()
        
        # Link co-authors
        co_authors = request.POST.getlist('co_authors')
        selected_staffs = [staff]
        for cid in co_authors:
            if cid != staff.staff_id:
                try:
                    co_staff = Staff.objects.get(staff_id=cid)
                    selected_staffs.append(co_staff)
                except Staff.DoesNotExist:
                    pass
        item.staff.set(selected_staffs)
        
        from .utils import log_audit
        log_audit(request, 'update', actor_type='staff', actor_id=staff.staff_id, actor_name=staff.name, object_type='Seminar', object_id=str(item.pk), message='Updated seminar')
        messages.success(request, "Entry updated.")
        return redirect('staffs:staff_portfolio')
        
    all_staffs = Staff.objects.all().order_by('name')
    return render(request, 'staff/portfolio_form.html', {
        'staff': staff, 'form_type': 'seminar', 'item': item, 'title': 'Edit Seminar / Workshop / Conference', 'all_staffs': all_staffs,
    })


def portfolio_delete_seminar(request, pk):
    staff = _get_staff_for_portfolio(request)
    if not staff:
        return redirect('staffs:stafflogin')
    item = get_object_or_404(StaffSeminar, pk=pk, staff=staff)
    if request.method == 'POST':
        item.delete()
        from .utils import log_audit
        log_audit(request, 'delete', actor_type='staff', actor_id=staff.staff_id, actor_name=staff.name, object_type='Seminar', object_id=str(pk), message='Deleted seminar')
        messages.success(request, "Entry removed.")
        return redirect('staffs:staff_portfolio')
    return render(request, 'staff/portfolio_confirm_delete.html', {
        'staff': staff, 'item': item, 'item_label': item.title, 'cancel_url': 'staffs:staff_portfolio',
    })


def portfolio_delete_award(request, pk):
    staff = _get_staff_for_portfolio(request)
    if not staff:
        return redirect('staffs:stafflogin')
    item = get_object_or_404(StaffAwardHonour, pk=pk, staff=staff)
    if request.method == 'POST':
        item.delete()
        from .utils import log_audit
        log_audit(request, 'delete', actor_type='staff', actor_id=staff.staff_id, actor_name=staff.name, object_type='Award', object_id=str(pk), message='Deleted award/honour')
        messages.success(request, "Entry removed.")
        return redirect('staffs:staff_portfolio')
    return render(request, 'staff/portfolio_confirm_delete.html', {
        'staff': staff, 'item': item, 'item_label': item.title, 'cancel_url': 'staffs:staff_portfolio',
    })


def portfolio_add_student(request):
    staff = _get_staff_for_portfolio(request)
    if not staff:
        return redirect('staffs:stafflogin')
    if request.method == 'POST':
        viva_date_str = request.POST.get('viva_date', '').strip()
        new_name = request.POST.get('student_name', '').strip()
        new_roll = request.POST.get('roll_number', '').strip()

        g = StaffStudentGuided.objects.create(
            staff=staff,
            student_name=new_name,
            degree_type=request.POST.get('degree_type', 'PG'),
            status=request.POST.get('status', 'Ongoing'),
            year=request.POST.get('year', '').strip(),
            viva_date=viva_date_str if viva_date_str else None,
            supporting_document=request.FILES.get('supporting_document'),
            department=request.POST.get('department', '').strip(),
            specialization=request.POST.get('specialization', '').strip(),
            roll_number=new_roll,
            thesis_title=request.POST.get('thesis_title', '').strip(),
            thesis_document=request.FILES.get('thesis_document'),
            papers_pdf=request.FILES.get('papers_pdf'),
        )

        from students.models import Student
        stu = None
        if new_roll:
            stu = Student.objects.filter(roll_number__iexact=new_roll).first()
        if not stu and new_name:
            stu = Student.objects.filter(student_name__iexact=new_name).first()

        if stu:
            updated = False
            if new_roll and stu.roll_number != new_roll:
                if not Student.objects.filter(roll_number__iexact=new_roll).exclude(pk=stu.pk).exists():
                    stu.roll_number = new_roll
                    updated = True
            if new_name and stu.student_name != new_name:
                stu.student_name = new_name
                updated = True
            if updated:
                stu.save()
        else:
            roll_val = new_roll if new_roll else f"GS{g.pk:04d}"
            Student.objects.get_or_create(
                roll_number=roll_val,
                defaults={
                    'student_name': new_name if new_name else 'Guided Student',
                    'current_semester': 8 if g.degree_type == 'PG' else 10,
                    'program_level': g.degree_type or 'PG',
                }
            )

        from .utils import log_audit
        log_audit(request, 'create', actor_type='staff', actor_id=staff.staff_id, actor_name=staff.name, object_type='StudentGuided', message='Added new student guidance')
        messages.success(request, "Student added.")
        return redirect('staffs:staff_portfolio')
    return render(request, 'staff/portfolio_form.html', {
        'staff': staff, 'form_type': 'student', 'item': None, 'title': 'Add Student Guided',
    })


def portfolio_edit_student(request, pk):
    staff = _get_staff_for_portfolio(request)
    if not staff:
        return redirect('staffs:stafflogin')
    item = get_object_or_404(StaffStudentGuided, pk=pk, staff=staff)
    if request.method == 'POST':
        old_roll = (item.roll_number or '').strip()
        old_name = (item.student_name or '').strip()

        new_name = request.POST.get('student_name', '').strip()
        new_roll = request.POST.get('roll_number', '').strip()

        item.student_name = new_name
        item.degree_type = request.POST.get('degree_type', 'PG')
        item.status = request.POST.get('status', 'Ongoing')
        item.year = request.POST.get('year', '').strip()
        viva_date_str = request.POST.get('viva_date', '').strip()
        item.viva_date = viva_date_str if viva_date_str else None
        item.department = request.POST.get('department', '').strip()
        item.specialization = request.POST.get('specialization', '').strip()
        item.roll_number = new_roll
        item.thesis_title = request.POST.get('thesis_title', '').strip()
        if 'supporting_document' in request.FILES:
            item.supporting_document = request.FILES['supporting_document']
        if 'thesis_document' in request.FILES:
            item.thesis_document = request.FILES['thesis_document']
        if 'papers_pdf' in request.FILES:
            item.papers_pdf = request.FILES['papers_pdf']
        item.save()

        # Keep Student model object roll_number & student_name in sync
        from students.models import Student
        stu = None
        if old_roll:
            stu = Student.objects.filter(roll_number__iexact=old_roll).first()
        if not stu and old_name:
            stu = Student.objects.filter(student_name__iexact=old_name).first()
        if not stu and new_roll:
            stu = Student.objects.filter(roll_number__iexact=new_roll).first()
        if not stu and new_name:
            stu = Student.objects.filter(student_name__iexact=new_name).first()

        if stu:
            updated = False
            if new_roll and stu.roll_number != new_roll:
                if not Student.objects.filter(roll_number__iexact=new_roll).exclude(pk=stu.pk).exists():
                    stu.roll_number = new_roll
                    updated = True
            if new_name and stu.student_name != new_name:
                stu.student_name = new_name
                updated = True
            if updated:
                stu.save()

        from .utils import log_audit
        log_audit(request, 'update', actor_type='staff', actor_id=staff.staff_id, actor_name=staff.name, object_type='StudentGuided', object_id=str(item.pk), message='Updated student guidance')
        messages.success(request, "Student entry updated.")
        return redirect('staffs:staff_portfolio')
    return render(request, 'staff/portfolio_form.html', {
        'staff': staff, 'form_type': 'student', 'item': item, 'title': 'Edit Student Guided',
    })


def portfolio_delete_student(request, pk):
    staff = _get_staff_for_portfolio(request)
    if not staff:
        return redirect('staffs:stafflogin')
    item = get_object_or_404(StaffStudentGuided, pk=pk, staff=staff)
    if request.method == 'POST':
        item.delete()
        from .utils import log_audit
        log_audit(request, 'delete', actor_type='staff', actor_id=staff.staff_id, actor_name=staff.name, object_type='StudentGuided', object_id=str(pk), message='Deleted student guidance')
        messages.success(request, "Student entry removed.")
        return redirect('staffs:staff_portfolio')
    return render(request, 'staff/portfolio_confirm_delete.html', {
        'staff': staff, 'item': item, 'item_label': f"{item.student_name} ({item.degree_type})", 'cancel_url': 'staffs:staff_portfolio',
    })

def archive_semester_data(student):
    """
    Helper to archive attendance and marks for all subjects in the student's current semester.
    """
    from staffs.models import Subject
    from students.models import StudentMarks, StudentAttendance, StudentGPA
    import datetime

    # Get all subjects for the student's current semester
    subjects = Subject.objects.filter(semester=student.current_semester)
    
    # Create/Get GPA record for this semester
    student_gpa, created = StudentGPA.objects.get_or_create(
        student=student, 
        semester=student.current_semester,
        defaults={'gpa': 0.0, 'total_credits': 0.0}
    )
    
    # Reset subject_data to avoid stale/duplicate entries if re-run
    student_gpa.subject_data = [] 
    
    total_points = 0
    total_sc = 0
    
    for subject in subjects:
        # 1. Calculate Attendance %
        total_classes = StudentAttendance.objects.filter(student=student, subject=subject).count()
        present_classes = StudentAttendance.objects.filter(student=student, subject=subject, status='Present').count()
        attendance_percentage = round((present_classes / total_classes) * 100, 1) if total_classes > 0 else 0.0
        
        # 2. Get Internals & Calculate Grade Point
        internal_marks = 0
        try:
            marks_record = StudentMarks.objects.get(student=student, subject=subject)
            internal_marks = marks_record.internal_marks or 0
        except StudentMarks.DoesNotExist:
            pass # Keep internal as 0
            
        # Simple Grade Point Logic 
        score = internal_marks 
        grade = 'RA'
        grade_point = 0
        
        if score >= 90: 
            grade_point = 10
            grade = 'O'
        elif score >= 80: 
            grade_point = 9
            grade = 'A+'
        elif score >= 70: 
            grade_point = 8
            grade = 'A'
        elif score >= 60: 
            grade_point = 7
            grade = 'B+'
        elif score >= 50: 
            grade_point = 6
            grade = 'B'
        else: 
            grade_point = 0
            grade = 'RA'
            
        # Append data
        new_entry = {
            'code': subject.code,
            'name': subject.name,
            'credits': getattr(subject, 'credits', 3), 
            'internal_marks': internal_marks,
            'attendance_percentage': attendance_percentage,
            'points': grade_point,
            'grade': grade,
            'archived_at': str(datetime.date.today())
        }
        student_gpa.subject_data.append(new_entry)
        
        # Accumulate for GPA
        creds = getattr(subject, 'credits', 3)
        total_points += (grade_point * creds)
        total_sc += creds

    # Finalize GPA
    student_gpa.gpa = round(total_points / total_sc, 2) if total_sc > 0 else 0.0
    student_gpa.total_credits = total_sc
    student_gpa.save()


def manage_semesters(request):
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')
    
    selected_semester = request.GET.get('semester')
    students = []
    
    if request.method == 'POST':
        student_ids = request.POST.getlist('student_ids')
        action = request.POST.get('action')

        if student_ids and action:
            from django.db.models import F
            
            if action == 'promote':
                # Loop through students to archive data individually BEFORE promoting
                count = 0
                for roll in student_ids:
                    try:
                        student = Student.objects.get(roll_number=roll)
                        if student.current_semester <= 8:
                            # ARCHIVE DATA FIRST
                            archive_semester_data(student)
                            
                            # PROMOTE
                            student.current_semester += 1
                            student.save()
                            count += 1
                    except Student.DoesNotExist:
                        continue
                        
                messages.success(request, f"Successfully promoted {count} students and archived their semester data.")
            
            elif action == 'demote':
                # Only demote if current_semester > 1.
                Student.objects.filter(roll_number__in=student_ids, current_semester__gt=1).update(current_semester=F('current_semester') - 1)
                messages.success(request, f"Successfully demoted selected students.")
                
            return redirect(f"{request.path}?semester={selected_semester}") # Stay on same page
        else:
            messages.warning(request, "No students selected or invalid action.")

    display_semester_selector = True
    header_text = "Filter by Current Semester"

    # Restrict for Class Incharge
    try:
        current_staff = Staff.objects.get(staff_id=request.session['staff_id'])
        if current_staff.has_role('Class Incharge') and current_staff.assigned_semester:
            selected_semester = str(current_staff.assigned_semester)
            display_semester_selector = False
            batch_str = f" (Batch {current_staff.assigned_batch})" if current_staff.assigned_batch in ['A', 'B'] else ""
            header_text = f"Managing Semester {selected_semester}{batch_str} (Assigned)"
    except Staff.DoesNotExist:
        pass

    if selected_semester:
        students = Student.objects.filter(current_semester=selected_semester)
        if 'current_staff' in locals() and current_staff and current_staff.has_role('Class Incharge') and current_staff.assigned_batch in ['A', 'B']:
            students = students.filter(lab_batch=current_staff.assigned_batch)
    
    return render(request, 'staff/manage_semesters.html', {
        'students': students, 
        'selected_semester': selected_semester,
        'display_semester_selector': display_semester_selector,
        'header_text': header_text
    })

# --- Staff Password Reset Logic ---

def staff_password_reset_identify(request):
    """Step 1: User provides their Staff ID."""
    staff = None
    if request.method == 'POST':
        staff_id = request.POST.get('staff_id')
        try:
            staff = Staff.objects.get(staff_id=staff_id)
            request.session['reset_staff_pk'] = staff.pk
            return redirect('staffs:password_reset_verify')
        except Staff.DoesNotExist:
            messages.error(request, 'No staff found with that Staff ID.')

    return render(request, 'staff/password_reset/p1.html', {'staff': staff})

def staff_password_reset_verify(request):
    """Step 2: User verifies with Mobile and Email (OTP)."""
    staff_pk = request.session.get('reset_staff_pk')
    if not staff_pk:
        return redirect('staffs:password_reset_identify')

    try:
        staff = Staff.objects.get(pk=staff_pk)
    except Staff.DoesNotExist:
        return redirect('staffs:password_reset_identify')

    if request.method == 'POST':
        action = request.POST.get('action')
        # Only OTP supported
        if action == 'send_otp':
            mobile_number = request.POST.get('staff_mobile')
            email_address = request.POST.get('staff_email')
            
            # Validation: Check if Mobile AND Email match
            if (staff.mobile_number == mobile_number and 
                staff.email == email_address):
                
                # Generate OTP
                import random
                from django.utils import timezone
                import datetime
                
                otp = str(random.randint(100000, 999999))
                
                # Store in session with expiry
                request.session['staff_reset_otp'] = otp
                request.session['staff_reset_otp_expiry'] = (timezone.now() + datetime.timedelta(minutes=10)).isoformat()
                
                # Send Email
                from django.core.mail import send_mail
                from django.template.loader import render_to_string
                from django.utils.html import strip_tags
                from django.conf import settings
                
                # Reuse student template or create generic? Using student generic one but passing staff name
                # 'emails/password_reset_email.html' expects 'otp' and 'student_name'. 
                # We can pass 'student_name' as staff.name to reuse it.
                
                html_content = render_to_string('emails/password_reset_email.html', {
                    'otp': otp,
                    'student_name': staff.name 
                })
                plain_message = strip_tags(html_content)

                try:
                    send_mail(
                        subject = "Password Reset OTP – Annamalai University - IT Department Staff Portal",
                        message = plain_message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[staff.email],
                        html_message=html_content,
                        fail_silently=False,
                    )
                    messages.success(request, f'OTP sent to registered email.')
                except Exception as e:
                    messages.error(request, f'Failed to send email: {str(e)}')
                
                return render(request, 'staff/password_reset/p2_otp.html', {
                    'email_mask': staff.email
                })
            else:
                 messages.error(request, 'Mobile Number or Email Address does not match our records.')

    return render(request, 'staff/password_reset/p2.html', {'staff': staff})

def staff_password_reset_otp_verify(request):
    """Step 2.5: Verify the entered OTP."""
    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        session_otp = request.session.get('staff_reset_otp')
        expiry_str = request.session.get('staff_reset_otp_expiry')
        
        if not session_otp or not expiry_str:
            messages.error(request, 'No OTP found or session expired. Please request a new one.')
            return redirect('staffs:password_reset_verify') 

        # Check expiry
        from django.utils import timezone
        import datetime
        expiry_time = datetime.datetime.fromisoformat(expiry_str)       
        if timezone.now() > expiry_time:
            messages.error(request, 'OTP has expired. Please request a new one.')
            return redirect('staffs:password_reset_identify')

        if entered_otp == session_otp:
            # Success
            request.session['staff_reset_verified'] = True
            # clear OTP session
            del request.session['staff_reset_otp']
            del request.session['staff_reset_otp_expiry']
            return redirect('staffs:password_reset_confirm')
        else:
            messages.error(request, 'Invalid OTP. Please try again.')
            # Re-render the OTP page
            staff_pk = request.session.get('reset_staff_pk')
            staff = Staff.objects.get(pk=staff_pk)
            return render(request, 'staff/password_reset/p2_otp.html', {
                 'email_mask': staff.email
            })
            
    return redirect('staffs:password_reset_identify')

def staff_password_reset_confirm(request):
    """Step 3: If verified, the user sets a new password."""
    staff_pk = request.session.get('reset_staff_pk')
    is_verified = request.session.get('staff_reset_verified')

    if not staff_pk or not is_verified:
        return redirect('staffs:password_reset_identify')

    try:
        staff = Staff.objects.get(pk=staff_pk)
    except Staff.DoesNotExist:
        return redirect('staffs:password_reset_identify')

    if request.method == 'POST':
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if not password or password != confirm_password:
            messages.error(request, 'Passwords do not match or are empty.')
            return render(request, 'staff/password_reset/p3.html', {'staff': staff})

        staff.set_password(password)
        staff.save()

        # Cleanup Session
        keys_to_delete = ['reset_staff_pk', 'staff_reset_verified', 'staff_reset_otp', 'staff_reset_otp_expiry']
        for key in keys_to_delete:
            if key in request.session:
                del request.session[key]
        
        messages.success(request, 'Your password has been reset successfully!')
        return redirect('staffs:stafflogin')
        
    return render(request, 'staff/password_reset/p3.html', {'staff': staff})


def generate_student(request):
    """
    Admin view to bulk generate student records with temporary passwords and export to CSV.
    """
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')
    
    if request.method == 'POST':
        action = request.POST.get('action', 'preview')
        
        try:
            # Logic to handle suffix-based generation
            
            if action == 'preview':
                start_roll = request.POST.get('start_roll')
                end_suffix = request.POST.get('end_suffix') # e.g. 110
                
                if not start_roll or not end_suffix:
                    messages.error(request, "Start Roll Number and End Suffix are required.")
                    return render(request, 'staff/generate_student.html')
                
                n = len(end_suffix)
                if n > len(start_roll):
                     messages.error(request, "End Suffix cannot be longer than Start Roll Number.")
                     return render(request, 'staff/generate_student.html')
                
                start_suffix_str = start_roll[-n:]
                if not start_suffix_str.isdigit() or not end_suffix.isdigit():
                     messages.error(request, "Roll number suffix must be numeric.")
                     return render(request, 'staff/generate_student.html')
    
                start_seq = int(start_suffix_str)
                end_seq = int(end_suffix)
                prefix = start_roll[:-n]
    
                if end_seq < start_seq:
                    messages.error(request, f"End Suffix ({end_seq}) cannot be less than the start sequence ({start_seq}).")
                    return render(request, 'staff/generate_student.html')
                
                count = end_seq - start_seq + 1
                if count > 500:
                     messages.error(request, f"Cannot generate {count} students at once (Limit: 500).")
                     return render(request, 'staff/generate_student.html')
                
                preview_list = []
                for seq in range(start_seq, end_seq + 1):
                     roll_str = f"{prefix}{str(seq).zfill(n)}"
                     # Check if exists
                     exists = Student.objects.filter(roll_number=roll_str).exists()
                     preview_list.append({'roll': roll_str, 'exists': exists})
                
                context = {
                    'show_preview': True,
                    'preview_list': preview_list,
                    'start_roll': start_roll,
                    'end_suffix': end_suffix,
                }
                return render(request, 'staff/generate_student.html', context)
            
            elif action == 'generate':
                selected_rolls = request.POST.getlist('selected_rolls')
                
                if not selected_rolls:
                    messages.error(request, "No students selected for generation.")
                    return redirect('staffs:generate_student')

                import csv
                import random
                from django.http import HttpResponse

                # Prepare CSV Response
                response = HttpResponse(content_type='text/csv')
                filename = f"generated_students_{len(selected_rolls)}_records.csv"
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                
                writer = csv.writer(response)
                writer.writerow(['Roll Number', 'Temp Password'])
                
                created_count = 0
                
                with transaction.atomic():
                    for roll_str in selected_rolls:
                        student, created = Student.objects.get_or_create(
                            roll_number=roll_str,
                            defaults={
                                'is_profile_complete': False,
                                'is_password_changed': False
                            }
                        )
                        
                        if created:
                            # New student: Generate and set password
                            temp_pass = "Pass" + str(random.randint(1000, 9999))
                            student.set_password(temp_pass)
                            student.save()
                            csv_pass_display = temp_pass
                            created_count += 1
                        else:
                            # Existing student: Do NOT change password
                            csv_pass_display = "Existing Password"
                            
                        # Format using formula to force string in Excel
                        writer.writerow([f'="{roll_str}"', csv_pass_display])
                
                # Set cookie to signal client that download has started
                response.set_cookie('download_complete', 'true', max_age=20)
                return response
            
            elif action == 'generate_single':
                single_roll = request.POST.get('single_roll').strip()
                
                if not single_roll:
                     messages.error(request, "Please enter a Roll Number.")
                     return redirect('staffs:generate_student')
                     
                import csv
                import random
                from django.http import HttpResponse
                
                # Prepare CSV Response (Single)
                response = HttpResponse(content_type='text/csv')
                filename = f"generated_student_{single_roll}.csv"
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                
                writer = csv.writer(response)
                writer.writerow(['Roll Number', 'Temp Password'])
                
                with transaction.atomic():
                    # Get or Create
                    student, created = Student.objects.get_or_create(
                         roll_number=single_roll,
                         defaults={
                                'is_profile_complete': False,
                                'is_password_changed': False
                         }
                    )
                    
                    # ALWAYS generate new password for Single Generation (Reset/Create)
                    temp_pass = "Pass" + str(random.randint(1000, 9999))
                    student.set_password(temp_pass)
                    student.save()
                    
                    # Write to CSV
                    writer.writerow([f'="{single_roll}"', temp_pass])
                
                # Set cookie
                response.set_cookie('download_complete', 'true', max_age=20)
                return response

            
            # Audit Log
            from .utils import log_audit
            log_audit(request, 'create', actor_type='staff', actor_id=request.session['staff_id'], 
                      object_type='StudentBatch', object_id=f"{start_roll}-{end_seq}", 
                      message=f'Bulk generated {created_count} students')

            return response
            
        except Exception as e:
            messages.error(request, f"Error generating students: {str(e)}")
            
    return render(request, 'staff/generate_student.html')

from django.contrib.auth.decorators import login_required
# @login_required(login_url='staffs:stafflogin')
@login_required(login_url='staffs:stafflogin')
def hod_manage_bonafide(request):
    """Specific view for HOD to approve/reject bonafide requests."""
    # Debug print removed for production cleanliness, but logic restored.
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')
    
    try:
        staff = Staff.objects.get(staff_id=request.session['staff_id'])
        # STRICT ROLE CHECK DISABLED to prevent lockout for non-exact 'HOD' roles
        # if staff.role.strip() != 'HOD':
        #     messages.error(request, "Access Denied.")
        #     return redirect('staffs:staff_dashboard')
    except Staff.DoesNotExist:
        return redirect('staffs:stafflogin')

    try:
        from students.models import BonafideRequest
        from django.shortcuts import get_object_or_404
        from django.http import HttpResponse

        if request.method == 'POST':
            action = request.POST.get('action')
            request_id = request.POST.get('request_id')
            rejection_reason = request.POST.get('rejection_reason', '')
            
            req = get_object_or_404(BonafideRequest, id=request_id)
            
            if action == 'approve':
                 if req.status == 'Pending HOD Approval':
                     req.status = 'Approved by HOD'
                     req.save()
                     messages.success(request, f"Approved request for {req.student.student_name}. Sent to Office.")
            elif action == 'reject':
                 req.status = 'Rejected'
                 req.rejection_reason = rejection_reason
                 req.save()
                 messages.warning(request, f"Rejected request for {req.student.student_name}.")
            
            return redirect('staffs:hod_manage_bonafide')

        # GET Logic
        # DEBUG: Verify imports
        try:
            pending_hod = BonafideRequest.objects.filter(status='Pending HOD Approval').order_by('-created_at')
            history = BonafideRequest.objects.filter(status__in=['Approved by HOD', 'Ready for Collection', 'Collected', 'Rejected']).order_by('-created_at')[:50]
        except Exception as db_err:
             return HttpResponse(f"<h1>DB Error in Bonafide View</h1><p>{str(db_err)}</p>")

        return render(request, 'staff/manage_bonafide_hod.html', {
            'staff': staff,
            'pending_hod': pending_hod,
            'history': history,
        })
    except Exception as e:
        import traceback
        return HttpResponse(f"<h1>Critical Error in HOD Bonafide View</h1><pre>{traceback.format_exc()}</pre>")

@login_required(login_url='staffs:stafflogin')
def office_manage_bonafide(request):
    """Specific view for Office Staff to process bonafide requests."""
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')
    
    try:
        staff = Staff.objects.get(staff_id=request.session['staff_id'])
        if staff.role.strip() != 'Office Staff':
            messages.error(request, "Access Denied: You are not authorized as Office Staff.")
            return redirect('staffs:staff_dashboard')
    except Staff.DoesNotExist:
        return redirect('staffs:stafflogin')

    from students.models import BonafideRequest
    from django.http import FileResponse
    from io import BytesIO
    from .utils import generate_bonafide_pdf, generate_bulk_bonafide_pdf
    from django.shortcuts import get_object_or_404

    if request.method == 'POST':
        action = request.POST.get('action')
        request_id = request.POST.get('request_id')
        
        if action == 'mark_ready':
             req = get_object_or_404(BonafideRequest, id=request_id)
             if req.status == 'Approved by HOD':
                 req.status = 'Ready for Collection'
                 req.save()
                 messages.success(request, f"Marked request for {req.student.student_name} as Ready for Collection.")
                 
        elif action == 'mark_collected':
             req = get_object_or_404(BonafideRequest, id=request_id)
             if req.status == 'Ready for Collection':
                 req.status = 'Collected'
                 req.save()
                 messages.success(request, f"Marked request for {req.student.student_name} as Collected.")
                 
        elif action == 'download_single':
             req = get_object_or_404(BonafideRequest, id=request_id)
             buffer = BytesIO()
             generate_bonafide_pdf(buffer, req)
             buffer.seek(0)
             return FileResponse(buffer, as_attachment=True, filename=f"bonafide_{req.student.roll_number}.pdf")
             
        elif action == 'download_bulk':
             request_ids = request.POST.getlist('request_ids')
             if request_ids:
                 reqs = BonafideRequest.objects.filter(id__in=request_ids)
                 buffer = BytesIO()
                 generate_bulk_bonafide_pdf(buffer, reqs)
                 buffer.seek(0)
                 return FileResponse(buffer, as_attachment=True, filename="bulk_bonafide_certificates.pdf")
        
        return redirect('staffs:office_manage_bonafide')

    # GET Logic
    approved_hod = BonafideRequest.objects.filter(status='Approved by HOD').order_by('-updated_at')
    ready_collection = BonafideRequest.objects.filter(status='Ready for Collection').order_by('-updated_at')
    history = BonafideRequest.objects.filter(status__in=['Collected', 'Rejected']).order_by('-updated_at')[:50]

    return render(request, 'staff/manage_bonafide_office.html', {
        'staff': staff,
        'approved_hod': approved_hod,
        'ready_collection': ready_collection,
        'history': history,
    })

# --- Student Remarks System ---

def remark_student_list(request):
    """Lists students for the class incharge to add/view remarks."""
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')
    
    staff = get_object_or_404(Staff, staff_id=request.session['staff_id'])
    
    # Security: Ensure only Class Incharge (or HOD/authorized roles) triggers this
    # For now, we assume Class Incharge logic as per request.
    if not staff.has_role('Class Incharge') and not staff.is_staff_admin:
         messages.error(request, "Access restricted to Class Incharges and Admins.")
         return redirect('staffs:staff_dashboard')

    students = Student.objects.none()
    
    if staff.has_role('Class Incharge') and staff.assigned_semester:
        students = Student.objects.filter(current_semester=staff.assigned_semester)
        if staff.assigned_batch in ['A', 'B']:
            students = students.filter(lab_batch=staff.assigned_batch)
        students = students.order_by('roll_number')
    elif staff.is_staff_admin:
        # HOD can see all? Or filter by sem? Let's show all for now or maybe a filter
        students = Student.objects.all().order_by('roll_number')

    return render(request, 'staff/remark_student_list.html', {'staff': staff, 'students': students})

def remark_history(request, roll_number):
    """View and add remarks for a specific student with violation types, incident details, and parent email notification."""
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')

    staff = get_object_or_404(Staff, staff_id=request.session['staff_id'])
    student = get_object_or_404(Student, roll_number=roll_number)
    
    from students.models import StudentRemark
    from staffs.utils import send_parent_notification_email

    if request.method == 'POST':
        remark_type = request.POST.get('remark_type')
        custom_violation_text = request.POST.get('custom_violation_text', '').strip()
        incident_date = request.POST.get('incident_date')
        description = request.POST.get('description', '').strip()
        evidence_document = request.FILES.get('evidence_document')
        apology_letter = request.FILES.get('apology_letter')
        send_email = request.POST.get('send_email') == 'on'
        
        # Validation
        if not remark_type:
            messages.error(request, 'Please select a violation type.')
        elif remark_type == 'OTHERS' and not custom_violation_text:
            messages.error(request, 'Please provide custom violation text for "Others".')
        elif not incident_date:
            messages.error(request, 'Please provide the incident date.')
        else:
            # Create the remark
            remark = StudentRemark.objects.create(
                student=student,
                staff=staff,
                remark_type=remark_type,
                custom_violation_text=custom_violation_text if remark_type == 'OTHERS' else None,
                incident_date=incident_date,
                description=description if description else None,
                evidence_document=evidence_document,
                apology_letter=apology_letter
            )
            
            # Send email notification if requested
            if send_email:
                violation_label = custom_violation_text if remark_type == 'OTHERS' else dict(StudentRemark.REMARK_TYPE_CHOICES)[remark_type]
                email_sent = send_parent_notification_email(student, [violation_label], staff.name)
                
                if email_sent:
                    from django.utils import timezone
                    remark.parent_notified = True
                    remark.notification_sent_at = timezone.now()
                    remark.save()
                    messages.success(request, 'Remark added and parent notified via email.')
                else:
                    messages.warning(request, 'Remark added, but email notification failed (parent email may be missing).')
            else:
                messages.success(request, 'Remark added successfully.')
            
            return redirect('staffs:remark_history', roll_number=roll_number)

    # Get all remarks for this student
    remarks = student.remarks.all().select_related('staff').order_by('-created_at')
    
    # Get violation type choices for the form
    violation_choices = StudentRemark.REMARK_TYPE_CHOICES

    return render(request, 'staff/remark_history.html', {
        'staff': staff,
        'student': student,
        'remarks': remarks,
        'violation_choices': violation_choices
    })

def attendance_deficit_list(request):
    """View to list students with < 70% attendance for Class Incharge."""
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')
        
    staff = get_object_or_404(Staff, staff_id=request.session['staff_id'])
    
    # Access Control: Class Incharge Only
    if not staff.has_role('Class Incharge') or not staff.assigned_semester:
        messages.error(request, "Access Restricted to Class Incharge.")
        return redirect('staffs:staff_dashboard')
        
    import datetime
    import calendar
    from .models import Subject, Timetable
    from students.models import StudentAttendance, Student
    
    # --- Month Selection ---
    today = datetime.date.today()
    month_offset = int(request.GET.get('month_offset', 0))
    
    # Calculate target month
    # Logic: Go back 'month_offset' months
    target_date = today
    for _ in range(month_offset):
        target_date = target_date.replace(day=1) - datetime.timedelta(days=1)
        
    target_month = target_date.month
    target_year = target_date.year
    month_name = calendar.month_name[target_month]
    
    # --- Logic ---
    # 1. Get Students in Assigned Semester
    students = Student.objects.filter(current_semester=staff.assigned_semester)
    if staff.assigned_batch in ['A', 'B']:
        students = students.filter(lab_batch=staff.assigned_batch)
    students = students.select_related('personalinfo')
    
    # 2. Get Subjects for this Semester
    subjects = Subject.objects.filter(semester=staff.assigned_semester)
    
    # 3. Calculate Attendance
    # We need: Total Working Days (Unique dates with ANY attendance for ANY subject in this sem)
    # AND Student Presence (Count of unique dates student was present)
    # NOTE: This approximates "days" rather than "periods". If strict period count needed, logic changes.
    # Assuming "Daily Attendance":
    
    # Get all dates where attendance was taken for this semester's subjects in this month
    working_dates_qs = StudentAttendance.objects.filter(
        subject__semester=staff.assigned_semester,
        date__year=target_year,
        date__month=target_month
    ).values_list('date', flat=True).distinct()
    
    working_days_count = working_dates_qs.count()
    
    deficit_students = []
    
    if working_days_count > 0:
        for student in students:
            # Count days present (distinct dates where status='Present' for any subject)
            # A student is "Present" for the day if they attended at least one class? 
            # OR better: Check percentage based on per-subject or aggregate?
            # Requirement: "monthly attendance deficit students below 70%" -> Usually global aggregate.
            
            # Let's use: (Total Periods Attended / Total Periods Conducted) * 100
            
            # Total Periods Conducted for this class (sum of all subject sessions)
            total_sessions = StudentAttendance.objects.filter(
                subject__semester=staff.assigned_semester,
                date__year=target_year,
                date__month=target_month,
                student=student # Filter by student to match exact records created for them
            ).count()
            
            # Total Present
            attended_sessions = StudentAttendance.objects.filter(
                subject__semester=staff.assigned_semester,
                date__year=target_year,
                date__month=target_month,
                student=student,
                status='Present'
            ).count()
            
            percentage = 0
            if total_sessions > 0:
                percentage = int((attended_sessions / total_sessions) * 100)
                
            if percentage < 70:
                parent_email = None
                if hasattr(student, 'personalinfo'):
                    parent_email = student.personalinfo.parent_email
                    
                deficit_students.append({
                    'roll': student.roll_number,
                    'name': student.student_name,
                    'present': attended_sessions,
                    'total': total_sessions,
                    'percentage': percentage,
                    'parent_email': parent_email
                })
    
    return render(request, 'staff/attendance_deficit_list.html', {
        'staff': staff,
        'deficit_students': deficit_students,
        'month_name': f"{month_name} {target_year}",
        'working_days': working_days_count, # Just for reference
        'month_offset': month_offset
    })

def send_deficit_email(request):
    """Action to send the deficit email."""
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')
        
    if request.method == 'POST':
        student_roll = request.POST.get('student_roll')
        month_offset = request.POST.get('month_offset')
        
        staff = get_object_or_404(Staff, staff_id=request.session['staff_id'])
        student = get_object_or_404(Student, roll_number=student_roll)
        
        # Re-calculate to get data for email (Hours based)
        import datetime
        import calendar
        from students.models import StudentAttendance
        from .models import MailLog
        
        today = datetime.date.today()
        offset = int(month_offset) if month_offset else 0
        target_date = today
        for _ in range(offset):
            target_date = target_date.replace(day=1) - datetime.timedelta(days=1)
            
        target_month = target_date.month
        target_year = target_date.year
        month_name = f"{calendar.month_name[target_month]} {target_year}"
        
        attendance_records = StudentAttendance.objects.filter(
            subject__semester=staff.assigned_semester,
            date__year=target_year,
            date__month=target_month,
            student=student
        ).select_related('subject')
        
        total_hours = 0
        attended_hours = 0
        for record in attendance_records:
            hours = 3 if record.subject.subject_type == 'Lab' else 1
            total_hours += hours
            if record.status == 'Present':
                attended_hours += hours
        
        percentage = 0
        if total_hours > 0:
            percentage = int((attended_hours / total_hours) * 100)
            
        # Send Email
        from .utils import send_attendance_deficit_email
        if send_attendance_deficit_email(student, month_name, percentage, total_hours, attended_hours, staff.name):
            # Log the email
            MailLog.objects.create(
                student=student,
                staff=staff,
                remark_type='Attendance Deficit',
                month=month_name,
                year=str(target_year)
            )
            messages.success(request, f"Alert sent to {student.student_name}'s parent.")
        else:
            messages.error(request, "Failed to send email. Check if parent email exists.")
            
        from django.urls import reverse
        return redirect(f"{reverse('staffs:attendance_deficit_list')}?month_offset={offset}")
        
    from django.urls import reverse
    return redirect('staffs:attendance_deficit_list')

# --- Notification Tool ---
from webpush import send_group_notification

def send_custom_notification(request):
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')
    
    try:
        staff = Staff.objects.get(staff_id=request.session['staff_id'])
    except Staff.DoesNotExist:
        return redirect('staffs:stafflogin')

    # Determine Base Template
    if staff.role == 'Class Incharge':
        base_template = 'staff/staffdash_class.html'
    elif staff.role == 'Course Incharge':
        base_template = 'staff/staffdash_course.html'
    elif staff.role == 'Scholarship Officer':
        base_template = 'staff/staffdash_scholarship.html'
    elif staff.role == 'Office Staff':
        base_template = 'staff/staffdash_office.html'
    else: # HOD
        base_template = 'staff/staffdash_hod.html'

    # Get student list (filtered by role)
    students = Student.objects.all().order_by('roll_number')
    if staff.has_role('Class Incharge') and staff.assigned_semester:
        students = students.filter(current_semester=staff.assigned_semester)
        if staff.assigned_batch in ['A', 'B']:
            students = students.filter(lab_batch=staff.assigned_batch)

    if request.method == 'POST':
        message = request.POST.get('message')
        
        if message:
             count = 0
             success_count = 0
             
             # Iterate and send to all
             for student in students:
                 group_name = f"student_{student.roll_number}"
                 payload = {
                     "head": "New Notification",
                     "body": message,
                     "icon": "/static/images/logo.png",
                     "url": request.build_absolute_uri('/students/dashboard/') 
                 }
                 try:
                     send_group_notification(group_name=group_name, payload=payload, ttl=1000)
                     success_count += 1
                 except Exception:
                     # Failures might happen if group doesn't exist (no subscription yet)
                     pass 
                 count += 1
            
             # If HOD or Office Staff, also send to ALL Staff
             if staff.role in ['HOD', 'Office Staff']:
                 all_staff = Staff.objects.all()
                 staff_count = 0
                 for s in all_staff:
                     # different payload url for staff?
                     from .utils import send_staff_notification
                     send_staff_notification(s, "New Notification", message, url="/staffs/")
                     staff_count += 1
                 # Add to success count purely for display (though existing count tracks students)
                 # We can just append to message
                 messages.success(request, f"Notification sent to {success_count} students and {staff_count} staff members.")
             else:
                 messages.success(request, f"Notification sent to {success_count} devices (out of {count} students).")
        else:
             messages.error(request, "Please enter a message.")
             
        return redirect('staffs:send_custom_notification')

    return render(request, 'staff/send_notification.html', {
        'students': students,
        'base_template': base_template, 
        'staff': staff
    })

def manage_scholar_attendance(request):
    staff_id = request.session.get('staff_id')
    if not staff_id:
        return redirect('stafflogin')
        
    staff = get_object_or_404(Staff, staff_id=staff_id)
    
    # Scholars assigned to this staff
    assigned_scholars = ResearchScholarProfile.objects.filter(supervisor=staff).values_list('student', flat=True)
    
    # Get attendance records
    pending_attendance = ScholarAttendance.objects.filter(scholar__in=assigned_scholars, status='Pending').order_by('-date', '-time_marked')
    history_attendance = ScholarAttendance.objects.filter(scholar__in=assigned_scholars).exclude(status='Pending').order_by('-date', '-time_marked')[:50]
    
    context = {
        'staff': staff,
        'pending_attendance': pending_attendance,
        'history_attendance': history_attendance
    }
    return render(request, 'staff/scholar_attendance.html', context)

def update_scholar_attendance(request, attendance_id):
    staff_id = request.session.get('staff_id')
    if not staff_id:
        return redirect('stafflogin')
        
    staff = get_object_or_404(Staff, staff_id=staff_id)
    attendance = get_object_or_404(ScholarAttendance, id=attendance_id)
    
    # Verify ownership
    if not getattr(attendance.scholar, 'scholar_profile', None) or attendance.scholar.scholar_profile.supervisor != staff:
        messages.error(request, "You are not authorized to update this attendance record.")
        return redirect('staffs:manage_scholar_attendance')
        
    action = request.POST.get('action')
    reason = request.POST.get('reason', '')
    
    if action == 'Approve':
        attendance.status = 'Approved'
        messages.success(request, f"Attendance approved for {attendance.scholar.student_name}.")
    elif action == 'Reject':
        attendance.status = 'Rejected'
        attendance.rejection_reason = reason
        messages.warning(request, f"Attendance rejected for {attendance.scholar.student_name}.")
        
    attendance.save()
    
    # Email notification to Scholar
    try:
        from django.core.mail import send_mail
        from django.conf import settings
        subject = f"Attendance {attendance.status} - {attendance.date}"
        message_body = f"Dear {attendance.scholar.student_name},\n\nYour attendance for {attendance.date.strftime('%d %B %Y')} has been {attendance.status} by your supervisor {staff.name}."
        if action == 'Reject' and reason:
            message_body += f"\n\nReason: {reason}"
        message_body += "\n\nThank you,\nAnnamalai University SSMSystem"
        
        if attendance.scholar.student_email:
            send_mail(subject, message_body, settings.DEFAULT_FROM_EMAIL, [attendance.scholar.student_email], fail_silently=True)
    except Exception as e:
        pass
        
    return redirect('staffs:manage_scholar_attendance')

def manage_scholar_leave(request):
    """Staff/Guide view to manage RS leave requests assigned to them."""
    staff_id = request.session.get('staff_id')
    if not staff_id:
        return redirect('staffs:stafflogin')

    staff = get_object_or_404(Staff, staff_id=staff_id)
    from students.models import LeaveRequest, ResearchScholarProfile

    # Scholars supervised by this staff member
    assigned_scholars = Student.objects.filter(
        scholar_profile__supervisor=staff,
        program_level='PHD'
    )

    pending_leaves = LeaveRequest.objects.filter(
        student__in=assigned_scholars,
        status='Pending Guide'
    ).order_by('created_at')

    history_leaves = LeaveRequest.objects.filter(
        student__in=assigned_scholars
    ).exclude(status='Pending Guide').order_by('-updated_at')[:50]

    return render(request, 'staff/scholar_leave_management.html', {
        'staff': staff,
        'pending_leaves': pending_leaves,
        'history_leaves': history_leaves,
    })


def update_scholar_leave_status(request, leave_id):
    """Approve or reject an RS leave request."""
    staff_id = request.session.get('staff_id')
    if not staff_id:
        return redirect('staffs:stafflogin')

    if request.method == 'POST':
        from students.models import LeaveRequest
        leave = get_object_or_404(LeaveRequest, id=leave_id)
        staff = get_object_or_404(Staff, staff_id=staff_id)

        # Security: only the assigned supervisor may act
        profile = getattr(leave.student, 'scholar_profile', None)
        if not profile or profile.supervisor != staff:
            messages.error(request, "You are not authorised to manage this leave request.")
            return redirect('staffs:manage_scholar_leave')

        action = request.POST.get('action')
        reason = request.POST.get('rejection_reason', '').strip()

        if action == 'approve':
            leave.status = 'Approved'
            messages.success(request, "Leave approved for " + leave.student.student_name + ".")
        elif action == 'reject':
            leave.status = 'Rejected'
            leave.rejection_reason = reason
            leave.rejected_by = staff.name + " (Guide)"
            messages.warning(request, "Leave rejected for " + leave.student.student_name + ".")

        leave.save()

        # Email scholar
        try:
            from django.core.mail import send_mail
            from django.conf import settings
            if leave.student.student_email:
                subj = "Leave Request " + leave.status + " - " + leave.start_date.strftime('%d %b %Y')
                body = (
                    "Dear " + leave.student.student_name + ",\n\n"
                    "Your leave request (" + leave.get_leave_type_display() + ") from "
                    + leave.start_date.strftime('%d %B %Y') + " to " + leave.end_date.strftime('%d %B %Y')
                    + " has been " + leave.status + " by your supervisor " + staff.name + "."
                )
                if action == 'reject' and reason:
                    body += "\n\nReason: " + reason
                body += "\n\nAnnamalai University SSMSystem"
                send_mail(subj, body, settings.DEFAULT_FROM_EMAIL, [leave.student.student_email], fail_silently=True)
        except Exception:
            pass

    return redirect('staffs:manage_scholar_leave')


def staff_view_scholar_profile(request, roll_number):
    """Displays complete details of a single research scholar for staff/HOD."""
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')

    student = get_object_or_404(Student, roll_number=roll_number, program_level='PHD')
    staff = get_object_or_404(Staff, staff_id=request.session['staff_id'])
    
    # helper to get object or None
    def get_or_none(model, **kwargs):
        try:
            return model.objects.get(**kwargs)
        except model.DoesNotExist:
            return None

    from students.models import (
        PersonalInfo, UGDetails, PGDetails, PhDDetails,
        RACMember, ZerothReview, RCWReview, PhDProgress
    )

    profile = get_or_none(ResearchScholarProfile, student=student)
    
    # Security: HOD / Admin sees all, others see only their assigned scholars
    if not staff.is_staff_admin and (not profile or profile.supervisor != staff):
        messages.error(request, "You are not authorised to view this scholar's profile.")
        return redirect('staffs:staff_dashboard')

    phd_progress, _ = PhDProgress.objects.get_or_create(scholar=student)

    context = {
        'student': student,
        'profile': profile,
        'personalinfo': get_or_none(PersonalInfo, student=student),
        'ug': get_or_none(UGDetails, student=student),
        'pg': get_or_none(PGDetails, student=student),
        'phd': get_or_none(PhDDetails, student=student),
        'rac_members': RACMember.objects.filter(scholar=student),
        'zeroth_review': get_or_none(ZerothReview, scholar=student),
        'rcw_reviews': RCWReview.objects.filter(scholar=student).order_by('-date', '-time'),
        'phd_progress': phd_progress,
        'phd_stats': phd_progress.progress_stats,
        'phd_deadline_info': phd_progress.current_deadline_info,
    }

    return render(request, 'staff/scholar_profile_detail.html', context)


def hod_portfolio_approvals(request):
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')
    staff = get_object_or_404(Staff, staff_id=request.session['staff_id'])
    if not staff.is_staff_admin:
        messages.error(request, "Access Denied: HOD / Admin only.")
        return redirect('staffs:staff_dashboard')
    
    from .models import StaffPastDesignation
    pending_designations = StaffPastDesignation.objects.filter(approval_status='Pending', is_additional=False).select_related('staff')
    pending_additional_posts = StaffPastDesignation.objects.filter(approval_status='Pending', is_additional=True).select_related('staff')
    
    return render(request, 'staff/hod_portfolio_approvals.html', {
        'staff': staff,
        'pending_quals': [],
        'pending_designations': pending_designations,
        'pending_additional_posts': pending_additional_posts,
        'pending_desigs': list(pending_designations) + list(pending_additional_posts),
    })

def approve_qualification(request, pk):
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')
    staff = get_object_or_404(Staff, staff_id=request.session['staff_id'])
    if not staff.is_staff_admin:
        messages.error(request, "Access Denied: HOD / Admin only.")
        return redirect('staffs:staff_dashboard')
    
    from .models import StaffQualification
    qual = get_object_or_404(StaffQualification, pk=pk)
    qual.approval_status = 'Approved'
    qual.save()
    messages.success(request, f"Approved qualification {qual.degree} for {qual.staff.name}.")
    return redirect('staffs:hod_portfolio_approvals')

def reject_qualification(request, pk):
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')
    staff = get_object_or_404(Staff, staff_id=request.session['staff_id'])
    if not staff.is_staff_admin:
        messages.error(request, "Access Denied: HOD / Admin only.")
        return redirect('staffs:staff_dashboard')
    
    from .models import StaffQualification
    qual = get_object_or_404(StaffQualification, pk=pk)
    qual.approval_status = 'Rejected'
    qual.save()
    messages.success(request, f"Rejected qualification {qual.degree} for {qual.staff.name}.")
    return redirect('staffs:hod_portfolio_approvals')

def approve_designation(request, pk):
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')
    staff = get_object_or_404(Staff, staff_id=request.session['staff_id'])
    if not staff.is_staff_admin:
        messages.error(request, "Access Denied: HOD / Admin only.")
        return redirect('staffs:staff_dashboard')
    
    from .models import StaffPastDesignation
    desig = get_object_or_404(StaffPastDesignation, pk=pk)
    desig.approval_status = 'Approved'
    desig.save()
    
    # Sync staff additional designation
    sync_staff_additional_designation(desig.staff)
    
    messages.success(request, f"Approved designation {desig.designation} for {desig.staff.name}.")
    return redirect('staffs:hod_portfolio_approvals')

def reject_designation(request, pk):
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')
    staff = get_object_or_404(Staff, staff_id=request.session['staff_id'])
    if not staff.is_staff_admin:
        messages.error(request, "Access Denied: HOD / Admin only.")
        return redirect('staffs:staff_dashboard')
    
    from .models import StaffPastDesignation
    desig = get_object_or_404(StaffPastDesignation, pk=pk)
    desig.approval_status = 'Rejected'
    desig.save()
    
    # Sync staff additional designation
    sync_staff_additional_designation(desig.staff)
    
    messages.success(request, f"Rejected designation {desig.designation} for {desig.staff.name}.")
    return redirect('staffs:hod_portfolio_approvals')


def hod_assign_post(request, staff_id):
    messages.error(request, "Direct additional post assignment from HOD dashboard is disabled. Staff must add their designation in their portfolio and upload verification documents for approval.")
    return redirect('staffs:staff_list')


def hod_manage_labs(request):
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')
    try:
        staff = Staff.objects.get(staff_id=request.session['staff_id'])
    except Staff.DoesNotExist:
        return redirect('staffs:stafflogin')
        
    if not staff.is_staff_admin:
        messages.error(request, "Access Denied: Only HOD or Admin can manage labs and classes.")
        return redirect('staffs:staff_dashboard')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create':
            name = request.POST.get('name', '').strip()
            short_name = request.POST.get('short_name', '').strip()
            staff_id = request.POST.get('staff_id', '').strip()
            from_date = request.POST.get('from_date', '').strip() or None
            to_date = request.POST.get('to_date', '').strip() or None
            
            if not name or not short_name:
                messages.error(request, "Lab Name and Lab Short Name are required.")
            else:
                try:
                    assigned_staff = None
                    if staff_id:
                        assigned_staff = Staff.objects.get(staff_id=staff_id)
                    
                    Lab.objects.create(
                        name=name, 
                        short_name=short_name, 
                        staff=assigned_staff,
                        from_date=from_date,
                        to_date=to_date
                    )
                    messages.success(request, f"Lab '{name}' created successfully.")
                    return redirect('staffs:hod_manage_labs')
                except Staff.DoesNotExist:
                    messages.error(request, "Selected staff member does not exist.")
                except Exception as e:
                    messages.error(request, f"Error creating lab: {str(e)}")
        
        elif action == 'edit':
            lab_id = request.POST.get('lab_id')
            name = request.POST.get('name', '').strip()
            short_name = request.POST.get('short_name', '').strip()
            staff_id = request.POST.get('staff_id', '').strip()
            from_date = request.POST.get('from_date', '').strip() or None
            to_date = request.POST.get('to_date', '').strip() or None
            
            try:
                lab = Lab.objects.get(id=lab_id)
                assigned_staff = None
                if staff_id:
                    assigned_staff = Staff.objects.get(staff_id=staff_id)
                
                lab.name = name
                lab.short_name = short_name
                lab.staff = assigned_staff
                lab.from_date = from_date
                lab.to_date = to_date
                lab.save()
                messages.success(request, f"Lab '{name}' updated successfully.")
                return redirect('staffs:hod_manage_labs')
            except Lab.DoesNotExist:
                messages.error(request, "Lab not found.")
            except Exception as e:
                messages.error(request, f"Error updating lab: {str(e)}")

        elif action == 'create_class':
            class_name = request.POST.get('class_name', '').strip()
            room_name = request.POST.get('room_name', '').strip()
            semester_raw = request.POST.get('semester', '').strip()
            from_date = request.POST.get('from_date', '').strip() or None
            to_date = request.POST.get('to_date', '').strip() or None

            semester = int(semester_raw) if semester_raw and semester_raw.isdigit() else None

            if not class_name or not room_name:
                messages.error(request, "Class Name and Class Room Name are required.")
            else:
                try:
                    ClassMapping.objects.create(
                        class_name=class_name,
                        room_name=room_name,
                        semester=semester,
                        from_date=from_date,
                        to_date=to_date
                    )
                    
                    messages.success(request, f"Class Mapping '{class_name}' ({room_name}) created successfully.")
                    return redirect('staffs:hod_manage_labs')
                except Exception as e:
                    messages.error(request, f"Error creating class mapping: {str(e)}")

        elif action == 'edit_class':
            class_id = request.POST.get('class_id')
            class_name = request.POST.get('class_name', '').strip()
            room_name = request.POST.get('room_name', '').strip()
            semester_raw = request.POST.get('semester', '').strip()
            from_date = request.POST.get('from_date', '').strip() or None
            to_date = request.POST.get('to_date', '').strip() or None

            semester = int(semester_raw) if semester_raw and semester_raw.isdigit() else None

            try:
                cm = ClassMapping.objects.get(id=class_id)

                cm.class_name = class_name
                cm.room_name = room_name
                cm.semester = semester
                cm.from_date = from_date
                cm.to_date = to_date
                cm.save()

                messages.success(request, f"Class Mapping '{class_name}' updated successfully.")
                return redirect('staffs:hod_manage_labs')
            except ClassMapping.DoesNotExist:
                messages.error(request, "Class mapping not found.")
            except Exception as e:
                messages.error(request, f"Error updating class mapping: {str(e)}")
                
    labs = Lab.objects.all().select_related('staff').order_by('name')
    class_mappings = ClassMapping.objects.all().order_by('semester', 'class_name')
    all_staff = Staff.objects.filter(is_active=True).order_by('name')
    
    return render(request, 'staff/manage_labs.html', {
        'staff': staff,
        'labs': labs,
        'class_mappings': class_mappings,
        'all_staff': all_staff
    })


def hod_delete_lab(request, lab_id):
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')
    try:
        staff = Staff.objects.get(staff_id=request.session['staff_id'])
    except Staff.DoesNotExist:
        return redirect('staffs:stafflogin')
        
    if not staff.is_staff_admin:
        messages.error(request, "Access Denied: Only HOD or Admin can delete labs.")
        return redirect('staffs:staff_dashboard')
        
    try:
        lab = Lab.objects.get(id=lab_id)
        name = lab.name
        lab.delete()
        messages.success(request, f"Lab '{name}' deleted successfully.")
    except Lab.DoesNotExist:
        messages.error(request, "Lab not found.")
    except Exception as e:
        messages.error(request, f"Error deleting lab: {str(e)}")
        
    return redirect('staffs:hod_manage_labs')


def hod_delete_class_mapping(request, class_id):
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')
    try:
        staff = Staff.objects.get(staff_id=request.session['staff_id'])
    except Staff.DoesNotExist:
        return redirect('staffs:stafflogin')
        
    if not staff.is_staff_admin:
        messages.error(request, "Access Denied: Only HOD or Admin can delete class mappings.")
        return redirect('staffs:staff_dashboard')
        
    try:
        cm = ClassMapping.objects.get(id=class_id)
        name = cm.class_name
        cm.delete()
        messages.success(request, f"Class mapping '{name}' deleted successfully.")
    except ClassMapping.DoesNotExist:
        messages.error(request, "Class mapping not found.")
    except Exception as e:
        messages.error(request, f"Error deleting class mapping: {str(e)}")
        
    return redirect('staffs:hod_manage_labs')



def manage_phd_stages(request):
    """View to search, filter by stages, view details, and upload documents for Ph.D. scholars."""
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')
        
    staff = get_object_or_404(Staff, staff_id=request.session['staff_id'])
    
    from students.models import Student, PhDProgress, ResearchScholarProfile
    from django.db.models import Q
    
    # Scholars matching query and supervisor status
    if staff.is_staff_admin:
        students_qs = Student.objects.filter(program_level='PHD').select_related('scholar_profile', 'phd_progress')
    else:
        students_qs = Student.objects.filter(scholar_profile__supervisor=staff, program_level='PHD').select_related('scholar_profile', 'phd_progress')

    # Apply search filter
    q = request.GET.get('q', '').strip()
    if q:
        students_qs = students_qs.filter(
            Q(student_name__icontains=q) | Q(roll_number__icontains=q)
        )
        
    # Get dynamic counts per stage (before stage filter is applied)
    stage_counts = {}
    stage_choices = PhDProgress.CURRENT_STAGE_CHOICES
    for choice, name in stage_choices:
        # We need to compute counts using the supervisor/HOD restricted set
        count_qs = Student.objects.filter(program_level='PHD')
        if not staff.is_staff_admin:
            count_qs = count_qs.filter(scholar_profile__supervisor=staff)
        if q:
            count_qs = count_qs.filter(
                Q(student_name__icontains=q) | Q(roll_number__icontains=q)
            )
        # We check count of students in this stage (handling default 'RAC_REVIEW' when no progress record exists yet)
        if choice == 'RAC_REVIEW':
            stage_counts[choice] = count_qs.filter(
                Q(phd_progress__current_stage=choice) | Q(phd_progress__isnull=True)
            ).count()
        else:
            stage_counts[choice] = count_qs.filter(phd_progress__current_stage=choice).count()

    # Apply stage filter
    stage_filter = request.GET.get('stage', '').strip()
    if stage_filter:
        if stage_filter == 'RAC_REVIEW':
            students_qs = students_qs.filter(
                Q(phd_progress__current_stage=stage_filter) | Q(phd_progress__isnull=True)
            )
        else:
            students_qs = students_qs.filter(phd_progress__current_stage=stage_filter)

    # Process selected student
    selected_student = None
    selected_roll = request.GET.get('student_roll', '').strip()
    if selected_roll:
        selected_student = students_qs.filter(roll_number=selected_roll).first()
    if not selected_student and students_qs.exists():
        selected_student = students_qs.first()

    phd_progress = None
    if selected_student:
        phd_progress, _ = PhDProgress.objects.get_or_create(scholar=selected_student)
        
        # Handle staff uploads / actions
        if request.method == 'POST':
            # Check current stage
            stage = phd_progress.current_stage
            
            if stage == 'SYNOPSIS':
                if request.FILES.get('synopsis_panel_of_examiner'):
                    phd_progress.synopsis_panel_of_examiner = request.FILES.get('synopsis_panel_of_examiner')
                if request.FILES.get('synopsis_foreign_examiner'):
                    phd_progress.synopsis_foreign_examiner = request.FILES.get('synopsis_foreign_examiner')
                if request.FILES.get('synopsis_indian_examiner'):
                    phd_progress.synopsis_indian_examiner = request.FILES.get('synopsis_indian_examiner')
                    
            elif stage == 'THESIS_HARDBOUND':
                if request.FILES.get('hardbound_examiner_report'):
                    phd_progress.hardbound_examiner_report = request.FILES.get('hardbound_examiner_report')
                    
            elif stage == 'VIVA_VOCE':
                viva_date = request.POST.get('viva_date')
                viva_time = request.POST.get('viva_time')
                if viva_date:
                    phd_progress.viva_date = viva_date
                if viva_time:
                    phd_progress.viva_time = viva_time
                    
                if request.FILES.get('viva_fixation'):
                    phd_progress.viva_fixation = request.FILES.get('viva_fixation')
                if request.FILES.get('viva_student_order'):
                    phd_progress.viva_student_order = request.FILES.get('viva_student_order')
                if request.FILES.get('viva_internal_order'):
                    phd_progress.viva_internal_order = request.FILES.get('viva_internal_order')
                if request.FILES.get('viva_external_order'):
                    phd_progress.viva_external_order = request.FILES.get('viva_external_order')
                    
            elif stage == 'MEMO':
                if request.FILES.get('memo_copy'):
                    phd_progress.memo_copy = request.FILES.get('memo_copy')
                    
            elif stage == 'PROVISIONAL':
                if request.FILES.get('provisional_doc'):
                    phd_progress.provisional_doc = request.FILES.get('provisional_doc')
                    
            elif stage == 'DEGREE':
                if request.FILES.get('degree_doc'):
                    phd_progress.degree_doc = request.FILES.get('degree_doc')
                    
            phd_progress.save()
            phd_progress.check_and_advance_stage()
            messages.success(request, f"Details for {selected_student.student_name} updated successfully.")
            return redirect(f"{request.path}?student_roll={selected_student.roll_number}&stage={stage_filter}&q={q}")

    # Build student metadata list for display
    students_display = []
    for s in students_qs:
        prog, _ = PhDProgress.objects.get_or_create(scholar=s)
        stats = prog.progress_stats
        dl_info = prog.current_deadline_info
        students_display.append({
            'student': s,
            'progress': prog,
            'stats': stats,
            'dl_info': dl_info,
        })

    # If a student is selected, build their stats and details
    selected_stats = phd_progress.progress_stats if phd_progress else None
    selected_dl_info = phd_progress.current_deadline_info if phd_progress else None

    # Load all RCW reviews for selected scholar if any
    selected_rcw_reviews = None
    if selected_student:
        selected_rcw_reviews = selected_student.rcw_reviews.all().order_by('-date', '-time')

    # Staff list for guide assignment (HOD only)
    guide_staff_list = Staff.objects.filter(is_active=True).order_by('name') if staff.is_staff_admin else []
    rs_count = Student.objects.filter(program_level='PHD').count() if staff.is_staff_admin else students_qs.count()

    context = {
        'staff': staff,
        'students': students_display,
        'selected_student': selected_student,
        'phd_progress': phd_progress,
        'phd_stats': selected_stats,
        'phd_deadline_info': selected_dl_info,
        'rcw_reviews': selected_rcw_reviews,
        'stage_choices': stage_choices,
        'stage_counts': stage_counts,
        'q': q,
        'stage_filter': stage_filter,
        'guide_staff_list': guide_staff_list,
        'rs_count': rs_count,
    }
    
    return render(request, 'staff/manage_phd_stages.html', context)


def assign_phd_guide(request):
    """HOD-only: Assign or change the guide (supervisor) for a PhD scholar."""
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')
    hod = get_object_or_404(Staff, staff_id=request.session['staff_id'])
    if not hod.is_staff_admin:
        messages.error(request, 'Only HOD or Admin can assign guides.')
        return redirect('staffs:manage_phd_stages')
    if request.method != 'POST':
        return redirect('staffs:manage_phd_stages')

    from students.models import Student, ResearchScholarProfile
    import datetime

    roll = request.POST.get('roll_number', '').strip()
    guide_id = request.POST.get('guide_staff_id', '').strip()
    redirect_back = request.POST.get('redirect_url', '').strip()

    student = get_object_or_404(Student, roll_number=roll, program_level='PHD')

    # Get or create a minimal profile if scholar hasn't completed registration yet
    profile, _ = ResearchScholarProfile.objects.get_or_create(
        student=student,
        defaults={
            'scholar_type': 'Full Time',
            'admission_date': datetime.date.today(),
            'supervisor': None,
        }
    )

    if guide_id:
        new_guide = get_object_or_404(Staff, staff_id=guide_id)
        old_guide_name = profile.supervisor.name if profile.supervisor else 'None'
        profile.supervisor = new_guide
        profile.save()
        messages.success(request, f'Guide for {student.student_name} changed from {old_guide_name} to {new_guide.name}.')
    else:
        profile.supervisor = None
        profile.save()
        messages.success(request, f'Guide removed for {student.student_name}.')

    if redirect_back:
        return redirect(redirect_back)
    from django.urls import reverse
    return redirect(reverse('staffs:manage_phd_stages') + f'?student_roll={roll}')


def manage_department_tasks(request):
    """View to assign Department Tasks & Roles to staff members with checkboxes."""
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')

    staff = Staff.objects.filter(staff_id=request.session['staff_id']).first()
    if not staff or (staff.role != 'HOD' and not staff.is_admin):
        messages.error(request, "Access Denied: Only HOD or Admin can manage department tasks and roles.")
        return redirect('staffs:staff_dashboard')

    from .models import DepartmentTask
    from django.db import transaction

    # Ensure default tasks exist
    DepartmentTask.seed_default_tasks()

    if request.method == 'POST':
        tasks = DepartmentTask.objects.all().prefetch_related('assigned_staff')
        with transaction.atomic():
            for task in tasks:
                selected_staff_ids = request.POST.getlist(f'task_{task.id}')
                task.assigned_staff.set(Staff.objects.filter(staff_id__in=selected_staff_ids))
        messages.success(request, "Department Tasks & Roles allocations updated successfully!")
        return redirect('staffs:manage_department_tasks')

    tasks = DepartmentTask.objects.all().prefetch_related('assigned_staff').order_by('task_number')
    staff_members = Staff.objects.filter(is_active=True).order_by('name')

    categories = sorted(list(set(t.category for t in tasks if t.category)))

    context = {
        'staff': staff,
        'tasks': tasks,
        'staff_members': staff_members,
        'categories': categories,
    }
    return render(request, 'staff/department_tasks.html', context)


def export_staff_tasks_csv(request):
    """Generates downloadable CSV report of staff members with assigned department tasks/roles."""
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')

    staff = Staff.objects.filter(staff_id=request.session['staff_id']).first()
    if not staff or (staff.role != 'HOD' and not staff.is_admin):
        messages.error(request, "Access Denied.")
        return redirect('staffs:staff_dashboard')

    import csv
    from django.http import HttpResponse
    from .models import DepartmentTask

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="staff_department_roles_report.csv"'
    response.write('\ufeff')

    writer = csv.writer(response)
    writer.writerow([
        'Staff ID', 'Salutation', 'Name', 'Designation', 'Department',
        'Email', 'Mobile', 'Primary Role', 'Total Assigned Tasks', 'Assigned Additional Tasks / Roles'
    ])

    staff_qs = Staff.objects.filter(is_active=True).prefetch_related('assigned_department_tasks').order_by('name')
    for member in staff_qs:
        tasks = [f"{t.task_number}. {t.name}" for t in member.assigned_department_tasks.all()]
        writer.writerow([
            member.staff_id,
            member.salutation or '',
            member.name,
            member.designation or '',
            member.department or '',
            member.email or '',
            member.mobile_number or '',
            member.role,
            len(tasks),
            "; ".join(tasks) if tasks else "No additional tasks assigned"
        ])

    return response


def export_task_matrix_csv(request):
    """Generates downloadable CSV matrix (Staff vs 58 Department Tasks)."""
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')

    staff = Staff.objects.filter(staff_id=request.session['staff_id']).first()
    if not staff or (staff.role != 'HOD' and not staff.is_admin):
        messages.error(request, "Access Denied.")
        return redirect('staffs:staff_dashboard')

    import csv
    from django.http import HttpResponse
    from .models import DepartmentTask

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="department_task_allocation_matrix.csv"'
    response.write('\ufeff')

    writer = csv.writer(response)
    all_tasks = DepartmentTask.objects.all().order_by('task_number')

    header = ['Staff ID', 'Staff Name', 'Designation', 'Primary Role'] + [f"[{t.task_number}] {t.name}" for t in all_tasks]
    writer.writerow(header)

    staff_qs = Staff.objects.filter(is_active=True).prefetch_related('assigned_department_tasks').order_by('name')
    for member in staff_qs:
        assigned_ids = set(member.assigned_department_tasks.values_list('id', flat=True))
        row = [
            member.staff_id,
            member.name,
            member.designation or '',
            member.role
        ]
        for task in all_tasks:
            row.append("YES" if task.id in assigned_ids else "NO")
        writer.writerow(row)

    return response


def office_manage_document_requests(request):
    """
    Office Staff view to manage student original document / marksheet requests (X, XII, TC, etc.).
    Workflow: Pending -> Ready for Collection -> Collected (Not Returned) -> Returned.
    """
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')

    staff = get_object_or_404(Staff, staff_id=request.session['staff_id'])

    # Allow Office Staff, HOD, and Admin
    if staff.role not in ['Office Staff', 'HOD'] and not staff.is_admin:
        messages.error(request, "Access Denied: You are not authorized as Office Staff.")
        return redirect('staffs:staff_dashboard')

    from students.models import DocumentRequest
    from django.utils import timezone

    if request.method == 'POST':
        action = request.POST.get('action')
        req_id = request.POST.get('request_id')
        doc_req = get_object_or_404(DocumentRequest, id=req_id)

        if action == 'ready':
            doc_req.status = 'Ready for Collection'
            doc_req.ready_at = timezone.now()
            remarks = request.POST.get('office_remarks', '').strip()
            if remarks:
                doc_req.office_remarks = remarks
            doc_req.save()

            messages.success(
                request,
                f"Document request for {doc_req.student.student_name} ({doc_req.document_type}) marked as Ready for Collection."
            )

            # Send Email Notification to Student
            if doc_req.student.student_email:
                try:
                    from django.core.mail import send_mail
                    from django.conf import settings

                    subject = f"SSMS Notice: Your Original {doc_req.document_type} is Ready for Collection"
                    message = (
                        f"Dear {doc_req.student.student_name},\n\n"
                        f"Your request to borrow original document ({doc_req.document_type}) has been approved and is READY FOR COLLECTION at the Department Office.\n\n"
                        f"Request Details:\n"
                        f"- Student Roll No: {doc_req.student.roll_number}\n"
                        f"- Document: {doc_req.document_type}\n"
                        f"- Reason: {doc_req.reason}\n\n"
                        f"Important Note: This is a borrowed original document. Once collected, you are required to return it to the office after your work is completed.\n\n"
                        f"Regards,\nDepartment Office Staff\nSSMS System"
                    )
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [doc_req.student.student_email],
                        fail_silently=True
                    )
                except Exception as e:
                    print(f"Failed to send email notification to student: {e}")

        elif action == 'collected':
            # Mark as Collected -> Automatically set status to 'Collected (Not Returned)'
            doc_req.status = 'Collected (Not Returned)'
            doc_req.collected_at = timezone.now()
            remarks = request.POST.get('office_remarks', '').strip()
            if remarks:
                doc_req.office_remarks = remarks
            doc_req.save()

            messages.info(
                request,
                f"Document marked as Collected by {doc_req.student.student_name}. Status changed to 'Collected (Not Returned)'."
            )

        elif action == 'returned':
            # Student returns physical document
            doc_req.status = 'Returned'
            doc_req.returned_at = timezone.now()
            remarks = request.POST.get('office_remarks', '').strip()
            if remarks:
                doc_req.office_remarks = remarks
            doc_req.save()

            messages.success(
                request,
                f"Original {doc_req.document_type} successfully returned by {doc_req.student.student_name}. Workflow completed!"
            )

        elif action == 'reject':
            rejection_reason = request.POST.get('rejection_reason', '').strip()
            doc_req.status = 'Rejected'
            doc_req.rejection_reason = rejection_reason or 'Request rejected by Department Office.'
            doc_req.save()

            messages.warning(
                request,
                f"Document request for {doc_req.student.student_name} ({doc_req.document_type}) was rejected."
            )

            if doc_req.student.student_email:
                try:
                    from django.core.mail import send_mail
                    from django.conf import settings

                    subject = f"SSMS Notice: Document Request Update ({doc_req.document_type})"
                    message = (
                        f"Dear {doc_req.student.student_name},\n\n"
                        f"Your request to borrow {doc_req.document_type} could not be approved.\n\n"
                        f"Reason for rejection: {doc_req.rejection_reason}\n\n"
                        f"Please contact the Department Office for further queries.\n\n"
                        f"Regards,\nDepartment Office Staff"
                    )
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [doc_req.student.student_email],
                        fail_silently=True
                    )
                except Exception as e:
                    print(f"Failed to send rejection email: {e}")

        return redirect('staffs:office_manage_document_requests')

    all_requests = DocumentRequest.objects.select_related('student').order_by('-updated_at')

    pending_list = all_requests.filter(status='Pending')
    ready_list = all_requests.filter(status='Ready for Collection')
    borrowed_list = all_requests.filter(status='Collected (Not Returned)')
    completed_list = all_requests.filter(status__in=['Returned', 'Rejected'])

    context = {
        'staff': staff,
        'all_requests': all_requests,
        'pending_list': pending_list,
        'ready_list': ready_list,
        'borrowed_list': borrowed_list,
        'completed_list': completed_list,
        'pending_count': pending_list.count(),
        'ready_count': ready_list.count(),
        'borrowed_count': borrowed_list.count(),
    }
    return render(request, 'staff/office_document_requests.html', context)


def update_staff_roles(request, staff_id):
    """Allows HOD or Admin to dynamically update assigned roles for any staff member at any time."""
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')

    current_staff = Staff.objects.filter(staff_id=request.session['staff_id']).first()
    if not current_staff or (current_staff.role != 'HOD' and not current_staff.is_admin):
        messages.error(request, "Access Denied: Only HOD or Admin can manage staff roles.")
        return redirect('staffs:staff_list')

    target_staff = get_object_or_404(Staff, staff_id=staff_id)

    if request.method == 'POST':
        roles_list = request.POST.getlist('staff_roles')
        if not roles_list:
            messages.error(request, "Please select at least one role for the staff member.")
            return redirect(request.META.get('HTTP_REFERER', 'staffs:staff_list'))

        OFFICE_DUTIES = {'Office Staff', 'Bonafide Issuing', 'Marksheet & Document Requests', 'Scholarship Management'}
        has_office_duty = any(r in OFFICE_DUTIES for r in roles_list)

        if has_office_duty:
            primary_role = 'Office Staff'
            sec_roles = [r for r in roles_list if r != 'Office Staff']
            secondary_roles_str = ", ".join(sec_roles)
        else:
            primary_role = roles_list[0]
            secondary_roles_str = ", ".join(roles_list[1:]) if len(roles_list) > 1 else ""

        roles_set = set(roles_list)

        target_staff.role = primary_role
        target_staff.secondary_roles = secondary_roles_str
        target_staff.is_scholarship_officer = ('Scholarship Officer' in roles_set or 'Scholarship Management' in roles_set)
        target_staff.is_timetable_incharge = ('Timetable Incharge' in roles_set)
        if 'HOD' in roles_set:
            target_staff.is_admin = True

        if 'Class Incharge' in roles_set:
            assigned_sem = request.POST.get('assigned_semester')
            assigned_b = request.POST.get('assigned_batch', 'All')
            target_staff.assigned_semester = int(assigned_sem) if (assigned_sem and assigned_sem.isdigit()) else None
            target_staff.assigned_batch = assigned_b if assigned_b in ['All', 'A', 'B'] else 'All'
        else:
            target_staff.assigned_semester = None
            target_staff.assigned_batch = 'All'

        from django.core.exceptions import ValidationError
        try:
            target_staff.full_clean()
            target_staff.save()
            messages.success(request, f"Roles updated successfully for {target_staff.salutation} {target_staff.name}!")
        except ValidationError as e:
            msg_str = ""
            if hasattr(e, 'message_dict'):
                msg_str = "; ".join([f"{k}: {', '.join(v)}" for k, v in e.message_dict.items()])
            elif hasattr(e, 'messages'):
                msg_str = "; ".join(e.messages)
            else:
                msg_str = str(e)
            messages.error(request, f"Cannot update roles: {msg_str}")

        return redirect(request.META.get('HTTP_REFERER', 'staffs:staff_list'))

    return redirect('staffs:staff_list')


