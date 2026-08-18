from django.db import migrations

def seed_tasks(apps, schema_editor):
    DepartmentTask = apps.get_model('staffs', 'DepartmentTask')
    DEFAULT_DEPARTMENT_TASKS = [
        (1, "Department Administration", "Administration"),
        (2, "Board of Studies", "Academic & Governance"),
        (3, "Department Advisory Committee (Retd. Staff)", "Governance & Advisory"),
        (4, "All India Council for Technical Education (AICTE)", "Accreditation & Approvals"),
        (5, "Internal Quality Assurance Cell (IQAC)", "Quality Assurance"),
        (6, "National Assessment and Accreditation Council (NAAC)", "Accreditation & Approvals"),
        (7, "National Board of Accreditation (NBA)", "Accreditation & Approvals"),
        (8, "Department Research Committee (DRC)", "Research & Higher Studies"),
        (9, "Department Planning Board", "Administration & Planning"),
        (10, "Curriculum and Syllabus", "Curriculum & Academics"),
        (11, "Timetable", "Academic Management"),
        (12, "Value Added Course (VAC)", "Curriculum & Academics"),
        (13, "SWAYAM Courses", "Online & E-Learning"),
        (14, "I Year – Department Coordinator", "Academic Coordination"),
        (15, "2025 – 2029 Batch Class in Charge", "Class Incharge"),
        (16, "2024 – 2028 Batch Class in Charge", "Class Incharge"),
        (17, "2023 – 2027 Batch Class in Charge", "Class Incharge"),
        (18, "Class Monitoring Committee", "Student Affairs"),
        (19, "Research Activities and PhD Programme Coordination", "Research & Higher Studies"),
        (20, "Students Attendance and Remedial Coaching", "Student Support"),
        (21, "Mentor - Mentee", "Student Support & Counseling"),
        (22, "Continuous Assessment Test (CAT)", "Examinations & Assessment"),
        (23, "University Examinations", "Examinations & Assessment"),
        (24, "Placement Activities", "Career & Placement"),
        (25, "Career Guidance & Counselling", "Career & Placement"),
        (26, "Skill Development", "Student Support"),
        (27, "Internship Activities", "Career & Placement"),
        (28, "Institution of Engineers - India (IEI) Association", "Professional Societies"),
        (29, "Alumni Association", "Alumni & Outreach"),
        (30, "Institution Innovation Council (IIC)", "Innovation & Entrepreneurship"),
        (31, "Sports and Games Activities", "Student Co-Curricular"),
        (32, "Website & Social Media Maintenance", "IT & Infrastructure"),
        (33, "Laboratory Maintenance & Incharges", "IT & Infrastructure"),
        (34, "Professional Societies & Student Chapters", "Professional Societies"),
        (35, "Entrepreneurship Development Cell (EDC)", "Innovation & Entrepreneurship"),
        (36, "Higher Education Cell", "Research & Higher Studies"),
        (37, "Discipline & Anti-Ragging Committee", "Student Welfare & Conduct"),
        (38, "Red Cross / NSS / Social Service", "Student Co-Curricular"),
        (39, "Women Empowerment Cell", "Student Welfare & Conduct"),
        (40, "Consultancy & Testing Services", "Industry & Consultancy"),
        (41, "Industry Institute Interaction Cell (IIIC)", "Industry & Consultancy"),
        (42, "Prevention of Sexual Harassment", "Student Welfare & Conduct"),
        (43, "Help Desk", "Administration & Support"),
        (44, "Staff Welfare Committee", "Staff Welfare & Development"),
        (45, "Staff Professional Development Committee", "Staff Welfare & Development"),
        (46, "Budget", "Finance & Maintenance"),
        (47, "Department Fund Maintenance", "Finance & Maintenance"),
        (48, "RUSA Library Grant for Book Purchase", "Library & Learning Resources"),
        (49, "Stock Maintenance", "Finance & Maintenance"),
        (50, "Infrastructure & Facilities Management", "IT & Infrastructure"),
        (51, "Classroom Maintenance", "IT & Infrastructure"),
        (52, "Department File Maintenance", "Administration & Support"),
        (53, "Annual Report Preparation and Maintenance", "Administration & Support"),
        (54, "Class Committee Arrangements, Staff Meeting Arrangements, Minutes of Meeting Preparation and Maintenance", "Administration & Support"),
        (55, "Magazine Preparation", "Publications & Media"),
        (56, "Pledge Coordination", "Student Co-Curricular"),
        (57, "Cultural & Festivals", "Student Co-Curricular"),
        (58, "Literary Activities", "Student Co-Curricular")
    ]
    for num, name, cat in DEFAULT_DEPARTMENT_TASKS:
        DepartmentTask.objects.get_or_create(
            task_number=num,
            defaults={'name': name, 'category': cat}
        )

def reverse_seed(apps, schema_editor):
    pass

class Migration(migrations.Migration):
    dependencies = [
        ('staffs', '0071_staff_assigned_batch'),
    ]

    operations = [
        migrations.RunPython(seed_tasks, reverse_code=reverse_seed),
    ]
