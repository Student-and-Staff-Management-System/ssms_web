from django.contrib import admin
from .models import (
    Student, PersonalInfo, AcademicHistory, DiplomaDetails, UGDetails, PGDetails,
    PhDDetails, ScholarshipInfo, StudentDocuments, BankDetails, OtherDetails,
    StudentSkill, StudentProject
)

class PersonalInfoInline(admin.StackedInline):
    model = PersonalInfo
    can_delete = False
    verbose_name_plural = 'Personal Information'
    extra = 0

class AcademicHistoryInline(admin.StackedInline):
    model = AcademicHistory
    can_delete = False
    verbose_name_plural = 'Academic History'
    extra = 0

class DiplomaDetailsInline(admin.StackedInline):
    model = DiplomaDetails
    can_delete = False
    verbose_name_plural = 'Diploma Details'
    extra = 0

class UGDetailsInline(admin.StackedInline):
    model = UGDetails
    can_delete = False
    verbose_name_plural = 'UG Details'
    extra = 0

class PGDetailsInline(admin.StackedInline):
    model = PGDetails
    can_delete = False
    verbose_name_plural = 'PG Details'
    extra = 0

class PhDDetailsInline(admin.StackedInline):
    model = PhDDetails
    can_delete = False
    verbose_name_plural = 'PhD Details'
    extra = 0

class ScholarshipInfoInline(admin.StackedInline):
    model = ScholarshipInfo
    can_delete = False
    verbose_name_plural = 'Scholarship Information'
    extra = 0

class StudentDocumentsInline(admin.StackedInline):
    model = StudentDocuments
    can_delete = False
    verbose_name_plural = 'Student Documents'
    extra = 0

class BankDetailsInline(admin.StackedInline):
    model = BankDetails
    can_delete = False
    verbose_name_plural = 'Bank Details'
    extra = 0

class OtherDetailsInline(admin.StackedInline):
    model = OtherDetails
    can_delete = False
    verbose_name_plural = 'Other Details'
    extra = 0

class StudentSkillInline(admin.TabularInline):
    model = StudentSkill
    extra = 1

class StudentProjectInline(admin.StackedInline):
    model = StudentProject
    extra = 0

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('roll_number', 'student_name', 'get_semester_display', 'program_level')
    search_fields = ('roll_number', 'student_name', 'student_email')
    list_filter = ('current_semester', 'program_level', 'ug_entry_type')
    actions = ['promote_students']
    
    inlines = [
        PersonalInfoInline,
        AcademicHistoryInline,
        DiplomaDetailsInline,
        UGDetailsInline,
        PGDetailsInline,
        PhDDetailsInline,
        ScholarshipInfoInline,
        StudentDocumentsInline,
        BankDetailsInline,
        OtherDetailsInline,
        StudentSkillInline,
        StudentProjectInline,
    ]

    @admin.display(description='Current Semester', ordering='current_semester')
    def get_semester_display(self, obj):
        if obj.current_semester > 8:
            return "Course Completed"
        return obj.current_semester

    @admin.action(description='Promote selected students to next semester')
    def promote_students(self, request, queryset):
        from django.db.models import F
        updated_count = queryset.filter(current_semester__lte=8).update(current_semester=F('current_semester') + 1)
        self.message_user(request, f"{updated_count} students were successfully promoted.")

    # Removed get_urls and generate_students_view from here to move to StudentGeneratorAdmin


# Register the Proxy Model to show in Sidebar
from .models import StudentGenerator

