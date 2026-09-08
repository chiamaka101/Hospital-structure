from multiprocessing import context
import profile

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q, Sum, F, ExpressionWrapper, DecimalField, Count
from django import forms
from django.forms import inlineformset_factory
import csv
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import matplotlib
from requests import request
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64
from datetime import timedelta

from .models import *
from .models import Medicine, Prescription, Invoice  
from .forms import *  
from .forms import LaboratoryTestForm, DoctorCreateForm, DoctorEditForm, ConsultationForm 
from .decorators import role_required
from .utils import (
    notify_patient_registered,
    notify_appointment_scheduled,
    notify_patient_admitted,
    notify_invoice_created,
    notify_payment_confirmed,
    notify_consultation_complete
)

# =========================================================
# FORMS
# =========================================================

class ContactForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your name'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Your email'})
    )
    subject = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Subject'})
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Your message'})
    )

# =========================================================
# HELPERS
# =========================================================

def log_activity(user, action, obj=None):
    ActivityLog.objects.create(
        user=user,
        action=action,
        model_name=obj.__class__.__name__ if obj else "System",
        object_id=obj.id if obj else None
    )

def get_role(user):
    """Return role in lowercase to match template checks"""
    try:
        if hasattr(user, 'profile') and user.profile.role:
            return str(user.profile.role).lower().strip()
    except Exception:
        pass
    return 'guest'

def get_doctor_profile(user):
    """Helper to get doctor profile for filtering"""
    if hasattr(user, 'profile'):
        return getattr(user.profile, 'doctor', None)
    return None

# =========================================================
# AUTHENTICATION
# =========================================================

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')

        # Find the account using the email address
        try:
            user_obj = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            user_obj = None
        except User.MultipleObjectsReturned:
            messages.error(
                request,
                'Multiple accounts are using this email address.'
            )
            return render(request, 'ward/login.html')

        # Authenticate using the actual Django username
        user = None

        if user_obj:
            user = authenticate(
                request,
                username=user_obj.username,
                password=password
            )

        if user is not None:
            login(request, user)

            try:
                log_activity(user, 'Logged in')
            except Exception:
                pass

            role = get_role(user)

            if role == 'patient':
                return redirect('patient_dashboard')

            elif role == 'nurse':
                return redirect('nurse_dashboard')

            return redirect('dashboard')

        messages.error(request, 'Invalid email or password.')

    return render(request, 'ward/login.html')

def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            role = form.cleaned_data['role']

            profile = UserProfile.objects.create(
                user=user,
                role=role,
                phone=form.cleaned_data['phone']
            )

            if role.lower() == 'nurse':
                Nurse.objects.create(profile=profile)
            elif role.lower() == 'patient':
                Patient.objects.create(
                    name=f"{user.first_name} {user.last_name}",
                    age=None,
                    gender='Other',
                    contact=user.email,
                    address='',
                    created_by=user
                )

            login(request, user)
            log_activity(user, 'Registered account')
            messages.success(request, 'Registration successful.')
            return redirect('dashboard')
    else:
        form = RegisterForm()

    return render(request, 'ward/register.html', {'form': form})

def logout_view(request):
    if request.user.is_authenticated:
        log_activity(request.user, 'Logged out')
    logout(request)
    return redirect('login')

# =========================================================
# LANDING PAGES
# =========================================================

@login_required(login_url='login')
def landing(request):
    return redirect('dashboard')

@login_required(login_url='login')
def about(request):
    return render(request, 'ward/home.html', {
        'page': 'about',
        'role': get_role(request.user),
    })

@login_required(login_url='login')
def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            log_activity(request.user, 'Sent contact message')
            messages.success(request, 'Message sent successfully.')
            return redirect('contact')
    else:
        form = ContactForm()

    return render(request, 'ward/home.html', {
        'page': 'contact',
        'role': get_role(request.user),
        'contact_form': form
    })

# =========================================================
# REPORTS - Receptionist/Admin only
# =========================================================

@login_required(login_url='login')
@role_required(['receptionist', 'admin'])
def report(request):
    today = timezone.now().date()
    now = timezone.now()
    dates, counts = [], []

    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        count = Appointment.objects.filter(date_time__date=day).count()
        dates.append(day.strftime('%a'))
        counts.append(count)

    stats = {
        'appointments': Appointment.objects.count(),
        'patients': Patient.objects.count(),
        'doctors': Doctor.objects.count(),
    }

    fig, ax = plt.subplots(figsize=(8, 3))
    ax.plot(dates, counts, marker='o', color='#2563eb', linewidth=2)
    ax.fill_between(dates, counts, alpha=0.2, color='#2563eb')
    ax.set_title('Appointments Last 7 Days', fontsize=12)
    ax.set_ylabel('Count')
    ax.grid(True, alpha=0.3)
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=100)
    plt.close(fig)
    buf.seek(0)
    chart_img = base64.b64encode(buf.read()).decode('utf-8')

    return render(request, 'ward/home.html', {
        'page': 'report',
        'chart_img': chart_img,
        'role': get_role(request.user),
        'stats': stats,
        'now': now
    })

@login_required(login_url='login')
@role_required(['receptionist', 'admin'])
def export_report_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="appointment_report_7days.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Day', 'Date', 'Appointments'])
    
    today = timezone.now().date()
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        count = Appointment.objects.filter(date_time__date=day).count()
        writer.writerow([day.strftime('%a'), day.strftime('%Y-%m-%d'), count])
    
    return response
