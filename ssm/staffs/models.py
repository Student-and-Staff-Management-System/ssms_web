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
    address = models.TextField(blank=True)

    # Professional Accomplishments (using TextField for flexibility)
    academic_details = models.TextField(blank=True, help_text="List your degrees and qualifications.")
    experience = models.TextField(blank=True, help_text="Describe your previous work experience.")
    publications = models.TextField(blank=True, help_text="List your key publications, one per line.")
    awards_and_memberships = models.TextField(blank=True, help_text="List any awards, honors, or professional memberships.")

    is_active = models.BooleanField(default=True)

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def __str__(self):
        return f"{self.salutation} {self.name}"

class Subject(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50) 
    semester = models.IntegerField(help_text="1-8")
    
    SUBJECT_Types = [
        ('Theory', 'Theory'),
        ('Lab', 'Lab'),
    ]
    subject_type = models.CharField(max_length=10, choices=SUBJECT_Types, default='Theory')
    
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
