from django.db import models
from django.contrib.auth.hashers import make_password, check_password

class Staff(models.Model):
    # Basic Info
    staff_id = models.CharField(max_length=50, primary_key=True)
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128) # Stores the hashed password
    photo = models.ImageField(upload_to='staff_photos/', blank=True, null=True)

    # Professional Details
    salutation = models.CharField(max_length=10, choices=[('Dr.', 'Dr.'), ('Prof.', 'Prof.'), ('Mr.', 'Mr.'), ('Ms.', 'Ms.')])
    designation = models.CharField(max_length=100)
    department = models.CharField(max_length=100, default="Information Technology")
    qualification = models.CharField(max_length=255)
    specialization = models.CharField(max_length=255)
    
    ROLE_CHOICES = [
        ('HOD', 'HOD'),
        ('Class Incharge', 'Class Incharge'),
        ('Course Incharge', 'Course Incharge'),
    ]
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='HOD')
    assigned_semester = models.IntegerField(null=True, blank=True, help_text="For Class Incharge: Specify which semester they manage (1-8).")
    
    # Personal & Employment Dates
    date_of_birth = models.DateField(null=True, blank=True)
    date_of_joining = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')], null=True, blank=True)
    blood_group = models.CharField(max_length=5, null=True, blank=True)
    mobile_number = models.CharField(max_length=15, null=True, blank=True)
    address = models.TextField(blank=True)

    # Professional Accomplishments (using TextField for flexibility)
    academic_details = models.TextField(blank=True, help_text="List your degrees and qualifications.")
    experience = models.TextField(blank=True, help_text="Describe your previous work experience.")
    publications = models.TextField(blank=True, help_text="List your key publications, one per line.")
    seminars = models.TextField(blank=True, help_text="List seminars, workshops, and conferences.")
    awards_and_memberships = models.TextField(blank=True, help_text="List any awards, honors, or professional memberships.")
    pg_students_guided = models.PositiveIntegerField(default=0, blank=True, help_text="Number of PG (Postgraduate) students guided.")
    pg_students_guided = models.PositiveIntegerField(default=0, blank=True, help_text="Number of PG (Postgraduate) students guided.")
    phd_students_guided = models.PositiveIntegerField(default=0, blank=True, help_text="Number of PhD students guided.")

    # Research & Social
    research_interests = models.TextField(blank=True, help_text="Comma-separated list of research interests.")
    google_scholar_link = models.URLField(blank=True, null=True)
    linkedin_link = models.URLField(blank=True, null=True)
    orcid_link = models.URLField(blank=True, null=True)
    research_gate_link = models.URLField(blank=True, null=True)

    is_active = models.BooleanField(default=True)

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def __str__(self):
        return f"{self.salutation} {self.name}"


class StaffPublication(models.Model):
    """Individual publication entry for staff."""
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='publication_list')
    title = models.CharField(max_length=500)
    venue_or_journal = models.CharField(max_length=300, blank=True)
    year = models.CharField(max_length=20, blank=True)
    PUB_TYPE_CHOICES = [
        ('Journal', 'Journal'),
        ('Conference', 'Conference'),
        ('Book', 'Book'),
        ('Book Chapter', 'Book Chapter'),
        ('Other', 'Other'),
    ]
    pub_type = models.CharField(max_length=20, choices=PUB_TYPE_CHOICES, default='Journal')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-order', '-year', 'title']

    def __str__(self):
        return f"{self.title} ({self.year})"


class StaffAwardHonour(models.Model):
    """Individual award, honour, or membership entry."""
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='award_list')
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    year = models.CharField(max_length=20, blank=True)
    CATEGORY_CHOICES = [
        ('Award', 'Award'),
        ('Honour', 'Honour'),
        ('Membership', 'Membership'),
    ]
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='Award')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-order', '-year', 'title']

    def __str__(self):
        return f"{self.title} ({self.category})"


class StaffSeminar(models.Model):
    """Seminar, workshop, or conference entry."""
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='seminar_list')
    title = models.CharField(max_length=400)
    EVENT_TYPE_CHOICES = [
        ('Seminar', 'Seminar'),
        ('Workshop', 'Workshop'),
        ('Conference', 'Conference'),
    ]
    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES, default='Seminar')
    venue_or_description = models.CharField(max_length=300, blank=True)
    year = models.CharField(max_length=20, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-order', '-year', 'title']

    def __str__(self):
        return f"{self.title} ({self.event_type})"


class StaffStudentGuided(models.Model):
    """PG or PhD student guided by staff."""
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='student_guided_list')
    student_name = models.CharField(max_length=255)
    degree_type = models.CharField(max_length=10, choices=[('PG', 'PG'), ('PhD', 'PhD')])
    status = models.CharField(max_length=20, choices=[('Ongoing', 'Ongoing'), ('Completed', 'Completed')], default='Ongoing')
    year = models.CharField(max_length=20, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-order', 'degree_type', 'student_name']

    def __str__(self):
        return f"{self.student_name} ({self.degree_type})"


class Subject(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50) 
    semester = models.IntegerField(help_text="1-8")
    
    SUBJECT_Types = [
        ('Theory', 'Theory'),
        ('Lab', 'Lab'),
    ]
    subject_type = models.CharField(max_length=10, choices=SUBJECT_Types, default='Theory')
    credits = models.IntegerField(default=3, help_text="Credit points for this subject")
    
    staff = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True, blank=True, related_name='subjects')
    
    def __str__(self):
        return f"{self.code} - {self.name} (Sem {self.semester})"

