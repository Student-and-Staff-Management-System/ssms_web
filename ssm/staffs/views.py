from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone

from .models import Staff, ExamSchedule, Timetable, StaffPublication, StaffAwardHonour, StaffSeminar, StaffStudentGuided, AuditLog
from students.models import Student
from django.db.models import Q, Case, When
from django.db import transaction

def stafflogin(request):
    """Handles staff login."""
    if 'staff_id' in request.session:
        return redirect('staffs:staff_dashboard')

    if request.method == 'POST':
        staff_id = request.POST.get('staff_id')
        password = request.POST.get('password')
        try:
            staff = Staff.objects.get(staff_id=staff_id)
            if staff.check_password(password):
                request.session['staff_id'] = staff.staff_id
                from .utils import log_audit
                log_audit(request, 'login', actor_type='staff', actor_id=staff.staff_id, actor_name=staff.name, message='Staff logged in')
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
    
    
    if staff.role == 'Class Incharge':
        template_name = 'staff/staffdash_class.html'
        # Filter students relevant to this class incharge
        if staff.assigned_semester:
            student_count = Student.objects.filter(current_semester=staff.assigned_semester).count()
        else:
            student_count = 0 
            
    elif staff.role == 'Course Incharge':
        template_name = 'staff/staffdash_course.html'
    elif staff.role == 'Scholarship Officer':
        template_name = 'staff/staffdash_scholarship.html'
    else:
        template_name = 'staff/staffdash_hod.html'
        
    # Fetch assigned subjects for this staff member
    assigned_subjects = staff.subjects.all().order_by('semester', 'code')
        
    # Calculate pending leaves for notification badge
    from students.models import LeaveRequest, BonafideRequest, ScholarshipInfo
    from staffs.models import StaffLeaveRequest, News
    pending_leaves_count = 0
    pending_staff_leaves_count = 0
    pending_bonafide_count = 0
    
    # Fetch News
    # Fetch News
    today = timezone.now().date()
    news_list = News.objects.filter(
        Q(is_active=True) & 
        Q(target__in=['All', 'Staff', 'Student']) &
        (Q(start_date__isnull=True) | Q(start_date__lte=today)) & 
        (Q(end_date__isnull=True) | Q(end_date__gte=today))
    ).order_by('-date', '-id')
    
    if staff.role == 'HOD':
        pending_leaves_count = LeaveRequest.objects.filter(status='Pending HOD').count()
        pending_staff_leaves_count = StaffLeaveRequest.objects.filter(status='Pending').count()
        pending_bonafide_count = BonafideRequest.objects.filter(status='Pending HOD').count()
    elif staff.role == 'Class Incharge' and staff.assigned_semester:
        pending_leaves_count = LeaveRequest.objects.filter(
            status='Pending Class Incharge',
            student__current_semester=staff.assigned_semester
        ).count()

    # Scholarship Officer Specific Logic
    scholarship_students = []
    selected_scholarship = request.GET.get('scholarship_type')
    
    if staff.role == 'Scholarship Officer':
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

    return render(request, template_name, {
        'staff': staff, 
        'student_count': student_count,
        'subjects': assigned_subjects,
        'assigned_subjects': assigned_subjects, # For HOD dashboard compatibility
        'pending_leaves_count': pending_leaves_count,
        'pending_staff_leaves_count': pending_staff_leaves_count,
        'pending_bonafide_count': pending_bonafide_count,
        'pending_bonafide_count': pending_bonafide_count,
        'news_list': news_list,
        'scholarship_students': scholarship_students,
        'selected_scholarship': selected_scholarship
    })

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
    if request.method == 'POST':
        form = StaffRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            new_staff = form.save()
            from .utils import log_audit
            log_audit(request, 'create', actor_type='system', actor_name='System', object_type='Staff', object_id=new_staff.staff_id, message=f'New staff registered: {new_staff.name}')
            messages.success(request, f"Staff member {new_staff.name} has been registered successfully.")
            return redirect('staffs:stafflogin')
        else:
            # Pass form errors to messages so they appear in the UI
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.title()}: {error}")
            # Render the form again with the entered data (optional, but good UX)
            return render(request, 'staff/staffreg.html', {'form': form})

    return render(request, 'staff/staffreg.html')