# =========================================================
# DASHBOARD - FIXED WITH DAILY DATA + UNPAID ₦ + CONSULTATION
# =========================================================
@login_required(login_url='login') 
def dashboard(request):
    role = get_role(request.user)
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    now = timezone.now()
    
    # 1. FIX: Extract appointment_id at the top of the view
    page = request.GET.get('page', 'dashboard')
    appointment_id = request.GET.get('appointment_id')
    doctor = get_doctor_profile(request.user)

    # Base querysets per role
    if role == 'doctor' and doctor:
        patients_qs = Patient.objects.filter(appointment__doctor=doctor).distinct()
        appointments_qs = Appointment.objects.filter(doctor=doctor)
        admissions_qs = Admission.objects.filter(doctor=doctor)
        invoices_qs = Invoice.objects.filter(doctor=doctor)
    else:
        patients_qs = Patient.objects.all()
        appointments_qs = Appointment.objects.all()
        admissions_qs = Admission.objects.all()
        invoices_qs = Invoice.objects.all()

    # KPI calculations
    patients_today = patients_qs.filter(created_at__date=today).count()
    patients_yesterday = patients_qs.filter(created_at__date=yesterday).count()
    patient_trend = patients_today - patients_yesterday

    appointments_today = appointments_qs.filter(date_time__date=today).count()
    
    active_admissions = admissions_qs.filter(discharge_date__isnull=True).count()
    discharged_today = admissions_qs.filter(discharge_date__date=today).count()
    
    unpaid_total = invoices_qs.filter(status='unpaid').aggregate(
        total=Sum(ExpressionWrapper(
            F('service_fee') + F('lab_fee') + F('admission_fee'),
            output_field=DecimalField(max_digits=12, decimal_places=2)
        ))
    )['total'] or 0
    unpaid_count = invoices_qs.filter(status='unpaid').count()
    
    paid_today = invoices_qs.filter(status='paid', paid_at__date=today).aggregate(
        total=Sum(ExpressionWrapper(
            F('service_fee') + F('lab_fee') + F('admission_fee'),
            output_field=DecimalField(max_digits=12, decimal_places=2)
        ))
    )['total'] or 0

    # Activity feed - last 8 activities
    activities = ActivityLog.objects.select_related('user').order_by('-timestamp')[:8]

    # Notifications
    notifications = Notification.objects.filter(user=request.user, is_read=False).order_by('-created_at')[:5]

    # Today's appointments & recent patients querysets
    today_apts_qs = appointments_qs.filter(date_time__date=today).select_related('patient', 'doctor__profile__user').order_by('date_time')
    recent_patients_qs = patients_qs.order_by('-created_at')[:5]

    # Pending consultations count
    pending_consultations_count = appointments_qs.filter(status='scheduled').count()

    context = {
        'page': page,
        'role': role,
        'today': today,
        'now': now,
        'activities': activities,
        'notifications': notifications,
        'unread_count': notifications.count(),

        # Doctor Dashboard Template Direct Variables
        'doctor_patient_count': patients_qs.count(),
        'doctor_today_appointments': appointments_today,
        'doctor_active_admissions': active_admissions,
        'doctor_pending_consultations': pending_consultations_count,
        'doctor_appointments_today': today_apts_qs,
        'doctor_recent_patients': recent_patients_qs,

        'stats': {
            'patients': patients_qs.count(),
            'patients_today': patients_today,
            'patient_trend': patient_trend,
            'appointments': appointments_today,
            'admissions': active_admissions,
            'discharged_today': discharged_today,
            'unpaid': unpaid_total,
            'unpaid_count': unpaid_count,
            'paid_today': paid_today,
            'doctors_on_duty': Doctor.objects.count(),
            'available_beds': 14,  
            'departments_open': 6,
        },
        'today_appointments': today_apts_qs,
        'recent_patients': recent_patients_qs,
        'recent_admissions': admissions_qs.filter(admission_date__date=today).select_related('patient', 'ward').order_by('-admission_date')[:5],
    }

    # Page router logic
    if page == 'patients':
        patients = patients_qs.prefetch_related(
            "medical_records__doctor__profile__user"
        ).order_by("-id")
        search = request.GET.get('search')
        gender = request.GET.get('gender')
        if search:
            patients = patients.filter(Q(name__icontains=search) | Q(contact__icontains=search) | Q(patient_id__icontains=search))
        if gender:
            patients = patients.filter(gender=gender)
        paginator = Paginator(patients, 10)
        page_num = request.GET.get('page_num', 1)
        context['patients'] = paginator.get_page(page_num)
        context['patient_form'] = PatientForm()

    elif page == 'patient_detail':
        patient_id = request.GET.get('id')
        patient = Patient.objects.filter(id=patient_id).first()

        if not patient:
            messages.error(request, "Patient not found.")
            return redirect('/dashboard/?page=patients')

        medical_records = MedicalRecord.objects.filter(
            patient=patient
        ).select_related(
            'doctor',
            'doctor__profile',
            'doctor__profile__user'
        ).order_by('-created_at')

        context.update({
            'patient': patient,
            'medical_records': medical_records,
        })

    elif page == 'create_patient':
        context['patient_form'] = PatientForm()

    elif page == 'appointments':
        appointments = appointments_qs.select_related('patient', 'doctor__profile__user').order_by('-date_time')
        
        search_query = request.GET.get('search', '').strip()
        if search_query:
            appointments = appointments.filter(
                Q(doctor__profile__user__first_name__icontains=search_query) |
                Q(doctor__profile__user__last_name__icontains=search_query) |
                Q(doctor__profile__user__username__icontains=search_query) |
                Q(patient__name__icontains=search_query)  
            )
        
        status = request.GET.get('status')
        if status:
            appointments = appointments.filter(status=status)

        paginator = Paginator(appointments, 10) 
        page_num = request.GET.get('page_num', 1)
        
        context['appointments'] = paginator.get_page(page_num)
        context['appointment_form'] = AppointmentForm()

    elif page == 'consultation' and appointment_id:
        appointment = Appointment.objects.filter(id=appointment_id).first()
        if not appointment:
            messages.error(request, 'Appointment not found.')
            return redirect('/dashboard/?page=appointments')

        if request.method == 'POST':
            form = ConsultationForm(request.POST)
            if form.is_valid():
                consultation = form.save(commit=False)
                consultation.appointment = appointment
                consultation.patient = appointment.patient
                consultation.doctor = appointment.doctor
                consultation.save()

                messages.success(
                    request,
                    'Consultation completed successfully.'
                )
                return redirect('/dashboard/?page=appointments')
        else:
            form = ConsultationForm()

        context['appointment'] = appointment
        context['form'] = form

    elif page == 'view_consultation' and appointment_id:
        appointment = Appointment.objects.filter(id=appointment_id).first()
        if not appointment:
            messages.error(request, 'Appointment not found.')
            return redirect('/dashboard/?page=appointments')
            
        context['appointment'] = appointment
        context['consultation'] = getattr(appointment, 'consultation', None)
        return render(request, 'ward/home.html', context)

    elif page == 'create_appointment':
        context['appointment_form'] = AppointmentForm()

    elif page == 'edit_appointment':
        appointment_id = request.GET.get('id')
        appointment = Appointment.objects.filter(id=appointment_id).first()

        if not appointment:
            messages.error(request, 'Appointment not found.')
            return redirect('/dashboard/?page=appointments')

        if role == 'doctor' and doctor and appointment.doctor != doctor:
            messages.error(request, 'You can only edit your own appointments.')
            return redirect('/dashboard/?page=appointments')

        if request.method == 'POST':
            appointment_form = AppointmentForm(request.POST, instance=appointment)
            if appointment_form.is_valid():
                appointment_form.save()
                messages.success(request, 'Appointment updated successfully.')
                return redirect('/dashboard/?page=appointments')
        else:
            appointment_form = AppointmentForm(instance=appointment)

        context['appointment'] = appointment
        context['appointment_form'] = appointment_form

    elif page == 'admissions':
        pass

    elif page == 'notifications':
        context['notifications'] = Notification.objects.filter(
            user=request.user
        ).order_by('-created_at')

    elif page == 'profile':
        context['role'] = role
        context['profile_form'] = ProfileForm(instance=request.user.profile, user=request.user)

    return render(request, 'ward/home.html', context)