class ExamSchedule(models.Model):
    semester = models.IntegerField()
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    date = models.DateField()
    session = models.CharField(max_length=2, choices=[('FN', 'Forenoon'), ('AN', 'Afternoon')])
    time = models.CharField(max_length=50, blank=True) # e.g. "10:00 AM - 01:00 PM"

    class Meta:
        ordering = ['date', 'session']

    def __str__(self):
        return f"Sem {self.semester} - {self.subject.code}"

class Timetable(models.Model):
    DAYS_OF_WEEK = [
        ('Monday', 'Monday'),
        ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'),
        ('Friday', 'Friday'),
    ]
    semester = models.IntegerField()
    day = models.CharField(max_length=10, choices=DAYS_OF_WEEK)
    period = models.IntegerField(help_text="1 to 7")
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True)
    staff = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True, blank=True) # Optional: Assign staff directly

    class Meta:
        ordering = ['semester', 'day', 'period']
        unique_together = ('semester', 'day', 'period')

    def __str__(self):
        return f"Sem {self.semester} - {self.day} - Period {self.period}"

class StaffLeaveRequest(models.Model):
    LEAVE_TYPES = [
        ('CL', 'Casual Leave (CL)'),
        ('Religious', 'Religious Holiday'),
        ('Medical', 'Medical Leave'),
        ('Earned', 'Earned Leave'),
        ('OD', 'On Other Duty'),
        ('Special', 'Special Casual Leave'),
    ]
    
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]
    
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='leave_requests')
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPES)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    document = models.FileField(upload_to='leave_docs/', blank=True, null=True, help_text="Required for Medical Leave and On Other Duty")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    rejection_reason = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.staff.name} - {self.get_leave_type_display()} ({self.status})"

class News(models.Model):
    TARGET_CHOICES = [
        ('All', 'All'),
        ('Staff', 'Staff Only'),
        ('Student', 'Student Only'),
    ]
    
    content = models.TextField()
    link = models.URLField(blank=True, null=True, help_text="Optional link to external resource")
    date = models.DateTimeField(auto_now_add=True)
    target = models.CharField(max_length=20, choices=TARGET_CHOICES, default='All')
    start_date = models.DateField(null=True, blank=True, help_text="Date when this announcement should start showing")
    end_date = models.DateField(null=True, blank=True, help_text="Date when this announcement should stop showing")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-date']
        verbose_name_plural = "News & Announcements"

    def __str__(self):
        return f"{self.date} - {self.target}: {self.content[:30]}..."


class AuditLog(models.Model):
    """Stores audit trail for admin and application actions (logins, edits, etc.)."""
    ACTION_CHOICES = [
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('view', 'View'),
        ('other', 'Other'),
    ]
    ACTOR_TYPE_CHOICES = [
        ('admin', 'Admin'),
        ('staff', 'Staff'),
        ('student', 'Student'),
        ('system', 'System'),
    ]
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, default='other', db_index=True)
    actor_type = models.CharField(max_length=20, choices=ACTOR_TYPE_CHOICES, blank=True)
    actor_id = models.CharField(max_length=100, blank=True, help_text="Staff ID, roll no, or username")
    actor_name = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    object_type = models.CharField(max_length=100, blank=True, help_text="e.g. Staff, Student, News")
    object_id = models.CharField(max_length=100, blank=True)
    message = models.TextField(blank=True)
    extra_data = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audits / Logs'

    def __str__(self):
        return f"{self.timestamp} | {self.get_action_display()} | {self.actor_type}:{self.actor_id or '—'} | {self.message[:50] or '—'}"


class ConferenceParticipation(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='conferences')
    national_international = models.CharField(max_length=20, choices=[('National', 'National'), ('International', 'International')], default='National')
    author_name = models.CharField(max_length=255)
    year_of_publication = models.CharField(max_length=20, blank=True)
    title_of_paper = models.CharField(max_length=500)
    title_of_proceedings = models.CharField(max_length=500, blank=True)
    date_from = models.DateField(null=True, blank=True)
    date_to = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=255, blank=True)
    page_numbers_from = models.CharField(max_length=50, blank=True)
    page_numbers_to = models.CharField(max_length=50, blank=True)
    place_of_publication = models.CharField(max_length=255, blank=True)
    publisher_proceedings = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title_of_paper} ({self.year_of_publication})"

class JournalPublication(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='journals')
    national_international = models.CharField(max_length=20, choices=[('National', 'National'), ('International', 'International')], default='National')
    published_month = models.CharField(max_length=20, blank=True)
    published_year = models.CharField(max_length=20, blank=True)
    author_name = models.CharField(max_length=255)
    title_of_paper = models.CharField(max_length=500)
    journal_name = models.CharField(max_length=500)
    volume_number = models.CharField(max_length=50, blank=True)
    issue_number = models.CharField(max_length=50, blank=True)
    year_of_publication_doi = models.CharField(max_length=255, blank=True)
    page_numbers_from = models.CharField(max_length=50, blank=True)
    page_numbers_to = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title_of_paper} - {self.journal_name}"

class BookPublication(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='books')
    type = models.CharField(max_length=20, choices=[('Book', 'Book'), ('Popular Article', 'Popular Article')], default='Book')
    author_name = models.CharField(max_length=255)
    title_of_book = models.CharField(max_length=500)
    publisher_name = models.CharField(max_length=255, blank=True)
    publisher_address = models.TextField(blank=True)
    isbn_issn_number = models.CharField(max_length=100, blank=True)
    page_numbers_from = models.CharField(max_length=50, blank=True)
    page_numbers_to = models.CharField(max_length=50, blank=True)
    month_of_publication = models.CharField(max_length=20, blank=True)
    year_of_publication = models.CharField(max_length=20, blank=True)
    url_address = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title_of_book} ({self.type})"

