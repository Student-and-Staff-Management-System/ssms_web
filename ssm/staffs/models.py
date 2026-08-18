from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from ssm.validators import validate_file_size
from ssm.upload_paths import (
    staff_photo_path, staff_award_document_path, staff_seminar_document_path,
    staff_student_guided_document_path, staff_leave_document_path,
    staff_conference_document_path, staff_journal_document_path,
    staff_book_document_path, staff_patent_document_path, news_documents_path,
    staff_qualification_document_path, staff_designation_document_path,
    staff_seminar_order_path, staff_joining_order_path, 
    staff_appointment_order_path, staff_board_order_path, 
    staff_joining_letter_path, staff_sslc_marksheet_path, staff_hsc_marksheet_path, staff_student_guided_thesis_path,
    staff_student_guided_papers_path, staff_research_project_path
)


class Staff(models.Model):
    # Basic Info
    staff_id = models.CharField(max_length=50, primary_key=True)
    name = models.CharField(max_length=255)
    initial = models.CharField(max_length=50, blank=True)
    email = models.EmailField(unique=True, blank=True, null=True)
    password = models.CharField(max_length=128) # Stores the hashed password
    photo = models.ImageField(
        upload_to=staff_photo_path,
        blank=True,
        null=True,
        validators=[validate_file_size]
    )

    # Professional Details
    salutation = models.CharField(max_length=10, choices=[('Dr.', 'Dr.'), ('Prof.', 'Prof.'), ('Mr.', 'Mr.'), ('Ms.', 'Ms.')], blank=True)
    designation = models.CharField(max_length=100, blank=True)
    additional_designation = models.CharField(max_length=100, blank=True, null=True)
    department = models.CharField(max_length=100, default="Information Technology")
    qualification = models.CharField(max_length=255, blank=True)
    specialization = models.CharField(max_length=255, blank=True)
    
    ROLE_CHOICES = [
        ('Teaching Staff', (
            ('HOD', 'HOD'),
            ('Class Incharge', 'Class Incharge'),
            ('Course Incharge', 'Course Incharge'),
            ('Scholarship Officer', 'Scholarship Officer'),
            ('Placement Officer', 'Placement Officer'),
        )),
        ('Non-Teaching Staff', (
            ('Office Staff', 'Office Staff'),
            ('Technical Officer', 'Technical Officer'),
        )),
    ]
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='Course Incharge')
    secondary_roles = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Comma-separated secondary roles (e.g. 'Class Incharge, Scholarship Officer')."
    )
    assigned_semester = models.IntegerField(null=True, blank=True, help_text="For Class Incharge: Specify which semester they manage (1-8).")
    
    # Personal & Employment Dates
    date_of_birth = models.DateField(null=True, blank=True)
    date_of_joining = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')], null=True, blank=True)
    blood_group = models.CharField(max_length=5, null=True, blank=True)
    mobile_number = models.CharField(max_length=15, null=True, blank=True)
    address = models.TextField(blank=True)
    joining_order = models.FileField(upload_to=staff_joining_order_path, blank=True, null=True, validators=[validate_file_size])
    appointment_order = models.FileField(upload_to=staff_appointment_order_path, blank=True, null=True, validators=[validate_file_size])
    board_order = models.FileField(upload_to=staff_board_order_path, blank=True, null=True, validators=[validate_file_size])
    joining_letter = models.FileField(upload_to=staff_joining_letter_path, blank=True, null=True, validators=[validate_file_size])
    sslc_marksheet = models.FileField(upload_to=staff_sslc_marksheet_path, blank=True, null=True, validators=[validate_file_size])
    hsc_marksheet = models.FileField(upload_to=staff_hsc_marksheet_path, blank=True, null=True, validators=[validate_file_size])

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
    is_profile_complete = models.BooleanField(default=False)
    is_admin = models.BooleanField(
        default=False,
        verbose_name="Is Admin",
        help_text="Designates whether this staff member has administrative access."
    )
    is_timetable_incharge = models.BooleanField(
        default=False,
        verbose_name="Timetable Incharge",
        help_text="Designates whether this staff member is a timetable incharge."
    )
    is_scholarship_officer = models.BooleanField(
        default=False,
        verbose_name="Scholarship Officer",
        help_text="Designates whether this staff member is a scholarship officer."
    )

    def get_roles_list(self):
        roles = []
        if self.role:
            roles.append(self.role)
        if self.secondary_roles:
            for r in self.secondary_roles.split(','):
                r_clean = r.strip()
                if r_clean and r_clean not in roles:
                    roles.append(r_clean)
        if self.is_scholarship_officer and 'Scholarship Officer' not in roles:
            roles.append('Scholarship Officer')
        if self.is_timetable_incharge and 'Timetable Incharge' not in roles:
            roles.append('Timetable Incharge')
        if self.is_admin and 'Admin' not in roles:
            roles.append('Admin')
        return roles

    def has_role(self, role_name):
        return role_name in self.get_roles_list()

    @property
    def is_hod(self):
        return self.has_role('HOD')

    @property
    def is_class_incharge(self):
        return self.has_role('Class Incharge')

    @property
    def is_course_incharge(self):
        return self.has_role('Course Incharge')

    @property
    def is_office_staff(self):
        return self.has_role('Office Staff')

    @property
    def is_technical_officer(self):
        return self.has_role('Technical Officer')

    @property
    def is_placement_officer(self):
        return self.has_role('Placement Officer')

    @property
    def phone(self):
        return self.mobile_number

    @property
    def can_manage_bonafide(self):
        return self.is_hod or self.is_admin or self.is_office_staff or self.has_role('Bonafide Issuing')

    @property
    def can_manage_documents(self):
        return self.is_hod or self.is_admin or self.is_office_staff or self.has_role('Marksheet & Document Requests')

    @property
    def can_manage_scholarships(self):
        return self.is_hod or self.is_admin or self.is_scholarship_officer or self.is_office_staff or self.has_role('Scholarship Management')

    @property
    def office_sub_tasks(self):
        tasks = []
        if self.has_role('Bonafide Issuing'):
            tasks.append('Bonafide Issuing')
        if self.has_role('Marksheet & Document Requests'):
            tasks.append('Marksheet Requests')
        if self.has_role('Scholarship Management'):
            tasks.append('Scholarship Management')
        return tasks

    @property
    def is_staff_admin(self):
        return self.is_hod or self.is_admin

    def get_teaching_subjects(self):
        from .models import Subject
        from django.db.models import Q
        return Subject.objects.filter(
            Q(staff=self) | Q(staff_batch_b=self)
        ).distinct().order_by('semester', 'code')

    def clean(self):
        """Validate staff role assignments."""
        from django.core.exceptions import ValidationError
        
        # Validate only one HOD
        if self.role == 'HOD':
            existing_hod = Staff.objects.filter(role='HOD').exclude(staff_id=self.staff_id)
            if existing_hod.exists():
                raise ValidationError({
                    'role': f'Only one HOD is allowed. Current HOD: {existing_hod.first().name} ({existing_hod.first().staff_id})'
                })
        
        # Validate additional admin count limit
        if self.is_admin:
            max_allowed = AdminSettings.get_max_additional_admins()
            existing_admins = Staff.objects.filter(is_admin=True)
            if self.pk:
                existing_admins = existing_admins.exclude(pk=self.pk)
            
            if existing_admins.count() >= max_allowed:
                raise ValidationError({
                    'is_admin': f'Cannot assign admin role. The maximum limit of additional admins ({max_allowed}) has been reached.'
                })
        
        # Validate Class Incharge semester uniqueness
        if self.role == 'Class Incharge' and self.assigned_semester:
            existing_ci = Staff.objects.filter(
                role='Class Incharge',
                assigned_semester=self.assigned_semester
            ).exclude(staff_id=self.staff_id)
            
            if existing_ci.exists():
                raise ValidationError({
                    'assigned_semester': f'Semester {self.assigned_semester} already has a Class Incharge: {existing_ci.first().name} ({existing_ci.first().staff_id})'
                })
        
        # Require assigned_semester for Class Incharge
        if self.role == 'Class Incharge' and not self.assigned_semester:
            raise ValidationError({
                'assigned_semester': 'Class Incharge must be assigned to a specific semester (1-8).'
            })

        # Validate timetable incharge limit (max 2)
        if self.is_timetable_incharge:
            existing_tt = Staff.objects.filter(is_timetable_incharge=True)
            if self.pk:
                existing_tt = existing_tt.exclude(pk=self.pk)
            if existing_tt.count() >= 2:
                raise ValidationError({
                    'is_timetable_incharge': 'Cannot assign timetable incharge. The maximum limit of 2 timetable incharges has been reached.'
                })

        # Validate scholarship officer limit (max 2)
        if self.is_scholarship_officer:
            existing_sch = Staff.objects.filter(is_scholarship_officer=True)
            if self.pk:
                existing_sch = existing_sch.exclude(pk=self.pk)
            if existing_sch.count() >= 2:
                raise ValidationError({
                    'is_scholarship_officer': 'Cannot assign scholarship officer. The maximum limit of 2 scholarship officers has been reached.'
                })

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def __str__(self):
        return f"{self.salutation} {self.name}"

    @property
    def publication_count(self):
        return self.journals.count() + self.conferences.count() + self.books.count()