# =========================================================
# CONSULTATION VIEWS (UPDATED WITHOUT 404)
# =========================================================
@login_required
def create_consultation(request, appointment_id):
    # Filter instead of get_object_or_404
    appointment = Appointment.objects.filter(id=appointment_id).first()
    if not appointment:
        messages.error(request, 'Appointment not found.')
        return redirect('/dashboard/?page=appointments')

    profile = request.user.profile
    role = profile.role

    if role == 'doctor' and appointment.doctor != profile:
        messages.error(request, 'You can only consult your assigned patients.')
        return redirect('/dashboard/?page=appointments')

    if hasattr(appointment, 'consultation'):
        messages.info(request, 'Consultation already exists for this appointment.')
        return redirect('view_consultation', appointment_id=appointment.id)

    if request.method == 'POST':
        form = ConsultationForm(request.POST)
        if form.is_valid():
            consultation = form.save(commit=False)
            consultation.appointment = appointment
            consultation.doctor = profile
            consultation.save()
            
            appointment.status = 'completed'
            appointment.save()
            
            messages.success(request, f'Consultation for {appointment.patient.name} completed successfully.')
            return redirect('view_consultation', appointment_id=appointment.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ConsultationForm()

    context = {
        'form': form,
        'appointment': appointment,
        'page': 'consultation',
        'role': role,
    }
    return render(request, 'ward/home.html', context)

@login_required
def view_consultation(request, appointment_id):
    # Filter instead of get_object_or_404
    appointment = Appointment.objects.filter(id=appointment_id).first()
    if not appointment:
        messages.error(request, 'Appointment not found.')
        return redirect('/dashboard/?page=appointments')

    profile = request.user.profile
    role = profile.role

    if role == 'doctor' and appointment.doctor != profile:
        messages.error(request, 'You do not have permission to view this consultation.')
        return redirect('/dashboard/?page=appointments')
        
    consultation = getattr(appointment, 'consultation', None)
    if not consultation:
        messages.warning(request, 'No consultation found for this appointment.')
        return redirect('/dashboard/?page=appointments')

    context = {
        'appointment': appointment,
        'consultation': consultation,
        'page': 'view_consultation',
        'role': role,
    }
    return render(request, 'ward/home.html', context)
# =========================================================
# NURSE DASHBOARD
# =========================================================

@role_required(['nurse'])
def nurse_dashboard(request):
    nurse = Nurse.objects.filter(profile=request.user.profile).first()
    patients = Patient.objects.filter(assigned_nurse=nurse) if nurse else Patient.objects.none()

    return render(request, 'ward/nurse_dashboard.html', {
        'page': 'nurse_dashboard',
        'role': 'Nurse',
        'nurse': nurse,
        'patients': patients,
    })


# =========================================================
# DOCTOR CRUD - Admin only
# =========================================================

@login_required(login_url='login')
@role_required(['admin'])
def doctor_list(request):
    doctors = Doctor.objects.all().order_by('id')
    return render(request, 'ward/home.html', {
        'page': 'doctors',
        'role': get_role(request.user),
        'doctors': doctors,
    })


@login_required(login_url='login')
@role_required(['admin'])
def add_doctor(request):
    if request.method == 'POST':
        form = DoctorCreateForm(request.POST)
        if form.is_valid():
            doctor = form.save()
            log_activity(request.user, 'Added doctor', doctor)
            messages.success(request, 'Doctor added successfully.')
    return redirect('/dashboard/?page=doctors')

@login_required(login_url='login')
@role_required(['admin'])
def edit_doctor(request, doctor_id):
    doctor = Doctor.objects.filter(id=doctor_id).first()

    if not doctor:
        messages.error(request, 'Doctor not found.')
        return redirect('doctor_list')

    if request.method == 'POST':
        form = DoctorEditForm(request.POST, instance=doctor)
        if form.is_valid():
            form.save()
            log_activity(request.user, 'Edited doctor', doctor)
            messages.success(request, 'Doctor updated successfully.')
            return redirect('doctor_list')
    
    return render(request, 'ward/home.html', {
        'page': 'edit_doctor',
        'doctor_form': DoctorEditForm(instance=doctor),
        'doctor': doctor,
        'role': get_role(request.user),
    })

@login_required(login_url='login')
@role_required(['admin'])
def delete_doctor(request, doctor_id):
    doctor = Doctor.objects.filter(id=doctor_id).first()
    if doctor and request.method == 'POST':
        log_activity(request.user, 'Deleted doctor', doctor)
        doctor.delete()
        messages.success(request, 'Doctor deleted successfully.')
    else:
        messages.error(request, 'Doctor not found.')
    return redirect('doctor_list')

# =========================================================
# PATIENT CRUD - Receptionist/Admin/Doctor
# =========================================================

@login_required(login_url='login')
@role_required(['receptionist', 'admin', 'doctor'])
def add_patient(request):
    if request.method == 'POST':
        form = PatientForm(request.POST)
        if form.is_valid():
            patient = form.save(commit=False)
            patient.created_by = request.user
            patient.save()
            notify_patient_registered(patient)
            log_activity(request.user, 'Added patient', patient)
            messages.success(request, 'Patient added successfully.')
    return redirect('/dashboard/?page=patients')

@login_required(login_url='login')
def edit_patient(request, patient_id):
    patient = Patient.objects.filter(id=patient_id).first()

    if not patient:
        messages.error(request, 'Patient not found.')
        return redirect('/dashboard/?page=patients')

    role = get_role(request.user)
    doctor = get_doctor_profile(request.user)
    if role == 'doctor' and doctor:
        if not Appointment.objects.filter(patient=patient, doctor=doctor).exists():
            messages.error(request, 'You can only edit your assigned patients.')
            return redirect('/dashboard/?page=patients')

    if request.method == 'POST':
        form = PatientForm(request.POST, instance=patient)
        if form.is_valid():
            patient = form.save()
            log_activity(
                request.user,
                f"Updated patient record for {patient.name}",
                patient
            )
            messages.success(request, "Patient updated successfully.")
            return redirect('/dashboard/?page=patients')
    else:
        form = PatientForm(instance=patient)
    
    return render(request, 'ward/home.html', {
        'page': 'edit_patient',
        'patient_form': form,                                        
        'patient': patient,
        'role': role,      
    })

@login_required(login_url='login')
@role_required(['receptionist', 'admin'])
def delete_patient(request, patient_id):
    patient = Patient.objects.filter(id=patient_id).first()
    if patient and request.method == 'POST':
        log_activity(request.user, 'Deleted patient', patient)
        patient.delete()
        messages.success(request, 'Patient deleted successfully.')
    else:
        messages.error(request, 'Patient not found.')
    return redirect('/dashboard/?page=patients')

# =========================================================
# APPOINTMENTS - Receptionist/Admin/Doctor
# =========================================================

@login_required
def create_appointment(request):
    role = get_role(request.user)
    
    if role not in ['admin', 'receptionist']:
        messages.error(request, 'Only Admin/Receptionist can book appointments.')
        return redirect('/dashboard/?page=appointments')

    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.created_by = request.user
            
            # HANDLE NEW PATIENT CREATION - FIXED
            new_name = form.cleaned_data.get('new_patient_name', '').strip()
            existing_patient = form.cleaned_data.get('patient')
            
            if new_name and not existing_patient:
                new_patient = Patient.objects.create(
                    name=new_name,
                    age=form.cleaned_data.get('new_patient_age'),
                    gender=form.cleaned_data.get('new_patient_gender'),
                    contact=form.cleaned_data.get('new_patient_contact', ''),
                    address=form.cleaned_data.get('new_patient_address', ''),
                    created_by=request.user
                )
                appointment.patient = new_patient
            elif existing_patient:
                appointment.patient = existing_patient
            else:
                messages.error(request, 'Please select a patient or enter new patient details.')
                context = {'appointment_form': form, 'page': 'create_appointment', 'role': role}
                return render(request, 'ward/home.html', context)
            
            appointment.save()
            messages.success(request, f'Appointment booked for {appointment.patient.name}')
            return redirect('/dashboard/?page=appointments')
        else:
            messages.error(request, f'Please fix errors: {form.errors}')
    else:
        form = AppointmentForm()

    context = {
        'appointment_form': form,
        'page': 'create_appointment',
        'role': role,
    }
    return render(request, 'ward/home.html', context)
@login_required
def create_consultation(request, appointment_id):
    appointment = Appointment.objects.select_related(
        'patient',
        'doctor__profile__user'
    ).filter(id=appointment_id).first()

    if not appointment:
        messages.error(request, 'Appointment not found.')
        return redirect('/dashboard/?page=appointments')

    profile = request.user.profile
    role = str(profile.role).lower().strip()

    # ---------------------------------------------------------
    # SECURITY: Only the assigned doctor can start consultation
    # ---------------------------------------------------------
    if role == 'doctor':
        assigned_doctor_user_id = appointment.doctor.profile.user_id

        if assigned_doctor_user_id != request.user.id:
            messages.error(
                request,
                'You can only consult patients assigned to you.'
            )
            return redirect('/dashboard/?page=appointments')

    # ---------------------------------------------------------
    # Prevent duplicate consultation
    # ---------------------------------------------------------
    if hasattr(appointment, 'consultation'):
        messages.info(
            request,
            'Consultation already exists for this appointment.'
        )
        return redirect(
            'view_consultation',
            appointment_id=appointment.id
        )

    # ---------------------------------------------------------
    # POST - Save consultation
    # ---------------------------------------------------------
    if request.method == 'POST':
        form = ConsultationForm(request.POST)

        if form.is_valid():
            consultation = form.save(commit=False)

            consultation.appointment = appointment
            consultation.patient = appointment.patient
            consultation.doctor = appointment.doctor

            consultation.save()

            # Mark appointment as completed
            appointment.status = 'completed'
            appointment.save(update_fields=['status'])

            # Create Medical Record
            MedicalRecord.objects.create(
                patient=appointment.patient,
                doctor=appointment.doctor,
                record_type='consultation',
                diagnosis=consultation.diagnosis,
                prescription=consultation.prescription,
                notes=consultation.visit_notes
            )

            messages.success(
                request,
                f'Consultation for {appointment.patient.name} '
                f'completed successfully.'
            )

            return redirect(
                'view_consultation',
                appointment_id=appointment.id
            )

    else:
        form = ConsultationForm()

    context = {
        'form': form,
        'appointment': appointment,
        'page': 'consultation',
        'role': role,
    }

    return render(request, 'ward/home.html', context)
@login_required
def view_consultation(request, appointment_id):
    appointment = Appointment.objects.select_related(
        'patient',
        'doctor__profile__user'
    ).filter(id=appointment_id).first()

    if not appointment:
        messages.error(request, 'Appointment not found.')
        return redirect('/dashboard/?page=appointments')

    profile = request.user.profile
    role = str(profile.role).lower().strip()

    # ---------------------------------------------------------
    # SECURITY
    # Doctor can only view consultations assigned to them.
    # Admin and receptionist can view all consultations.
    # ---------------------------------------------------------
    if role == 'doctor':
        assigned_doctor_user_id = appointment.doctor.profile.user_id

        if assigned_doctor_user_id != request.user.id:
            messages.error(
                request,
                'You do not have permission to view this consultation.'
            )
            return redirect('/dashboard/?page=appointments')

    elif role not in ['admin', 'receptionist']:
        messages.error(
            request,
            'You do not have permission to view this consultation.'
        )
        return redirect('/dashboard/?page=appointments')

    # ---------------------------------------------------------
    # Get consultation
    # ---------------------------------------------------------
    consultation = getattr(appointment, 'consultation', None)

    if not consultation:
        messages.warning(
            request,
            'No consultation found for this appointment.'
        )
        return redirect('/dashboard/?page=appointments')

    context = {
        'appointment': appointment,
        'consultation': consultation,
        'page': 'view_consultation',
        'role': role,
    }

    return render(
        request,
        'ward/home.html',
        context
    )
@login_required(login_url='login')
@role_required(['receptionist', 'admin', 'doctor'])
def edit_appointment(request, appointment_id):
    appointment = Appointment.objects.filter(id=appointment_id).first()

    if not appointment:
        messages.error(request, 'Appointment not found.')
        return redirect('/dashboard/?page=appointments')

    role = get_role(request.user)
    doctor = get_doctor_profile(request.user)
    
    if role == 'doctor' and doctor:
        if appointment.doctor != doctor:
            messages.error(request, 'You can only edit your own appointments.')
            return redirect('/dashboard/?page=appointments')

    if request.method == 'POST':
        form = AppointmentForm(request.POST, instance=appointment)
        if form.is_valid():
            new_name = form.cleaned_data.get('new_patient_name', '').strip()
            new_age = form.cleaned_data.get('new_patient_age')
            new_gender = form.cleaned_data.get('new_patient_gender')
            if new_name and not form.cleaned_data.get('patient'):
                patient = Patient.objects.create(
                    name=new_name,
                    age=new_age,
                    gender=new_gender or 'Other',
                    contact='',
                    created_by=request.user
                )
                form.instance.patient = patient
            
            form.save()
            log_activity(request.user, 'Edited appointment', appointment)
            messages.success(request, 'Appointment updated successfully.')
            return redirect('/dashboard/?page=appointments')
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = AppointmentForm(instance=appointment)
    
    return render(request, 'ward/home.html', {
        'page': 'edit_appointment',
        'appointment_form': form,
        'appointment': appointment,
        'role': role,
    })
@login_required
def create_consultation(request, appointment_id):
    appointment = Appointment.objects.filter(id=appointment_id).first()
    profile = request.user.profile
    role = profile.role

    # Handle if appointment doesn't exist
    if not appointment:
        messages.error(request, 'Appointment not found.')
        return redirect('/dashboard/?page=appointments')

    # SECURITY: Only the assigned doctor can consult
    if role == 'doctor' and appointment.doctor != profile:
        messages.error(request, 'You can only consult your assigned patients.')
        return redirect('/dashboard/?page=appointments')

    # Prevent double consultation
    if hasattr(appointment, 'consultation'):
        messages.info(request, 'Consultation already exists for this appointment.')
        return redirect('view_consultation', appointment_id=appointment.id)

    if request.method == 'POST':
        form = ConsultationForm(request.POST)
        if form.is_valid():
            consultation = form.save(commit=False)
            consultation.appointment = appointment
            consultation.doctor = profile
            consultation.save()
            
            # Auto mark appointment as completed
            appointment.status = 'completed'
            appointment.save()
            
            messages.success(request, f'Consultation for {appointment.patient.name} completed successfully.')
            return redirect('view_consultation', appointment_id=appointment.id)
        else:
            messages.error(request, 'Please fill all required fields correctly.')
    else:
        form = ConsultationForm()

    context = {
        'form': form,
        'appointment': appointment,
        'page': 'consultation',
        'role': role,
    }
    return render(request, 'ward/home.html', context)

@login_required
def view_consultation(request, appointment_id):
    appointment = Appointment.objects.filter(id=appointment_id).first()
    profile = request.user.profile
    role = profile.role

    # Handle if appointment doesn't exist
    if not appointment:
        messages.error(request, 'Appointment not found.')
        return redirect('/dashboard/?page=appointments')

    # SECURITY: Only assigned doctor, admin, or receptionist can view
    if role == 'doctor' and appointment.doctor != profile:
        messages.error(request, 'You do not have permission to view this consultation.')
        return redirect('/dashboard/?page=appointments')
        
    consultation = getattr(appointment, 'consultation', None)
    if not consultation:
        messages.warning(request, 'No consultation found for this appointment.')
        return redirect('/dashboard/?page=appointments')

    context = {
        'appointment': appointment,
        'consultation': consultation,
        'page': 'view_consultation',
        'role': role,
    }
    return render(request, 'ward/home.html', context)
@login_required(login_url='login')
@role_required(['admin', 'receptionist'])  
def delete_appointment(request, appointment_id):
    if request.method == 'POST':
        appointment = Appointment.objects.filter(id=appointment_id).first()
        if appointment:
            log_activity(request.user, 'Deleted appointment', appointment)
            appointment.delete()
            messages.success(request, 'Appointment deleted successfully.')
        else:
            messages.error(request, 'Appointment not found.')
    else:
        messages.error(request, 'Invalid request method.')
        
    
    return redirect('/dashboard/?page=appointments')
@login_required(login_url='login')
def patient_detail(request, pk):
    patient = Patient.objects.filter(id=pk).first()
    if not patient:
        messages.error(request, 'Patient not found.')
        return redirect('/dashboard/?page=patients')
    
    role = get_role(request.user)
    doctor = get_doctor_profile(request.user)
    
    if role == 'doctor' and doctor:
        if not Appointment.objects.filter(patient=patient, doctor=doctor).exists():
            messages.error(request, 'Access denied.')
            return redirect('/dashboard/?page=patients')
    
    appointments = Appointment.objects.filter(patient=patient).order_by('-date_time')[:5]
    
    return render(request, 'ward/home.html', {
        'page': 'patient_detail',
        'patient': patient,
        'appointments': appointments,
        'role': role,
    })

# =========================================================
# ADMISSIONS - Receptionist/Admin/Doctor
# =========================================================

@login_required(login_url='login')
@role_required(['receptionist', 'admin', 'doctor'])
def admit_patient(request):
    if request.method != 'POST':
        return redirect('/dashboard/?page=admissions')

    form = AdmissionForm(request.POST)
    if form.is_valid():
        admission = form.save(commit=False)
        admission.status = 'admitted'
        admission.save()

        try:
            notify_patient_admitted(admission)
        except Exception:
            pass

        try:
            log_activity(request.user, f'Admitted patient {admission.patient.name}', admission)
        except Exception:
            pass

        messages.success(request, f'{admission.patient.name} admitted successfully.')
    else:
        error_list = []
        for field, errors in form.errors.items():
            for error in errors:
                if field == '__all__':
                    error_list.append(error)
                else:
                    error_list.append(f"{field}: {error}")
        messages.error(request, "Admission failed. " + " | ".join(error_list))

    return redirect('/dashboard/?page=admissions')


@login_required(login_url='login')
@role_required(['receptionist', 'admin', 'doctor'])
def edit_admission(request):
    if request.method == "POST":
        admission = Admission.objects.filter(id=request.POST.get("edit_id")).first()
        if admission:
            admission.ward_id = request.POST.get("ward")
            admission.doctor_id = request.POST.get("doctor")
            admission.diagnosis = request.POST.get("diagnosis")
            admission.save()
            messages.success(request, "Admission updated successfully.")
        else:
            messages.error(request, "Admission record not found.")

    return redirect('/dashboard/?page=admissions') 


@login_required(login_url='login')
@role_required(['receptionist', 'admin', 'doctor'])
def admissions_view(request):
    role = get_role(request.user)
    doctor = get_doctor_profile(request.user)
    
    admissions = Admission.objects.select_related('patient', 'ward', 'doctor__user').all()
    
    q = request.GET.get('q')
    if q:
        admissions = admissions.filter(
            Q(patient__name__icontains=q) |
            Q(patient__patient_id__icontains=q) |
            Q(ward__name__icontains=q) |
            Q(doctor__user__first_name__icontains=q) |
            Q(doctor__user__last_name__icontains=q)
        )
    
    ward_id = request.GET.get('ward')
    if ward_id:
        admissions = admissions.filter(ward_id=ward_id)
    
    status = request.GET.get('status')
    if status == 'admitted':
        admissions = admissions.filter(status='admitted')
    elif status == 'discharged':
        admissions = admissions.filter(status='discharged')
    
    start_date = request.GET.get('start_date')
    if start_date:
        admissions = admissions.filter(admission_date__date__gte=start_date)
    
    admissions = admissions.order_by('-admission_date')
    
    total_admissions = Admission.objects.count()
    admitted_count = Admission.objects.filter(status='admitted').count()
    discharged_today = Admission.objects.filter(
        status='discharged', 
        discharge_date__date=timezone.now().date()
    ).count()
    emergency_count = Admission.objects.filter(status='admitted', is_emergency=True).count()
    pending_discharge = Admission.objects.filter(status='admitted', pending_discharge=True).count()
    
    ward_stats = Admission.objects.filter(status='admitted').values('ward__name').annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    total_active = admitted_count or 1
    for w in ward_stats:
        w['percent'] = round((w['count'] / total_active) * 100)
    
    recent_admissions = Admission.objects.select_related('patient', 'ward').order_by('-admission_date')[:5]
    
    admission_form = AdmissionForm()
    wards = Ward.objects.all()
    doctors = Doctor.objects.select_related('user').filter(is_active=True)
    
    if request.method == 'POST':
        if 'admit_patient' in request.POST:
            admission_form = AdmissionForm(request.POST)

            if admission_form.is_valid():
                admission = admission_form.save(commit=False)
                admission.status = 'admitted'

                # Only keep this if diagnosis exists in your Admission model
                diagnosis = request.POST.get('diagnosis')
                if diagnosis:
                    admission.diagnosis = diagnosis

                admission.save()

                messages.success(
                    request,
                    f'{admission.patient.name} admitted successfully.'
                )

                try:
                    notify_patient_admitted(admission)
                except Exception:
                    pass

                try:
                    log_activity(
                        request.user,
                        f'Admitted patient {admission.patient.name}',
                        admission
                    )
                except Exception:
                    pass

                return redirect('/dashboard/?page=admissions')

            else:
                print(admission_form.errors)
                messages.error(
                    request,
                    admission_form.errors.as_text()
                )
        
        elif 'discharge' in request.POST:
            discharge_id = request.POST.get('discharge_id')
            admission = Admission.objects.filter(id=discharge_id).first()
            if admission and admission.status == 'admitted':
                admission.status = 'discharged'
                admission.discharge_date = timezone.now()
                admission.save()
                log_activity(request.user, f"Discharged patient {admission.patient.name}", admission.patient)
                messages.success(request, f'{admission.patient.name} discharged successfully.')
            else:
                messages.error(request, 'Admission not found or already discharged.')
            return redirect('/dashboard/?page=admissions')
        
        elif 'edit_id' in request.POST:
            edit_id = request.POST.get('edit_id')
            admission = Admission.objects.filter(id=edit_id).first()
            
            if not admission:
                messages.error(request, 'Admission record not found.')
                return redirect('/dashboard/?page=admissions')
            
            if role == 'doctor' and doctor:
                if admission.doctor != doctor:
                    messages.error(request, 'You can only edit your assigned patients.')
                    return redirect('/dashboard/?page=admissions')
            
            ward_id = request.POST.get('ward')
            doctor_id = request.POST.get('doctor')
            diagnosis = request.POST.get('diagnosis')
            
            if ward_id:
                admission.ward_id = ward_id
            if doctor_id:
                admission.doctor_id = doctor_id
            if diagnosis:
                admission.diagnosis = diagnosis
            
            admission.save()
            log_activity(request.user, f"Updated admission for {admission.patient.name}", admission.patient)
            messages.success(request, 'Admission updated successfully.')
            return redirect('/dashboard/?page=admissions')
    
    context = {
        'page': 'admissions',
        'admissions': admissions,
        'admission_form': admission_form,
        'wards': wards,
        'doctors': doctors,
        'total_admissions': total_admissions,
        'admitted_count': admitted_count,
        'discharged_today': discharged_today,
        'emergency_count': emergency_count,
        'pending_discharge': pending_discharge,
        'ward_stats': ward_stats,
        'recent_admissions': recent_admissions,
        'role': role,
    }
    
    return render(request, 'ward/home.html', context)
# =========================================================
# CONSULTATION - Doctor only
# =========================================================

@login_required(login_url='login')
@role_required(['doctor'])
def create_consultation(request, appointment_id):
    appointment = Appointment.objects.filter(id=appointment_id).first()

    if not appointment:
        messages.error(request, 'Appointment not found.')
        return redirect('/dashboard/?page=appointments')

    doctor = get_doctor_profile(request.user)
    if appointment.doctor != doctor:
        messages.error(request, 'Not your appointment.')
        return redirect('/dashboard/?page=appointments')

    if request.method == 'POST':
        form = ConsultationForm(request.POST)
        if form.is_valid():
            consultation = form.save(commit=False)
            consultation.appointment = appointment
            consultation.save()
            notify_consultation_complete(consultation)
            log_activity(request.user, 'Created consultation', consultation)
            messages.success(request, 'Consultation completed.')
    return redirect('/dashboard/?page=appointments')

# =========================================================
# PRESCRIPTIONS - Doctor only
# =========================================================

@login_required(login_url='login')
@role_required(['doctor'])
def create_prescription(request):
    doctor = get_doctor_profile(request.user)

    if not doctor:
        messages.error(request, 'Doctor profile not found.')
        return redirect('/dashboard/?page=prescriptions')

    if request.method == 'POST':
        form = PrescriptionForm(request.POST)

        if form.is_valid():
            prescription = form.save(commit=False)
            prescription.doctor = doctor
            
            # --- CHANGE THIS LINE TO 'Pending' ---
            prescription.status = 'Pending'
            # -------------------------------------
            
            prescription.save()

            PrescriptionItem.objects.create(
                prescription=prescription,
                drug_name=request.POST.get('drug_name'),
                dosage=request.POST.get('dosage'),
                frequency=request.POST.get('frequency'),
                duration=request.POST.get('duration'),
                quantity=request.POST.get('quantity') or 1
            )

            log_activity(
                request.user,
                f'Created prescription for {prescription.patient}',
                prescription
            )

            messages.success(request, 'Prescription created successfully.')
            return redirect('/dashboard/?page=prescriptions')

        else:
            messages.error(request, f'Form errors: {form.errors}')
            return redirect('/dashboard/?page=prescriptions')

    return redirect('/dashboard/?page=prescriptions')

@login_required(login_url='login')
def view_prescription(request, pk):
    prescription = Prescription.objects.select_related(
        'patient',
        'doctor'
    ).filter(pk=pk).first()

    if not prescription:
        messages.error(request, 'Prescription not found.')
        return redirect('/dashboard/?page=prescriptions')

    items = prescription.items.all()

    return render(
        request,
        'ward/home.html',
        {
            'page': 'view_prescription',
            'prescription': prescription,
            'items': items,
            'role': get_role(request.user),
            'user': request.user,
        }
    )

@login_required(login_url='login')
@role_required(['doctor'])
def edit_prescription(request, pk):
    prescription = Prescription.objects.filter(id=pk).first()

    if not prescription:
        messages.error(request, 'Prescription not found.')
        return redirect('/dashboard/?page=prescriptions')

    ItemFormSet = inlineformset_factory(
        Prescription, 
        PrescriptionItem, 
        form=PrescriptionItemForm, 
        extra=0,
        can_delete=True
    )

    if request.method == 'POST':
        form = PrescriptionForm(request.POST, instance=prescription)
        formset = ItemFormSet(request.POST, instance=prescription)

        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, 'Prescription updated successfully.')
            return redirect('/dashboard/?page=prescriptions')
        else:
            messages.error(request, 'Please fix errors below')
    else:
        form = PrescriptionForm(instance=prescription)
        formset = ItemFormSet(instance=prescription)

    return render(
        request,
        'ward/home.html',
        {
            'page': 'edit_prescription',
            'role': get_role(request.user),
            'prescription': prescription,
            'form': form,
            'formset': formset,
        }
    )

