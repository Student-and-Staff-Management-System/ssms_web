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

]
