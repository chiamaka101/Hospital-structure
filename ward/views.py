from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.utils import timezone
from django.urls import reverse
from reportlab.pdfgen import canvas
from.models import *
from.forms import *
from.decorators import role_required
from.utils import (
    notify_patient_registered, notify_appointment_scheduled, notify_patient_admitted,
    notify_invoice_created, notify_payment_confirmed, notify_consultation_complete
)

def login_view(request):
    if request.user.is_authenticated:
        if hasattr(request.user, 'profile'):
            if request.user.profile.role == 'patient':
                return redirect('patient_dashboard')
            elif request.user.profile.role == 'nurse':
                return redirect('nurse_dashboard')
        return redirect('landing')
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            if hasattr(user, 'profile'):
                if user.profile.role == 'patient':
                    return redirect('patient_dashboard')
                elif user.profile.role == 'nurse':
                    return redirect('nurse_dashboard')
            return redirect('landing')
        else:
            messages.error(request, 'Invalid email or password')
    return render(request, 'ward/login.html')

def register_view(request):
    if request.user.is_authenticated:
        return redirect('landing')
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
            if role == 'nurse':
                Nurse.objects.create(profile=profile)
                login(request, user)
                messages.success(request, f'Welcome {user.get_full_name()}! Nurse account created.')
                return redirect('nurse_dashboard')
            elif role == 'patient':
                Patient.objects.create(
                    name=f"{user.first_name} {user.last_name}",
                    age=0,
                    gender='Other',
                    contact=user.email,
                    address='',
                    created_by=user
                )
                login(request, user)
                messages.success(request, f'Welcome {user.get_full_name()}! Registration complete.')
                return redirect('patient_dashboard')
            else:
                login(request, user)
                messages.success(request, f'Welcome {user.get_full_name()}! Registration complete.')
                return redirect('landing')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = RegisterForm()
    return render(request, 'ward/register.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required(login_url='login')
def landing(request):
    ctx = {
        'page': 'landing',
        'role': request.user.profile.role if hasattr(request.user, 'profile') else 'guest',
    }
    return render(request, 'ward/home.html', ctx)

@role_required('nurse')
def nurse_dashboard(request):
    nurse = Nurse.objects.filter(profile=request.user.profile).first()
    if not nurse:
        messages.error(request, 'Nurse profile not linked. Contact admin.')
        return redirect('login')

    patients = Patient.objects.filter(assigned_nurse=nurse).order_by('-created_at')

    ctx = {
        'page': 'nurse_dashboard',
        'role': 'nurse',
        'nurse': nurse,
        'patients': patients,
        'patient_count': patients.count(),
    }
    return render(request, 'ward/nurse_dashboard.html', ctx)

@login_required(login_url='login')
def doctor_list(request):
    doctors = Doctor.objects.select_related('profile__user').order_by(
        'department',
        'profile__user__first_name',
        'profile__user__last_name'
    )
    ctx = {
        'doctors': doctors,
        'page': 'doctors',
        'role': request.user.profile.role if hasattr(request.user, 'profile') else 'guest',
    }
    return render(request, 'ward/home.html', ctx)

@login_required(login_url='login')
def dashboard(request):
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:
        logout(request)
        messages.error(request, 'UserProfile not found. Contact admin.')
        return redirect('login')

    role = profile.role

    if role == 'patient':
        return redirect('patient_dashboard')
    if role == 'nurse':
        return redirect('nurse_dashboard')

    if request.path == '/patients/':
        page = 'patients'
    elif request.path == '/invoices/':
        page = 'invoices'
    elif request.path == '/admissions/':
        page = 'admissions'
    else:
        page = request.GET.get('page', 'dashboard')

    ctx = {
        'page': page,
        'role': role,
        'stats': {
            'patients': Patient.objects.count(),
            'doctors': Doctor.objects.count(),
            'nurses': Nurse.objects.count(),
            'admissions': Admission.objects.filter(status='admitted').count(),
            'unpaid': Invoice.objects.filter(status='unpaid').count(),
            'appointments': Appointment.objects.count(),
        }
    }

    if role == 'admin':
        ctx.update({
            'recent_patients': Patient.objects.order_by('-created_at')[:5],
            'doctors': Doctor.objects.select_related('profile__user').all(),
            'nurses': Nurse.objects.select_related('profile__user').all(),
            'doctor_form': DoctorCreateForm(),
        })
    elif role == 'doctor':
        doc = Doctor.objects.filter(profile=profile).first()
        if not doc:
            logout(request)
            messages.error(request, 'Doctor profile not linked. Contact admin.')
            return redirect('login')

        today = timezone.now().date()
        appointments_today = Appointment.objects.filter(
            doctor=doc,
            date_time__date=today,
            status='scheduled'
        ).order_by('date_time')

        ctx.update({
            'appointments': appointments_today,
            'patients': Patient.objects.filter(appointment__doctor=doc).distinct(),
            'today_count': appointments_today.count(),
            'debug_date': today,
        })
    elif role == 'receptionist':
        ctx.update({
            'appointments': Appointment.objects.filter(date_time__date=timezone.now().date()),
            'patient_form': PatientForm(),
            'appointment_form': AppointmentForm(),
            'admission_form': AdmissionForm(),
            'invoice_form': InvoiceForm(),
        })

    if page == 'patients':
        if role == 'doctor':
            doc = Doctor.objects.filter(profile=profile).first()
            ctx['patients'] = Patient.objects.filter(appointment__doctor=doc).distinct()
        else:
            ctx['patients'] = Patient.objects.all().order_by('-created_at')

    if page == 'invoices':
        ctx['invoices'] = Invoice.objects.all().order_by('-date')
        ctx['invoice_form'] = InvoiceForm()

    if page == 'admissions':
        ads = Admission.objects.filter(status='admitted')
        if role == 'doctor':
            doc = Doctor.objects.filter(profile=profile).first()
            if doc:
                ads = ads.filter(doctor=doc)
        ctx['admissions'] = ads

    return render(request, 'ward/home.html', ctx)

@role_required('patient')
def patient_dashboard(request):
    try:
        profile = request.user.profile
        patient = Patient.objects.get(contact=request.user.email)
    except Patient.DoesNotExist:
        patient = Patient.objects.create(
            name=f"{request.user.first_name} {request.user.last_name}",
            age=0,
            gender='Other',
            contact=request.user.email,
            address='',
            created_by=request.user
        )
        messages.info(request, 'Patient profile was missing. Created it for you.')

    page = request.GET.get('page', 'my_appointments')
    appointments = Appointment.objects.filter(patient=patient).order_by('-date_time')

    ctx = {
        'page': page,
        'role': 'patient',
        'patient': patient,
        'appointments': appointments,
        'appointment_form': AppointmentForm(initial={'patient': patient}),
    }
    return render(request, 'ward/home.html', ctx)

@role_required('patient')
def patient_book_appointment(request):
    try:
        patient = Patient.objects.get(contact=request.user.email)
    except Patient.DoesNotExist:
        patient = Patient.objects.create(
            name=f"{request.user.first_name} {request.user.last_name}",
            age=0,
            gender='Other',
            contact=request.user.email,
            address='',
            created_by=request.user
        )

    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        if form.is_valid():
            appt = form.save(commit=False)
            appt.patient = patient
            appt.created_by = request.user
            appt.save()
            notify_appointment_scheduled(appt)
            messages.success(request, 'Appointment booked successfully.')
            return redirect('patient_dashboard')
        else:
            messages.error(request, 'Error booking appointment.')
    else:
        form = AppointmentForm(initial={'patient': patient})
        form.fields['patient'].widget = forms.HiddenInput()

    return render(request, 'ward/home.html', {
        'page': 'book',
        'role': 'patient',
        'appointment_form': form,
        'patient': patient
    })

@role_required('patient')
def cancel_appointment(request, appointment_id):
    try:
        patient = Patient.objects.get(contact=request.user.email)
        appt = Appointment.objects.filter(id=appointment_id, patient=patient).first()
    except Patient.DoesNotExist:
        patient = Patient.objects.create(
            name=f"{request.user.first_name} {request.user.last_name}",
            age=0,
            gender='Other',
            contact=request.user.email,
            address='',
            created_by=request.user
        )
        appt = None

    if request.method == 'POST':
        if appt and appt.status == 'scheduled':
            appt.status = 'cancelled'
            appt.save()
            messages.success(request, 'Appointment cancelled successfully.')
        else:
            messages.error(request, 'Appointment not found or cannot be cancelled.')
    return redirect('patient_dashboard')

@role_required('admin')
def add_doctor(request):
    if request.method == 'POST':
        form = DoctorCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            profile = UserProfile.objects.create(user=user, role='doctor', phone=form.cleaned_data['phone'])
            Doctor.objects.create(profile=profile, specialization=form.cleaned_data['specialization'])
            messages.success(request, f'Doctor {user.get_full_name()} created.')
        else:
            messages.error(request, f'Error creating doctor: {form.errors}')
    return redirect('dashboard')

@role_required('admin')
def edit_doctor(request, doctor_id):
    doctor = Doctor.objects.filter(id=doctor_id).first()
    if not doctor:
        messages.error(request, 'Doctor not found.')
        return redirect('dashboard')
    if request.method == 'POST':
        form = DoctorEditForm(request.POST, instance=doctor)
        if form.is_valid():
            form.save()
            messages.success(request, 'Doctor updated.')
        else:
            messages.error(request, 'Error updating doctor.')
    return redirect('dashboard')

@role_required('admin')
def delete_doctor(request, doctor_id):
    if request.method!= 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('dashboard')

    doctor = Doctor.objects.filter(id=doctor_id).first()
    if not doctor:
        messages.error(request, 'Doctor not found.')
        return redirect('dashboard')
    name = doctor.profile.user.get_full_name()
    doctor.profile.user.delete()
    messages.success(request, f'Doctor {name} deleted.')
    return redirect('dashboard')

@role_required('receptionist')
def add_patient(request):
    if request.method == 'POST':
        form = PatientForm(request.POST)
        if form.is_valid():
            patient = form.save(commit=False)
            patient.created_by = request.user
            patient.save()
            user = User.objects.create_user(
                username=patient.contact,
                password='patient123',
                first_name=patient.name.split()[0],
                last_name=' '.join(patient.name.split()[1:]) if len(patient.name.split()) > 1 else ''
            )
            UserProfile.objects.create(user=user, role='patient', phone=patient.contact)
            notify_patient_registered(patient)
            messages.success(request, f'Patient {patient.name} registered. Login: {patient.contact} / patient123')
    return redirect(f"{reverse('dashboard')}?page=patients")

@role_required('receptionist')
def edit_patient(request, patient_id):
    patient = Patient.objects.filter(id=patient_id).first()
    if not patient:
        messages.error(request, 'Patient not found.')
        return redirect(f"{reverse('dashboard')}?page=patients")
    if request.method == 'POST':
        form = PatientForm(request.POST, instance=patient)
        if form.is_valid():
            form.save()
            messages.success(request, 'Patient updated.')
            return redirect(f"{reverse('dashboard')}?page=patients")
    else:
        form = PatientForm(instance=patient)
    return render(request, 'ward/home.html', {'page': 'edit_patient', 'form': form, 'patient': patient, 'role': 'receptionist'})

@role_required('receptionist')
def delete_patient(request, patient_id):
    if request.method!= 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect(f"{reverse('dashboard')}?page=patients")

    patient = Patient.objects.filter(id=patient_id).first()
    if patient:
        name = patient.name
        patient.delete()
        messages.success(request, f'Patient {name} deleted.')
    else:
        messages.error(request, 'Patient not found.')
    return redirect(f"{reverse('dashboard')}?page=patients")

@role_required('receptionist')
def create_appointment(request):
    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        if form.is_valid():
            appt = form.save(commit=False)
            appt.created_by = request.user
            appt.save()
            notify_appointment_scheduled(appt)
            messages.success(request, 'Appointment scheduled. Patient notified.')
    return redirect('dashboard')

@role_required('receptionist')
def edit_appointment(request, appointment_id):
    appt = Appointment.objects.filter(id=appointment_id).first()
    if not appt:
        messages.error(request, 'Appointment not found.')
        return redirect('dashboard')
    if request.method == 'POST':
        form = AppointmentForm(request.POST, instance=appt)
        if form.is_valid():
            form.save()
            messages.success(request, 'Appointment updated.')
            return redirect('dashboard')
    else:
        form = AppointmentForm(instance=appt)
    return render(request, 'ward/home.html', {'page': 'edit_appointment', 'form': form, 'appointment': appt, 'role': 'receptionist'})

@role_required('receptionist')
def delete_appointment(request, appointment_id):
    if request.method!= 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('dashboard')

    appt = Appointment.objects.filter(id=appointment_id).first()
    if appt:
        appt.delete()
        messages.success(request, 'Appointment deleted.')
    else:
        messages.error(request, 'Appointment not found.')
    return redirect('dashboard')

@role_required('receptionist')
def admit_patient(request):
    if request.method == 'POST':
        form = AdmissionForm(request.POST)
        if form.is_valid():
            admission = form.save()
            admission.ward.beds_available -= 1
            admission.ward.save()
            if not Invoice.objects.filter(admission=admission).exists():
                inv = Invoice.objects.create(patient=admission.patient, doctor=admission.doctor, admission=admission, admission_fee=5000)
                notify_invoice_created(inv)
            notify_patient_admitted(admission)
            messages.success(request, f'{admission.patient.name} admitted to {admission.ward.name}. Notification sent.')
    return redirect('dashboard')

@role_required('receptionist')
def discharge_patient(request, admission_id):
    if request.method!= 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect(f"{reverse('dashboard')}?page=admissions")

    admission = Admission.objects.filter(id=admission_id, status='admitted').first()
    if not admission:
        messages.error(request, 'Admission not found or already discharged.')
        return redirect(f"{reverse('dashboard')}?page=admissions")

    admission.status = 'discharged'
    admission.discharge_date = timezone.now()
    admission.save()

    admission.ward.beds_available += 1
    admission.ward.save()

    messages.success(request, f'{admission.patient.name} discharged from {admission.ward.name}.')
    return redirect(f"{reverse('dashboard')}?page=admissions")

@role_required('receptionist', 'admin')
def create_invoice(request):
    if request.method == 'POST':
        form = InvoiceForm(request.POST)
        if form.is_valid():
            inv = form.save()
            notify_invoice_created(inv)
            messages.success(request, f'Invoice {inv.invoice_id} created. Total: ${inv.total}. Patient notified.')
        else:
            messages.error(request, f'Error creating invoice: {form.errors}')
    return redirect(f"{reverse('dashboard')}?page=invoices")

@role_required('receptionist', 'admin')
def mark_invoice_paid(request, invoice_id):
    if request.method!= 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect(f"{reverse('dashboard')}?page=invoices")

    invoice = Invoice.objects.filter(id=invoice_id).first()
    if not invoice:
        messages.error(request, 'Invoice not found.')
        return redirect(f"{reverse('dashboard')}?page=invoices")

    payment_method = request.POST.get('payment_method')
    if payment_method not in ['cash', 'transfer', 'pos']:
        messages.error(request, 'Please select a valid payment method.')
        return redirect(f"{reverse('dashboard')}?page=invoices")

    invoice.status = 'paid'
    invoice.payment_method = payment_method
    invoice.paid_at = timezone.now()
    invoice.save()

    notify_payment_confirmed(invoice)
    messages.success(request, f'Invoice {invoice.invoice_id} marked as paid via {payment_method.title()}.')
    return redirect(f"{reverse('dashboard')}?page=invoices")

@role_required('doctor')
def create_consultation(request, appointment_id):
    profile = request.user.profile
    doc = Doctor.objects.filter(profile=profile).first()
    appointment = Appointment.objects.filter(id=appointment_id, doctor=doc).first()
    if not appointment:
        messages.error(request, 'Appointment not found or not assigned to you.')
        return redirect('dashboard')
    if request.method == 'POST':
        form = ConsultationForm(request.POST)
        if form.is_valid():
            consult = form.save(commit=False)
            consult.appointment = appointment
            consult.patient = appointment.patient
            consult.doctor = appointment.doctor
            consult.save()
            appointment.status = 'completed'
            appointment.save()
            inv = Invoice.objects.create(patient=consult.patient, doctor=consult.doctor, consultation=consult, service_fee=3000)
            notify_consultation_complete(consult, inv)
            messages.success(request, 'Consultation saved. Patient notified.')
            return redirect('dashboard')
    return render(request, 'ward/home.html', {'page': 'consultation', 'form': ConsultationForm(), 'appointment': appointment, 'role': 'doctor'})

@login_required(login_url='login')
def invoice_pdf(request, invoice_id):
    inv = Invoice.objects.filter(id=invoice_id).first()
    if not inv:
        messages.error(request, 'Invoice not found.')
        return redirect(f"{reverse('dashboard')}?page=invoices")
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{inv.invoice_id}.pdf"'
    p = canvas.Canvas(response)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(200, 800, "LIFESPRING MEDICAL CENTER")
    p.setFont("Helvetica", 12)
    p.drawString(100, 760, f"Invoice: {inv.invoice_id}")
    p.drawString(100, 740, f"Patient: {inv.patient.name} - {inv.patient_id}")
    p.drawString(100, 720, f"Date: {inv.date}")
    y_pos = 700
    if inv.payment_method:
        p.drawString(100, y_pos, f"Payment Method: {inv.get_payment_method_display()}")
        y_pos -= 20
    p.drawString(100, y_pos, f"Service: ${inv.service_fee} | Lab: ${inv.lab_fee} | Admission: ${inv.admission_fee}")
    y_pos -= 30
    p.setFont("Helvetica-Bold", 14)
    p.drawString(100, y_pos, f"TOTAL: ${inv.total} - {inv.status.upper()}")
    p.showPage()
    p.save()
    return response

@login_required(login_url='login')
def contact(request):
    try:
        role = request.user.profile.role
    except UserProfile.DoesNotExist:
        role = 'guest'

    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')
        messages.success(request, 'Message sent successfully! We will get back to you soon.')
        return redirect('contact')

    return render(request, 'ward/home.html', {
        'page': 'contact',
        'role': role
    })

@login_required(login_url='login')
def about(request):
    try:
        role = request.user.profile.role
    except UserProfile.DoesNotExist:
        role = 'guest'

    return render(request, 'ward/home.html', {
        'page': 'about',
        'role': role
    })

@login_required(login_url='login')
def report(request):
    try:
        role = request.user.profile.role
    except UserProfile.DoesNotExist:
        logout(request)
        messages.error(request, 'UserProfile not found. Contact admin.')
        return redirect('login')

    total_patients = Patient.objects.count()
    total_appointments = Appointment.objects.count()
    total_admissions = Admission.objects.filter(status='admitted').count()

    return render(request, 'ward/home.html', {
        'page': 'report',
        'role': role,
        'stats': {
            'patients': total_patients,
            'appointments': total_appointments,
            'admissions': total_admissions
        }
    })