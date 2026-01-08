from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from .models import Staff, ExamSchedule, Timetable
from students.models import Student
from django.db.models import Q

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
                # --- THIS IS THE FIX ---
                # Use the correct URL name 'staff_dashboard' with the namespace
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
        if 'staff_id' in request.session:
            del request.session['staff_id']
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
    else:
        template_name = 'staff/staffdash_hod.html'
        
    # Fetch assigned subjects for this staff member
    assigned_subjects = staff.subjects.all().order_by('semester', 'code')
        
    # Calculate pending leaves for notification badge
    from students.models import LeaveRequest
    from staffs.models import StaffLeaveRequest, News
    pending_leaves_count = 0
    pending_staff_leaves_count = 0
    
    # Fetch News
    news_list = News.objects.filter(is_active=True, target__in=['All', 'Staff']).order_by('-date', '-id')
    
    if staff.role == 'HOD':
        pending_leaves_count = LeaveRequest.objects.filter(status='Pending HOD').count()
        pending_staff_leaves_count = StaffLeaveRequest.objects.filter(status='Pending').count()
    elif staff.role == 'Class Incharge' and staff.assigned_semester:
        pending_leaves_count = LeaveRequest.objects.filter(
            status='Pending Class Incharge',
            student__current_semester=staff.assigned_semester
        ).count()

    return render(request, template_name, {
        'staff': staff, 
        'student_count': student_count,
        'assigned_subjects': assigned_subjects,
        'pending_leaves_count': pending_leaves_count,
        'pending_staff_leaves_count': pending_staff_leaves_count,
        'news_list': news_list
    })

