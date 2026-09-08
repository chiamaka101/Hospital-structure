from django import forms
from .models import (
    Doctor, UserProfile, Patient, Appointment, Admission, Invoice, Medicine, Consultation,
    MedicalRecord, Prescription, LaboratoryTest, PrescriptionItem
)
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.utils import timezone

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'you@hospital.com'}))
    first_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    
    ROLE_CHOICES = [
        ('receptionist', 'Receptionist'), 
        ('doctor', 'Doctor'), 
        ('admin', 'Admin'), 
        ('nurse', 'Nurse')
    ]
    role = forms.ChoiceField(choices=ROLE_CHOICES, required=True, widget=forms.Select(attrs={'class': 'form-control'}))
    
    phone = forms.CharField(
        max_length=15, 
        required=True,
        validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$', message='Phone: 9-15 digits')],
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+2348012345678'})
    )

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'password1', 'password2', 'role', 'phone']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})
        self.fields['password1'].help_text = None
        self.fields['password2'].help_text = None

    def clean_email(self):
        email = self.cleaned_data.get('email').lower().strip()
        if User.objects.filter(email=email).exists():
            raise ValidationError("This email is already registered.")
        return email

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        if len(password) < 4:
            raise ValidationError("Password must be at least 4 characters.")
        return password

    def _post_clean(self):
        pass

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user

class DoctorCreateForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    first_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    phone = forms.CharField(
        max_length=15, 
        required=True,
        validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$', message='Invalid phone format')],
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    specialization = forms.CharField(max_length=100, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'password1', 'password2', 'phone', 'specialization']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})
        self.fields['password1'].help_text = None
        self.fields['password2'].help_text = None

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        if len(password) < 4:
            raise ValidationError("Password must be at least 4 characters.")
        return password

    def _post_clean(self):
        pass

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user

class DoctorEditForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    phone = forms.CharField(max_length=15, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    
    class Meta:
        model = Doctor
        fields = ['specialization']
        widgets = {'specialization': forms.TextInput(attrs={'class': 'form-control'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.profile:
            self.fields['first_name'].initial = self.instance.profile.user.first_name
            self.fields['last_name'].initial = self.instance.profile.user.last_name
            self.fields['email'].initial = self.instance.profile.user.email
            self.fields['phone'].initial = self.instance.profile.phone

    def save(self, commit=True):
        doctor = super().save(commit=False)
        user = doctor.profile.user
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        user.username = self.cleaned_data['email']
        user.save()
        doctor.profile.phone = self.cleaned_data['phone']
        doctor.profile.save()
        if commit:
            doctor.save()
        return doctor

class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = ['name', 'age', 'gender', 'contact', 'address','medical_history']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter full name'}),
            'age': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Age'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'contact': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Home address'}),
            'medical_history': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Medical history'}),
        }

class AppointmentForm(forms.ModelForm):
    new_patient_name = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Type new patient name if not in list'
        })
    )
    new_patient_age = forms.IntegerField(
        required=False,
        min_value=0,
        max_value=150,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Age'
        })
    )
    new_patient_gender = forms.ChoiceField(
        required=False,
        choices=[('', 'Select gender'), ('M', 'Male'), ('F', 'Female'), ('Other', 'Other')],  # FIX: M/F to match model
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    new_patient_contact = forms.CharField(
        required=False,
        max_length=15,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Phone or Email'
        })
    )
    new_patient_address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Address'
        })
    )

    class Meta:
        model = Appointment
        fields = ['patient', 'doctor', 'date_time', 'status', 'reason', 
                  'new_patient_name', 'new_patient_age', 'new_patient_gender', 
                  'new_patient_contact', 'new_patient_address']
        widgets = {
            'patient': forms.Select(attrs={'class': 'form-control'}),
            'doctor': forms.Select(attrs={'class': 'form-control'}),
            'date_time': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['patient'].required = False
        self.fields['patient'].empty_label = "Select existing patient..."
        # Only show doctors in dropdown
        self.fields['doctor'].queryset = Doctor.objects.select_related('profile__user').all()

    def clean(self):
        cleaned_data = super().clean()
        patient = cleaned_data.get('patient')
        new_name = cleaned_data.get('new_patient_name', '').strip()
        new_age = cleaned_data.get('new_patient_age')
        new_gender = cleaned_data.get('new_patient_gender')

        if not patient and not new_name:
            raise forms.ValidationError('Select a patient OR type a new patient name.')

        if new_name:
            if not new_age:
                self.add_error('new_patient_age', 'Age is required for new patients.')
            if not new_gender:
                self.add_error('new_patient_gender', 'Gender is required for new patients.')

        if patient and new_name:
            self.add_error('patient', 'Leave this empty if you are adding a new patient above.')
        
        return cleaned_data

class AdmissionForm(forms.ModelForm):
    admission_date = forms.DateTimeField(
        initial=timezone.now,
        widget=forms.DateTimeInput(
            attrs={'class': 'form-control', 'type': 'datetime-local'}
        ),
        input_formats=['%Y-%m-%dT%H:%M']
    )

    class Meta:
        model = Admission
        fields = ['patient', 'ward', 'doctor', 'admission_date', 'reason']
        widgets = {
            'patient': forms.Select(attrs={'class': 'form-control'}),
            'ward': forms.Select(attrs={'class': 'form-control'}),
            'doctor': forms.Select(attrs={'class': 'form-control'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

class ConsultationForm(forms.ModelForm): # <-- THIS WAS MISSING
    class Meta:
        model = Consultation
        fields = ['visit_notes', 'diagnosis', 'prescription']
        widgets = {
            'visit_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Patient symptoms, observations...'}),
            'diagnosis': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Doctor diagnosis...'}),
            'prescription': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Drugs and dosage...'}),
        }

class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = [
            'patient', 'doctor', 'consultation', 'admission',
            'service_fee', 'lab_fee', 'admission_fee',
            'payment_method', 'status'
        ]
        widgets = {
            'patient': forms.Select(attrs={'class': 'form-select'}),
            'doctor': forms.Select(attrs={'class': 'form-select'}),
            'consultation': forms.Select(attrs={'class': 'form-select'}),
            'admission': forms.Select(attrs={'class': 'form-select'}),
            'service_fee': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'lab_fee': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'admission_fee': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        self.fields['patient'].queryset = Patient.objects.all().order_by('name')
        self.fields['doctor'].queryset = Doctor.objects.select_related('profile__user').all()
        self.fields['doctor'].required = False

        self.fields['consultation'].queryset = Consultation.objects.all()
        self.fields['admission'].queryset = Admission.objects.all()
        self.fields['consultation'].required = False
        self.fields['admission'].required = False

        self.fields['service_fee'].initial = 0
        self.fields['lab_fee'].initial = 0
        self.fields['admission_fee'].initial = 0

        if user and hasattr(user, 'profile') and hasattr(user.profile, 'doctor'):
            self.fields['doctor'].initial = user.profile.doctor.id
            self.fields['doctor'].disabled = True

        if not self.instance.pk:
            self.fields['status'].initial = 'unpaid'

    def clean(self):
        cleaned = super().clean()
        service = cleaned.get('service_fee') or 0
        lab = cleaned.get('lab_fee') or 0
        admission = cleaned.get('admission_fee') or 0
        total = service + lab + admission

        if total <= 0:
            raise forms.ValidationError("Total amount must be greater than 0. Add at least one fee.")
        return cleaned

class MedicalRecordForm(forms.ModelForm):
    class Meta:
        model = MedicalRecord
        fields = ['patient', 'record_type', 'diagnosis', 'prescription', 'notes', 'files']
        widgets = {
            'patient': forms.Select(attrs={'class': 'form-select'}),
            'record_type': forms.Select(attrs={'class': 'form-select'}),
            'diagnosis': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Malaria, Typhoid'}),
            'prescription': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'files': forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.jpg,.jpeg,.png,.docx'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['patient'].queryset = Patient.objects.all().order_by('name')

class PrescriptionForm(forms.ModelForm):
    class Meta:
        model = Prescription
        fields = ['patient', 'record', 'notes']
        widgets = {
            'patient': forms.Select(attrs={'class': 'form-select'}),
            'record': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Instructions...'}),
        }

class PrescriptionItemForm(forms.ModelForm):
    class Meta:
        model = PrescriptionItem
        fields = ['drug_name', 'dosage', 'frequency', 'duration', 'quantity']
        widgets = {
            'drug_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Amoxicillin 500mg'}),
            'dosage': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 1 capsule'}),
            'frequency': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Twice daily'}),
            'duration': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 3 days'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'placeholder': 'e.g. 6'}),
        }

class MedicineForm(forms.ModelForm):
    class Meta:
        model = Medicine
        fields = '__all__'
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Paracetamol'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'category': forms.TextInput(attrs={'class': 'form-control'}),
            'quantity_in_stock': forms.NumberInput(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'expiry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

class LaboratoryTestForm(forms.ModelForm):
    class Meta:
        model = LaboratoryTest
        fields = ['patient', 'doctor', 'test_name', 'sample_type', 'priority', 'note']
        widgets = {
            'patient': forms.Select(attrs={'class': 'form-select'}),
            'doctor': forms.Select(attrs={'class': 'form-select'}),
            'test_name': forms.TextInput(attrs={'class': 'form-control'}),
            'sample_type': forms.TextInput(attrs={'class': 'form-control'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class ProfileForm(forms.ModelForm):                         
    username = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    first_name = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={'class': 'form-control'}))

    class Meta:
        model = UserProfile
        fields = ['phone', 'avatar']
        widgets = {
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'avatar': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['username'].initial = user.username
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['email'].initial = user.email

    def save(self, commit=True):
        profile = super().save(commit=False)
        if hasattr(profile, 'user'):
            profile.user.first_name = self.cleaned_data.get('first_name')
            profile.user.last_name = self.cleaned_data.get('last_name')
            profile.user.email = self.cleaned_data.get('email')
            if commit:
                profile.user.save()
        if commit:
            profile.save()
        return profile