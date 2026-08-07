import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    
    def __str__(self): 
        return self.name

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('doctor', 'Doctor'),
        ('receptionist', 'Receptionist'),
        ('nurse', 'Nurse')
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    phone = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self): 
        return f"{self.user.get_full_name()} - {self.role}"

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.message

class Doctor(models.Model):
    profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name='doctor')
    specialization = models.CharField(max_length=100)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    availability = models.CharField(max_length=200, blank=True)
    
    def __str__(self): 
        return f"Dr. {self.profile.user.get_full_name()}"

class Nurse(models.Model):
    profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name='nurse')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    shift = models.CharField(max_length=50, blank=True)  # Morning, Night
    
    def __str__(self): 
        return f"Nurse {self.profile.user.get_full_name()}"

class Ward(models.Model):
    name = models.CharField(max_length=100)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    capacity = models.IntegerField(default=10)
    beds_available = models.IntegerField(default=10)
    
    def __str__(self): 
        return f"{self.name}"

class Patient(models.Model):
    GENDER_CHOICES = [('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')]
    patient_id = models.CharField(max_length=20, unique=True, editable=False)
    name = models.CharField(max_length=100)
    age = models.IntegerField()
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    contact = models.CharField(max_length=20)
    address = models.TextField(blank=True)
    medical_history = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    assigned_nurse = models.ForeignKey(Nurse, on_delete=models.SET_NULL, null=True, blank=True, related_name='patients')

    def save(self, *args, **kwargs):
        if not self.patient_id:
            self.patient_id = f"PAT{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)
    
    def __str__(self): 
        return f"{self.name} - {self.patient_id}"

class Appointment(models.Model):
    GENDER_CHOICES = [('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')]
    STATUS_CHOICES = [('scheduled', 'Scheduled'), ('completed', 'Completed'), ('cancelled', 'Cancelled')]
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    date_time = models.DateTimeField(default=timezone.now)
    reason = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta: 
        ordering = ['-date_time']

class Consultation(models.Model):
    appointment = models.OneToOneField(
        Appointment,
        on_delete=models.CASCADE,
        related_name='consultation'
    )
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    visit_notes = models.TextField()
    diagnosis = models.TextField()
    prescription = models.TextField(blank=True)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Consultation #{self.id} - {self.patient.name}"

class Admission(models.Model):
    STATUS_CHOICES = [
        ('admitted', 'Admitted'),
        ('discharged', 'Discharged')
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    ward = models.ForeignKey(Ward, on_delete=models.SET_NULL, null=True)
    doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True)
    admission_date = models.DateTimeField(default=timezone.now)
    discharge_date = models.DateTimeField(null=True, blank=True)
    reason = models.TextField()
    diagnosis = models.TextField(blank=True) 
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='admitted')
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Admission #{self.id} - {self.patient.name}"
       
class LabTest(models.Model):
    STATUS_CHOICES = [('requested', 'Requested'), ('completed', 'Completed')]
    consultation = models.ForeignKey(Consultation, on_delete=models.CASCADE, related_name='lab_tests')
    test_name = models.CharField(max_length=100)
    result = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='requested')
    requested_by = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True)
    date_requested = models.DateTimeField(auto_now_add=True)
    date_completed = models.DateTimeField(null=True, blank=True)

