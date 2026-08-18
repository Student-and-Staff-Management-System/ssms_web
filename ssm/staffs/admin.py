from django.contrib import admin
from .models import Staff, Subject, ExamSchedule, Timetable, News, StaffLeaveRequest, AuditLog, StaffGenerator, AdminSettings, Lab, ClassMapping, PublishedTimetableVersion, DepartmentTask
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction
import csv
import random
from django.http import HttpResponse

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'semester', 'staff')
    list_filter = ('semester',)
    search_fields = ('name', 'code')

@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ('staff_id', 'name', 'designation', 'role', 'get_all_assigned_roles', 'get_assigned_department_tasks', 'get_class_incharge_assignment', 'is_admin', 'is_timetable_incharge', 'is_scholarship_officer', 'department')
    list_editable = ('role', 'is_admin', 'is_timetable_incharge', 'is_scholarship_officer')
    search_fields = ('staff_id', 'name', 'email')
    list_filter = ('role', 'assigned_batch', 'is_admin', 'is_timetable_incharge', 'is_scholarship_officer', 'department', 'designation', 'assigned_department_tasks')
    actions = ['export_staff_tasks_csv', 'export_staff_allocation_matrix_csv']
    fieldsets = (
        ('Basic Info', {
            'fields': ('staff_id', 'name', 'email', 'photo')
        }),
        ('Role & Designation', {
            'fields': ('role', 'secondary_roles', 'is_admin', 'is_timetable_incharge', 'is_scholarship_officer', 'assigned_semester', 'assigned_batch', 'salutation', 'designation', 'department'),
            'description': 'Specify Primary Role, Secondary Roles (comma-separated, e.g. "Class Incharge, Scholarship Officer"), and Role Flags below.'
        }),
        ('Professional Details', {
            'fields': ('qualification', 'specialization', 'experience')
        }),
        ('Personal Details', {
            'fields': ('date_of_birth', 'date_of_joining', 'address')
        }),
        ('Accomplishments', {
            'fields': ('academic_details', 'publications', 'awards_and_memberships')
        }),
        ('Permissions', {
            'fields': ('is_active',)
        }),
    )

    def get_class_incharge_assignment(self, obj):
        if obj.has_role('Class Incharge') and obj.assigned_semester:
            if obj.assigned_batch and obj.assigned_batch != 'All':
                return f"Sem {obj.assigned_semester} (Batch {obj.assigned_batch})"
            return f"Sem {obj.assigned_semester} (Whole Sem)"
        return "—"
    get_class_incharge_assignment.short_description = 'Class Incharge Scope'

    def get_all_assigned_roles(self, obj):
        roles = obj.get_roles_list()
        return ", ".join(roles) if roles else "—"
    get_all_assigned_roles.short_description = 'All Assigned Roles'


    def get_assigned_department_tasks(self, obj):
        tasks = obj.assigned_department_tasks.all()
        if not tasks.exists():
            return "—"
        return ", ".join([f"{t.task_number}. {t.name}" for t in tasks[:3]]) + ("..." if tasks.count() > 3 else "")
    get_assigned_department_tasks.short_description = 'Assigned Tasks / Roles'

    @admin.action(description="📥 Export Selected Staff List with Assigned Tasks/Roles (CSV)")
    def export_staff_tasks_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="staff_assigned_roles_report.csv"'
        response.write('\ufeff')
        writer = csv.writer(response)
        writer.writerow(['Staff ID', 'Salutation', 'Name', 'Designation', 'Department', 'Email', 'Mobile', 'Primary Role', 'Assigned Department Tasks / Roles'])

        for staff in queryset.prefetch_related('assigned_department_tasks'):
            tasks = [f"{t.task_number}. {t.name}" for t in staff.assigned_department_tasks.all()]
            writer.writerow([
                staff.staff_id,
                staff.salutation or '',
                staff.name,
                staff.designation or '',
                staff.department or '',
                staff.email or '',
                staff.mobile_number or '',
                staff.role,
                "; ".join(tasks) if tasks else "No additional tasks assigned"
            ])
        return response

    @admin.action(description="📊 Export Complete Task Allocation Matrix (CSV)")
    def export_staff_allocation_matrix_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="department_task_allocation_matrix.csv"'
        response.write('\ufeff')
        writer = csv.writer(response)

        all_tasks = DepartmentTask.objects.all().order_by('task_number')
        header = ['Staff ID', 'Staff Name', 'Designation', 'Role'] + [f"Task {t.task_number}: {t.name}" for t in all_tasks]
        writer.writerow(header)

        for staff in queryset.prefetch_related('assigned_department_tasks'):
            assigned_ids = set(staff.assigned_department_tasks.values_list('id', flat=True))
            row = [
                staff.staff_id,
                staff.name,
                staff.designation or '',
                staff.role
            ]
            for task in all_tasks:
                row.append("YES" if task.id in assigned_ids else "NO")
            writer.writerow(row)

        return response
    
    def get_logged_in_staff(self, request):
        if not request.user or not request.user.is_authenticated:
            return None
        try:
            return Staff.objects.filter(email=request.user.email).first()
        except Exception:
            return None

    def has_change_permission(self, request, obj=None):
        has_perm = super().has_change_permission(request, obj)
        if not has_perm:
            return False
        if obj:
            # If the target object is an admin (HOD or is_admin)
            if obj.role == 'HOD' or obj.is_admin:
                logged_in = self.get_logged_in_staff(request)
                # Only the HOD can modify admin profiles
                if logged_in and logged_in.role != 'HOD':
                    return False
        return True

    def has_delete_permission(self, request, obj=None):
        has_perm = super().has_delete_permission(request, obj)
        if not has_perm:
            return False
        if obj:
            if obj.role == 'HOD' or obj.is_admin:
                logged_in = self.get_logged_in_staff(request)
                if logged_in and logged_in.role != 'HOD':
                    return False
        return True

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        logged_in = self.get_logged_in_staff(request)
        if logged_in and logged_in.role != 'HOD':
            # Additional admins cannot toggle is_admin or role in detail view
            if 'is_admin' not in fields:
                fields.append('is_admin')
            if 'role' not in fields:
                fields.append('role')
        return fields

    def save_model(self, request, obj, form, change):
        if change:
            logged_in = self.get_logged_in_staff(request)
            if logged_in and logged_in.role != 'HOD':
                original = Staff.objects.get(pk=obj.pk)
                # Prevent modifying administrator status
                if original.is_admin != obj.is_admin:
                    from django.core.exceptions import ValidationError
                    raise ValidationError("You do not have permission to modify administrator status.")
                # Prevent modifying roles
                if original.role != obj.role:
                    from django.core.exceptions import ValidationError
                    raise ValidationError("You do not have permission to modify staff roles.")
                # Prevent modifying existing admin profiles
                if original.role == 'HOD' or original.is_admin:
                    from django.core.exceptions import ValidationError
                    raise ValidationError("You do not have permission to modify administrator profiles.")
        obj.clean()
        super().save_model(request, obj, form, change)