class StaffGenerator(Staff):
    class Meta:
        proxy = True
        verbose_name = "Generate Staff"
        verbose_name_plural = "Generate Staff"


class AdminSettings(models.Model):
    max_additional_admins = models.PositiveIntegerField(
        default=3,
        verbose_name="Max Additional Admins",
        help_text="The maximum number of staff members (excluding the HOD) that can be set as Admin (is_admin=True)."
    )

    class Meta:
        verbose_name = "Admin Settings"
        verbose_name_plural = "Admin Settings"

    def clean(self):
        from django.core.exceptions import ValidationError
        # Enforce singleton pattern
        if not self.pk and AdminSettings.objects.exists():
            raise ValidationError("Only one Admin Settings configuration can exist.")
        
        # Enforce that max_additional_admins cannot be less than current additional admins
        current_admin_count = Staff.objects.filter(is_admin=True).count()
        if self.max_additional_admins < current_admin_count:
            raise ValidationError({
                'max_additional_admins': f"Cannot set limit to {self.max_additional_admins} because there are currently {current_admin_count} active additional admins. Disable some admins first."
            })
        super().clean()

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_max_additional_admins(cls):
        config = cls.objects.first()
        if config:
            return config.max_additional_admins
        return 3  # default fallback

    def __str__(self):
        return f"Global Admin Settings (Max Additional Admins: {self.max_additional_admins})"


