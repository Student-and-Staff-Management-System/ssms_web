from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.contrib.auth.hashers import make_password, check_password
import datetime


def get_year_choices():
    """Generates a list of years for dropdown choices."""
    current_year = datetime.date.today().year
    # Goes from 41 years ago to the current year
    return [(str(year), str(year)) for year in range(current_year, current_year - 41, -1)]

PROGRAM_LEVEL_CHOICES = [('UG', 'Undergraduate'), ('PG', 'Postgraduate'), ('PHD', 'PhD')]
UG_ENTRY_CHOICES = [('Regular', 'Regular (HSC)'), ('Lateral', 'Lateral (Diploma)'),]
GENDER_CHOICES = [('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')]
BLOOD_GROUP_CHOICES = [('O+', 'O+'), ('O-', 'O-'), ('A+', 'A+'), ('A-', 'A-'), ('B+', 'B+'), ('B-', 'B-'), ('AB+', 'AB+'), ('AB-', 'AB-')]
RELIGION_CHOICES = [('Hindu', 'Hindu'), ('Christian', 'Christian'), ('Muslim', 'Muslim')]
COMMUNITY_CHOICES = [('OC', 'OC'), ('BC', 'BC'), ('MBC', 'MBC'), ('SC', 'SC'), ('ST', 'ST'),('BC MUSLIM','BC MUSLIM')]