@admin.register(ExamSchedule)
class ExamScheduleAdmin(admin.ModelAdmin):
    list_display = ('semester', 'subject', 'date', 'session', 'time')
    list_filter = ('semester', 'date')
    ordering = ('date', 'session')

@admin.register(Timetable)
class TimetableAdmin(admin.ModelAdmin):
    list_display = ('semester', 'day', 'period', 'subject', 'staff')
    list_filter = ('semester', 'day')
    ordering = ('semester', 'day', 'period')

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.staff:
            try:
                from .utils import send_staff_notification
                action = "updated" if change else "assigned"
                subject_name = obj.subject.name if obj.subject else "a subject"
                send_staff_notification(
                    staff=obj.staff,
                    title="📅 Timetable Updated",
                    body=f"Your schedule has been {action}. {subject_name} — {obj.day}, Period {obj.period}.",
                    url="/staffs/my-timetable/"
                )
            except Exception:
                pass

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'action', 'actor_type', 'actor_id', 'actor_name', 'ip_address', 'object_type', 'message_short')
    list_filter = ('action', 'actor_type', 'timestamp')
    search_fields = ('actor_id', 'actor_name', 'message', 'object_type', 'ip_address')
    readonly_fields = ('timestamp', 'action', 'actor_type', 'actor_id', 'actor_name', 'ip_address', 'user_agent', 'object_type', 'object_id', 'message', 'extra_data')
    ordering = ('-timestamp',)
    date_hierarchy = 'timestamp'
    list_per_page = 50

    def message_short(self, obj):
        return (obj.message[:60] + '...') if obj.message and len(obj.message) > 60 else (obj.message or '—')
    message_short.short_description = 'Message'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ('content_short', 'target', 'date', 'start_date', 'end_date', 'is_active', 'has_document', 'has_new_indicator')
    list_filter = ('target', 'is_active', 'start_date', 'end_date')
    search_fields = ('content', 'link')
    list_editable = ('target', 'is_active', 'start_date', 'end_date')
    
    fieldsets = (
        ('Content', {
            'fields': ('content', 'link', 'document')
        }),
        ('Visibility', {
            'fields': ('target', 'is_active', 'start_date', 'end_date'),
            'description': 'News will auto-disable after end date.'
        }),
        ('NEW Indicator', {
            'fields': ('new_gif_start_date', 'new_gif_end_date'),
            'description': 'Show a NEW indicator during this date range.'
        }),
    )
    
    def content_short(self, obj):
        return (obj.content[:50] + '...') if len(obj.content) > 50 else obj.content
    content_short.short_description = 'Content'
    
    def has_document(self, obj):
        return '📎' if obj.document else '—'
    has_document.short_description = 'Doc'
    
    def has_new_indicator(self, obj):
        return '🆕' if obj.should_show_new_indicator() else '—'
    has_new_indicator.short_description = 'NEW'
    
    def save_model(self, request, obj, form, change):
        obj.full_clean()
        super().save_model(request, obj, form, change)