class Lab(models.Model):
    name = models.CharField(max_length=255, unique=True, verbose_name="Lab Name")
    short_name = models.CharField(
        max_length=50, 
        unique=True, 
        verbose_name="Lab Short Name",
        help_text="Unique short identifier for the lab (e.g. IT-LAB-01)"
    )
    staff = models.ForeignKey(
        Staff, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='assigned_labs',
        verbose_name="Lab Incharge",
        help_text="The staff member in charge of this lab."
    )
    from_date = models.DateField(null=True, blank=True, verbose_name="From Date")
    to_date = models.DateField(null=True, blank=True, verbose_name="To Date")

    class Meta:
        verbose_name = "Lab"
        verbose_name_plural = "Labs"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.short_name})"


class ClassMapping(models.Model):
    class_name = models.CharField(max_length=255, verbose_name="Class Name", help_text="e.g. III Year IT - Sem 5")
    room_name = models.CharField(max_length=100, verbose_name="Class Room Name", help_text="e.g. LH-201, Room 102")
    semester = models.IntegerField(null=True, blank=True, verbose_name="Semester (1-8)")
    from_date = models.DateField(null=True, blank=True, verbose_name="From Date")
    to_date = models.DateField(null=True, blank=True, verbose_name="To Date")

    class Meta:
        verbose_name = "Class Mapping"
        verbose_name_plural = "Class Mappings"
        ordering = ['semester', 'class_name']

    def __str__(self):
        return f"{self.class_name} ({self.room_name})"


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

    @property
    def mla_format(self):
        parts = []
        if self.staff:
            parts.append(f"{self.staff.name.strip()} {self.staff.initial.strip()},".strip())
        if self.title:
            title = self.title.strip()
            if not title.endswith('.'):
                title += '.'
            parts.append(f'"{title}"')
        if self.venue_or_journal:
            parts.append(f"{self.venue_or_journal.strip()},")
        if self.year:
            parts.append(f"{self.year.strip()}.")
        return " ".join(parts)


class StaffQualification(models.Model):
    """Educational qualifications of staff."""
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='qualifications')
    degree = models.CharField(max_length=100)
    specialization = models.CharField(max_length=255, blank=True, null=True, help_text="Specialization (e.g. Computer Science)")
    university = models.CharField(max_length=255)
    year_completed = models.CharField(max_length=10)
    certificate = models.FileField(
        upload_to=staff_qualification_document_path,
        blank=True,
        null=True,
        help_text="Upload Certificate",
        validators=[validate_file_size]
    )
    order = models.PositiveIntegerField(default=0)
    approval_status = models.CharField(
        max_length=20,
        choices=[('Pending', 'Pending'), ('Approved', 'Approved'), ('Rejected', 'Rejected')],
        default='Pending'
    )

    class Meta:
        ordering = ['-year_completed', '-order', 'degree']

    def __str__(self):
        return f"{self.degree} from {self.university} ({self.year_completed})"


