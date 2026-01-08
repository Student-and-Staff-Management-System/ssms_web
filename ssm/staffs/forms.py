from django import forms
from django.core.validators import RegexValidator
from .models import Staff
import datetime

# Common Validators
alpha_space_validator = RegexValidator(r'^[a-zA-Z\s\.]+$', "Name must contain only letters, dots and spaces.")
alphanumeric_validator = RegexValidator(r'^[a-zA-Z0-9]*$', "Must be alphanumeric.")

class StaffRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    
    # Strict Field Validators
    name = forms.CharField(validators=[alpha_space_validator])
    # Designation/Dept can be loose text (e.g. "H.O.D", "Assistant Prof.") allow dots/spaces
    designation = forms.CharField(validators=[RegexValidator(r'^[a-zA-Z\s\.]+$', "Designation contains invalid characters.")])
    department = forms.CharField(validators=[RegexValidator(r'^[a-zA-Z\s\.]+$', "Department contains invalid characters.")])
    
    date_of_birth = forms.DateField(required=False)
    date_of_joining = forms.DateField(required=False)

    class Meta:
        model = Staff
        fields = [
            'staff_id', 'name', 'email', 'password', 'photo',
            'salutation', 'designation', 'department', 'qualification',
            'specialization', 'date_of_birth', 'date_of_joining', 'address',
            'academic_details', 'experience', 'publications', 'awards_and_memberships'
        ]

    def clean_staff_id(self):
        staff_id = self.cleaned_data.get('staff_id')
        if Staff.objects.filter(staff_id=staff_id).exists():
            raise forms.ValidationError(f"A staff member with ID '{staff_id}' already exists.")
        # Optional: Force ID format (e.g. STF-001) if required, assuming free text for now but alphanumeric check good?
        # if not staff_id.isalnum(): raise forms.ValidationError("Staff ID must be alphanumeric.")
        return staff_id

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if Staff.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if len(password) < 6:
            raise forms.ValidationError("Password must be at least 6 characters long.")
        return password

    def clean(self):
        cleaned_data = super().clean()
        dob = cleaned_data.get('date_of_birth')
        doj = cleaned_data.get('date_of_joining')

        if dob:
            age = (datetime.date.today() - dob).days / 365.25
            if age < 18:
                self.add_error('date_of_birth', "Staff must be at least 18 years old.")
        
        if dob and doj and doj < dob:
            self.add_error('date_of_joining', "Date of Joining cannot be before Date of Birth.")

        return cleaned_data

    def save(self, commit=True):
        staff = super().save(commit=False)
        staff.set_password(self.cleaned_data["password"])
        if commit:
            staff.save()
        return staff

from .models import StaffLeaveRequest

class StaffLeaveRequestForm(forms.ModelForm):
    class Meta:
        model = StaffLeaveRequest
        fields = ['leave_type', 'start_date', 'end_date', 'reason', 'document']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'reason': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Reason for leave...'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.staff = kwargs.pop('staff', None)
        super(StaffLeaveRequestForm, self).__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_date')
        end = cleaned_data.get('end_date')
        leave_type = cleaned_data.get('leave_type')
        document = cleaned_data.get('document')
        
        if start and end:
            if end < start:
                self.add_error('end_date', "End date cannot be before start date.")
            
            requested_days = (end - start).days + 1
            
            # Document Validation
            if leave_type in ['Medical', 'OD'] and not document:
                self.add_error('document', f"Document is required for {dict(StaffLeaveRequest.LEAVE_TYPES).get(leave_type)}.")

            # Leave Limit Validation
            if self.staff:
                # Calculate Academic Year Start (January 1st) - Calendar Year Update
                today = datetime.date.today()
                ay_start = datetime.date(today.year, 1, 1)
                
                limits = {
                    'CL': 12,
                    'Religious': 3,
                    'Special': 15
                }
                
                if leave_type in limits:
                    limit = limits[leave_type]
                    # Fetch approved/pending leaves of this type in this AY
                    existing_leaves = StaffLeaveRequest.objects.filter(
                        staff=self.staff,
                        leave_type=leave_type,
                        status__in=['Approved', 'Pending'],
                        start_date__gte=ay_start
                    )
                    
                    total_days_taken = 0
                    for leave in existing_leaves:
                        days = (leave.end_date - leave.start_date).days + 1
                        total_days_taken += days
                        
                    if total_days_taken + requested_days > limit:
                         remaining = limit - total_days_taken
                         remaining = max(0, remaining)
                         leave_name = dict(StaffLeaveRequest.LEAVE_TYPES).get(leave_type)
                         raise forms.ValidationError(f"{leave_name} limit exceeded. You have {remaining} days remaining for this academic year. Requested: {requested_days} days.")
        
        return cleaned_data
