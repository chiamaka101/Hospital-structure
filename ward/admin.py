from django.contrib import admin
from.models import *

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'get_full_name', 'role', 'phone', 'department']
    list_filter = ['role', 'department']
    search_fields = ['user__first_name', 'user__last_name', 'user__email', 'phone']

    def get_full_name(self, obj):
        return obj.user.get_full_name()
    get_full_name.short_description = 'Full Name'

@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ['profile', 'get_doctor_name', 'specialization', 'department']
    list_filter = ['specialization', 'department']
    search_fields = ['profile__user__first_name', 'profile__user__last_name', 'specialization']
    raw_id_fields = ['profile']

    def get_doctor_name(self, obj):
        return f"Dr. {obj.profile.user.get_full_name()}"
    get_doctor_name.short_description = 'Doctor Name'

@admin.register(Nurse)
class NurseAdmin(admin.ModelAdmin):
    list_display = ['profile', 'get_nurse_name', 'department', 'shift']
    list_filter = ['department', 'shift']
    search_fields = ['profile__user__first_name', 'profile__user__last_name']
    raw_id_fields = ['profile']

    def get_nurse_name(self, obj):
        return f"Nurse {obj.profile.user.get_full_name()}"
    get_nurse_name.short_description = 'Nurse Name'

@admin.register(Ward)
class WardAdmin(admin.ModelAdmin):
    list_display = ['name', 'department', 'capacity', 'beds_available']
    list_filter = ['department']
    search_fields = ['name']
    raw_id_fields = ['department']

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ['patient_id', 'name', 'age', 'gender', 'contact', 'assigned_nurse', 'created_at']
    list_filter = ['gender', 'created_at', 'assigned_nurse']
    search_fields = ['patient_id', 'name', 'contact']
    readonly_fields = ['patient_id', 'created_at']
    date_hierarchy = 'created_at'
    raw_id_fields = ['assigned_nurse', 'created_by']

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['patient', 'doctor', 'date_time', 'status', 'created_by']
    list_filter = ['status', 'date_time', 'doctor']
    search_fields = ['patient__name', 'patient__patient_id', 'doctor__profile__user__last_name']
    date_hierarchy = 'date_time'
    raw_id_fields = ['patient', 'doctor', 'created_by']

@admin.register(Consultation)
class ConsultationAdmin(admin.ModelAdmin):
    list_display = ['patient', 'doctor', 'date', 'diagnosis']
    list_filter = ['date', 'doctor']
    search_fields = ['patient__name', 'doctor__profile__user__last_name', 'diagnosis']
    date_hierarchy = 'date'
    raw_id_fields = ['appointment', 'patient', 'doctor']

@admin.register(Admission)
class AdmissionAdmin(admin.ModelAdmin):
    list_display = ['patient', 'ward', 'doctor', 'admission_date', 'discharge_date', 'status']
    list_filter = ['status', 'admission_date', 'ward', 'doctor']
    search_fields = ['patient__name', 'patient__patient_id']
    date_hierarchy = 'admission_date'
    raw_id_fields = ['patient', 'ward', 'doctor']

@admin.register(LabTest)
class LabTestAdmin(admin.ModelAdmin):
    list_display = ['test_name', 'consultation', 'status', 'date_requested', 'date_completed']
    list_filter = ['status', 'date_requested']
    search_fields = ['test_name', 'consultation__patient__name']
    raw_id_fields = ['consultation', 'requested_by']

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_id', 'patient', 'total', 'status', 'payment_method', 'date', 'paid_at']
    list_filter = ['status', 'payment_method', 'date', 'doctor']
    search_fields = ['invoice_id', 'patient__name', 'patient__patient_id']
    readonly_fields = ['invoice_id', 'total', 'paid_at']
    date_hierarchy = 'date'
    raw_id_fields = ['patient', 'doctor', 'consultation', 'admission']

    fieldsets = (
        ('Invoice Info', {
            'fields': ('invoice_id', 'patient', 'doctor', 'date', 'status')
        }),
        ('Linked Records', {
            'fields': ('consultation', 'admission'),
            'classes': ('collapse',)
        }),
        ('Charges', {
            'fields': ('service_fee', 'lab_fee', 'admission_fee', 'total')
        }),
        ('Payment', {
            'fields': ('payment_method', 'paid_at')
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ['patient', 'doctor', 'consultation', 'admission']
        return self.readonly_fields

# ==================== NEW ADMINS ====================

@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display = ['record_id', 'patient', 'doctor', 'record_type', 'created_at']
    list_filter = ['record_type', 'created_at', 'doctor']
    search_fields = ['record_id', 'patient__name', 'diagnosis', 'notes']
    readonly_fields = ['record_id', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'
    raw_id_fields = ['patient', 'doctor']
    list_per_page = 25

class PrescriptionItemInline(admin.TabularInline):
    model = PrescriptionItem
    extra = 1
    fields = ['drug_name', 'dosage', 'frequency', 'duration', 'quantity']

@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ['prescription_id', 'patient', 'doctor', 'status', 'date_issued']
    list_filter = ['status', 'date_issued', 'doctor']
    search_fields = ['prescription_id', 'patient__name', 'doctor__profile__user__last_name']
    readonly_fields = ['prescription_id', 'date_issued']
    raw_id_fields = ['patient', 'doctor', 'record']
    inlines = [PrescriptionItemInline]
    date_hierarchy = 'date_issued'

@admin.register(PrescriptionItem)
class PrescriptionItemAdmin(admin.ModelAdmin):
    list_display = ['drug_name', 'dosage', 'frequency', 'prescription']
    search_fields = ['drug_name', 'prescription__prescription_id']
    raw_id_fields = ['prescription']

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'user', 'action', 'model_name', 'object_id']
    list_filter = ['action', 'model_name', 'timestamp']
    search_fields = ['user__username', 'user__email', 'action', 'model_name']
    readonly_fields = ['user', 'action', 'model_name', 'object_id', 'timestamp']
    date_hierarchy = 'timestamp'
    list_per_page = 50

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False