class StaffPastDesignation(models.Model):
    """Past and alternative designations of staff."""
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='past_designations')
    designation = models.CharField(max_length=100)
    from_date = models.DateField(null=True, blank=True)
    to_date = models.DateField(null=True, blank=True)
    order_img = models.FileField(
        upload_to=staff_designation_document_path,
        blank=True,
        null=True,
        help_text="Upload Order Document",
        validators=[validate_file_size]
    )
    order = models.PositiveIntegerField(default=0)
    approval_status = models.CharField(
        max_length=20,
        choices=[('Pending', 'Pending'), ('Approved', 'Approved'), ('Rejected', 'Rejected')],
        default='Pending'
    )
    is_additional = models.BooleanField(default=False)

    class Meta:
        ordering = ['-from_date', '-order', 'designation']

    def __str__(self):
        return f"{self.designation} ({self.from_date} to {self.to_date or 'Present'})"


class StaffMembership(models.Model):
    """Professional memberships of staff."""
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='memberships')
    institute_name = models.CharField(max_length=255)
    membership_no = models.CharField(max_length=100)
    membership_type = models.CharField(max_length=100)
    year = models.CharField(max_length=10, blank=True)
    month = models.CharField(max_length=20, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-year', '-order', 'institute_name']

    def __str__(self):
        return f"{self.membership_type} at {self.institute_name} ({self.year})"


class StaffAwardHonour(models.Model):
    """Individual award, honour, or membership entry."""
    staff = models.ManyToManyField(Staff, related_name='award_list', blank=True)
    student = models.ForeignKey('students.Student', on_delete=models.SET_NULL, null=True, blank=True, related_name='scholar_awards')
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    year = models.CharField(max_length=20, blank=True)
    CATEGORY_CHOICES = [
        ('Award', 'Award'),
        ('Honour', 'Honour'),
        ('Membership', 'Membership'),
    ]
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='Award')
    awarded_by = models.CharField(max_length=200, blank=True)
    supporting_document = models.FileField(
        upload_to=staff_award_document_path,
        blank=True,
        null=True,
        help_text="Upload Certificate/Letter",
        validators=[validate_file_size]
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-order', '-year', 'title']

    def __str__(self):
        return f"{self.title} ({self.category})"


class StaffSeminar(models.Model):
    """Seminar, workshop, conference, symposia, FDP, STTP, training entry."""
    staff = models.ManyToManyField(Staff, related_name='seminar_list', blank=True)
    student = models.ForeignKey('students.Student', on_delete=models.SET_NULL, null=True, blank=True, related_name='scholar_seminars')
    title = models.CharField(max_length=400)
    EVENT_TYPE_CHOICES = [
        ('Conference', 'Conference'),
        ('Seminar', 'Seminar'),
        ('Workshop', 'Workshop'),
        ('Symposia', 'Symposia'),
        ('FDP', 'FDP'),
        ('STTP', 'STTP'),
        ('Summer/Winter School', 'Summer/Winter School'),
        ('Orientation Programme', 'Orientation Programme'),
        ('Refresher Course / Training', 'Refresher Course / Training'),
    ]
    event_type = models.CharField(max_length=60, choices=EVENT_TYPE_CHOICES, default='Seminar')
    venue_or_description = models.CharField(max_length=300, blank=True)
    organized_by = models.CharField(max_length=300, blank=True)
    sponsoring_agency = models.CharField(max_length=300, blank=True)
    national_international = models.CharField(max_length=30, choices=[('National', 'National'), ('International', 'International')], default='National', blank=True)
    proceedings_title = models.CharField(max_length=400, blank=True)
    date_from = models.DateField(null=True, blank=True)
    date_to = models.DateField(null=True, blank=True)
    total_days = models.PositiveIntegerField(null=True, blank=True)
    year = models.CharField(max_length=20, blank=True)
    supporting_document = models.FileField(
        upload_to=staff_seminar_document_path,
        blank=True,
        null=True,
        help_text="Upload Completion Certificate (Required)",
        validators=[validate_file_size]
    )
    order_certificate = models.FileField(
        upload_to=staff_seminar_order_path,
        blank=True,
        null=True,
        help_text="Upload Deputation Order Copy (Optional)",
        validators=[validate_file_size]
    )
    mode = models.CharField(
        max_length=20,
        choices=[('Online', 'Online'), ('Offline', 'Offline')],
        default='Offline'
    )
    participation_role = models.CharField(
        max_length=20,
        choices=[('Attended', 'Attended'), ('Conducted', 'Conducted')],
        default='Attended'
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-date_from', '-year', '-order', 'title']

    def save(self, *args, **kwargs):
        import datetime
        d_from = self.date_from
        d_to = self.date_to

        if isinstance(d_from, str):
            try:
                d_from = datetime.datetime.strptime(d_from, '%Y-%m-%d').date()
            except ValueError:
                d_from = None
        elif isinstance(d_from, datetime.datetime):
            d_from = d_from.date()

        if isinstance(d_to, str):
            try:
                d_to = datetime.datetime.strptime(d_to, '%Y-%m-%d').date()
            except ValueError:
                d_to = None
        elif isinstance(d_to, datetime.datetime):
            d_to = d_to.date()

        if d_from and d_to:
            self.total_days = (d_to - d_from).days + 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.event_type})"


