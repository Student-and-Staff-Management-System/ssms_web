from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.contrib.auth.hashers import make_password, check_password
import datetime
from ssm.validators import validate_file_size
from ssm.upload_paths import (
    student_photo_path, student_id_card_path, community_certificate_path,
    aadhaar_card_path, first_graduate_certificate_path, sslc_marksheet_path,
    hsc_marksheet_path, income_certificate_path, bank_passbook_path,
    driving_license_path, student_leave_document_path, result_screenshot_path,
    scholar_admission_doc_path, scholar_zeroth_review_exam1_path,
    scholar_zeroth_review_exam2_path, scholar_rcw_document_path,
    tuition_fee_challan_path, hostel_fee_challan_path,
    ug_marksheet_path, pg_marksheet_path
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
BLOOD_GROUP_CHOICES = [
    ('O+', 'O+'),
    ('O-', 'O-'),
    ('A+', 'A+'),
    ('A-', 'A-'),
    ('B+', 'B+'),
    ('B-', 'B-'),
    ('AB+', 'AB+'),
    ('AB-', 'AB-'),
    ('A1+', 'A1+'),
    ('A1-', 'A1-'),
    ('A2+', 'A2+'),
    ('A2-', 'A2-'),
    ('A1B+', 'A1B+'),
    ('A1B-', 'A1B-'),
    ('A2B+', 'A2B+'),
    ('A2B-', 'A2B-'),
]

RELIGION_CHOICES = [('Hindu', 'Hindu'), ('Christian', 'Christian'), ('Muslim', 'Muslim')]
COMMUNITY_CHOICES = [('OC', 'OC'), ('BC', 'BC'), ('MBC', 'MBC'), ('SC', 'SC'), ('ST', 'ST'),('BC MUSLIM','BC MUSLIM')]

class Caste(models.Model):
    name = models.CharField(max_length=500, unique=True)

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
    lab_batch = models.CharField(max_length=1, choices=[('A', 'Batch A'), ('B', 'Batch B')], blank=True, null=True)
    is_class_representative = models.BooleanField(default=False, verbose_name="Class Representative")
    
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

    @property
    def phd_overall_percent(self):
        try:
            if hasattr(self, 'phd_progress') and self.phd_progress:
                return self.phd_progress.progress_stats.get('overall_percent', 0)
        except Exception:
            pass
        return 0

    @property
    def phd_stage_label(self):
        try:
            if hasattr(self, 'phd_progress') and self.phd_progress:
                return self.phd_progress.get_current_stage_display()
        except Exception:
            pass
        return "RAC REVIEW"

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
    caste_other = models.CharField(max_length=500, blank=True, null=True)
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
    is_hosteler = models.BooleanField(default=False)

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
    sslc_board = models.CharField(max_length=150, blank=True)
    hsc_register_number = models.CharField(max_length=50, blank=True)
    hsc_percentage = models.FloatField(blank=True, null=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    hsc_year_of_passing = models.CharField(max_length=4, choices=get_year_choices(), blank=True)
    hsc_school_name = models.CharField(max_length=255, blank=True)
    hsc_board = models.CharField(max_length=150, blank=True)
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
    ug_college_name = models.CharField(max_length=255, blank=True)
    ug_college_address = models.TextField(blank=True)
    ug_university = models.CharField(max_length=255, blank=True)
    ug_ogpa = models.FloatField(blank=True, null=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    ug_year_of_passing = models.CharField(max_length=4, choices=get_year_choices(), blank=True)

class PGDetails(models.Model):
    student = models.OneToOneField(Student, on_delete=models.CASCADE, primary_key=True)
    pg_course = models.CharField(max_length=100, blank=True)
    pg_college_name = models.CharField(max_length=255, blank=True)
    pg_college_address = models.TextField(blank=True)
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
    is_7_5_reservation = models.BooleanField(default=False)

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
    ug_marksheet = models.FileField(
        upload_to=ug_marksheet_path,
        blank=True,
        null=True,
        validators=[validate_file_size]
    )
    pg_marksheet = models.FileField(
        upload_to=pg_marksheet_path,
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

class FeeChallanRecord(models.Model):
    YEAR_CHOICES = [
        (1, 'Year 1'),
        (2, 'Year 2'),
        (3, 'Year 3'),
        (4, 'Year 4'),
    ]
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='fee_challans')
    academic_year = models.IntegerField(choices=YEAR_CHOICES)
    is_hosteler = models.BooleanField(default=False)
    tuition_fee_challan = models.FileField(
        upload_to=tuition_fee_challan_path,
        blank=True,
        null=True,
        validators=[validate_file_size]
    )
    hostel_fee_challan = models.FileField(
        upload_to=hostel_fee_challan_path,
        blank=True,
        null=True,
        validators=[validate_file_size]
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'academic_year')
        ordering = ['student', 'academic_year']

    def __str__(self):
        return f"{self.student.student_name} - Year {self.academic_year}"

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
        ('Pending Guide', 'Pending Guide'),
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

class ScholarAttendance(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected')
    ]
    scholar = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='scholar_attendance')
    date = models.DateField(default=datetime.date.today)
    time_marked = models.TimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    rejection_reason = models.TextField(blank=True, null=True)
    
    class Meta:
        unique_together = ('scholar', 'date')
        ordering = ['-date', '-time_marked']

    def __str__(self):
        return f"{self.scholar.student_name} - {self.date} ({self.status})"


class ResearchScholarProfile(models.Model):
    SCHOLAR_TYPE_CHOICES = [
        ('Full Time', 'Full Time'),
        ('Part Time Internal', 'Part Time Internal'),
        ('Part Time External', 'Part Time External'),
    ]

    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name='scholar_profile')
    scholar_type = models.CharField(max_length=50, choices=SCHOLAR_TYPE_CHOICES)
    admission_date = models.DateField()
    admission_order_doc = models.FileField(
        upload_to=scholar_admission_doc_path, 
        blank=True, 
        null=True,
        validators=[validate_file_size]
    )
    supervisor = models.ForeignKey(
        'staffs.Staff', 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='supervised_scholars'
    )
    status = models.CharField(max_length=20, choices=[('Ongoing', 'Ongoing'), ('Completed', 'Completed')], default='Ongoing')
    completion_year = models.CharField(max_length=10, blank=True, null=True)
    is_visvesvaraya_scheme = models.BooleanField(default=False)

    def __str__(self):
        return f"Scholar Profile - {self.student.student_name}"

class RACMember(models.Model):
    MEMBER_TYPE_CHOICES = [
        ('Internal', 'Intra Department'),
        ('External', 'Inter Department'),
    ]

    scholar = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='rac_members')
    member_type = models.CharField(max_length=20, choices=MEMBER_TYPE_CHOICES)
    
    # Internal Member (Same Department)
    staff = models.ForeignKey(
        'staffs.Staff', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='rac_memberships'
    )
    
    # External Member (Other Department)
    external_name = models.CharField(max_length=255, blank=True)
    external_designation = models.CharField(max_length=255, blank=True)
    external_department = models.CharField(max_length=255, blank=True)

    def __str__(self):
        if self.member_type == 'Internal' and self.staff:
            return f"Internal: {self.staff.name}"
        return f"External: {self.external_name} ({self.external_department})"