def student_list(request):
    """Displays a list of students with search functionality for staff."""
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')

    query = request.GET.get('q')
    semester = request.GET.get('semester')
    
    
    students = Student.objects.all().select_related('studentdocuments')

    # Restrict view for Class Incharge
    try:
        current_staff = Staff.objects.get(staff_id=request.session['staff_id'])
        if current_staff.role == 'Class Incharge' and current_staff.assigned_semester:
            students = students.filter(current_semester=current_staff.assigned_semester)
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

    return render(request, 'studlist.html', {
        'students': students,
        'query': query,
        'selected_semester': semester
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
    try:
        current_staff = Staff.objects.get(staff_id=request.session['staff_id'])
        if current_staff.role == 'Class Incharge' and current_staff.assigned_semester:
            selected_semester = str(current_staff.assigned_semester)
            display_semester_selector = False
            header_text = f"Managing Semester {selected_semester} (Assigned)"
    except Staff.DoesNotExist:
        pass

    if selected_semester:
        students = Student.objects.filter(current_semester=selected_semester)
    
    return render(request, 'staff/manage_semesters.html', {
        'students': students, 
        'selected_semester': selected_semester,
        'display_semester_selector': display_semester_selector,
        'header_text': header_text
    })

def manage_subjects(request):
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')
    
    # Check if HOD
    try:
        current_staff = Staff.objects.get(staff_id=request.session['staff_id'])
        if current_staff.role != 'HOD':
             messages.error(request, "Access Denied: Only HOD can manage courses.")
             return redirect('staffs:staff_dashboard')
    except Staff.DoesNotExist:
         return redirect('staffs:stafflogin')

    from .models import Subject # Import locally to avoid circularity if any

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add_subject':
            name = request.POST.get('name')
            code = request.POST.get('code')
            semester = request.POST.get('semester')
            subject_type = request.POST.get('type', 'Theory')
            
            if name and code and semester:
                Subject.objects.create(name=name, code=code, semester=semester, subject_type=subject_type)
                messages.success(request, f"{subject_type} '{name}' added successfully.")
            else:
                 messages.error(request, "All fields are required to add a subject.")
                 
        elif action == 'assign_staff':
            subject_id = request.POST.get('subject_id')
            staff_id = request.POST.get('staff_id')
            
            if subject_id:
                subject = get_object_or_404(Subject, id=subject_id)
                if staff_id:
                     staff_member = get_object_or_404(Staff, staff_id=staff_id)
                     
                     # Check if staff is already assigned to a subject in this semester
                     existing_assignment = Subject.objects.filter(staff=staff_member, semester=subject.semester).exclude(id=subject.id)
                     
                     if existing_assignment.exists():
                         messages.error(request, f"{staff_member.name} is already assigned to a subject in Semester {subject.semester} ({existing_assignment.first().name}). Cannot assign more than 1 subject per semester.")
                     else:
                         subject.staff = staff_member
                         subject.save()
                         messages.success(request, f"Assigned {staff_member.name} to {subject.name}.")
                else:
                    subject.staff = None
                    subject.save()
                    messages.success(request, f"Unassigned staff from {subject.name}.")

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
        'current_staff': current_staff
    })