class StaffStudentGuided(models.Model):
    """PG or PhD student guided by staff."""
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='student_guided_list')
    student_name = models.CharField(max_length=255)
    degree_type = models.CharField(max_length=10, choices=[('PG', 'PG'), ('PhD', 'PhD')])
    status = models.CharField(max_length=20, choices=[('Ongoing', 'Ongoing'), ('Completed', 'Completed')], default='Ongoing')
    year = models.CharField(max_length=20, blank=True)
    viva_date = models.DateField(null=True, blank=True, help_text="Viva Voce Examination Date (Completed Ph.D. scholars)")
    supporting_document = models.FileField(
        upload_to=staff_student_guided_document_path,
        blank=True,
        null=True,
        help_text="Memo/Provisional Certificate for PG/PhD, Allocation Order for New Students",
        validators=[validate_file_size]
    )
    department = models.CharField(max_length=255, blank=True, default='')
    specialization = models.CharField(max_length=255, blank=True, default='', help_text="Specialization / Area of Research")
    roll_number = models.CharField(max_length=100, blank=True, default='')
    thesis_title = models.CharField(max_length=500, blank=True, default='')
    thesis_document = models.FileField(
        upload_to=staff_student_guided_thesis_path,
        blank=True,
        null=True,
        validators=[validate_file_size],
        help_text="Upload Thesis PDF"
    )
    papers_pdf = models.FileField(
        upload_to=staff_student_guided_papers_path,
        blank=True,
        null=True,
        validators=[validate_file_size],
        help_text="Upload Publication Papers PDF"
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-order', 'degree_type', 'student_name']

    def __str__(self):
        return f"{self.student_name} ({self.degree_type})"


class StaffResearchProject(models.Model):
    """Research Project undertaken by staff."""
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='research_projects')
    title = models.CharField(max_length=400)
    description = models.TextField(blank=True, default='')
    funded_by = models.CharField(max_length=255, blank=True, default='')
    funding_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Funding amount in INR")
    supporting_document = models.FileField(
        upload_to=staff_research_project_path,
        blank=True,
        null=True,
        validators=[validate_file_size],
        help_text="Upload Project Sanction Order or related supporting document (PDF)"
    )
    status = models.CharField(
        max_length=20,
        choices=[('Ongoing', 'Ongoing'), ('Completed', 'Completed')],
        default='Ongoing'
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-order', '-start_date', 'title']

    def __str__(self):
        return f"{self.title} ({self.status})"


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
    staff_batch_b = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True, blank=True, related_name='subjects_b')
    
    ASSIGNED_BATCH_CHOICES = [
        ('A', 'Batch A'),
        ('B', 'Batch B'),
        ('Both', 'Both'),
    ]
    assigned_batch = models.CharField(
        max_length=10, 
        choices=ASSIGNED_BATCH_CHOICES, 
        default='Both',
        help_text="Designate if this course assignment applies to Batch A, Batch B, or Both."
    )
    
    classroom = models.ForeignKey('ClassMapping', on_delete=models.SET_NULL, null=True, blank=True, related_name='subjects', verbose_name="Classroom Mapping")
    lab = models.ForeignKey('Lab', on_delete=models.SET_NULL, null=True, blank=True, related_name='subjects', verbose_name="Lab Mapping")
    location_name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Location Name", help_text="Assigned class room or lab room name e.g. LH-201, OS Lab")

    def get_location_display(self):
        if self.location_name:
            return self.location_name
        if self.lab:
            return self.lab.name
        if self.classroom:
            return f"{self.classroom.room_name} ({self.classroom.class_name})"
        return f"Sem {self.semester} Room"

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
    academic_year = models.CharField(max_length=20, default='2026-2027', help_text="Academic year e.g. 2026-2027")
    semester = models.IntegerField()
    day = models.CharField(max_length=10, choices=DAYS_OF_WEEK)
    period = models.IntegerField(help_text="1 to 7")
    batch = models.CharField(max_length=3, choices=[('All', 'All'), ('A', 'Batch A'), ('B', 'Batch B')], default='All')
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True, blank=True)
    staff = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True, blank=True) # Optional: Assign staff directly
    is_published = models.BooleanField(default=True, help_text="Indicates whether this timetable entry is published")
    from_date = models.DateField(null=True, blank=True, help_text="Effective From Date")
    to_date = models.DateField(null=True, blank=True, help_text="Effective To Date")

    class Meta:
        ordering = ['academic_year', 'semester', 'day', 'period']
        unique_together = ('academic_year', 'semester', 'day', 'period', 'batch')

    def __str__(self):
        return f"Sem {self.semester} - {self.day} - Period {self.period} ({self.batch})"


