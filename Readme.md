# 🏥 LifeSpring Medical Center — Hospital Management System

A Django-based Hospital Management System designed to help manage hospital operations including patients, doctors, appointments, admissions, consultations, prescriptions, laboratory services, pharmacy operations, and billing.

## 📌 Project Overview

LifeSpring Medical Center is a database-driven web application developed with Django to provide a centralized platform for managing different hospital workflows.

The system uses role-based access control to provide different functionality for administrators, receptionists, doctors, nurses, and other hospital staff.

## ✨ Key Features

### 👥 User & Role Management

The system supports different user roles with role-specific access:

- **Admin** — Manage hospital staff and monitor system records.
- **Receptionist** — Register patients, manage appointments, admissions, and billing.
- **Doctor** — View appointments, access patient information, create consultations and prescriptions.
- **Nurse** — Access relevant patient and ward information.
- **Laboratory Staff** — Manage laboratory test requests and results.
- **Patient** — Book appointments and view appointment history.

### 👤 Patient Management

- Register new patients
- Edit patient information
- View patient details and history
- Manage patient records
- Assign relevant hospital staff

### 👨‍⚕️ Doctor Management

- Manage doctor records
- Assign doctors to patients and appointments
- Manage doctor-related hospital workflows

### 📅 Appointment Management

- Schedule appointments
- View upcoming appointments
- Manage appointment status
- Cancel or reschedule appointments
- Track appointment history

### 🏥 Admission Management

- Admit patients
- Assign wards
- Assign doctors
- Track active admissions
- Discharge patients
- Manage admission information

### 🩺 Medical Records & Consultations

- Record patient consultations
- Record diagnoses
- Add clinical notes
- Maintain patient medical history
- Create prescriptions

### 💊 Prescription & Pharmacy Management

- Create prescriptions
- Manage prescription items
- Manage medicines
- Monitor medicine stock
- Identify low-stock medicines
- Monitor medicine expiry dates

### 🧪 Laboratory Management

- Create laboratory test requests
- Record sample information
- Track test status
- Manage test results
- Add laboratory remarks

### 💳 Billing & Invoices

- Create invoices
- Manage hospital charges
- Track payment status
- Record payments
- Generate PDF invoices using ReportLab

### 📊 Dashboard

The system includes dashboard interfaces for monitoring important hospital activities and providing users with quick access to relevant information.



## 🛠️ Technologies

- **Python**
- **Django**
- **SQLite**
- **HTML5**
- **CSS3**
- **JavaScript**
- **Bootstrap**
- **Django ORM**
- **ReportLab**
- **Git & GitHub**



## 🔐 Authentication & Security

The application includes:

- User authentication
- Login and logout functionality
- Role-based access control
- Protected views
- Form validation
- Permission-based functionality



## 📂 Project Structure


HOSPITAL-STRUCTURE/
│
├── core/
│   ├── static/
│   │   └── hospital.css
│   └── templates/
│       └── core/
│
├── ward/
│   ├── migrations/
│   ├── templates/
│   │   └── ward/
│   │       ├── home.html
│   │       ├── login.html
│   │       ├── nurse_dashboard.html
│   │       └── register.html
│   │
│   ├── admin.py
│   ├── apps.py
│   ├── decorators.py
│   ├── forms.py
│   ├── models.py
│   ├── tests.py
│   ├── urls.py
│   ├── utils.py
│   └── views.py
│
├── manage.py
├── requirements.txt
├── .gitignore
└── README.md