@admin.register(StaffGenerator)
class StaffGeneratorAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False
        
    def has_change_permission(self, request, obj=None):
        return False
        
    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        return self.generate_staff_view(request)

    def generate_staff_view(self, request):
        if request.method == 'POST':
            action = request.POST.get('action')
            staff_role = request.POST.get('staff_role', 'Course Incharge')
            
            try:
                if action == 'preview_bulk':
                    bulk_input = request.POST.get('bulk_input', '').strip()
                    if not bulk_input:
                        messages.error(request, "Please enter staff details.")
                        return render(request, 'staff/generate_staff.html', {'active_tab': 'bulk', 'staff_role': staff_role})
                    
                    preview_list = []
                    lines = bulk_input.split('\n')
                    for line in lines:
                        if ',' in line:
                            s_id, s_name = line.split(',', 1)
                            s_id = s_id.strip()
                            s_name = s_name.strip()
                            if s_id:
                                exists = Staff.objects.filter(staff_id=s_id).exists()
                                preview_list.append({'staff_id': s_id, 'name': s_name, 'exists': exists})
                    
                    if not preview_list:
                        messages.error(request, "No valid staff details found. Use format: ID, Name")
                        return render(request, 'staff/generate_staff.html', {'active_tab': 'bulk', 'bulk_input': bulk_input, 'staff_role': staff_role})

                    return render(request, 'staff/generate_staff.html', {
                        'show_preview': True,
                        'preview_list': preview_list,
                        'bulk_input': bulk_input,
                        'staff_role': staff_role
                    })

                elif action == 'generate_bulk':
                    selected_entries = request.POST.getlist('selected_entries')
                    if not selected_entries:
                        messages.error(request, "No staff selected.")
                        return render(request, 'staff/generate_staff.html', {'active_tab': 'bulk', 'staff_role': staff_role})

                    response = HttpResponse(content_type='text/csv')
                    response['Content-Disposition'] = 'attachment; filename="generated_staff.csv"'
                    writer = csv.writer(response)
                    writer.writerow(['Staff ID', 'Name', 'Role', 'Temp Password'])

                    with transaction.atomic():
                        for entry in selected_entries:
                            s_id, s_name = entry.split('||', 1)
                            staff, created = Staff.objects.get_or_create(
                                staff_id=s_id,
                                defaults={
                                    'name': s_name,
                                    'role': staff_role,
                                    'is_active': True,
                                    'is_profile_complete': False
                                }
                            )
                            pwd = "Staff" + str(random.randint(1000, 9999))
                            if created:
                                staff.set_password(pwd)
                                staff.save()
                                writer.writerow([f'="{s_id}"', s_name, staff.role, pwd])
                            else:
                                writer.writerow([f'="{s_id}"', s_name, staff.role, "Existing"])

                    response.set_cookie('download_complete', 'true', max_age=20)
                    return response

                elif action == 'generate_single':
                    s_id = request.POST.get('single_staff_id', '').strip()
                    s_name = request.POST.get('single_name', '').strip()
                    
                    if not s_id or not s_name:
                        messages.error(request, "Please enter both Staff ID and Name.")
                        return render(request, 'staff/generate_staff.html', {'active_tab': 'single', 'single_staff_id': s_id, 'single_name': s_name, 'staff_role': staff_role})

                    response = HttpResponse(content_type='text/csv')
                    response['Content-Disposition'] = f'attachment; filename="staff_{s_id}.csv"'
                    writer = csv.writer(response)
                    writer.writerow(['Staff ID', 'Name', 'Role', 'Temp Password'])

                    with transaction.atomic():
                        staff, created = Staff.objects.get_or_create(
                            staff_id=s_id,
                            defaults={
                                'name': s_name,
                                'role': staff_role,
                                'is_active': True,
                                'is_profile_complete': False
                            }
                        )
                        pwd = "Staff" + str(random.randint(1000, 9999))
                        staff.set_password(pwd)
                        staff.save()
                        writer.writerow([f'="{s_id}"', s_name, staff.role, pwd])

                    response.set_cookie('download_complete', 'true', max_age=20)
                    return response

            except Exception as e:
                messages.error(request, f"Error generating staff: {str(e)}")
                return redirect('admin:staffs_staffgenerator_changelist')

        return render(request, 'staff/generate_staff.html', {'active_tab': 'bulk', 'staff_role': 'Course Incharge'})


