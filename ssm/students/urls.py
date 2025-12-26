from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from . import views


urlpatterns = [
    path('', views.prevhome, name='homepage'),
    path('login/', views.stdlogin, name='student_login'),
    #path('stafflogin/', views.stdlogin, name='staff_login'),
    path('register/', views.stdregister, name='student_register'),
    path('api/register/', views.register_student, name='api_register_student'),
    path('success/', views.registration_success, name='registration_success'),
    path('dashboard/', views.student_dashboard, name='student_dashboard'),
    path('logout/', views.student_logout, name='student_logout'),

    # 1. Request password reset
    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='password_reset_form.html',
        email_template_name='students/password_reset_email.html',
        subject_template_name='students/password_reset_subject.txt',
        success_url=reverse_lazy('students:password_reset_done')
    ), name='password_reset'),

    # 2. Email sent page
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='password_reset_done.html'
    ), name='password_reset_done'),

    # 3. Reset link in email
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='password_reset_confirm.html',
        success_url=reverse_lazy('students:password_reset_complete')
    ), name='password_reset_confirm'),

    # 4. Reset complete
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='password_reset_complete.html'
    ), name='password_reset_complete'),

    # Other views
    path('support/', views.help_and_support, name='help_and_support'),
    path('exam-timetable/', views.exam_timetable, name='exam_timetable'),
    path('class-timetable/', views.class_timetable, name='class_timetable'),
    path('edit_profile/', views.student_editprofile, name='student_editprofile'),
    #path('api/get-castes/', views.get_castes, name='get_castes'),
    path('api/get-castes/', views.get_caste_data_api, name='api_get_castes'),
   # path('reset-password-request/', views.password_reset_request, name='password_reset_request'),
    #path('reset-password/<uuid:token>/', views.password_reset_confirmm, name='password_reset_confirm'),
    #path('reset-password/', views.password_reset_security, name='password_reset_security'),
    path('password-reset/identify/', views.password_reset_identify, name='password_reset_identify'),
    path('password-reset/verify/', views.password_reset_verify, name='password_reset_verify'),
    path('password-reset/confirm/', views.password_reset_confirm, name='password_reset_confirm'),
    path('service-unavailable/', views.service_unavailable, name='service_unavailable'),
    
    # Student attendance and marks
    path('attendance/', views.student_attendance, name='student_attendance'),
    path('student/marks/', views.student_marks, name='student_marks'),
    
    # Resume Builder
    path('resume-builder/', views.resume_builder, name='resume_builder'),
    path('resume-builder/download/', views.generate_resume_pdf, name='generate_resume_pdf'),
    path('resume-builder/ai-generate/', views.ai_generate_resume, name='ai_generate_resume'),

    path('student/export/marks/', views.export_student_marks_csv, name='export_marks_csv'),
    path('student/export/attendance/', views.export_student_attendance_csv, name='export_attendance_csv'),
]
