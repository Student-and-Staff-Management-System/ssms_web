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