def staff_logout(request):
    """Logs the staff member out."""
    try:
        del request.session['staff_id']
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
        PhDDetails, ScholarshipInfo, StudentDocuments, BankDetails, OtherDetails
    )

    context = {
        'student': student,
        'personal_info': get_or_none(PersonalInfo, student=student),
        'academic_history': get_or_none(AcademicHistory, student=student),
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
                # Only promote if current_semester <= 8. 
                # If they are already 9 (Course Completed), do not increment further.
                Student.objects.filter(roll_number__in=student_ids, current_semester__lte=8).update(current_semester=F('current_semester') + 1)
                messages.success(request, f"Successfully promoted selected students.")
            
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

    students = Student.objects.filter(current_semester=subject.semester).order_by('roll_number')

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

    return render(request, 'staff/manage_marks.html', {
        'subject': subject,
        'students': students,
        'student_marks_map': student_marks_map,
        'is_readonly': is_readonly
    })

def manage_attendance(request, subject_id):
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')
    
    from .models import Subject
    from students.models import StudentAttendance
    import datetime

    subject = get_object_or_404(Subject, id=subject_id)
    current_staff = get_object_or_404(Staff, staff_id=request.session['staff_id'])

    # Access Control
    if current_staff.role != 'HOD' and subject.staff != current_staff:
        messages.error(request, "Access Denied: You are not assigned to this subject.")
        return redirect('staffs:staff_dashboard')

    # Date Handling
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

    if request.method == 'POST':
        if is_readonly:
             messages.error(request, "Read-only access: Cannot save attendance.")
             return redirect(request.path + f"?date={formatted_date}")

        # If date is changed via POST (e.g. date picker form submission if handled that way, 
        # but usually date picker is GET for view, POST for save. Let's assume POST includes date or uses current view date)
        # Better to trust the POSTed date if available, or fall back to view date.
        
        post_date_str = request.POST.get('attendance_date')
        if post_date_str:
             try:
                save_date = datetime.datetime.strptime(post_date_str, '%Y-%m-%d').date()
             except ValueError:
                save_date = date_obj
        else:
            save_date = date_obj

        for student in students:
            status = request.POST.get(f'status_{student.roll_number}')
            if status:
                StudentAttendance.objects.update_or_create(
                    student=student, 
                    subject=subject, 
                    date=save_date,
                    defaults={'status': status}
                )
        messages.success(request, f"Attendance saved for {save_date}.")
        from django.urls import reverse
        return redirect(reverse('staffs:manage_attendance', kwargs={'subject_id': subject.id}) + f"?date={save_date}")

    # Fetch existing attendance
    attendance_map = {}
    attendance_entries = StudentAttendance.objects.filter(subject=subject, date=date_obj, student__in=students)
    
    attendance_map = {entry.student.roll_number: entry.status for entry in attendance_entries}

    return render(request, 'staff/manage_attendance.html', {
        'subject': subject,
        'students': students,
        'attendance_map': attendance_map,
        'current_date': formatted_date,
        'is_readonly': is_readonly
    })

def attendance_report(request, subject_id):
    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')
        
    from .models import Subject
    from students.models import StudentAttendance
    from django.db.models import Count, Q
    import datetime

    subject = get_object_or_404(Subject, id=subject_id)
    current_staff = get_object_or_404(Staff, staff_id=request.session['staff_id'])

    # Access Control
    if current_staff.role != 'HOD' and subject.staff != current_staff:
        messages.error(request, "Access Denied: You are not assigned to this subject.")
        return redirect('staffs:staff_dashboard')

    students = Student.objects.filter(current_semester=subject.semester).order_by('roll_number')
    
    # Filter Handling
    month = request.GET.get('month')
    year = request.GET.get('year')
    
    attendance_qs = StudentAttendance.objects.filter(subject=subject)
    
    if month and year:
        attendance_qs = attendance_qs.filter(date__month=month, date__year=year)
    elif year:
         attendance_qs = attendance_qs.filter(date__year=year)

    # Calculate attendance summary
    summary_data = []
    
    # Get total working days (unique dates with attendance for this subject within filter)
    working_dates_qs = attendance_qs.values_list('date', flat=True).distinct().order_by('date')
    working_dates = list(working_dates_qs)
    total_dates = len(working_dates)
    
    for student in students:
        # We need to filter by student AND the previously applied date filters
        # Ideally we'd aggregate, but doing loop for detailed calculation is fine for class size < 100
        
        student_attendance = attendance_qs.filter(student=student)
        present_count = student_attendance.filter(status='Present').count()
        absent_count = student_attendance.filter(status='Absent').count()
        
        percentage = (present_count / total_dates * 100) if total_dates > 0 else 0
        
        summary_data.append({
            'student': student,
            'present': present_count,
            'absent': absent_count,
            'percentage': round(percentage, 2)
        })

    return render(request, 'staff/attendance_report.html', {
        'subject': subject,
        'summary_data': summary_data,
        'total_working_days': total_dates,
        'working_dates': working_dates,
        'selected_month': int(month) if month else '',
        'selected_year': int(year) if year else '',
        'current_year': datetime.date.today().year,
        'years': range(2024, datetime.date.today().year + 2), # Adjust range as needed
        'current_staff': current_staff
    })

def export_attendance_csv(request, subject_id):
    import csv
    from django.http import HttpResponse
    from .models import Subject
    from students.models import StudentAttendance
    import datetime

    if 'staff_id' not in request.session:
        return redirect('staffs:stafflogin')

    subject = get_object_or_404(Subject, id=subject_id)
    # Basic access check (reuse logic or decorator in real app)
    
    students = Student.objects.filter(current_semester=subject.semester).order_by('roll_number')
    
    month = request.GET.get('month')
    year = request.GET.get('year')
    
    attendance_qs = StudentAttendance.objects.filter(subject=subject)
    if month and year:
        attendance_qs = attendance_qs.filter(date__month=month, date__year=year)
        filename = f"Attendance_{subject.code}_{month}_{year}.csv"
    elif year:
        attendance_qs = attendance_qs.filter(date__year=year)
        filename = f"Attendance_{subject.code}_{year}.csv"
    else:
        filename = f"Attendance_{subject.code}_Overall.csv"

    working_dates_qs = attendance_qs.values_list('date', flat=True).distinct().order_by('date')
    working_dates = list(working_dates_qs)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    
    # Header Row: Roll No, Name, [Dates...], Total Present, Total Absent, %
    header = ['Roll Number', 'Student Name'] + [d.strftime('%d-%b') for d in working_dates] + ['Total Present', 'Total Absent', 'Percentage']
    writer.writerow(header)

    for student in students:
        # User requested last 3 digits of roll number
        short_roll = str(student.roll_number)[-3:]
        row = [short_roll, student.student_name]
        
        student_attendance_qs = attendance_qs.filter(student=student)
        # Create a map for quick lookup: date -> status
        status_map = {att.date: att.status for att in student_attendance_qs}
        
        present_count = 0
        absent_count = 0
        
        for date in working_dates:
            status = status_map.get(date, '-') # '-' if no record for that date (should ideally utilize defaults)
            # Shorten status for CSV
            if status == 'Present':
                row.append('P')
                present_count += 1
            elif status == 'Absent':
                row.append('A')
                absent_count += 1
            else:
                row.append('-')
        
        total_days = len(working_dates)
        percentage = (present_count / total_days * 100) if total_days > 0 else 0
        
        row.append(present_count)
        row.append(absent_count)
        row.append(f"{round(percentage, 2)}%")
        
        writer.writerow(row)

    return response

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
        'semesters': range(1, 9),
    })

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
