from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.contrib.auth.hashers import make_password, check_password
import datetime
from ssm.validators import validate_file_size
from ssm.upload_paths import (
    student_photo_path, student_id_card_path, community_certificate_path,
    aadhaar_card_path, first_graduate_certificate_path, sslc_marksheet_path,
    hsc_marksheet_path, income_certificate_path, bank_passbook_path,
    driving_license_path, student_leave_document_path, result_screenshot_path
)


# ... existing imports ...

# Student Discipline/Remark Model
class StudentRemark(models.Model):
    REMARK_TYPE_CHOICES = [
        ('DRESSING_CODE', 'Dressing Code'),
        ('HAIRCUT_STYLING', 'Haircut / Styling'),
        ('BEARD', 'Beard'),
        ('CELL_PHONE', 'Cell Phone'),
        ('BRACELET', 'Bracelet'),
        ('MISBEHAVIOR', 'Misbehavior'),
        ('DRUG_USAGE', 'Drug Usage'),
        ('ACCIDENT', 'Accident'),
        ('FIGHTING_QUARREL', 'Fighting / Quarrel'),
        ('BIKE_RACING', 'Bike Racing'),
        ('EARRING', 'Earring'),
        ('OTHER_DEPT_ISSUES', 'Other Department Issues'),
        ('HOSTEL', 'Hostel'),
        ('TEASING', 'Teasing'),
        ('MALPRACTICE', 'Malpractice'),
        ('THEFT', 'Theft'),
        ('OTHERS', 'Others'),
    ]
    
    student = models.ForeignKey('Student', on_delete=models.CASCADE, related_name='remarks')
    staff = models.ForeignKey('staffs.Staff', on_delete=models.SET_NULL, null=True, related_name='given_remarks')
    remark_type = models.CharField(max_length=50, choices=REMARK_TYPE_CHOICES)
    custom_violation_text = models.CharField(max_length=200, blank=True, null=True, help_text="Custom violation text when 'Others' is selected")
    incident_date = models.DateField(help_text="Date when the incident occurred")
    description = models.TextField(blank=True, null=True, help_text="Additional notes or details about the incident")
    evidence_document = models.FileField(
        upload_to='ssm.upload_paths.student_remark_evidence_path',
        blank=True,
        null=True,
        help_text="Upload evidence (photo, document, etc.)"
    )
    apology_letter = models.FileField(
        upload_to='ssm.upload_paths.student_remark_apology_path',
        blank=True,
        null=True,
        help_text="Upload student's apology letter"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    parent_notified = models.BooleanField(default=False)
    notification_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        violation = self.custom_violation_text if self.remark_type == 'OTHERS' else self.get_remark_type_display()
        return f"{violation} - {self.student.student_name} ({self.created_at.strftime('%Y-%m-%d')})"




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
    student_email = models.EmailField(unique=True, blank=True, null=True)
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
    
    # Registration Flow Flags
    is_profile_complete = models.BooleanField(default=False)
    is_password_changed = models.BooleanField(default=False)

    def set_password(self, raw_password):
        """Hashes the raw password and sets it."""
        self.password = make_password(raw_password)
        self.save()

    def check_password(self, raw_password):
        """Checks if the raw password matches the hashed one."""
        return check_password(raw_password, self.password)

    def __str__(self):
        return f"{self.student_name} ({self.roll_number})"

class StudentGenerator(Student):
    class Meta:
        proxy = True
        verbose_name = "Generate Students"
        verbose_name_plural = "Generate Students"


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
    parent_email = models.EmailField(blank=True, null=True)
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
    student_photo = models.ImageField(
        upload_to=student_photo_path,
        blank=True,
        null=True,
        validators=[validate_file_size]
    )
    student_id_card = models.FileField(
        upload_to=student_id_card_path,
        blank=True,
        null=True,
        validators=[validate_file_size]
    )
    community_certificate = models.FileField(
        upload_to=community_certificate_path,
        blank=True,
        null=True,
        validators=[validate_file_size]
    )
    aadhaar_card = models.FileField(
        upload_to=aadhaar_card_path,
        blank=True,
        null=True,
        validators=[validate_file_size]
    )
    first_graduate_certificate = models.FileField(
        upload_to=first_graduate_certificate_path,
        blank=True,
        null=True,
        validators=[validate_file_size]
    )
    sslc_marksheet = models.FileField(
        upload_to=sslc_marksheet_path,
        blank=True,
        null=True,
        validators=[validate_file_size]
    )
    hsc_marksheet = models.FileField(
        upload_to=hsc_marksheet_path,
        blank=True,
        null=True,
        validators=[validate_file_size]
    )
    income_certificate = models.FileField(
        upload_to=income_certificate_path,
        blank=True,
        null=True,
        validators=[validate_file_size]
    )
    bank_passbook = models.FileField(
        upload_to=bank_passbook_path,
        blank=True,
        null=True,
        validators=[validate_file_size]
    )
    driving_license = models.FileField(
        upload_to=driving_license_path,
        blank=True,
        null=True,
        validators=[validate_file_size]
    )
    
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
    time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=[('Present', 'Present'), ('Absent', 'Absent')], default='Present')

    class Meta:
        unique_together = ('student', 'subject', 'date', 'time')

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
    document = models.FileField(
        upload_to=student_leave_document_path,
        blank=True,
        null=True,
        help_text="Required for Medical and OD"
    )
    
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='Pending Class Incharge')
    rejection_reason = models.TextField(blank=True, null=True)
    rejected_by = models.CharField(max_length=100, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.student.student_name} - {self.get_leave_type_display()} ({self.status})"


class StudentGPA(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='gpa_records')
    semester = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(8)])
    gpa = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(10.0)])
    total_credits = models.FloatField(default=0.0)
    subject_data = models.JSONField(blank=True, null=True, help_text="List of subjects with grades for editing")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'semester')
        ordering = ['semester']

    def __str__(self):
        return f"{self.student.student_name} - Sem {self.semester}: {self.gpa}"


class ResultScreenshot(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='result_screenshots')
    subject = models.ForeignKey('staffs.Subject', on_delete=models.CASCADE, related_name='result_screenshots')
    screenshot = models.ImageField(upload_to=result_screenshot_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"Result: {self.student.student_name} - {self.subject.code}"

class BonafideRequest(models.Model):
    STATUS_CHOICES = [
        ('Pending Office Approval', 'Pending Office Approval'), # Renamed from Pending HOD
        ('Approved by HOD', 'Approved by HOD'), # Legacy
        ('Waiting for HOD Sign', 'Waiting for HOD Sign'),
        ('Signed', 'Signed'),
        ('Ready for Collection', 'Ready for Collection'), # Legacy
        ('Collected', 'Collected'),
        ('Rejected', 'Rejected')
    ]
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='bonafide_requests')
    reason = models.TextField()
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='Pending Office Approval')
    rejection_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.student.student_name} - Bonafide ({self.status})"