@login_required
def delete_medical_record(request, record_id):
    is_doctor = Doctor.objects.filter(profile__user=request.user).exists()
    
    if not is_doctor: 
        messages.error(request, "You do not have permission to delete medical records.")
        return redirect('/dashboard/?page=medical_records')

    if request.method == 'POST':
        record = MedicalRecord.objects.filter(id=record_id).first()
        if record:
            record.delete()
            messages.success(request, "Medical record deleted successfully.")
        else:
            messages.error(request, "The medical record you are trying to delete does not exist.")
        
    return redirect('/dashboard/?page=medical_records')

@login_required(login_url='login')
@role_required(['doctor'])
def delete_prescription(request, pk):
    prescription = Prescription.objects.filter(id=pk).first()

    if not prescription:
        messages.error(request, 'Prescription not found.')
        return redirect('/dashboard/?page=prescriptions')

    prescription.delete()
    messages.success(request, 'Prescription deleted successfully.')
    return redirect('/dashboard/?page=prescriptions')

# =========================================================
# MEDICAL RECORDS - Doctor only
# =========================================================

@login_required(login_url='login')
@role_required(['doctor'])
def add_medical_record(request):
    if request.method == 'POST':
        form = MedicalRecordForm(
            request.POST,
            request.FILES,
            user=request.user
        )

        if form.is_valid():
            record = form.save(commit=False)
            doctor = get_doctor_profile(request.user)

            if not doctor:
                messages.error(request, 'Doctor profile not found.')
                return redirect('/dashboard/?page=medical_records')

            record.doctor = doctor
            record.save()

            messages.success(request, 'Medical record added successfully.')
            return redirect('/dashboard/?page=medical_records')
        else:
            messages.error(request, form.errors)

    return redirect('/dashboard/?page=medical_records')