class Caste(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name

class Student(models.Model):
    roll_number = models.CharField(max_length=20, primary_key=True)
    register_number = models.CharField(max_length=20, blank=True, null=True)
    student_name = models.CharField(max_length=100)
    student_email = models.EmailField(unique=True)
    password = models.CharField(max_length=128) # Stores the hashed password
    program_level = models.CharField(max_length=10, choices=PROGRAM_LEVEL_CHOICES, blank=True)
    ug_entry_type = models.CharField(max_length=10, choices=UG_ENTRY_CHOICES, blank=True)
    
    current_semester = models.PositiveIntegerField(default=1) # Added for semester management
    
    # Batch Info
    joining_year = models.IntegerField(null=True, blank=True)
    ending_year = models.IntegerField(null=True, blank=True)
    
    # Security Questions (Added to fix DB sync issue)
    security_question_1 = models.CharField(max_length=255, blank=True, null=True)
    security_answer_1 = models.CharField(max_length=255, blank=True, null=True)
    security_question_2 = models.CharField(max_length=255, blank=True, null=True)
    security_answer_2 = models.CharField(max_length=255, blank=True, null=True)

    def set_password(self, raw_password):
        """Hashes the raw password and sets it."""
        self.password = make_password(raw_password)
        self.save()

    def check_password(self, raw_password):
        """Checks if the raw password matches the hashed one."""
        return check_password(raw_password, self.password)

    def __str__(self):
        return f"{self.student_name} ({self.roll_number})"


class PersonalInfo(models.Model):
    student = models.OneToOneField(Student, on_delete=models.CASCADE, primary_key=True)
    umis_id = models.CharField(max_length=50, blank=True)
    emis_id = models.CharField(max_length=50, blank=True)
    abc_id = models.CharField(max_length=50, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True)
    blood_group = models.CharField(max_length=5, choices=BLOOD_GROUP_CHOICES, blank=True)
    community = models.CharField(max_length=50, choices=COMMUNITY_CHOICES, blank=True)
    caste = models.ForeignKey(Caste, on_delete=models.SET_NULL, blank=True, null=True)
    caste_other = models.CharField(max_length=100, blank=True, null=True)
    religion = models.CharField(max_length=50, choices=RELIGION_CHOICES, blank=True)
    aadhaar_number = models.CharField(max_length=12, blank=True)
    permanent_address = models.TextField(blank=True)
    present_address = models.TextField(blank=True)
    student_mobile = models.CharField(max_length=15, blank=True)
    father_name = models.CharField(max_length=100, blank=True)
    father_occupation = models.CharField(max_length=100, blank=True)
    father_mobile = models.CharField(max_length=15, blank=True)
    mother_name = models.CharField(max_length=100, blank=True)
    mother_occupation = models.CharField(max_length=100, blank=True)
    mother_mobile = models.CharField(max_length=15, blank=True)
    parent_annual_income = models.PositiveIntegerField(blank=True, null=True)
    has_scholarship = models.BooleanField(default=False)

class BankDetails(models.Model):
    student = models.OneToOneField(Student, on_delete=models.CASCADE, primary_key=True)
    account_holder_name = models.CharField(max_length=100, blank=True)
    account_number = models.CharField(max_length=20, blank=True)
    bank_name = models.CharField(max_length=100, blank=True)
    branch_name = models.CharField(max_length=100, blank=True)
    ifsc_code = models.CharField(max_length=15, blank=True)

class AcademicHistory(models.Model):
    student = models.OneToOneField(Student, on_delete=models.CASCADE, primary_key=True)
    sslc_register_number = models.CharField(max_length=50, blank=True)
    sslc_percentage = models.FloatField(blank=True, null=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    sslc_year_of_passing = models.CharField(max_length=4, choices=get_year_choices(), blank=True)
    sslc_school_name = models.CharField(max_length=255, blank=True)
    sslc_school_address = models.TextField(blank=True)
    hsc_register_number = models.CharField(max_length=50, blank=True)
    hsc_percentage = models.FloatField(blank=True, null=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    hsc_year_of_passing = models.CharField(max_length=4, choices=get_year_choices(), blank=True)
    hsc_school_name = models.CharField(max_length=255, blank=True)
    hsc_school_address = models.TextField(blank=True)

class DiplomaDetails(models.Model):
    student = models.OneToOneField(Student, on_delete=models.CASCADE, primary_key=True)
    diploma_register_number = models.CharField(max_length=50, blank=True)
    diploma_percentage = models.FloatField(blank=True, null=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    diploma_year_of_passing = models.CharField(max_length=4, choices=get_year_choices(), blank=True)
    diploma_college_name = models.CharField(max_length=255, blank=True)
    diploma_college_address = models.TextField(blank=True)

class UGDetails(models.Model):
    student = models.OneToOneField(Student, on_delete=models.CASCADE, primary_key=True)
    ug_course = models.CharField(max_length=100, blank=True)
    ug_university = models.CharField(max_length=255, blank=True)
    ug_ogpa = models.FloatField(blank=True, null=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    ug_year_of_passing = models.CharField(max_length=4, choices=get_year_choices(), blank=True)

class PGDetails(models.Model):
    student = models.OneToOneField(Student, on_delete=models.CASCADE, primary_key=True)
    pg_course = models.CharField(max_length=100, blank=True)
    pg_university = models.CharField(max_length=255, blank=True)
    pg_ogpa = models.FloatField(blank=True, null=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    pg_year_of_passing = models.CharField(max_length=4, choices=get_year_choices(), blank=True)

class PhDDetails(models.Model):
    student = models.OneToOneField(Student, on_delete=models.CASCADE, primary_key=True)
    phd_specialization = models.CharField(max_length=255, blank=True)
    phd_university = models.CharField(max_length=255, blank=True)
    phd_year_of_joining = models.CharField(max_length=4, choices=get_year_choices(), blank=True)

class ScholarshipInfo(models.Model):
    student = models.OneToOneField(Student, on_delete=models.CASCADE, primary_key=True)
    is_first_graduate = models.BooleanField(default=False)
    sch_bcmbc = models.BooleanField(default=False)
    sch_postmetric = models.BooleanField(default=False)
    sch_pm = models.BooleanField(default=False)
    sch_govt = models.BooleanField(default=False)
    sch_pudhumai = models.BooleanField(default=False)
    sch_tamizh = models.BooleanField(default=False)
    sch_private = models.BooleanField(default=False)
    private_scholarship_name = models.CharField(max_length=100, blank=True)

class StudentDocuments(models.Model):
    student = models.OneToOneField(Student, on_delete=models.CASCADE, primary_key=True)
    student_photo = models.ImageField(upload_to='photos/', blank=True, null=True)
    student_id_card = models.FileField(upload_to='docs/', blank=True, null=True)
    community_certificate = models.FileField(upload_to='docs/', blank=True, null=True)
    aadhaar_card = models.FileField(upload_to='docs/', blank=True, null=True)
    first_graduate_certificate = models.FileField(upload_to='docs/', blank=True, null=True)
    sslc_marksheet = models.FileField(upload_to='docs/', blank=True, null=True)
    hsc_marksheet = models.FileField(upload_to='docs/', blank=True, null=True)
    income_certificate = models.FileField(upload_to='docs/', blank=True, null=True)
    bank_passbook = models.FileField(upload_to='docs/', blank=True, null=True)
    driving_license = models.FileField(upload_to='docs/', blank=True, null=True)
    
class OtherDetails(models.Model):
    student = models.OneToOneField(Student, on_delete=models.CASCADE, primary_key=True)
    ambition = models.CharField(max_length=200, blank=True)
    role_model = models.CharField(max_length=100, blank=True)
    hobbies = models.TextField(blank=True)
    identification_marks = models.TextField(blank=True)

class StudentMarks(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='marks')
    subject = models.ForeignKey('staffs.Subject', on_delete=models.CASCADE, related_name='student_marks')
    test1_marks = models.IntegerField(null=True, blank=True)
    test2_marks = models.IntegerField(null=True, blank=True)
    internal_marks = models.IntegerField(null=True, blank=True)

    class Meta:
        unique_together = ('student', 'subject')

    def __str__(self):
        return f"{self.student.student_name} - {self.subject.code}"

class StudentAttendance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendance')
    subject = models.ForeignKey('staffs.Subject', on_delete=models.CASCADE, related_name='attendance')
    date = models.DateField()
    status = models.CharField(max_length=20, choices=[('Present', 'Present'), ('Absent', 'Absent')], default='Present')

    class Meta:
        unique_together = ('student', 'subject', 'date')

    def __str__(self):
        return f"{self.student.student_name} - {self.subject.code} - {self.date}"

class StudentSkill(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='skills')
    skill_name = models.CharField(max_length=100)
    proficiency = models.CharField(max_length=20, choices=[
        ('Beginner', 'Beginner'),
        ('Intermediate', 'Intermediate'),
        ('Advanced', 'Advanced'),
        ('Expert', 'Expert')
    ], default='Intermediate')

    def __str__(self):
        return f"{self.skill_name} ({self.proficiency})"

class StudentProject(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='projects')
    title = models.CharField(max_length=200)
    description = models.TextField()
    role = models.CharField(max_length=100, blank=True)
    technologies = models.CharField(max_length=200, blank=True)
    project_link = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.title

class LeaveRequest(models.Model):
    LEAVE_TYPES = [
        ('OD', 'On Other Duty - Doc Required'),
        ('Medical', 'Medical Leave - Doc Required'),
        ('Permission', 'Leave on Permission')
    ]
    STATUS_CHOICES = [
        ('Pending Class Incharge', 'Pending Class Incharge'),
        ('Pending HOD', 'Pending HOD'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected')
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='leave_requests')
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPES)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    document = models.FileField(upload_to='student_leave_docs/', blank=True, null=True, help_text="Required for Medical and OD")
    
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='Pending Class Incharge')
    rejection_reason = models.TextField(blank=True, null=True)
    rejected_by = models.CharField(max_length=100, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.student.student_name} - {self.get_leave_type_display()} ({self.status})"

