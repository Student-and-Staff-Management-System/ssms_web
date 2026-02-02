from django import forms
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from .models import (
    Student, PersonalInfo, BankDetails, AcademicHistory, 
    DiplomaDetails, UGDetails, PGDetails, PhDDetails, 
    ScholarshipInfo, StudentDocuments, OtherDetails, Caste,
    StudentSkill, StudentProject, LeaveRequest
)
import datetime

# --- Common Validators ---
# 1. basic text checks
alpha_space_validator = RegexValidator(r'^[a-zA-Z\s\.]+$', "Name must contain only letters, dots and spaces.")
alphanumeric_validator = RegexValidator(r'^[a-zA-Z0-9]*$', "Must be alphanumeric (letters and numbers only).")
# 2. strict format checks
mobile_validator = RegexValidator(r'^\d{10}$', "Mobile number must be exactly 10 digits.")
aadhaar_validator = RegexValidator(r'^\d{12}$', "Aadhaar number must be exactly 12 digits.")
ifsc_validator = RegexValidator(r'^[A-Z]{4}0[A-Z0-9]{6}$', "Invalid IFSC Code format (e.g., SBIN0123456).")
year_validator = RegexValidator(r'^\d{4}$', "Year must be a 4-digit number (e.g., 2023).")
# 3. numeric ranges (helpers)
percentage_validator_min = MinValueValidator(0, "Percentage cannot be less than 0.")
percentage_validator_max = MaxValueValidator(100, "Percentage cannot be more than 100.")

class StudentForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput, required=False)
    
    # Validation for fields in Student model
    student_name = forms.CharField(validators=[alpha_space_validator])
    register_number = forms.CharField(required=False, validators=[alphanumeric_validator])
    joining_year = forms.IntegerField(required=False, validators=[MinValueValidator(2000), MaxValueValidator(2100)])
    ending_year = forms.IntegerField(required=False, validators=[MinValueValidator(2000), MaxValueValidator(2100)])

    class Meta:
        model = Student
        fields = [
            'roll_number', 'register_number', 'student_name', 'student_email', 
            'password', 'program_level', 'ug_entry_type', 'current_semester',
            'joining_year', 'ending_year'
        ]

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")

        if password and len(password) < 6:
            self.add_error('password', "Password must be at least 6 characters long.")
        
        # Logic: Ending year > Joining year
        start = cleaned_data.get('joining_year')
        end = cleaned_data.get('ending_year')
        if start and end and end < start:
            self.add_error('ending_year', "Ending Year cannot be before Joining Year.")

        return cleaned_data

    # Uniqueness checks
    def clean_student_email(self):
        email = self.cleaned_data.get('student_email')
        qs = Student.objects.filter(student_email=email)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A student with this email already exists.")
        return email

    def clean_roll_number(self):
        roll = self.cleaned_data.get('roll_number')
        qs = Student.objects.filter(roll_number=roll)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A student with this Roll Number already exists.")
        return roll

    def save(self, commit=True):
        student = super().save(commit=False)
        student.set_password(self.cleaned_data["password"])
        if commit:
            student.save()
        return student

class PersonalInfoForm(forms.ModelForm):
    caste_name = forms.CharField(max_length=255, required=False)
    
    # Extensive Validation
    umis_id = forms.CharField(required=False, validators=[alphanumeric_validator])
    emis_id = forms.CharField(required=False, validators=[alphanumeric_validator])
    abc_id = forms.CharField(required=False, validators=[alphanumeric_validator]) # ABC ID is 12 digits usually but strictly alphanumeric safe
    
    father_name = forms.CharField(required=False, validators=[alpha_space_validator])
    mother_name = forms.CharField(required=False, validators=[alpha_space_validator])
    
    student_mobile = forms.CharField(validators=[mobile_validator], required=False)
    father_mobile = forms.CharField(validators=[mobile_validator], required=False)
    mother_mobile = forms.CharField(validators=[mobile_validator], required=False)
    
    aadhaar_number = forms.CharField(validators=[aadhaar_validator], required=False)
    parent_annual_income = forms.IntegerField(required=False, validators=[MinValueValidator(0)])
    
    date_of_birth = forms.DateField(required=False)

    class Meta:
        model = PersonalInfo
        exclude = ['student', 'caste']

    def clean_date_of_birth(self):
        dob = self.cleaned_data.get('date_of_birth')
        if dob:
            age = (datetime.date.today() - dob).days / 365.25
            if age < 15:
                raise forms.ValidationError("Student must be at least 15 years old.")
        return dob