# =========================================================
# MEDICINE & PHARMACY - Receptionist/Admin only
# =========================================================

@login_required(login_url='login')
@role_required(['admin', 'receptionist'])
def add_medicine(request):
    if request.method == 'POST':
        form = MedicineForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Medicine added successfully.')
        else:
            messages.error(request, 'Please correct the errors below.')

    return redirect('/dashboard/?page=pharmacy')
@login_required(login_url='login')
@role_required(['receptionist', 'admin'])
def dispense_prescription(request, prescription_id):
    if request.method == 'POST':
        # Retrieve the prescription or return a 404 error if it doesn't exist
        prescription = Prescription.objects.get(id=prescription_id)
        
        # Update the status so it clears from the active waiting queue
        prescription.status = 'Completed'
        prescription.save()
        
        # Log the activity (using your existing log_activity function)
        log_activity(
            request.user,
            f'Dispensed prescription for {prescription.patient}',
            prescription
        )
        
        messages.success(request, f'Prescription for {prescription.patient.name} has been successfully dispensed.')
        return redirect('/dashboard/?page=pharmacy')
        
    # If someone tries to access via GET, just send them back to the pharmacy page
    return redirect('/dashboard/?page=pharmacy')
@login_required(login_url='login')
@role_required(['admin', 'receptionist'])
def edit_medicine(request, medicine_id):
    medicine = Medicine.objects.filter(id=medicine_id).first()

    if not medicine:
        messages.error(request, 'Medicine not found.')
        return redirect('/dashboard/?page=pharmacy')

    if request.method == 'POST':
        form = MedicineForm(request.POST, instance=medicine)
        if form.is_valid():
            form.save()
            messages.success(request, 'Medicine updated successfully.')
        else:
            messages.error(request, 'Please correct the errors below.')

    return redirect('/dashboard/?page=pharmacy')