# ==================== INVOICE MODEL ====================
class Invoice(models.Model):
    STATUS_CHOICES = [('unpaid', 'Unpaid'), ('paid', 'Paid')]
    PAYMENT_METHOD_CHOICES = [('', 'Not Paid'), ('cash', 'Cash'), ('transfer', 'Bank Transfer'), ('pos', 'POS')]
    
    invoice_id = models.CharField(max_length=20, unique=True, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='invoices')
    doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True)
    consultation = models.OneToOneField(Consultation, on_delete=models.SET_NULL, null=True, blank=True)
    admission = models.ForeignKey(Admission, on_delete=models.SET_NULL, null=True, blank=True)
    service_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    lab_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    admission_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    date = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='unpaid')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, blank=True, default='')
    paid_at = models.DateTimeField(null=True, blank=True)

    @property
    def total(self):
         return (self.service_fee or 0) + (self.lab_fee or 0) + (self.admission_fee or 0)
    def save(self, *args, **kwargs):
        if not self.invoice_id:
            self.invoice_id = f"INV{uuid.uuid4().hex[:8].upper()}"
        # Auto set paid_at when status changes to paid
        if self.status == 'paid' and not self.paid_at:
            self.paid_at = timezone.now()
        super().save(*args, **kwargs)
    
    def __str__(self): 
        return self.invoice_id

# ==================== NEW MODELS BELOW ====================
class MedicalRecord(models.Model):
    RECORD_TYPES = [
        ('consultation', 'Consultation'),
        ('lab', 'Lab Result'),
        ('imaging', 'Imaging'),
        ('surgery', 'Surgery'),
    ]
    
    record_id = models.CharField(max_length=20, unique=True, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='medical_records')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    record_type = models.CharField(max_length=20, choices=RECORD_TYPES, default='consultation')
    diagnosis = models.TextField()
    prescription = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True)
    files = models.FileField(upload_to='medical_records/%Y/%m/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.record_id:
            self.record_id = f"MR{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.record_id} - {self.patient.name}"

class Prescription(models.Model):
    STATUS_CHOICES = [('active', 'Active'), ('filled', 'Filled'), ('cancelled', 'Cancelled')]
    
    prescription_id = models.CharField(max_length=20, unique=True, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='prescriptions')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    record = models.ForeignKey(MedicalRecord, on_delete=models.SET_NULL, null=True, blank=True, related_name='prescriptions')
    date_issued = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    class Meta:
        ordering = ['-date_issued']

    def save(self, *args, **kwargs):
        if not self.prescription_id:
            self.prescription_id = f"RX{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.prescription_id} - {self.patient.name}"

class PrescriptionItem(models.Model):
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='items')
    drug_name = models.CharField(max_length=200)
    dosage = models.CharField(max_length=100)
    frequency = models.CharField(max_length=100)
    duration = models.CharField(max_length=100)
    quantity = models.IntegerField(default=1)
    
    def __str__(self):
        return f"{self.drug_name} - {self.dosage}"
class Medicine(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=100, blank=True)
    quantity_in_stock = models.PositiveIntegerField(default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    expiry_date = models.DateField(null=True, blank=True)
    def __str__(self):
        return self.name
class LaboratoryTest(models.Model):

    STATUS = (
        ('Pending', 'Pending'),
        ('Processing', 'Processing'),
        ('Completed', 'Completed'),
    )

    PRIORITY = (
        ('Routine', 'Routine'),
        ('Urgent', 'Urgent'),
        ('Critical', 'Critical'),
    )

    patient = models.ForeignKey(                                        
        Patient,
        on_delete=models.CASCADE,
        related_name="laboratory_tests"
    )

    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    test_name = models.CharField(max_length=200)

    sample_type = models.CharField(max_length=100)

    priority = models.CharField(
        max_length=20,
        choices=PRIORITY,
        default='Routine'
    )
    note = models.TextField(    
        blank=True,
        null=True
    )
    status = models.CharField(     
        max_length=20,
        choices=STATUS,
        default='Pending'
    )

    result = models.TextField(    
        blank=True,
        null=True
    )

    remarks = models.TextField(
        blank=True,
        null=True
    )

    requested_date = models.DateTimeField(
        default=timezone.now
    )

    completed_date = models.DateTimeField(
        blank=True,
        null=True
    )

    class Meta:
        ordering = ['-requested_date']

    def __str__(self):
        return f"{self.patient.name} - {self.test_name}"
class ActivityLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=255)
    model_name = models.CharField(max_length=50) 
    object_id = models.IntegerField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)      
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.user} - {self.action} - {self.timestamp}"