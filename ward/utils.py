from django.core.mail import send_mail
from django.conf import settings
from twilio.rest import Client
import re

# ----------------------------
# 🔧 HELPERS
# ----------------------------

def is_email(value):
    return bool(re.match(r"[^@]+@[^@]+\.[^@]+", value))

# ----------------------------
# 📧 EMAIL
# ----------------------------

def safe_send_email(subject, message, recipient_email):
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [recipient_email],
            fail_silently=False
        )
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        return False

# ----------------------------
# 📱 SMS
# ----------------------------

def safe_send_sms(message, phone_number):
    try:
        client = Client(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN
        )
        client.messages.create(
            body=message,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=phone_number
        )
        return True
    except Exception as e:
        print(f"[SMS ERROR] {e}")
        return False

# ----------------------------
# 🔔 UNIFIED NOTIFICATION
# ----------------------------

def send_notification(contact, subject=None, message=""):
    """
    Sends email or SMS depending on contact type
    """
    if is_email(contact):
        return safe_send_email(subject or "Notification", message, contact)
    return safe_send_sms(message, contact)

# ----------------------------
# ✅ FIXED: Accept string or list
# ----------------------------

def send_email_notification(subject, message, recipient):
    """
    Wrapper to match views.py import requirement
    Accepts either string email or list of emails
    """
    if isinstance(recipient, str):
        recipient_list = [recipient]
    else:
        recipient_list = recipient

    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            recipient_list,
            fail_silently=False
        )
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        return False

# ----------------------------
# 👤 PATIENT REGISTRATION
# ----------------------------

def notify_patient_registered(patient):
    subject = f"Lifespring Medical Center - Patient Registration {patient.patient_id}"
    message = f"""Hello {patient.name},

You have been successfully registered.

Patient ID: {patient.patient_id}
Age: {patient.age}
Contact: {patient.contact}

Please keep your Patient ID safe.

Lifespring Medical Center Team"""
    return send_notification(patient.contact, subject, message)

# ----------------------------
# 📅 APPOINTMENT
# ----------------------------

def notify_appointment_scheduled(appointment):
    subject = f"Appointment Confirmed - {appointment.patient.patient_id}"
    message = f"""Hello {appointment.patient.name},

Appointment Details:
Doctor: Dr. {appointment.doctor.profile.user.get_full_name()}
Date: {appointment.date_time.strftime('%A, %B %d, %Y')}
Time: {appointment.date_time.strftime('%I:%M %p')}
Reason: {appointment.reason}

Please arrive 15 minutes early.

Lifespring Medical Center Team"""
    return send_notification(appointment.patient.contact, subject, message)

# ----------------------------
# 🏥 ADMISSION
# ----------------------------

def notify_patient_admitted(admission):
    subject = f"Admission Notice - {admission.patient.patient_id}"
    message = f"""Hello {admission.patient.name},

You have been admitted.

Ward: {admission.ward.name}
Department: {admission.ward.department.name}
Doctor: Dr. {admission.doctor.profile.user.get_full_name()}
Reason: {admission.reason}

We wish you a speedy recovery.

Lifespring Medical Center Team"""
    return send_notification(admission.patient.contact, subject, message)

# ----------------------------
# 🧾 INVOICE CREATED
# ----------------------------

def notify_invoice_created(invoice):
    subject = f"New Invoice - {invoice.invoice_id}"
    message = f"""Hello {invoice.patient.name},

A new invoice has been generated.

Invoice ID: {invoice.invoice_id}
Total Amount: ${invoice.total}
Status: {invoice.status.title()}

Please visit the reception to make payment.

Lifespring Medical Center Team"""
    return send_notification(invoice.patient.contact, subject, message)

# ----------------------------
# 💰 PAYMENT CONFIRMED
# ----------------------------

def notify_payment_confirmed(invoice):
    subject = f"Payment Confirmed - {invoice.invoice_id}"
    message = f"""Hello {invoice.patient.name},

Payment confirmed for Invoice {invoice.invoice_id}.

Amount Paid: ${invoice.total}
Payment Method: {invoice.get_payment_method_display()}
Date: {invoice.paid_at.strftime('%b %d, %Y %H:%M')}

Thank you for your payment.

Lifespring Medical Center Team"""
    return send_notification(invoice.patient.contact, subject, message)

# ----------------------------
# 🩺 CONSULTATION COMPLETE
# ----------------------------

def notify_consultation_complete(consultation, invoice):
    subject = f"Consultation Complete - Invoice {invoice.invoice_id}"
    message = f"""Hello {consultation.patient.name},

Your consultation with Dr. {consultation.doctor.profile.user.get_full_name()} is complete.

Diagnosis: {consultation.diagnosis}
Prescription: {consultation.prescription}

Invoice: {invoice.invoice_id}
Total: ${invoice.total}
Status: {invoice.status.title()}

Please visit reception to settle your bill.

Lifespring Medical Center Team"""
    return send_notification(consultation.patient.contact, subject, message)