@login_required(login_url='login')
@role_required(['admin', 'receptionist'])
def delete_medicine(request, medicine_id):
    medicine = Medicine.objects.filter(id=medicine_id).first()

    if not medicine:
        messages.error(request, 'Medicine not found.')
        return redirect('/dashboard/?page=pharmacy')

    if request.method == 'POST':
        medicine.delete()
        messages.success(request, 'Medicine deleted successfully.')

    return redirect('/dashboard/?page=pharmacy')

@login_required(login_url='login')
def export_medicines(request):
    """
    Exports the current pharmaceutical medicine records as a downloadable CSV.
    """
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="medicine_inventory.csv"'

    writer = csv.writer(response)
    writer.writerow(['ID', 'Name', 'Category', 'Quantity in Stock', 'Price (₦)', 'Expiry Date'])

    medicines = Medicine.objects.all().order_by('name')
    for med in medicines:
        writer.writerow([
            med.id,
            getattr(med, 'name', 'N/A'),
            getattr(med, 'category', 'N/A'),
            getattr(med, 'quantity_in_stock', 0),
            getattr(med, 'price', 0.0),
            med.expiry_date.strftime('%Y-%m-%d') if med.expiry_date else 'N/A'
        ])

    return response

# =========================================================
# laboratory test requests - Receptionist/Admin/Doctor
# =========================================================