class ZerothReview(models.Model):
    scholar = models.OneToOneField(Student, on_delete=models.CASCADE, related_name='zeroth_review')
    tentative_title = models.CharField(max_length=500, blank=True)
    
    # Course Works
    rcw001_subject = models.CharField(max_length=255, blank=True)
    rcw002_subject = models.CharField(max_length=255, blank=True)
    rcw003_subject = models.CharField(max_length=255, blank=True)
    rcw004_subject = models.CharField(max_length=255, blank=True)

    exam1_marksheet = models.FileField(
        upload_to=scholar_zeroth_review_exam1_path, 
        blank=True, 
        null=True,
        validators=[validate_file_size],
        help_text="Upload marksheet for RCW001 and RCW002"
    )
    exam2_marksheet = models.FileField(
        upload_to=scholar_zeroth_review_exam2_path, 
        blank=True, 
        null=True,
        validators=[validate_file_size],
        help_text="Upload marksheet for RCW003 and RCW004"
    )

    def __str__(self):
        return f"Zeroth Review - {self.scholar.student_name}"

class RCWReview(models.Model):
    scholar = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='rcw_reviews')
    date = models.DateField()
    time = models.TimeField()
    progress = models.TextField()
    document = models.FileField(
        upload_to=scholar_rcw_document_path, 
        blank=True, 
        null=True,
        validators=[validate_file_size]
    )
    is_final = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date', 'time']

    def __str__(self):
        return f"RCW Review - {self.scholar.student_name} on {self.date}"


