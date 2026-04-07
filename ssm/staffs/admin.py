from django.contrib import admin
from .models import Staff, Subject, ExamSchedule, Timetable, News, StaffLeaveRequest, AuditLog, StaffGenerator
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
    list_display = ('staff_id', 'name', 'designation', 'role', 'assigned_semester', 'department')
    list_editable = ('role', 'assigned_semester')
    search_fields = ('staff_id', 'name', 'email')
    list_filter = ('role', 'department', 'designation')
    fieldsets = (
        ('Basic Info', {
            'fields': ('staff_id', 'name', 'email', 'photo')
        }),
        ('Role & Designation', {
            'fields': ('role', 'assigned_semester', 'salutation', 'designation', 'department'),
            'description': 'Note: Only one HOD is allowed. Class Incharge must be assigned to a unique semester.'
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
    
    def save_model(self, request, obj, form, change):
        obj.full_clean()
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
            
            try:
                if action == 'preview_bulk':
                    bulk_input = request.POST.get('bulk_input', '').strip()
                    if not bulk_input:
                        messages.error(request, "Please enter staff details.")
                        return render(request, 'staff/generate_staff.html', {'active_tab': 'bulk'})
                    
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
                        return render(request, 'staff/generate_staff.html', {'active_tab': 'bulk', 'bulk_input': bulk_input})

                    return render(request, 'staff/generate_staff.html', {
                        'show_preview': True,
                        'preview_list': preview_list,
                        'bulk_input': bulk_input
                    })

                elif action == 'generate_bulk':
                    selected_entries = request.POST.getlist('selected_entries')
                    if not selected_entries:
                        messages.error(request, "No staff selected.")
                        return render(request, 'staff/generate_staff.html', {'active_tab': 'bulk'})

                    response = HttpResponse(content_type='text/csv')
                    response['Content-Disposition'] = 'attachment; filename="generated_staff.csv"'
                    writer = csv.writer(response)
                    writer.writerow(['Staff ID', 'Name', 'Temp Password'])

                    with transaction.atomic():
                        for entry in selected_entries:
                            s_id, s_name = entry.split('||', 1)
                            staff, created = Staff.objects.get_or_create(
                                staff_id=s_id,
                                defaults={
                                    'name': s_name,
                                    'is_active': True
                                }
                            )
                            pwd = "Staff" + str(random.randint(1000, 9999))
                            if created:
                                staff.set_password(pwd)
                                staff.save()
                                writer.writerow([f'="{s_id}"', s_name, pwd])
                            else:
                                writer.writerow([f'="{s_id}"', s_name, "Existing"])

                    response.set_cookie('download_complete', 'true', max_age=20)
                    return response

                elif action == 'generate_single':
                    s_id = request.POST.get('single_staff_id', '').strip()
                    s_name = request.POST.get('single_name', '').strip()
                    
                    if not s_id or not s_name:
                        messages.error(request, "Please enter both Staff ID and Name.")
                        return render(request, 'staff/generate_staff.html', {'active_tab': 'single', 'single_staff_id': s_id, 'single_name': s_name})

                    response = HttpResponse(content_type='text/csv')
                    response['Content-Disposition'] = f'attachment; filename="staff_{s_id}.csv"'
                    writer = csv.writer(response)
                    writer.writerow(['Staff ID', 'Name', 'Temp Password'])

                    with transaction.atomic():
                        staff, created = Staff.objects.get_or_create(
                            staff_id=s_id,
                            defaults={'name': s_name, 'is_active': True}
                        )
                        pwd = "Staff" + str(random.randint(1000, 9999))
                        staff.set_password(pwd)
                        staff.save()
                        writer.writerow([f'="{s_id}"', s_name, pwd])

                    response.set_cookie('download_complete', 'true', max_age=20)
                    return response

            except Exception as e:
                messages.error(request, f"Error: {str(e)}")

        return render(request, 'staff/generate_staff.html', {})