@login_required
def create_test_request(request):
    if request.method == "POST":
        form = LaboratoryTestForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Laboratory test request created successfully.")
            return redirect("/dashboard/?page=laboratory")
    else:
        form = LaboratoryTestForm()

    return render(request, "ward/home.html", {
        "page": "laboratory",
        "lab_form": form,
    })
def collect_sample(request, test_id):
    test = LaboratoryTest.objects.filter(id=test_id).first()

    if not test:
        messages.error(request, "Laboratory test not found.")
        return redirect("/dashboard/?page=laboratory")

    if request.method == "POST":
        test.status = "Processing"
        test.save()
        messages.success(request, "Sample collected successfully.")

    return redirect("/dashboard/?page=laboratory")
def input_lab_result(request, test_id):
    test = LaboratoryTest.objects.get(id=test_id)

    if request.method == "POST":
        test.result = request.POST.get("result_details")
        test.status = "Completed"
        test.save()

        messages.success(request, "Laboratory result saved successfully.")

    return redirect("/dashboard/?page=laboratory")
def view_lab_report(request, pk):
    test = LaboratoryTest.objects.get(pk=pk)

    context = {
        "test": test,
    }

    return render(request,"ward/home.html", context)    
@login_required
def laboratory(request):

    tests = LaboratoryTest.objects.select_related(
        'patient',
        'doctor__user'
    )

    q = request.GET.get("q")

    if q:
        tests = tests.filter(

            Q(patient__name__icontains=q) |
            Q(test_name__icontains=q) |
            Q(sample_type__icontains=q)

        )

    pending = LaboratoryTest.objects.filter(
        status="Pending"
    ).count()

    processing = LaboratoryTest.objects.filter(
        status="Processing"
    ).count()

    completed = LaboratoryTest.objects.filter(
        status="Completed",
        completed_date__date=timezone.now().date()
    ).count()

    urgent = LaboratoryTest.objects.filter(
        priority="Critical"
    ).count()

    context = {

        "tests": tests,

        "pending": pending,

        "processing": processing,

        "completed": completed,

        "urgent": urgent,

        "lab_form": LaboratoryTestForm(),

        "page":"laboratory",

    }

    return render(
        request,
        "ward/home.html",
        context
    )
# =========================================================
# PROFILE
# =========================================================

@login_required(login_url='login')
def edit_profile(request):
    profile = request.user.profile

    if request.method == 'POST':
        new_email = request.POST.get('email', '').strip()

        request.user.first_name = request.POST.get('first_name', '').strip()
        request.user.last_name = request.POST.get('last_name', '').strip()

        request.user.email = new_email
        request.user.username = new_email

        form = ProfileForm(
            request.POST,
            request.FILES,
            instance=profile
        )

        if form.is_valid():
            request.user.save()
            form.save()
            messages.success(request, 'Your profile has been updated successfully.')
        else:
            messages.error(request, 'Please correct the errors below.')

    return redirect('/dashboard/?page=profile')

# =========================================================
# BILLING & INVOICES - Receptionist/Admin only
# =========================================================

@login_required(login_url='login')
@role_required(['receptionist', 'admin'])
def create_invoice(request):
    preview_data = None

    if request.method == 'POST':
        form = InvoiceForm(request.POST, user=request.user)

        if 'preview' in request.POST and form.is_valid():
            cleaned = form.cleaned_data
            service = cleaned.get('service_fee') or 0
            lab = cleaned.get('lab_fee') or 0
            admission = cleaned.get('admission_fee') or 0

            preview_data = {
                'patient': cleaned.get('patient'),
                'service_fee': service,
                'lab_fee': lab,
                'admission_fee': admission,
                'total': service + lab + admission,
                'payment_method': cleaned.get('payment_method'),
                'status': cleaned.get('status'),
            }

        elif 'save' in request.POST and form.is_valid():
            invoice = form.save(commit=False)
            doctor = get_doctor_profile(request.user)
            if doctor:
                invoice.doctor = doctor
            invoice.save()

            messages.success(request, f'Invoice {invoice.invoice_id} created successfully.')
            return redirect('invoice_pdf', invoice_id=invoice.id)

    else:
        form = InvoiceForm(user=request.user)

    return render(request, 'ward/home.html', {
        'page': 'create_invoice',
        'form': form,
        'preview': preview_data,
        'role': get_role(request.user)
    })