def phd_progress_doc_path(instance, filename):
    ext = filename.split('.')[-1]
    import uuid
    unique_id = uuid.uuid4().hex[:8]
    return f'students/{instance.scholar.roll_number}/phd_stages/{unique_id}_{filename}'


class PhDProgress(models.Model):
    CURRENT_STAGE_CHOICES = [
        ('RAC_REVIEW', 'RAC Review'),
        ('PRE_SUBMISSION', 'Pre-Submission'),
        ('SYNOPSIS', 'Synopsis'),
        ('THESIS_SUBMISSION', 'Thesis Submission'),
        ('THESIS_HARDBOUND', 'Thesis Hardbound'),
        ('VIVA_VOCE', 'Viva Voce'),
        ('MEMO', 'Memo'),
        ('PROVISIONAL', 'Provisional'),
        ('DEGREE', 'Degree'),
        ('COMPLETED', 'Completed'),
    ]

    scholar = models.OneToOneField(Student, on_delete=models.CASCADE, related_name='phd_progress')
    current_stage = models.CharField(max_length=50, choices=CURRENT_STAGE_CHOICES, default='RAC_REVIEW')
    
    # Stage Completion timestamps (acts as start date of next stage too)
    rac_completed_at = models.DateTimeField(null=True, blank=True)
    pre_submission_started_at = models.DateTimeField(null=True, blank=True)
    pre_submission_completed_at = models.DateTimeField(null=True, blank=True)
    
    synopsis_started_at = models.DateTimeField(null=True, blank=True)
    synopsis_completed_at = models.DateTimeField(null=True, blank=True)
    
    thesis_started_at = models.DateTimeField(null=True, blank=True)
    thesis_completed_at = models.DateTimeField(null=True, blank=True)
    
    thesis_hardbound_started_at = models.DateTimeField(null=True, blank=True)
    thesis_hardbound_completed_at = models.DateTimeField(null=True, blank=True)
    
    viva_voce_started_at = models.DateTimeField(null=True, blank=True)
    viva_voce_completed_at = models.DateTimeField(null=True, blank=True)
    
    memo_started_at = models.DateTimeField(null=True, blank=True)
    memo_completed_at = models.DateTimeField(null=True, blank=True)
    
    provisional_started_at = models.DateTimeField(null=True, blank=True)
    provisional_completed_at = models.DateTimeField(null=True, blank=True)
    
    degree_started_at = models.DateTimeField(null=True, blank=True)
    degree_completed_at = models.DateTimeField(null=True, blank=True)

    # --- STAGE 2: PRE-SUBMISSION DOCUMENTS
    pre_sub_letter = models.FileField(upload_to=phd_progress_doc_path, null=True, blank=True, validators=[validate_file_size])
    pre_sub_attendance = models.FileField(upload_to=phd_progress_doc_path, null=True, blank=True, validators=[validate_file_size])
    pre_sub_circular = models.FileField(upload_to=phd_progress_doc_path, null=True, blank=True, validators=[validate_file_size])
    
    # --- STAGE 3: SYNOPSIS
    synopsis_letter_copies = models.FileField(upload_to=phd_progress_doc_path, null=True, blank=True, validators=[validate_file_size])
    synopsis_copy = models.FileField(upload_to=phd_progress_doc_path, null=True, blank=True, validators=[validate_file_size])
    # Staff upload reference only
    synopsis_panel_of_examiner = models.FileField(upload_to=phd_progress_doc_path, null=True, blank=True, validators=[validate_file_size])
    synopsis_foreign_examiner = models.FileField(upload_to=phd_progress_doc_path, null=True, blank=True, validators=[validate_file_size])
    synopsis_indian_examiner = models.FileField(upload_to=phd_progress_doc_path, null=True, blank=True, validators=[validate_file_size])
    
    # --- STAGE 4: THESIS SUBMISSION
    thesis_letter_docs = models.FileField(upload_to=phd_progress_doc_path, null=True, blank=True, validators=[validate_file_size])
    thesis_copy_file = models.FileField(upload_to=phd_progress_doc_path, null=True, blank=True, validators=[validate_file_size])
    thesis_plagiarism_docs = models.FileField(upload_to=phd_progress_doc_path, null=True, blank=True, validators=[validate_file_size])
    
    # --- STAGE 5: THESIS HARDBOUND
    hardbound_letters_with_corrections = models.FileField(upload_to=phd_progress_doc_path, null=True, blank=True, validators=[validate_file_size])
    hardbound_final_thesis = models.FileField(upload_to=phd_progress_doc_path, null=True, blank=True, validators=[validate_file_size])
    # Staff upload, visible to student
    hardbound_examiner_report = models.FileField(upload_to=phd_progress_doc_path, null=True, blank=True, validators=[validate_file_size])
    
    # --- STAGE 6: VIVA VOCE
    viva_date = models.DateField(null=True, blank=True)
    viva_time = models.TimeField(null=True, blank=True)
    # Staff uploads
    viva_fixation = models.FileField(upload_to=phd_progress_doc_path, null=True, blank=True, validators=[validate_file_size])
    viva_student_order = models.FileField(upload_to=phd_progress_doc_path, null=True, blank=True, validators=[validate_file_size]) # visible to student
    viva_internal_order = models.FileField(upload_to=phd_progress_doc_path, null=True, blank=True, validators=[validate_file_size]) # hidden from student
    viva_external_order = models.FileField(upload_to=phd_progress_doc_path, null=True, blank=True, validators=[validate_file_size]) # hidden from student
    # Student uploads
    viva_circular = models.FileField(upload_to=phd_progress_doc_path, null=True, blank=True, validators=[validate_file_size])
    viva_letter_attendance = models.FileField(upload_to=phd_progress_doc_path, null=True, blank=True, validators=[validate_file_size])
    
    # --- STAGE 7: MEMO
    memo_copy = models.FileField(upload_to=phd_progress_doc_path, null=True, blank=True, validators=[validate_file_size])
    
    # --- STAGE 8: PROVISIONAL
    provisional_challan = models.FileField(upload_to=phd_progress_doc_path, null=True, blank=True, validators=[validate_file_size])
    provisional_doc = models.FileField(upload_to=phd_progress_doc_path, null=True, blank=True, validators=[validate_file_size])
    
    # --- STAGE 9: DEGREE
    degree_challan = models.FileField(upload_to=phd_progress_doc_path, null=True, blank=True, validators=[validate_file_size])
    degree_doc = models.FileField(upload_to=phd_progress_doc_path, null=True, blank=True, validators=[validate_file_size])

    def __str__(self):
        return f"PhD Progress - {self.scholar.student_name} ({self.current_stage})"

    def check_and_advance_stage(self):
        """Automatically transitions to the next stage when all requirements of the current stage are met."""
        from django.utils import timezone
        now = timezone.now()
        updated = False

        if self.current_stage == 'RAC_REVIEW':
            if self.scholar.rcw_reviews.filter(is_final=True).exists():
                self.current_stage = 'PRE_SUBMISSION'
                self.rac_completed_at = now
                self.pre_submission_started_at = now
                updated = True
        elif self.current_stage == 'PRE_SUBMISSION':
            if self.pre_sub_letter and self.pre_sub_attendance and self.pre_sub_circular:
                self.current_stage = 'SYNOPSIS'
                self.pre_submission_completed_at = now
                self.synopsis_started_at = now
                updated = True
        elif self.current_stage == 'SYNOPSIS':
            if (self.synopsis_letter_copies and self.synopsis_copy and 
                self.synopsis_panel_of_examiner and self.synopsis_foreign_examiner and self.synopsis_indian_examiner):
                self.current_stage = 'THESIS_SUBMISSION'
                self.synopsis_completed_at = now
                self.thesis_started_at = now
                updated = True
        elif self.current_stage == 'THESIS_SUBMISSION':
            if self.thesis_letter_docs and self.thesis_copy_file and self.thesis_plagiarism_docs:
                self.current_stage = 'THESIS_HARDBOUND'
                self.thesis_completed_at = now
                self.thesis_hardbound_started_at = now
                updated = True
        elif self.current_stage == 'THESIS_HARDBOUND':
            if self.hardbound_letters_with_corrections and self.hardbound_final_thesis and self.hardbound_examiner_report:
                self.current_stage = 'VIVA_VOCE'
                self.thesis_hardbound_completed_at = now
                self.viva_voce_started_at = now
                updated = True
        elif self.current_stage == 'VIVA_VOCE':
            if (self.viva_date and self.viva_time and self.viva_fixation and 
                self.viva_student_order and self.viva_internal_order and self.viva_external_order and 
                self.viva_circular and self.viva_letter_attendance):
                self.current_stage = 'MEMO'
                self.viva_voce_completed_at = now
                self.memo_started_at = now
                updated = True
        elif self.current_stage == 'MEMO':
            if self.memo_copy:
                self.current_stage = 'PROVISIONAL'
                self.memo_completed_at = now
                self.provisional_started_at = now
                updated = True
        elif self.current_stage == 'PROVISIONAL':
            if self.provisional_challan and self.provisional_doc:
                self.current_stage = 'DEGREE'
                self.provisional_completed_at = now
                self.degree_started_at = now
                updated = True
        elif self.current_stage == 'DEGREE':
            if self.degree_challan and self.degree_doc:
                self.current_stage = 'COMPLETED'
                self.degree_completed_at = now
                updated = True
                
                # Update status in ResearchScholarProfile
                profile = getattr(self.scholar, 'scholar_profile', None)
                if profile:
                    profile.status = 'Completed'
                    profile.completion_year = str(now.year)
                    profile.save()

        if updated:
            self.save()
            # Recursive check in case multiple stages unlock instantly (e.g. if files were pre-set in db)
            self.check_and_advance_stage()

    @property
    def current_deadline_info(self):
        """Calculates days remaining, expiration status, and warning class for deadlines."""
        import datetime
        today = datetime.date.today()

        if self.current_stage == 'SYNOPSIS' and self.pre_submission_completed_at:
            start_date = self.pre_submission_completed_at.date()
            deadline = start_date + datetime.timedelta(days=160)
            days_remaining = (deadline - today).days
            is_expired = days_remaining < 0
            status_class = 'danger' if is_expired else ('warning' if days_remaining <= 10 else 'success')
            return {
                'has_deadline': True,
                'days_remaining': abs(days_remaining),
                'is_expired': is_expired,
                'status_class': status_class,
                'deadline_date': deadline,
            }
        elif self.current_stage == 'THESIS_SUBMISSION' and self.synopsis_completed_at:
            start_date = self.synopsis_completed_at.date()
            deadline = start_date + datetime.timedelta(days=120)  # 4 months = 120 days
            days_remaining = (deadline - today).days
            is_expired = days_remaining < 0
            status_class = 'danger' if is_expired else ('warning' if days_remaining <= 10 else 'success')
            return {
                'has_deadline': True,
                'days_remaining': abs(days_remaining),
                'is_expired': is_expired,
                'status_class': status_class,
                'deadline_date': deadline,
            }
        elif self.current_stage == 'THESIS_HARDBOUND' and self.thesis_completed_at:
            start_date = self.thesis_completed_at.date()
            deadline = start_date + datetime.timedelta(days=15)
            days_remaining = (deadline - today).days
            is_expired = days_remaining < 0
            status_class = 'danger' if is_expired else ('warning' if days_remaining <= 3 else 'success')
            return {
                'has_deadline': True,
                'days_remaining': abs(days_remaining),
                'is_expired': is_expired,
                'status_class': status_class,
                'deadline_date': deadline,
            }

        return {
            'has_deadline': False,
            'days_remaining': 0,
            'is_expired': False,
            'status_class': 'success',
            'deadline_date': None,
        }

    @property
    def progress_stats(self):
        """Computes stage-wise completion rates and completion dates."""
        stages_ordered = [
            ('RAC_REVIEW', 'rac_completed_at'),
            ('PRE_SUBMISSION', 'pre_submission_completed_at'),
            ('SYNOPSIS', 'synopsis_completed_at'),
            ('THESIS_SUBMISSION', 'thesis_completed_at'),
            ('THESIS_HARDBOUND', 'thesis_hardbound_completed_at'),
            ('VIVA_VOCE', 'viva_voce_completed_at'),
            ('MEMO', 'memo_completed_at'),
            ('PROVISIONAL', 'provisional_completed_at'),
            ('DEGREE', 'degree_completed_at'),
        ]
        
        # Calculate overall progress
        completed_count = 0
        if self.current_stage == 'COMPLETED':
            completed_count = len(stages_ordered)
        else:
            for s_name, _ in stages_ordered:
                if self.current_stage == s_name:
                    break
                completed_count += 1

        overall_percent = int((completed_count / len(stages_ordered)) * 100)

        # Calculate stage-wise progress
        stage_uploaded = 0
        stage_total = 1

        if self.current_stage == 'RAC_REVIEW':
            stage_uploaded = 1 if self.rac_completed_at else 0
            stage_total = 1
        elif self.current_stage == 'PRE_SUBMISSION':
            stage_uploaded = sum(1 for f in [self.pre_sub_letter, self.pre_sub_attendance, self.pre_sub_circular] if f)
            stage_total = 3
        elif self.current_stage == 'SYNOPSIS':
            stage_uploaded = sum(1 for f in [self.synopsis_letter_copies, self.synopsis_copy, self.synopsis_panel_of_examiner, self.synopsis_foreign_examiner, self.synopsis_indian_examiner] if f)
            stage_total = 5
        elif self.current_stage == 'THESIS_SUBMISSION':
            stage_uploaded = sum(1 for f in [self.thesis_letter_docs, self.thesis_copy_file, self.thesis_plagiarism_docs] if f)
            stage_total = 3
        elif self.current_stage == 'THESIS_HARDBOUND':
            stage_uploaded = sum(1 for f in [self.hardbound_letters_with_corrections, self.hardbound_final_thesis, self.hardbound_examiner_report] if f)
            stage_total = 3
        elif self.current_stage == 'VIVA_VOCE':
            stage_uploaded = sum(1 for f in [self.viva_date, self.viva_time, self.viva_fixation, self.viva_student_order, self.viva_internal_order, self.viva_external_order, self.viva_circular, self.viva_letter_attendance] if f)
            stage_total = 8
        elif self.current_stage == 'MEMO':
            stage_uploaded = 1 if self.memo_copy else 0
            stage_total = 1
        elif self.current_stage == 'PROVISIONAL':
            stage_uploaded = sum(1 for f in [self.provisional_challan, self.provisional_doc] if f)
            stage_total = 2
        elif self.current_stage == 'DEGREE':
            stage_uploaded = sum(1 for f in [self.degree_challan, self.degree_doc] if f)
            stage_total = 2
        elif self.current_stage == 'COMPLETED':
            stage_uploaded = 1
            stage_total = 1

        stage_percent = int((stage_uploaded / stage_total) * 100)

        # Stage dates mapping
        completion_dates = {}
        for s_name, date_field in stages_ordered:
            val = getattr(self, date_field, None)
            if val:
                # Store string representation of the date
                completion_dates[s_name] = val.strftime('%d-%m-%Y')

        # Determine unlocked/reached stages
        stage_names_only = [s[0] for s in stages_ordered] + ['COMPLETED']
        try:
            curr_idx = stage_names_only.index(self.current_stage)
        except ValueError:
            curr_idx = 0
        unlocked_stages = {s: (stage_names_only.index(s) <= curr_idx) for s in stage_names_only}

        return {
            'overall_percent': overall_percent,
            'stage_percent': stage_percent,
            'completed_count': completed_count,
            'total_stages': len(stages_ordered),
            'completion_dates': completion_dates,
            'unlocked_stages': unlocked_stages,
        }