def manage_marks(request, subject_id):
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')

    from .models import Subject

    subject = get_object_or_404(Subject, id=subject_id)
    current_staff = get_object_or_404(Staff, staff_id=request.session['staff_id'])

    # Access Control: HOD or Assigned Staff
    if current_staff.role != 'HOD' and subject.staff != current_staff:
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
    if current_staff.role == 'HOD' and subject.staff != current_staff:
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

    # Access Control
    if current_staff.role != 'HOD' and subject.staff != current_staff:
        messages.error(request, "Access Denied: You are not assigned to this subject.")
        return redirect('staffs:staff_dashboard')

    # --- Date Handling (Current Selected Date) ---
    date_str = request.GET.get('date')
    if date_str:
        try:
            date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
             date_obj = datetime.date.today()
    else:
        date_obj = datetime.date.today()
    
    formatted_date = date_obj.strftime('%Y-%m-%d')
    students = Student.objects.filter(current_semester=subject.semester).order_by('roll_number')

    # Determine if read-only
    is_readonly = False
    if current_staff.role == 'HOD' and subject.staff != current_staff:
        is_readonly = True

    # --- POST Handler (Saving Attendance) ---
    if request.method == 'POST':
        if is_readonly:
             messages.error(request, "Read-only access: Cannot save attendance.")
             return redirect(request.path + f"?date={formatted_date}")

        post_date_str = request.POST.get('attendance_date')
        if post_date_str:
             try:
                save_date = datetime.datetime.strptime(post_date_str, '%Y-%m-%d').date()
             except ValueError:
                save_date = date_obj
        else:
            save_date = date_obj

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
        for student in students:
            status = request.POST.get(f'status_{student.roll_number}')
            if status:
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
        
        time_msg = ""
        if class_time:
            time_msg = f" at {class_time.strftime('%I:%M %p')}"
            if end_time:
                time_msg += f" - {end_time.strftime('%I:%M %p')}"

        messages.success(request, f"Attendance saved for {save_date.strftime('%d-%b-%Y')} ({day_name}){time_msg}. {count_present}/{len(students)} Present.")
        return redirect(reverse('staffs:manage_attendance', kwargs={'subject_id': subject.id}) + f"?date={save_date.strftime('%Y-%m-%d')}")

    # --- CALENDAR GENERATION ---
    
    # 1. Setup Month/Year nav
    cal_year = date_obj.year
    cal_month = date_obj.month
    
    cal = calendar.Calendar(firstweekday=0) # 0 = Monday
    month_days = cal.monthdatescalendar(cal_year, cal_month) # List of weeks, each week is list of date objects
    
    # 2. Key Data Mappings
    PERIOD_TIMES = {
        1: "08:30 - 09:30",
        2: "09:30 - 10:30",
        3: "10:40 - 11:40",
        4: "11:40 - 12:40",
        5: "01:30 - 02:30",
        6: "02:30 - 03:30",
        7: "03:30 - 04:30",
    }

    # 3. Fetch Timetable for this Subject
    # We need to know which DAYS have classes.
    # Structure: {'Monday': [ {period: 1, time: ...}, ... ], ...}
    timetable_entries = Timetable.objects.filter(subject=subject)
    timetable_map = {}
    for entry in timetable_entries:
        if entry.day not in timetable_map:
            timetable_map[entry.day] = []
        timetable_map[entry.day].append({
            'period': entry.period,
            'time': PERIOD_TIMES.get(entry.period, f"Period {entry.period}")
        })
    
    # 4. Fetch Existing Attendance for this Month
    # We want to color code days.
    # Valid Dates with attendance:
    attendance_dates = set(
        StudentAttendance.objects.filter(
            subject=subject, 
            date__year=cal_year, 
            date__month=cal_month
        ).values_list('date', flat=True)
    )

    # 5. Build Calendar Data Structure
    calendar_rows = []
    
    for week in month_days:
        week_data = []
        for day in week:
            is_current_month = (day.month == cal_month)
            day_classes = []
            status_class = "" # 'recorded', 'pending', 'empty'
            
            # Identify classes for this day
            day_name = day.strftime('%A')
            if day_name in timetable_map:
                day_classes = timetable_map[day_name]
                day_classes.sort(key=lambda x: x['period'])
            
            # Determine Status
            if day in attendance_dates:
                status_class = "recorded" # Activity done
            elif day_classes and day <= datetime.date.today():
                status_class = "pending" # Should have been done
            elif day_classes:
                status_class = "future" # Upcoming
            else:
                status_class = "empty" # No class
                
            week_data.append({
                'date': day,
                'day_num': day.day,
                'is_current_month': is_current_month,
                'is_selected': (day == date_obj),
                'is_today': (day == datetime.date.today()),
                'classes': day_classes,
                'status_class': status_class,
                'url': reverse('staffs:manage_attendance', kwargs={'subject_id': subject.id}) + f"?date={day.strftime('%Y-%m-%d')}"
            })
        calendar_rows.append(week_data)

    # --- Fetch Data for List View (Selected Date) ---
    attendance_map = {}
    attendance_entries = StudentAttendance.objects.filter(subject=subject, date=date_obj, student__in=students)
    attendance_map = {entry.student.roll_number: entry.status for entry in attendance_entries}

    return render(request, 'staff/manage_attendance.html', {
        'subject': subject,
        'students': students,
        'attendance_map': attendance_map,
        'current_date': formatted_date,
        'is_readonly': is_readonly,
        # Calendar Context
        'calendar_rows': calendar_rows,
        'month_name': calendar.month_name[cal_month],
        'year': cal_year,
        'prev_month_url': f"?date={(date_obj.replace(day=1) - datetime.timedelta(days=1)).strftime('%Y-%m-%d')}",
        # Calculate next month strictly
        'next_month_url': f"?date={( (date_obj.replace(day=28) + datetime.timedelta(days=4)).replace(day=1) ).strftime('%Y-%m-%d')}", 
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
    if current_staff.role != 'HOD' and subject.staff != current_staff:
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

    return render(request, 'staff/stafflist.html', {
        'staff_members': staff_members,
        'query': query,
        'departments': Staff.objects.values_list('department', flat=True).distinct()
    })
def passed_out_batches(request):
    """View to list batches (Ending Years) of passed out students."""
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')
        
    staff = Staff.objects.get(staff_id=request.session['staff_id'])
    
    # Simple access check: Only HOD should ideally access this, but can be open to staff
    if staff.role != 'HOD':
         messages.error(request, "Access Restricted to HOD.")
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
    """View to display weekly timetable."""
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')
        
    staff = Staff.objects.get(staff_id=request.session['staff_id'])
    
    selected_semester = request.GET.get('semester', 1)
    try:
        selected_semester = int(selected_semester)
    except ValueError:
        selected_semester = 1
        
    # Fetch timetable entries
    entries = Timetable.objects.filter(semester=selected_semester)
    
    # Structure data for the template: { 'Day': { periods... } }
    # Or just pass entries and let template handle filtering, but structured is better
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    timetable_data = {day: [None]*7 for day in days} # 7 Periods
    
    for entry in entries:
        if 1 <= entry.period <= 7:
             timetable_data[entry.day][entry.period-1] = entry

    # Convert to list of tuples for template iteration: [('Monday', [p1, p2...]), ...]
    timetable_rows = []
    for day in days:
        timetable_rows.append((day, timetable_data[day]))
             
    return render(request, 'staff/timetable.html', {
        'staff': staff,
        'timetable_rows': timetable_rows,
        'selected_semester': selected_semester,
        'semesters': range(1, 9)
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

    if staff.role == 'HOD':
        # HOD sees all subjects
        subjects_to_analyze = Subject.objects.all().order_by('semester', 'code')
    
    elif staff.role == 'Class Incharge' and staff.assigned_semester:
        # Class Incharge sees subjects they teach + ALL subjects in their assigned semester
        teaching_subjects = staff.subjects.all()
        semester_subjects = Subject.objects.filter(semester=staff.assigned_semester)
        subjects_to_analyze = (teaching_subjects | semester_subjects).distinct().order_by('semester', 'code')
        
    else:
        # Regular Staff / Course Incharge
        subjects_to_analyze = staff.subjects.all().order_by('semester', 'code')

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
    if staff.role == 'HOD':
        can_access = True
    elif staff.role == 'Class Incharge' and staff.assigned_semester:
        # Allow if subject is in their assigned semester OR if they teach it
        if subject.semester == staff.assigned_semester or subject in staff.subjects.all():
            can_access = True
    else:
        if subject in staff.subjects.all():
            can_access = True
            
    # If HOD, access is True. If strict access needed:
    if not can_access and staff.role != 'HOD':
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
    if staff.role == 'Class Incharge' and staff.assigned_semester:
        # Class Incharge sees 'Pending Class Incharge' for their semester
        leave_requests = LeaveRequest.objects.filter(
            status='Pending Class Incharge',
            student__current_semester=staff.assigned_semester
        ).order_by('created_at')
    elif staff.role == 'HOD':
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
            elif staff.role == 'HOD':
                leave_request.status = 'Approved'
                messages.success(request, f"Leave approved for {leave_request.student.student_name}.")
                
        elif action == 'reject':
            leave_request.status = 'Rejected'
            leave_request.rejection_reason = reason
            leave_request.rejected_by = f"{staff.name} ({staff.role})"
            messages.warning(request, f"Leave rejected for {leave_request.student.student_name}.")
        
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
    if current_staff.role != 'HOD':
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
        if current_staff.role != 'HOD':
             messages.error(request, "Unauthorized action.")
             return redirect('staffs:staff_dashboard')

        action = request.POST.get('action')
        reason = request.POST.get('rejection_reason', '')
        
        if action == 'approve':
            leave_request.status = 'Approved'
            messages.success(request, f"Approved leave for {leave_request.staff.name}.")
        elif action == 'reject':
            leave_request.status = 'Rejected'
            leave_request.rejection_reason = reason
            messages.warning(request, f"Rejected leave for {leave_request.staff.name}.")
        
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

    if staff.role != 'HOD':
        messages.error(request, "Access Denied: Only HOD can access Admin Portal.")
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
    """Dedicated page for managing scholarships with advanced filtering and export."""
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')
        
    try:
        staff = Staff.objects.get(staff_id=request.session['staff_id'])
    except Staff.DoesNotExist:
        return redirect('staffs:stafflogin')
        
    if staff.role != 'Scholarship Officer':
        messages.error(request, "Access restricted to Scholarship Officer.")
        return redirect('staffs:staff_dashboard')
        
    from students.models import Student, ScholarshipInfo, PersonalInfo
    from django.db.models import Q
    import csv
    from django.http import HttpResponse

    # Base QuerySet
    students = Student.objects.select_related('scholarshipinfo', 'personalinfo').all()

    # --- Filtering ---
    # 1. Scholarship Type (handling multiple selections if needed, though simple select for now)
    sch_type = request.GET.get('scholarship_type')
    if sch_type:
        SCHOLARSHIP_MAPPING = {
            'First Graduate': 'scholarshipinfo__is_first_graduate',
            'BC/MBC': 'scholarshipinfo__sch_bcmbc',
            'Postmatric': 'scholarshipinfo__sch_postmetric',
            'PM': 'scholarshipinfo__sch_pm',
            'Govt': 'scholarshipinfo__sch_govt',
            'Pudhumai Penn': 'scholarshipinfo__sch_pudhumai',
            'Tamizh Puthalvan': 'scholarshipinfo__sch_tamizh',
            'Private': 'scholarshipinfo__sch_private'
        }
        if sch_type in SCHOLARSHIP_MAPPING:
            filter_kwargs = {SCHOLARSHIP_MAPPING[sch_type]: True}
            students = students.filter(**filter_kwargs)

    # 2. Program Level
    program = request.GET.get('program_level')
    if program:
        students = students.filter(program_level=program)

    # 3. Semester
    semester = request.GET.get('semester')
    if semester:
        students = students.filter(current_semester=semester)

    # 4. Gender (from PersonalInfo)
    gender = request.GET.get('gender')
    if gender:
        students = students.filter(personalinfo__gender=gender)

    # 5. Community (from PersonalInfo)
    community = request.GET.get('community')
    if community:
        students = students.filter(personalinfo__community=community)

    # --- Export to CSV ---
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="scholarship_students.csv"'

        writer = csv.writer(response)
        writer.writerow(['Roll Number', 'Name', 'Program', 'Semester', 'Community', 'Gender', 'Scholarships'])

        for s in students:
            # Determine active scholarships
            active_sch = []
            try:
                si = s.scholarshipinfo
                if si.is_first_graduate: active_sch.append('First Graduate')
                if si.sch_bcmbc: active_sch.append('BC/MBC')
                if si.sch_postmetric: active_sch.append('Postmetric')
                if si.sch_pm: active_sch.append('PM')
                if si.sch_govt: active_sch.append('Govt')
                if si.sch_pudhumai: active_sch.append('Pudhumai Penn')
                if si.sch_tamizh: active_sch.append('Tamizh Puthalvan')
                if si.sch_private: active_sch.append(f"Private ({si.private_scholarship_name})")
            except ScholarshipInfo.DoesNotExist:
                pass
            
            # Helper to safely get personal info
            comm = 'N/A'
            gen = 'N/A'
            try:
                comm = s.personalinfo.community
                gen = s.personalinfo.gender
            except PersonalInfo.DoesNotExist:
                pass

            writer.writerow([
                s.roll_number,
                s.student_name,
                s.program_level,
                s.current_semester,
                comm,
                gen,
                ", ".join(active_sch)
            ])
        return response

    context = {
        'staff': staff,
        'students': students,
        'filters': { # Pass current filters back to template
            'scholarship_type': sch_type,
            'program_level': program,
            'semester': semester,
            'gender': gender,
            'community': community
        }
    }
    return render(request, 'staff/scholarship_manager.html', context)


def staff_profile(request):
    """View to display the logged-in staff's profile."""
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')

    try:
        staff = Staff.objects.get(staff_id=request.session['staff_id'])
    except Staff.DoesNotExist:
        return redirect('staffs:stafflogin')

    return render(request, 'staff/profile.html', {'staff': staff})

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
        staff.qualification = request.POST.get('qualification', '')
        staff.specialization = request.POST.get('specialization', '')
        staff.academic_details = request.POST.get('academic_details', '')
        staff.experience = request.POST.get('experience', '')

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

    publications = staff.publication_list.all()
    awards = staff.award_list.all()
    seminars = staff.seminar_list.all()
    students_guided = staff.student_guided_list.all()
    
    # New Models
    conferences = staff.conferences.all().order_by('-year_of_publication', '-created_at')
    journals = staff.journals.all().order_by('-published_year', '-created_at')
    books = staff.books.all().order_by('-year_of_publication', '-created_at')

    return render(request, 'staff/staff_portfolio.html', {
        'staff': staff,
        'publications': publications,
        'awards': awards,
        'seminars': seminars,
        'students_guided': students_guided,
        'conferences': conferences,
        'journals': journals,
        'books': books,
    })


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
        StaffAwardHonour.objects.create(
            staff=staff,
            title=request.POST.get('title', '').strip(),
            awarded_by=request.POST.get('awarded_by', '').strip(),
            description=request.POST.get('description', '').strip(),
            year=request.POST.get('year', '').strip(),
            category=request.POST.get('category', 'Award'),
            supporting_document=request.FILES.get('supporting_document'),
        )
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
        StaffSeminar.objects.create(
            staff=staff,
            title=request.POST.get('title', '').strip(),
            event_type=request.POST.get('event_type', 'Seminar'),
            venue_or_description=request.POST.get('venue_or_description', '').strip(),
            date_from=request.POST.get('date_from') or None,
            date_to=request.POST.get('date_to') or None,
            year=request.POST.get('year', '').strip(),
            supporting_document=request.FILES.get('supporting_document'),
        )
        from .utils import log_audit
        log_audit(request, 'create', actor_type='staff', actor_id=staff.staff_id, actor_name=staff.name, object_type='Seminar', message='Added new seminar')
        messages.success(request, "Seminar added.")
        return redirect('staffs:staff_portfolio')
    return render(request, 'staff/portfolio_form.html', {
        'staff': staff, 'form_type': 'seminar', 'item': None, 'title': 'Add Seminar / Workshop',
    })

# --- New Portfolio Views (Conferences, Journals, Books) ---

def portfolio_add_conference(request):
    staff = _get_staff_for_portfolio(request)
    if not staff: return redirect('staffs:stafflogin')
    
    if request.method == 'POST':
        from .models import ConferenceParticipation
        ConferenceParticipation.objects.create(
            staff=staff,
            participation_type=request.POST.get('participation_type', 'Presented'),
            national_international=request.POST.get('national_international', 'National'),
            author_name=request.POST.get('author_name', ''),
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
        messages.success(request, "Conference entry added successfully.")
        return redirect('staffs:staff_portfolio')
    
    return render(request, 'staff/portfolio_form.html', {
        'staff': staff, 'form_type': 'conference', 'item': None, 'title': 'Add Conference Participation',
    })

def portfolio_add_journal(request):
    staff = _get_staff_for_portfolio(request)
    if not staff: return redirect('staffs:stafflogin')

    if request.method == 'POST':
        from .models import JournalPublication
        JournalPublication.objects.create(
            staff=staff,
            national_international=request.POST.get('national_international', 'National'),
            published_month=request.POST.get('published_month', ''),
            published_year=request.POST.get('published_year', ''),
            author_name=request.POST.get('author_name', ''),
            title_of_paper=request.POST.get('title_of_paper', ''),
            journal_name=request.POST.get('journal_name', ''),
            volume_number=request.POST.get('volume_number', ''),
            issue_number=request.POST.get('issue_number', ''),
            year_of_publication_doi=request.POST.get('year_of_publication_doi', ''),
            page_numbers_from=request.POST.get('page_numbers_from', ''),
            page_numbers_to=request.POST.get('page_numbers_to', ''),
            supporting_document=request.FILES.get('supporting_document'),
        )
        messages.success(request, "Journal publication added successfully.")
        return redirect('staffs:staff_portfolio')
    
    return render(request, 'staff/portfolio_form.html', {
        'staff': staff, 'form_type': 'journal', 'item': None, 'title': 'Add Journal Publication',
    })

def portfolio_add_book(request):
    staff = _get_staff_for_portfolio(request)
    if not staff: return redirect('staffs:stafflogin')

    if request.method == 'POST':
        from .models import BookPublication
        BookPublication.objects.create(
            staff=staff,
            type=request.POST.get('type', 'Book'),
            author_name=request.POST.get('author_name', ''),
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
        messages.success(request, "Book/Article entry added successfully.")
        return redirect('staffs:staff_portfolio')
    
    return render(request, 'staff/portfolio_form.html', {
        'staff': staff, 'form_type': 'book', 'item': None, 'title': 'Add Book / Popular Article',
    })

def portfolio_delete_entry(request, model_name, pk):
    staff = _get_staff_for_portfolio(request)
    if not staff: return redirect('staffs:stafflogin')
    
    from .models import ConferenceParticipation, JournalPublication, BookPublication, StaffAwardHonour, StaffSeminar, StaffStudentGuided, StaffPublication
    
    model_map = {
        'conference': ConferenceParticipation,
        'journal': JournalPublication,
        'book': BookPublication,
        'award': StaffAwardHonour,
        'seminar': StaffSeminar,
        'student_guided': StaffStudentGuided,
    }
    
    ModelClass = model_map.get(model_name)
    if ModelClass:
        get_object_or_404(ModelClass, pk=pk, staff=staff).delete()
        messages.success(request, "Entry deleted.")
    
    return redirect('staffs:staff_portfolio')



def portfolio_edit_seminar(request, pk):
    staff = _get_staff_for_portfolio(request)
    if not staff:
        return redirect('staffs:stafflogin')
    item = get_object_or_404(StaffSeminar, pk=pk, staff=staff)
    if request.method == 'POST':
        item.title = request.POST.get('title', '').strip()
        item.event_type = request.POST.get('event_type', 'Seminar')
        item.venue_or_description = request.POST.get('venue_or_description', '').strip()
        item.date_from = request.POST.get('date_from') or None
        item.date_to = request.POST.get('date_to') or None
        item.year = request.POST.get('year', '').strip()
        if 'supporting_document' in request.FILES:
            item.supporting_document = request.FILES['supporting_document']
        item.save()
        from .utils import log_audit
        log_audit(request, 'update', actor_type='staff', actor_id=staff.staff_id, actor_name=staff.name, object_type='Seminar', object_id=str(item.pk), message='Updated seminar')
        messages.success(request, "Entry updated.")
        return redirect('staffs:staff_portfolio')
    return render(request, 'staff/portfolio_form.html', {
        'staff': staff, 'form_type': 'seminar', 'item': item, 'title': 'Edit Seminar / Workshop / Conference',
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
        StaffStudentGuided.objects.create(
            staff=staff,
            student_name=request.POST.get('student_name', '').strip(),
            degree_type=request.POST.get('degree_type', 'PG'),
            status=request.POST.get('status', 'Ongoing'),
            year=request.POST.get('year', '').strip(),
            supporting_document=request.FILES.get('supporting_document'),
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
        item.student_name = request.POST.get('student_name', '').strip()
        item.degree_type = request.POST.get('degree_type', 'PG')
        item.status = request.POST.get('status', 'Ongoing')
        item.year = request.POST.get('year', '').strip()
        if 'supporting_document' in request.FILES:
            item.supporting_document = request.FILES['supporting_document']
        item.save()
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
        if current_staff.role == 'Class Incharge' and current_staff.assigned_semester:
            selected_semester = str(current_staff.assigned_semester)
            display_semester_selector = False
            header_text = f"Managing Semester {selected_semester} (Assigned)"
    except Staff.DoesNotExist:
        pass

    if selected_semester:
        students = Student.objects.filter(current_semester=selected_semester)
    
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


def manage_bonafide(request):
    """View for HOD to manage bonafide requests."""
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')
    
    try:
        staff = Staff.objects.get(staff_id=request.session['staff_id'])
        if staff.role != 'HOD':
            messages.error(request, "Access Denied: Only HOD can manage bonafide requests.")
            return redirect('staffs:staff_dashboard')
    except Staff.DoesNotExist:
         return redirect('staffs:stafflogin')

    from students.models import BonafideRequest

    if request.method == 'POST':
        request_id = request.POST.get('request_id')
        action = request.POST.get('action') # 'approve' or 'reject'
        rejection_reason = request.POST.get('rejection_reason', '')

        if request_id and action:
            bonafide_req = get_object_or_404(BonafideRequest, id=request_id)
            
            if action == 'approve':
                bonafide_req.status = 'Approved'
                bonafide_req.save()
                messages.success(request, f"Bonafide request for {bonafide_req.student.student_name} approved.")
            elif action == 'reject':
                bonafide_req.status = 'Rejected'
                bonafide_req.rejection_reason = rejection_reason
                bonafide_req.save()
                messages.warning(request, f"Bonafide request for {bonafide_req.student.student_name} rejected.")
                
            return redirect('staffs:manage_bonafide')

    # Fetch all requests, ordered by pending first, then date
    requests = BonafideRequest.objects.all().order_by(
        Case(When(status='Pending HOD', then=0), default=1),
        '-created_at'
    )

    return render(request, 'staff/manage_bonafide.html', {
        'requests': requests,
        'staff': staff
    })