@login_required(login_url='login')
def invoices_list(request):
    q = request.GET.get('search', '')
    status = request.GET.get('status', '')
    method = request.GET.get('method', '')

    invoices = Invoice.objects.select_related('patient', 'doctor').all().order_by('-date')

    if q:
        invoices = invoices.filter(Q(invoice_id__icontains=q) | Q(patient__name__icontains=q))
    if status:
        invoices = invoices.filter(status=status)
    if method:
        invoices = invoices.filter(payment_method=method)

    total_revenue = sum(inv.total for inv in invoices)
    paid_revenue = sum(inv.total for inv in invoices if inv.status == 'paid')
    outstanding = sum(inv.total for inv in invoices if inv.status == 'unpaid')

    role = get_role(request.user)
    my_revenue = 0

    if role == 'doctor':
        doctor = get_doctor_profile(request.user)
        if doctor:
            invoices = invoices.filter(doctor=doctor)
            my_revenue = sum(inv.total for inv in invoices if inv.status == 'paid')

    return render(request, 'ward/home.html', {
        'page': 'invoices',
        'invoices': invoices,
        'total_revenue': total_revenue,
        'paid_this_month': paid_revenue,
        'outstanding': outstanding,
        'my_revenue': my_revenue,
        'role': role
    })

@login_required(login_url='login')
def edit_invoice(request, invoice_id):
    invoice = Invoice.objects.filter(id=invoice_id).first()
    if not invoice:
        messages.error(request, "Invoice not found.")
        return redirect('/dashboard/?page=invoices')
    
    if request.method == 'POST':
        form = InvoiceForm(request.POST, instance=invoice, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f"Invoice #{invoice.id} was updated successfully!")
            return redirect('/dashboard/?page=invoices') 
    else:
        form = InvoiceForm(instance=invoice, user=request.user)
        
    return render(request, 'ward/edit_invoice.html', {
        'invoice': invoice,
        'form': form
    })

@login_required(login_url='login')
@role_required(['receptionist', 'admin'])
def mark_invoice_paid(request, invoice_id):
    invoice = Invoice.objects.filter(id=invoice_id).first()

    if not invoice:
        messages.error(request, "Invoice not found.")
        return redirect('/dashboard/?page=invoices')

    if request.method == 'POST':
        invoice.status = 'paid'
        invoice.paid_at = timezone.now()
        invoice.save()
        messages.success(request, f'Invoice {invoice.invoice_id} marked as paid.')

    return redirect('/dashboard/?page=invoices')

@login_required(login_url='login')
def invoice_pdf(request, invoice_id):
    invoice = Invoice.objects.select_related('patient', 'doctor').filter(id=invoice_id).first()

    if not invoice:
        messages.error(request, "Invoice not found.")
        return redirect('/dashboard/?page=invoices')

    role = get_role(request.user)
    if role == 'doctor':
        doctor = get_doctor_profile(request.user)
        if doctor and invoice.doctor != doctor:
            messages.error(request, "Access denied.")
            return redirect('/dashboard/?page=invoices')

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{invoice.invoice_id}.pdf"'

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    # HEADER
    p.setFont("Helvetica-Bold", 18)
    p.drawString(50, height - 50, "LIFESPRING MEDICAL CENTER")
    p.setFont("Helvetica", 10)
    p.drawString(50, height - 70, "Hospital Billing Invoice")
    p.drawString(380, height - 50, f"Invoice: {invoice.invoice_id}")
    p.drawString(380, height - 70, f"Date: {invoice.date.strftime('%d %b %Y')}")
    p.drawString(380, height - 90, f"Status: {invoice.get_status_display()}")

    # PATIENT INFORMATION
    y = height - 140
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, "Patient Information")
    y -= 25
    p.setFont("Helvetica", 10)
    p.drawString(50, y, f"Patient: {invoice.patient.name if invoice.patient else 'N/A'}")

    if invoice.doctor:
        y -= 20
        p.drawString(50, y, f"Doctor: {invoice.doctor}")

    # FEES
    y -= 50
    p.setFont("Helvetica-Bold", 11)
    p.drawString(50, y, "Description")
    p.drawString(350, y, "Amount (₦)")
    y -= 10
    p.line(50, y, 500, y)
    y -= 20
    p.setFont("Helvetica", 10)

    if invoice.service_fee and invoice.service_fee > 0:
        p.drawString(50, y, "Service Fee")
        p.drawString(350, y, f"{invoice.service_fee:,.2f}")
        y -= 20

    if invoice.lab_fee and invoice.lab_fee > 0:
        p.drawString(50, y, "Lab Fee")
        p.drawString(350, y, f"{invoice.lab_fee:,.2f}")
        y -= 20

    if invoice.admission_fee and invoice.admission_fee > 0:
        p.drawString(50, y, "Admission Fee")
        p.drawString(350, y, f"{invoice.admission_fee:,.2f}")
        y -= 20

    p.line(50, y, 500, y)
    y -= 25
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, "TOTAL")
    p.drawString(350, y, f"₦{invoice.total:,.2f}")
    y -= 40
    p.setFont("Helvetica", 10)
    p.drawString(50, y, f"Payment Method: {invoice.get_payment_method_display() or 'Not Paid'}")

    if invoice.paid_at:
        y -= 20
        p.drawString(50, y, f"Paid On: {invoice.paid_at.strftime('%d %b %Y %H:%M')}")

    p.setFont("Helvetica-Oblique", 9)
    p.drawString(50, 50, "Thank you for choosing Lifespring Medical Center")
    p.showPage()
    p.save()

    return response

# =========================================================
# PATIENT PORTAL
# =========================================================

@role_required(['patient'])
def patient_dashboard(request):
    patient = Patient.objects.filter(contact=request.user.email).first()

    if not patient:
        patient = Patient.objects.create(
            name=f"{request.user.first_name} {request.user.last_name}",
            age=None,
            gender='Other',
            contact=request.user.email,
            address='',
            created_by=request.user
        )

    appointments = Appointment.objects.filter(patient=patient).order_by('-date_time')

    return render(request, 'ward/home.html', {
        'page': 'my_appointments',
        'role': 'Patient',
        'patient': patient,
        'appointments': appointments,
        'appointment_form': AppointmentForm(initial={'patient': patient}),
    })

@role_required(['patient'])
def patient_book_appointment(request):
    patient = Patient.objects.filter(contact=request.user.email).first()

    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.patient = patient
            appointment.created_by = request.user
            appointment.save()
            notify_appointment_scheduled(appointment)
            messages.success(request, 'Appointment booked successfully.')
    return redirect('patient_dashboard')

@role_required(['patient'])
def cancel_appointment(request, appointment_id):
    appointment = Appointment.objects.filter(id=appointment_id, patient__contact=request.user.email).first()
    if appointment and request.method == 'POST':
        appointment.status = 'cancelled'
        appointment.save()
        messages.success(request, 'Appointment cancelled.')
    else:
        messages.error(request, 'Appointment not found.')
    return redirect('patient_dashboard')

# =========================================================
# API
# =========================================================

@login_required(login_url='login')
def api_stats(request):
    role = get_role(request.user)
    doctor = get_doctor_profile(request.user)
    
    if role == 'Doctor' and doctor:
        data = {
            'patients': Patient.objects.filter(appointment__doctor=doctor).distinct().count(),
            'doctors': Doctor.objects.count(),
            'appointments': Appointment.objects.filter(doctor=doctor).count(),
            'admissions': Admission.objects.filter(doctor=doctor).count(),
            'invoices': Invoice.objects.filter(doctor=doctor).count(),
        }
    else:
        data = {
            'patients': Patient.objects.count(),
            'doctors': Doctor.objects.count(),
            'appointments': Appointment.objects.count(),
            'admissions': Admission.objects.count(),
            'invoices': Invoice.objects.count(),
        }
    return JsonResponse(data)