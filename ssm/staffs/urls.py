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
    path('profile/', views.staff_profile, name='staff_profile'), # User profile
    path('profile/edit/', views.staff_edit_profile, name='staff_edit_profile'),
    path('profile/portfolio/', views.staff_portfolio, name='staff_portfolio'),
    path('profile/portfolio/publication/add/', views.portfolio_add_publication, name='portfolio_add_publication'),
    path('profile/portfolio/publication/<int:pk>/edit/', views.portfolio_edit_publication, name='portfolio_edit_publication'),
    path('profile/portfolio/publication/<int:pk>/delete/', views.portfolio_delete_publication, name='portfolio_delete_publication'),
    path('profile/portfolio/award/add/', views.portfolio_add_award, name='portfolio_add_award'),
    path('profile/portfolio/award/<int:pk>/edit/', views.portfolio_edit_award, name='portfolio_edit_award'),
    path('profile/portfolio/award/<int:pk>/delete/', views.portfolio_delete_award, name='portfolio_delete_award'),
    path('profile/portfolio/seminar/add/', views.portfolio_add_seminar, name='portfolio_add_seminar'),
    path('profile/portfolio/seminar/<int:pk>/edit/', views.portfolio_edit_seminar, name='portfolio_edit_seminar'),
    path('profile/portfolio/seminar/<int:pk>/delete/', views.portfolio_delete_seminar, name='portfolio_delete_seminar'),
    path('profile/portfolio/student/add/', views.portfolio_add_student, name='portfolio_add_student'),
    path('profile/portfolio/student/<int:pk>/edit/', views.portfolio_edit_student, name='portfolio_edit_student'),
    path('profile/portfolio/student/add/', views.portfolio_add_student, name='portfolio_add_student'),
    path('profile/portfolio/student/<int:pk>/edit/', views.portfolio_edit_student, name='portfolio_edit_student'),
    path('profile/portfolio/student/<int:pk>/delete/', views.portfolio_delete_student, name='portfolio_delete_student'),

    # New Portfolio Sections
    path('profile/portfolio/conference/add/', views.portfolio_add_conference, name='portfolio_add_conference'),
    path('profile/portfolio/journal/add/', views.portfolio_add_journal, name='portfolio_add_journal'),
    path('profile/portfolio/book/add/', views.portfolio_add_book, name='portfolio_add_book'),
    path('profile/portfolio/delete/<str:model_name>/<int:pk>/', views.portfolio_delete_entry, name='portfolio_delete_entry'),

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
    path('generate-student/', views.generate_student, name='generate_student'),
    
    # Password Reset
    path('password-reset/', views.staff_password_reset_identify, name='password_reset_identify'),
    path('password-reset/verify/', views.staff_password_reset_verify, name='password_reset_verify'),
    path('password-reset/verify-otp/', views.staff_password_reset_otp_verify, name='password_reset_otp_verify'),
    path('password-reset/confirm/', views.staff_password_reset_confirm, name='password_reset_confirm'),
]