class PublishedTimetableVersion(models.Model):
    academic_year = models.CharField(max_length=20, default='2026-2027', help_text="Academic year e.g. 2026-2027")
    semester = models.IntegerField(help_text="Semester 1 to 8")
    version_name = models.CharField(max_length=100, default='v1.0', null=True, blank=True, help_text="Timetable Version Name")
    from_date = models.DateField(null=True, blank=True, help_text="Effective From Date")
    to_date = models.DateField(null=True, blank=True, help_text="Effective To Date")
    published_by = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True, blank=True)
    published_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True, help_text="Is current active published version")
    timetable_data_json = models.TextField(default='{}', help_text="JSON snapshot of saved timetable grid entries")

    class Meta:
        ordering = ['-published_at']

    def __str__(self):
        return f"Sem {self.semester} ({self.from_date} to {self.to_date}) - {self.version_name}"

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
    document = models.FileField(
        upload_to=staff_leave_document_path,
        blank=True,
        null=True,
        help_text="Required for Medical Leave and On Other Duty",
        validators=[validate_file_size]
    )
    
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
    
    # Document upload
    document = models.FileField(
        upload_to=news_documents_path,
        blank=True,
        null=True,
        help_text="Upload a document (PDF, DOC, etc.) related to this announcement"
    )
    
    # NEW gif indicator dates
    new_gif_start_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when the NEW indicator should start showing"
    )
    new_gif_end_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when the NEW indicator should stop showing (must not exceed news end date)"
    )

    class Meta:
        ordering = ['-date']
        verbose_name_plural = "News & Announcements"
    
    def clean(self):
        """Validate NEW gif dates."""
        from django.core.exceptions import ValidationError
        
        # Validate NEW gif end date doesn't exceed news end date
        if self.new_gif_end_date and self.end_date:
            if self.new_gif_end_date > self.end_date:
                raise ValidationError({
                    'new_gif_end_date': 'NEW indicator end date cannot exceed the news end date.'
                })
        
        # Validate gif start date is before end date
        if self.new_gif_start_date and self.new_gif_end_date:
            if self.new_gif_start_date > self.new_gif_end_date:
                raise ValidationError({
                    'new_gif_end_date': 'NEW indicator end date must be after start date.'
                })
    
    def should_show_new_indicator(self):
        """Check if NEW gif should be displayed."""
        from django.utils import timezone
        today = timezone.now().date()
        
        if not self.new_gif_start_date or not self.new_gif_end_date:
            return False
        
        return self.new_gif_start_date <= today <= self.new_gif_end_date

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
    staff = models.ManyToManyField(Staff, related_name='conferences', blank=True)
    student = models.ForeignKey('students.Student', on_delete=models.SET_NULL, null=True, blank=True, related_name='scholar_conferences')
    national_international = models.CharField(max_length=20, choices=[('National', 'National'), ('International', 'International')], default='National')
    participation_type = models.CharField(max_length=20, choices=[('Presented', 'Presented'), ('Attended', 'Attended')], default='Presented')
    author_name = models.CharField(max_length=255, blank=True)
    year_of_publication = models.CharField(max_length=20, blank=True)
    title_of_paper = models.CharField(max_length=500, blank=True)
    title_of_proceedings = models.CharField(max_length=500, blank=True)
    date_from = models.DateField(null=True, blank=True)
    date_to = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=255, blank=True)
    page_numbers_from = models.CharField(max_length=50, blank=True)
    page_numbers_to = models.CharField(max_length=50, blank=True)
    place_of_publication = models.CharField(max_length=255, blank=True)
    publisher_proceedings = models.CharField(max_length=500, blank=True)
    supporting_document = models.FileField(
        upload_to=staff_conference_document_path,
        blank=True,
        null=True,
        help_text="Upload Certificate/Paper",
        validators=[validate_file_size]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title_of_paper} ({self.year_of_publication})"

    @property
    def mla_format(self):
        parts = []
        if self.author_name:
            parts.append(f"{self.author_name.strip()},")
        if self.title_of_paper:
            title = self.title_of_paper.strip()
            if not title.endswith('.'):
                title += '.'
            parts.append(f'"{title}"')
        if self.title_of_proceedings:
            parts.append(f"{self.title_of_proceedings.strip()},")
            
        date_str = ""
        if self.date_from:
            date_str += self.date_from.strftime("%b %Y")
        elif self.year_of_publication:
            date_str += self.year_of_publication.strip()
        if date_str:
            parts.append(f"{date_str.strip()},")
            
        if self.page_numbers_from and self.page_numbers_to:
            parts.append(f"pp. {self.page_numbers_from.strip()}-{self.page_numbers_to.strip()}.")
        elif self.page_numbers_from:
            parts.append(f"p. {self.page_numbers_from.strip()}.")
            
        if self.year_of_publication:
            parts.append(f"{self.year_of_publication.strip()}.")
            
        return " ".join(parts)

