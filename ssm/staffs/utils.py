from students.models import Student, StudentAttendance, StudentMarks

def get_risk_metrics(subject):
    """
    Calculates risk metrics for a subject.
    Returns a list of dictionaries for students at risk.
    Risk Criteria:
    - Attendance < 75%
    - Internal Marks < 40 (if entered)
    """
    # Get students for this semester
    students = Student.objects.filter(current_semester=subject.semester).order_by('roll_number')
    
    # Pre-fetch attendance and marks to avoid N+1
    attendance_qs = StudentAttendance.objects.filter(subject=subject)
    
    # Calculate total working days for this subject
    # This might be slow if huge data, but accurate
    working_dates = attendance_qs.values_list('date', flat=True).distinct()
    total_dates = len(working_dates)
    
    # Marks
    marks_qs = StudentMarks.objects.filter(subject=subject)
    marks_map = {m.student_id: m for m in marks_qs}
    
    # Optimization: Fetch all attendance counts for this subject in one query if possible
    # But simple matching is safer for now to ensure correctness with existing logic
    
    risk_students = []
    
    for student in students:
        # 1. Attendance
        # Filter for this specific student from the pre-fetched QS (this still hits DB if not evaluating carefully)
        # Better: Aggregation
        # For now, let's stick to the working logic but optimize if needed. 
        # Actually, iterating filter inside loop is N queries.
        # Let's optimize: Fetch all present/absent counts for the subject grouped by student.
        pass

    # Optimized Approach
    from django.db.models import Count, Q
    
    # Get attendance stats per student for this subject
    att_stats = attendance_qs.values('student').annotate(
        present_count=Count('id', filter=Q(status='Present')),
        total_classes=Count('id') 
        # Note: total_classes here is records for that student. 
        # If a student wasn't marked for a day (late joiner), their total might be less.
        # Strict attendance usually checks against 'total_dates' (global classes conducted).
    )
    att_map = {stat['student']: stat['present_count'] for stat in att_stats}

    for student in students:
        # 1. Attendance Calculation
        present = att_map.get(student.roll_number, 0)
        # Use global total_dates for strict attendance (classes conducted vs attended)
        # If total_dates is 0, avoid division by zero
        percentage = (present / total_dates * 100) if total_dates > 0 else 0.0
        
        # 2. Marks
        marks = marks_map.get(student.roll_number)
        internal = marks.internal_marks if marks else None
        
        risk_factors = []
        if total_dates > 0 and percentage < 75:
            risk_factors.append(f"Low Attendance ({round(percentage, 1)}%)")
        
        if internal is not None and internal < 40:
             risk_factors.append(f"Low Internal ({internal})")
        
        if risk_factors:
            risk_students.append({
                'name': student.student_name,
                'roll_number': student.roll_number,
                'current_semester': student.current_semester,
                'attendance_percentage': round(percentage, 1),
                'internal_marks': internal if internal is not None else '-',
                'risk_factors': risk_factors
            })
            
    return risk_students