@admin.register(StudentGenerator)
class StudentGeneratorAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False
        
    def has_change_permission(self, request, obj=None):
        return False
        
    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        # Directly serve the generation view when clicking the sidebar link
        return self.generate_students_view(request)

    def generate_students_view(self, request):
        from django.shortcuts import render, redirect
        from django.contrib import messages
        from django.db import transaction
        import csv
        import random
        from django.http import HttpResponse
        from .models import Student

        if request.method == 'POST':
            action = request.POST.get('action', 'preview')
            
            try:
                if action == 'preview':
                    start_roll = request.POST.get('start_roll')
                    end_suffix = request.POST.get('end_suffix') # e.g. 110
                    
                    if not start_roll or not end_suffix:
                        messages.error(request, "Start Roll Number and End Suffix are required.")
                        return render(request, 'staff/generate_student.html', {'is_admin': True})
                    
                    n = len(end_suffix)
                    if n > len(start_roll):
                         messages.error(request, "End Suffix cannot be longer than Start Roll Number.")
                         return render(request, 'staff/generate_student.html', {'is_admin': True})
                    
                    start_suffix_str = start_roll[-n:]
                    if not start_suffix_str.isdigit() or not end_suffix.isdigit():
                         messages.error(request, "Roll number suffix must be numeric.")
                         return render(request, 'staff/generate_student.html', {'is_admin': True})
        
                    start_seq = int(start_suffix_str)
                    end_seq = int(end_suffix)
                    prefix = start_roll[:-n]
        
                    if end_seq < start_seq:
                        messages.error(request, f"End Suffix ({end_seq}) cannot be less than the start sequence ({start_seq}).")
                        return render(request, 'staff/generate_student.html', {'is_admin': True})
                    
                    count = end_seq - start_seq + 1
                    if count > 500:
                         messages.error(request, f"Cannot generate {count} students at once (Limit: 500).")
                         return render(request, 'staff/generate_student.html', {'is_admin': True})
                    
                    preview_list = []
                    for seq in range(start_seq, end_seq + 1):
                         roll_str = f"{prefix}{str(seq).zfill(n)}"
                         exists = Student.objects.filter(roll_number=roll_str).exists()
                         preview_list.append({'roll': roll_str, 'exists': exists})
                    
                    context = {
                        'show_preview': True,
                        'preview_list': preview_list,
                        'start_roll': start_roll,
                        'end_suffix': end_suffix,
                        'is_admin': True
                    }
                    return render(request, 'staff/generate_student.html', context)
                
                elif action == 'generate':
                    selected_rolls = request.POST.getlist('selected_rolls')
                    
                    if not selected_rolls:
                        messages.error(request, "No students selected for generation.")
                        return redirect('admin:students_studentgenerator_changelist')
    
                    response = HttpResponse(content_type='text/csv')
                    filename = f"generated_students_{len(selected_rolls)}_records.csv"
                    response['Content-Disposition'] = f'attachment; filename="{filename}"'
                    
                    writer = csv.writer(response)
                    writer.writerow(['Roll Number', 'Temp Password'])
                    
                    with transaction.atomic():
                        for roll_str in selected_rolls:
                            student, created = Student.objects.get_or_create(
                                roll_number=roll_str,
                                defaults={'is_profile_complete': False, 'is_password_changed': False}
                            )
                            if created:
                                temp_pass = "Pass" + str(random.randint(1000, 9999))
                                student.set_password(temp_pass)
                                student.save()
                                csv_pass_display = temp_pass
                            else:
                                csv_pass_display = "Existing Password"
                            writer.writerow([f'="{roll_str}"', csv_pass_display])
                    
                    response.set_cookie('download_complete', 'true', max_age=20)
                    return response
                
                elif action == 'generate_single':
                    single_roll = request.POST.get('single_roll').strip()
                    
                    if not single_roll:
                         messages.error(request, "Please enter a Roll Number.")
                         return redirect('admin:students_studentgenerator_changelist')
                         
                    response = HttpResponse(content_type='text/csv')
                    filename = f"generated_student_{single_roll}.csv"
                    response['Content-Disposition'] = f'attachment; filename="{filename}"'
                    
                    writer = csv.writer(response)
                    writer.writerow(['Roll Number', 'Temp Password'])
                    
                    with transaction.atomic():
                        student, created = Student.objects.get_or_create(
                             roll_number=single_roll,
                             defaults={'is_profile_complete': False, 'is_password_changed': False}
                        )
                        temp_pass = "Pass" + str(random.randint(1000, 9999))
                        student.set_password(temp_pass)
                        student.save()
                        writer.writerow([f'="{single_roll}"', temp_pass])
                    
                    response.set_cookie('download_complete', 'true', max_age=20)
                    return response

            except Exception as e:
                messages.error(request, f"Error generating students: {str(e)}")
                return redirect('admin:students_studentgenerator_changelist')
        
        # Initial GET request
        return render(request, 'staff/generate_student.html', {'is_admin': True})