class JournalPublication(models.Model):
    staff = models.ManyToManyField(Staff, related_name='journals', blank=True)
    student = models.ForeignKey('students.Student', on_delete=models.SET_NULL, null=True, blank=True, related_name='scholar_journals')
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
    supporting_document = models.FileField(
        upload_to=staff_journal_document_path,
        blank=True,
        null=True,
        help_text="Upload Paper Copy",
        validators=[validate_file_size]
    )
    is_scopus = models.BooleanField(default=False, verbose_name="SCOPUS")
    is_wos = models.BooleanField(default=False, verbose_name="WOS")
    is_sci = models.BooleanField(default=False, verbose_name="SCI")
    is_scie = models.BooleanField(default=False, verbose_name="SCIE")
    is_ugc = models.BooleanField(default=False, verbose_name="UGC")
    created_at = models.DateTimeField(auto_now_add=True)

    def get_journal_types(self):
        types = []
        if self.is_scopus: types.append("SCOPUS")
        if self.is_wos: types.append("WOS")
        if self.is_sci: types.append("SCI")
        if self.is_scie: types.append("SCIE")
        if self.is_ugc: types.append("UGC")
        return types

    def __str__(self):
        return f"{self.title_of_paper} - {self.journal_name}"

    @property
    def mla_format(self):
        parts = []
        if self.author_name:
            parts.append(f"{self.author_name.strip()},")
        if self.title_of_paper:
            title = self.title_of_paper.strip()
            if not title.endswith('.'):
                title += '.'
            parts.append(f'"{title}"')
        if self.journal_name:
            parts.append(f"{self.journal_name.strip()},")
        if self.volume_number:
            parts.append(f"Volume {self.volume_number.strip()},")
        if self.issue_number:
            parts.append(f"Number {self.issue_number.strip()},")
        
        date_str = ""
        if self.published_month:
            date_str += f"{self.published_month.strip()} "
        if self.published_year:
            date_str += f"{self.published_year.strip()}"
        if date_str:
            parts.append(f"{date_str.strip()},")
            
        if self.page_numbers_from and self.page_numbers_to:
            parts.append(f"pp. {self.page_numbers_from.strip()}-{self.page_numbers_to.strip()}.")
        elif self.page_numbers_from:
            parts.append(f"p. {self.page_numbers_from.strip()}.")
            
        if self.published_year:
            parts.append(f"{self.published_year.strip()}.")
            
        return " ".join(parts)

class BookPublication(models.Model):
    staff = models.ManyToManyField(Staff, related_name='books', blank=True)
    student = models.ForeignKey('students.Student', on_delete=models.SET_NULL, null=True, blank=True, related_name='scholar_books')
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
    supporting_document = models.FileField(
        upload_to=staff_book_document_path,
        blank=True,
        null=True,
        help_text="Upload Cover Page/Proof",
        validators=[validate_file_size]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title_of_book} ({self.type})"

    @property
    def mla_format(self):
        parts = []
        if self.author_name:
            parts.append(f"{self.author_name.strip()},")
        if self.title_of_book:
            title = self.title_of_book.strip()
            if not title.endswith('.'):
                title += '.'
            parts.append(f'"{title}"')
        if self.publisher_name:
            parts.append(f"{self.publisher_name.strip()},")
        if self.publisher_address:
            parts.append(f"{self.publisher_address.strip()},")
            
        date_str = ""
        if self.month_of_publication:
            date_str += f"{self.month_of_publication.strip()} "
        if self.year_of_publication:
            date_str += f"{self.year_of_publication.strip()}"
        if date_str:
            parts.append(f"{date_str.strip()},")
            
        if self.page_numbers_from and self.page_numbers_to:
            parts.append(f"pp. {self.page_numbers_from.strip()}-{self.page_numbers_to.strip()}.")
        elif self.page_numbers_from:
            parts.append(f"p. {self.page_numbers_from.strip()}.")
            
        if self.year_of_publication:
            parts.append(f"{self.year_of_publication.strip()}.")
            
        return " ".join(parts)


