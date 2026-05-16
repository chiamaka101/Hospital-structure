from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),

    # Landing page - new home after login
    path('', views.landing, name='landing'),
    
    # Dashboard 
    path('dashboard/', views.dashboard, name='dashboard'),
    path('patients/', views.dashboard, name='patient_list'),
    path('invoices/', views.dashboard, name='invoices'),
    path('admissions/', views.dashboard, name='admissions'),

    # Nurse Dashboard
    path('nurse/dashboard/', views.nurse_dashboard, name='nurse_dashboard'),

    # Doctors 
    path('doctors/', views.doctor_list, name='doctor_list'),  
    path('doctors/add/', views.add_doctor, name='add_doctor'),
    path('doctors/<int:doctor_id>/edit/', views.edit_doctor, name='edit_doctor'),
    path('doctors/<int:doctor_id>/delete/', views.delete_doctor, name='delete_doctor'),

    # Patients
    path('patients/add/', views.add_patient, name='add_patient'),
    path('patients/edit/<int:patient_id>/', views.edit_patient, name='edit_patient'),
    path('patients/delete/<int:patient_id>/', views.delete_patient, name='delete_patient'),

    # Appointments
    path('appointments/create/', views.create_appointment, name='create_appointment'),
    path('appointments/edit/<int:appointment_id>/', views.edit_appointment, name='edit_appointment'),
    path('appointments/delete/<int:appointment_id>/', views.delete_appointment, name='delete_appointment'),

    # Admissions
    path('admissions/admit/', views.admit_patient, name='admit_patient'),
    path('admissions/discharge/<int:admission_id>/', views.discharge_patient, name='discharge_patient'),

    # Consultation
    path('consultation/<int:appointment_id>/', views.create_consultation, name='create_consultation'),

    # Billing
    path('invoices/create/', views.create_invoice, name='create_invoice'),
    path('invoices/<int:invoice_id>/paid/', views.mark_invoice_paid, name='mark_invoice_paid'),
    path('invoices/<int:invoice_id>/pdf/', views.invoice_pdf, name='invoice_pdf'),
    
    path('contact/', views.contact, name='contact'),
    path('about/', views.about, name='about'),
    path('report/', views.report, name='report'),

    # Patient Portal
    path('patient/dashboard/', views.patient_dashboard, name='patient_dashboard'),
    path('patient/book-appointment/', views.patient_book_appointment, name='patient_book_appointment'),
    path('patient/cancel-appointment/<int:appointment_id>/', views.cancel_appointment, name='cancel_appointment'),
]