from django.contrib import admin
from .models import Staff, Subject, ExamSchedule, Timetable

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'semester', 'staff')
    list_filter = ('semester',)
    search_fields = ('name', 'code')

@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ('staff_id', 'name', 'designation', 'role', 'assigned_semester', 'department')
    list_editable = ('role', 'assigned_semester')
    search_fields = ('staff_id', 'name', 'email')
    list_filter = ('role', 'department', 'designation')
    fieldsets = (
        ('Basic Info', {
            'fields': ('staff_id', 'name', 'email', 'photo')
        }),
        ('Role & Designation', {
            'fields': ('role', 'assigned_semester', 'salutation', 'designation', 'department')
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
            'fields': ('is_active',) # Removed password field for security, use set_password via custom form or shell if really needed via admin, but standard is fine
        }),
    )

from .models import ExamSchedule, Timetable

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

from .models import News, StaffLeaveRequest, AuditLog


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
    list_display = ('content', 'target', 'date', 'start_date', 'end_date', 'is_active', 'link')
    list_filter = ('target', 'is_active', 'start_date', 'end_date')
    search_fields = ('content', 'link')
    list_editable = ('target', 'is_active', 'start_date', 'end_date')

@admin.register(StaffLeaveRequest)
class StaffLeaveRequestAdmin(admin.ModelAdmin):
    list_display = ('staff', 'leave_type', 'start_date', 'status')
    list_filter = ('staff', 'leave_type', 'status')
