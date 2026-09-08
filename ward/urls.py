from django.urls import path
from . import views

urlpatterns = [
    # ================================
    # AUTH
    # ================================
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),

    # ================================
    # PUBLIC PAGES
    # ================================
    path('', views.landing, name='landing'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('report/', views.report, name='report'),

    # ================================
    # DASHBOARD & SUB-PAGES
    # ================================
    path('dashboard/', views.dashboard, name='dashboard'),
    path('patients/', views.dashboard, name='patient_list'),
    path('appointments/', views.dashboard, name='appointments'),
    path('invoices/', views.dashboard, name='invoices'),
    path('admissions/', views.dashboard, name='admissions'),
    path('medical-records/', views.dashboard, name='medical_records'),
    path('prescriptions/', views.dashboard, name='prescriptions'),
    path('profile/', views.dashboard, name='profile'),
    path('audit/', views.dashboard, name='audit'),

    # ================================
    # NURSE
    # ================================
    path('nurse/dashboard/', views.nurse_dashboard, name='nurse_dashboard'),

    # ================================
    # DOCTORS
    # ================================
    path('doctors/', views.doctor_list, name='doctor_list'),
    path('doctors/add/', views.add_doctor, name='add_doctor'),
    path('doctors/<int:doctor_id>/edit/', views.edit_doctor, name='edit_doctor'),
    path('doctors/<int:doctor_id>/delete/', views.delete_doctor, name='delete_doctor'),

    # ================================
    # PATIENTS
    # ================================
    path('patients/add/', views.add_patient, name='add_patient'),
    path('patients/edit/<int:patient_id>/', views.edit_patient, name='edit_patient'),
    path('patients/delete/<int:patient_id>/', views.delete_patient, name='delete_patient'),

    # ================================
    #      APPOINTMENTS
    # ================================
   path('appointments/create/', views.create_appointment, name='create_appointment'),
   path('appointments/edit/<int:appointment_id>/', views.edit_appointment, name='edit_appointment'),
   path('appointments/delete/<int:appointment_id>/', views.delete_appointment, name='delete_appointment'),
   path('appointments/<int:appointment_id>/consultation/', views.create_consultation, name='create_consultation'),
   path('appointments/<int:appointment_id>/consultation/view/', views.view_consultation, name='view_consultation'),
   path('patients/<int:pk>/', views.patient_detail, name='patient_detail'),  # <-- ADD THIS
    
       
    # ================================
    # ADMISSIONS
    # ================================
    path('admissions/',views.admissions_view,name='admissions'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('edit_admission/',views.edit_admission,name='edit_admission'), # same view handles edit POST
   
    # ================================
    # CONSULTATIONS
    # ================================
    path('consultation/<int:appointment_id>/', views.create_consultation, name='create_consultation'),
    path('consultation/<int:appointment_id>/create/', views.create_consultation, name='create_consultation'),
    path('consultation/<int:appointment_id>/view/', views.view_consultation, name='view_consultation'),

    # ================================
    # MEDICAL RECORDS
    # ================================
    path('add-medical-record/', views.add_medical_record, name='add_medical_record'),
    path('medical-records/<int:record_id>/delete/', views.delete_medical_record, name='delete_medical_record'),
    

    # ================================
    # PRESCRIPTIONS
    # ================================
    path('prescriptions/add/', views.create_prescription, name='create_prescription'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('prescription/<int:pk>/', views.view_prescription, name='view_prescription'),
    path('prescription/<int:pk>/edit/', views.edit_prescription, name='edit_prescription'),
    path('prescription/<int:pk>/delete/', views.delete_prescription, name='delete_prescription'),
    path('prescription/<int:prescription_id>/dispense/', views.dispense_prescription, name='dispense_prescription'),
    

    # ================================
    # medicine inventory
    # ================================       
    path('medicine/add/', views.add_medicine, name='add_medicine'),       
    path('medicines/<int:medicine_id>/edit/', views.edit_medicine, name='edit_medicine'),
    path('medicines/<int:medicine_id>/delete/', views.delete_medicine, name='delete_medicine'),
    path('medicines/export/', views.export_medicines, name='export_medicines'),

    # ================================
    # LABORATORY TEST REQUESTS
    # ================================
    path('laboratory/new-request/', views.create_test_request, name='create_test_request'),
    path('laboratory/collect/<int:test_id>/',views.collect_sample,name='collect_sample'),
    path('laboratory/input-result/<int:test_id>/',views.input_lab_result,name='input_lab_result'),
    path('lab-report/<int:pk>/', views.view_lab_report, name='view_lab_report'), 

    # ================================
    # PROFILE
    # ================================
    path('profile/edit/', views.edit_profile, name='edit_profile'),  

    # ================================
    # BILLING / INVOICES
    # ================================
    path('invoices/create/', views.create_invoice, name='create_invoice'),
    path('invoices/<int:invoice_id>/paid/', views.mark_invoice_paid, name='mark_invoice_paid'),
    path('invoices/<int:invoice_id>/pdf/', views.invoice_pdf, name='invoice_pdf'),
    path('invoices/', views.invoices_list, name='invoices'),
    path('invoices/<int:invoice_id>/edit/', views.edit_invoice, name='edit_invoices'),
    
    
    
    # ================================
    # PATIENT PORTAL
    # ================================
    path('patient/dashboard/', views.patient_dashboard, name='patient_dashboard'),
    path('patient/book-appointment/', views.patient_book_appointment, name='patient_book_appointment'),
    path('patient/cancel-appointment/<int:appointment_id>/', views.cancel_appointment, name='cancel_appointment'),

    # ================================
    # API
    # ================================
    path('api/stats/', views.api_stats, name='api_stats'),

    # ================================
    # REPORTS
    # ================================
    path('export-report/', views.export_report_csv, name='export_report_csv'),
]