# 🏥 LifeSpring Medical Center - Hospital Management System

A Django-based Hospital Management System designed to manage patients, doctors, appointments, admissions, consultations, and billing in a hospital environment.

---

# 📌 Features

## 👥 User Roles

### 1. Admin
- Manage doctors and hospital staff
- View all system records
- Monitor appointments and admissions

### 2. Receptionist
- Register new patients
- Schedule and manage appointments
- Admit and discharge patients
- Generate invoices and billing records

### 3. Doctor
- View today's appointments
- Access patient information
- Create consultations and prescriptions

### 4. Patient
- Book appointments
- View appointment history
- Cancel appointments

---

# 🏥 Core Modules

## Patient Management
- Register new patients
- Edit patient details
- Delete patient records
- View patient history

## Doctor Management
- Add, edit, delete doctors
- Assign departments and schedules

## Appointment Scheduling
- Book appointments
- Reschedule or cancel appointments
- Track appointment status

## Admission Management
- Admit patients into wards
- Assign beds and rooms
- Discharge patients

## Billing System
- Create invoices
- Track payments
- Generate PDF invoices (ReportLab)

## Consultation System
- Doctors record diagnoses
- Add prescriptions and notes
- Maintain medical history

---

# 💻 Tech Stack

- Python 3.14+
- Django 5.0
- SQLite / PostgreSQL
- Bootstrap 5
- ReportLab (PDF generation)
- HTML, CSS, JavaScript

---

# 📂 Project Structure
HOSPITAL-STRUCTURE/
│
├── core/
│ ├── static/
│ │ └── hospital.css
│ │
│ ├── templates/
│ │ └── core/
│
├── ward/
│ ├── migrations/
│ ├── templates/
│ │ └── ward/
│ │ ├── home.html
│ │ ├── login.html
│ │ ├── nurse_dashboard.html
│ │ ├── register.html
│ │
│ ├── admin.py
│ ├── apps.py
│ ├── decorators.py
│ ├── forms.py
│ ├── models.py
│ ├── tests.py
│ ├── urls.py
│ ├── utils.py
│ ├── views.py
│
├── venv/
├── db.sqlite3
├── manage.py
├── requirements.txt
├── .gitignore
└── README.md