class BankDetailsForm(forms.ModelForm):
    account_holder_name = forms.CharField(required=False, validators=[alpha_space_validator])
    # account number usually numeric but can have dashes? assuming numeric mostly
    account_number = forms.CharField(required=False, validators=[RegexValidator(r'^\d+$', "Account number should be numeric.")])
    bank_name = forms.CharField(required=False, validators=[alpha_space_validator])
    branch_name = forms.CharField(required=False, validators=[alpha_space_validator])
    ifsc_code = forms.CharField(validators=[ifsc_validator], required=False)

    class Meta:
        model = BankDetails
        exclude = ['student']

class AcademicHistoryForm(forms.ModelForm):
    sslc_percentage = forms.FloatField(required=False, validators=[percentage_validator_min, percentage_validator_max])
    hsc_percentage = forms.FloatField(required=False, validators=[percentage_validator_min, percentage_validator_max])
    sslc_year_of_passing = forms.CharField(required=False, validators=[year_validator])
    hsc_year_of_passing = forms.CharField(required=False, validators=[year_validator])

    class Meta:
        model = AcademicHistory
        exclude = ['student']

class DiplomaDetailsForm(forms.ModelForm):
    diploma_percentage = forms.FloatField(required=False, validators=[percentage_validator_min, percentage_validator_max])
    diploma_year_of_passing = forms.CharField(required=False, validators=[year_validator])
    
    class Meta:
        model = DiplomaDetails
        exclude = ['student']

class UGDetailsForm(forms.ModelForm):
    ug_ogpa = forms.FloatField(required=False, validators=[percentage_validator_min, percentage_validator_max])
    ug_year_of_passing = forms.CharField(required=False, validators=[year_validator])
    
    class Meta:
        model = UGDetails
        exclude = ['student']

class PGDetailsForm(forms.ModelForm):
    pg_ogpa = forms.FloatField(required=False, validators=[percentage_validator_min, percentage_validator_max])
    pg_year_of_passing = forms.CharField(required=False, validators=[year_validator])

    class Meta:
        model = PGDetails
        exclude = ['student']

class PhDDetailsForm(forms.ModelForm):
    phd_year_of_joining = forms.CharField(required=False, validators=[year_validator])

    class Meta:
        model = PhDDetails
        exclude = ['student']

class ScholarshipInfoForm(forms.ModelForm):
    class Meta:
        model = ScholarshipInfo
        exclude = ['student']

class StudentDocumentsForm(forms.ModelForm):
    class Meta:
        model = StudentDocuments
        exclude = ['student']

class OtherDetailsForm(forms.ModelForm):
    # ambition/role model/hobbies are free text
    class Meta:
        model = OtherDetails
        exclude = ['student']

class StudentSkillForm(forms.ModelForm):
    class Meta:
        model = StudentSkill
        fields = ['skill_name', 'proficiency']

class StudentProjectForm(forms.ModelForm):
    class Meta:
        model = StudentProject
        fields = ['title', 'description', 'role', 'technologies', 'project_link']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class LeaveRequestForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = ['leave_type', 'start_date', 'end_date', 'reason', 'document']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'reason': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Reason for leave...'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_date')
        end = cleaned_data.get('end_date')
        leave_type = cleaned_data.get('leave_type')
        document = cleaned_data.get('document')
        
        if start and end and end < start:
            self.add_error('end_date', "End date cannot be before start date.")
        
        # Document Validation
        if leave_type in ['Medical', 'OD'] and not document:
             self.add_error('document', f"Document is required for {dict(LeaveRequest.LEAVE_TYPES).get(leave_type)}.")
        
        return cleaned_data