@admin.register(DepartmentTask)
class DepartmentTaskAdmin(admin.ModelAdmin):
    list_display = ('task_number', 'name', 'category', 'get_assigned_staff_count', 'get_assigned_staff_list')
    list_filter = ('category',)
    search_fields = ('task_number', 'name', 'category', 'assigned_staff__name', 'assigned_staff__staff_id')
    filter_horizontal = ('assigned_staff',)
    ordering = ('task_number',)
    actions = ['export_tasks_csv', 'seed_missing_tasks']

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        from django.db.models import Max
        max_num = DepartmentTask.objects.aggregate(Max('task_number'))['task_number__max'] or 0
        initial['task_number'] = max_num + 1
        return initial


    def get_assigned_staff_count(self, obj):
        return obj.assigned_staff.count()
    get_assigned_staff_count.short_description = 'Staff Count'

    def get_assigned_staff_list(self, obj):
        names = [s.name for s in obj.assigned_staff.all()]
        return ", ".join(names) if names else "Unassigned"
    get_assigned_staff_list.short_description = 'Assigned Staff Members'

    @admin.action(description="📥 Export Selected Tasks & Assigned Staff (CSV)")
    def export_tasks_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="department_tasks_assignment_report.csv"'
        response.write('\ufeff')
        writer = csv.writer(response)
        writer.writerow(['Task No', 'Task / Role Name', 'Category', 'Assigned Staff Count', 'Assigned Staff (IDs & Names)'])

        for task in queryset.prefetch_related('assigned_staff'):
            staff_details = [f"{s.name} ({s.staff_id})" for s in task.assigned_staff.all()]
            writer.writerow([
                task.task_number,
                task.name,
                task.category,
                task.assigned_staff.count(),
                "; ".join(staff_details) if staff_details else "Unassigned"
            ])
        return response

    @admin.action(description="🌱 Seed / Reset 58 Default Department Tasks")
    def seed_missing_tasks(self, request, queryset):
        DepartmentTask.seed_default_tasks()
        self.message_user(request, "Successfully seeded default 58 Department Tasks & Roles.", messages.SUCCESS)


@admin.register(AdminSettings)
class AdminSettingsAdmin(admin.ModelAdmin):
    list_display = ('max_additional_admins',)

    def has_add_permission(self, request):
        return not AdminSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Lab)
class LabAdmin(admin.ModelAdmin):
    list_display = ('short_name', 'name', 'staff', 'from_date', 'to_date')
    search_fields = ('short_name', 'name')
    list_filter = ('staff', 'from_date', 'to_date')


@admin.register(ClassMapping)
class ClassMappingAdmin(admin.ModelAdmin):
    list_display = ('class_name', 'room_name', 'semester', 'from_date', 'to_date')
    search_fields = ('class_name', 'room_name')
    list_filter = ('semester', 'from_date', 'to_date')


@admin.register(PublishedTimetableVersion)
class PublishedTimetableVersionAdmin(admin.ModelAdmin):
    list_display = ('academic_year', 'semester', 'version_name', 'from_date', 'to_date', 'published_by', 'published_at', 'is_active')
    search_fields = ('version_name', 'academic_year')
    list_filter = ('academic_year', 'semester', 'is_active', 'from_date', 'to_date')

