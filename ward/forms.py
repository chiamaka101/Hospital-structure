from django import forms
from .models import Doctor, UserProfile, Patient, Appointment, Admission, Invoice, Consultation
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
import re

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'you@hospital.com'}))
    first_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    
    ROLE_CHOICES = [
        ('receptionist', 'Receptionist'), 
        ('doctor', 'Doctor'), 
        ('admin', 'Admin'), 
        ('nurse', 'Nurse')  # changed from patient
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
        # Skip Django's built-in password validators
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
        fields = ['name', 'age', 'gender', 'contact', 'address']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'age': forms.NumberInput(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'contact': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Email or +234...'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

class AppointmentForm(forms.ModelForm):
    date_time = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        input_formats=['%Y-%m-%dT%H:%M']
    )
    
    class Meta:
        model = Appointment
        fields = ['patient', 'doctor', 'date_time', 'reason']
        widgets = {
            'patient': forms.Select(attrs={'class': 'form-control'}),
            'doctor': forms.Select(attrs={'class': 'form-control'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

class AdmissionForm(forms.ModelForm):
    class Meta:
        model = Admission
        fields = ['patient', 'ward', 'doctor', 'reason']
        widgets = {
            'patient': forms.Select(attrs={'class': 'form-control'}),
            'ward': forms.Select(attrs={'class': 'form-control'}),
            'doctor': forms.Select(attrs={'class': 'form-control'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

class ConsultationForm(forms.ModelForm):
    class Meta:
        model = Consultation
        fields = ['visit_notes', 'diagnosis', 'prescription']
        widgets = {
            'visit_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'diagnosis': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'prescription': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ['patient', 'doctor', 'consultation', 'admission', 'service_fee', 'lab_fee', 'admission_fee']
        widgets = {
            'patient': forms.Select(attrs={'class': 'form-select'}),
            'doctor': forms.Select(attrs={'class': 'form-select'}),
            'consultation': forms.Select(attrs={'class': 'form-select'}),
            'admission': forms.Select(attrs={'class': 'form-select'}),
            'service_fee': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'lab_fee': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'admission_fee': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['patient'].queryset = Patient.objects.all().order_by('name')
        self.fields['doctor'].queryset = Doctor.objects.select_related('profile__user').all()
        self.fields['doctor'].required = False
        self.fields['consultation'].required = False
        self.fields['admission'].required = False
        self.fields['service_fee'].initial = 0
        self.fields['lab_fee'].initial = 0
        self.fields['admission_fee'].initial = 0
        self.fields['consultation'].queryset = Consultation.objects.filter(invoice__isnull=True)
        self.fields['admission'].queryset = Admission.objects.filter(invoice__isnull=True)