from django.urls import path
from . import views
# from students.views import prevhome  # importing student view


# Set the namespace for this app
# Set the namespace for this app
app_name = 'staffs'
# Force reload

urlpatterns = [
    # The URL will be /staff/login/
    path('login/', views.stafflogin, name='stafflogin'),
    
    # The URL will be /staff/dashboard/
    path('dashboard/', views.staff_dashboard, name='staff_dashboard'),

    # The URL will be /staff/logout/
    path('logout/', views.staff_logout, name='staff_logout'),
    path('register/', views.staff_register, name='staff_register'),
    path('students/', views.student_list, name='student_list'),
    path('students/<str:roll_number>/', views.student_detail, name='student_detail'),
    path('semesters/', views.manage_semesters, name='manage_semesters'),
    path('subjects/', views.manage_subjects, name='manage_subjects'),
    path('subjects/<int:subject_id>/marks/', views.manage_marks, name='manage_marks'),
    path('subjects/<int:subject_id>/marks/export/', views.export_marks_csv, name='export_marks_csv'),
    path('subjects/<int:subject_id>/attendance/', views.manage_attendance, name='manage_attendance'),
    path('subjects/<int:subject_id>/attendance/report/', views.attendance_report, name='attendance_report'),
    path('subjects/<int:subject_id>/attendance/export/', views.export_attendance_csv, name='export_attendance_csv'),
    path('staff/list/', views.staff_list, name='staff_list'),
    
    # Passed Out Students
    path('passed-out/', views.passed_out_batches, name='passed_out_batches'),
    path('passed-out/<int:year>/', views.batch_students, name='batch_students'),
    path('exam-schedule/', views.exam_schedule, name='exam_schedule'),
    path('timetable/', views.timetable, name='timetable'),

    # Leave Management (Student -> Staff)
    path('leave/requests/', views.view_leave_requests, name='view_leave_requests'),
    path('leave/update/<int:request_id>/', views.update_leave_status, name='update_leave_status'),

    # Staff Leave System (Staff -> HOD)
    path('my-leave/apply/', views.staff_apply_leave, name='staff_apply_leave'),
    path('my-leave/history/', views.staff_leave_history, name='staff_leave_history'),
    path('hod/leave-requests/', views.hod_leave_dashboard, name='hod_leave_dashboard'),
    path('hod/leave-update/<int:request_id>/', views.hod_update_leave_status, name='hod_update_leave_status'),
    path('admin-portal/', views.admin_portal_login, name='admin_portal_login'),
    path('risk-students/', views.risk_students, name='risk_students'),
    path('risk-students/export/<int:subject_id>/', views.export_risk_list, name='export_risk_list'),
]