class StaffPatent(models.Model):
    PATENT_TYPE_CHOICES = [
        ('Indian', 'Indian'),
        ('International', 'International'),
    ]
    STATUS_CHOICES = [
        ('Applied', 'Applied'),
        ('Published', 'Published'),
        ('Granted', 'Granted'),
    ]

    staff = models.ManyToManyField(Staff, related_name='patents', blank=True)
    student = models.ForeignKey('students.Student', on_delete=models.SET_NULL, null=True, blank=True, related_name='scholar_patents')
    title = models.CharField(max_length=500, verbose_name='Title of Invention')
    application_number = models.CharField(max_length=100, blank=True, verbose_name='Application Number')
    patent_type = models.CharField(max_length=20, choices=PATENT_TYPE_CHOICES, default='Indian', verbose_name='Patent Type')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Applied', verbose_name='Status')
    application_year = models.CharField(max_length=10, blank=True, verbose_name='Year of Application')
    grant_year = models.CharField(max_length=10, blank=True, verbose_name='Year of Grant (if Granted)')
    inventors = models.CharField(max_length=500, blank=True, verbose_name='Inventor Names (auto-generated)')
    funding_agency = models.CharField(max_length=255, blank=True, verbose_name='Funding Agency (if any)')
    description = models.TextField(blank=True, verbose_name='Brief Description')
    supporting_document = models.FileField(
        upload_to=staff_patent_document_path,
        blank=True,
        null=True,
        help_text='Upload Patent Certificate / Filing Receipt (Max 100KB)',
        validators=[validate_file_size]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-application_year', '-created_at']

    def __str__(self):
        return f"{self.title} [{self.patent_type} · {self.status}]"


class MailLog(models.Model):
    """Tracks email notifications sent to parents/students."""
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='mail_logs')
    staff = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True, blank=True)
    remark_type = models.CharField(max_length=100, default='Attendance Deficit')
    month = models.CharField(max_length=20)
    year = models.CharField(max_length=4)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-sent_at']

    def __str__(self):
        return f"Mail to {self.student.student_name} ({self.remark_type}) - {self.sent_at}"


class ClassSubstitutionRequest(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Cancelled', 'Cancelled')
    ]
    
    requester = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='substitution_requests_made')
    substitute = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='substitution_requests_received')
    
    date = models.DateField()
    period = models.IntegerField(help_text="1 to 7")
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    
    # Optional link to leave request
    leave_request = models.ForeignKey('StaffLeaveRequest', on_delete=models.SET_NULL, null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    rejection_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', 'period']
        unique_together = ('requester', 'date', 'period')

    def __str__(self):
        return f"{self.requester.name} -> {self.substitute.name} on {self.date} (P{self.period})"


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


class DepartmentTask(models.Model):
    task_number = models.IntegerField(unique=True, help_text="Task number e.g. 1, 2, 3...")
    name = models.CharField(max_length=255, verbose_name="Task / Role Name")
    category = models.CharField(max_length=100, default="Department Administration", blank=True)
    assigned_staff = models.ManyToManyField(
        Staff,
        blank=True,
        related_name='assigned_department_tasks',
        verbose_name="Assigned Staff Members"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['task_number']
        verbose_name = "Department Task / Role"
        verbose_name_plural = "Department Tasks & Roles"

    def __str__(self):
        return f"{self.task_number}. {self.name}"

    @property
    def assigned_staff_count(self):
        return self.assigned_staff.count()

    @property
    def assigned_staff_names_display(self):
        names = [s.name for s in self.assigned_staff.all()]
        return ", ".join(names) if names else "Unassigned"

    @classmethod
    def seed_default_tasks(cls):
        """Ensures all default 58 tasks exist in the database."""
        for num, name, cat in DEFAULT_DEPARTMENT_TASKS:
            cls.objects.get_or_create(
                task_number=num,
                defaults={'name': name, 'category': cat}
            )


