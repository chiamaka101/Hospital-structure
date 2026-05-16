from django.contrib import admin
from .models import *

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
    list_display = ['profile', 'get_doctor_name', 'specialization']
    list_filter = ['specialization']
    search_fields = ['profile__user__first_name', 'profile__user__last_name', 'specialization']
    raw_id_fields = ['profile']
    
    def get_doctor_name(self, obj):
        return f"Dr. {obj.profile.user.get_full_name()}"
    get_doctor_name.short_description = 'Doctor Name'

@admin.register(Ward)
class WardAdmin(admin.ModelAdmin):
    list_display = ['name', 'beds_available']
    search_fields = ['name']

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ['patient_id', 'name', 'age', 'gender', 'contact', 'created_at', 'created_by']
    list_filter = ['gender', 'created_at']
    search_fields = ['patient_id', 'name', 'contact']
    readonly_fields = ['patient_id', 'created_at']
    date_hierarchy = 'created_at'

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['patient', 'doctor', 'date_time', 'status', 'created_by']
    list_filter = ['status', 'date_time', 'doctor']
    search_fields = ['patient__name', 'patient__patient_id', 'doctor__profile__user__last_name']
    date_hierarchy = 'date_time'
    raw_id_fields = ['patient', 'doctor']

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
        if obj:  # editing existing invoice
            return self.readonly_fields + ['patient', 'doctor', 'consultation', 'admission']
        return self.readonly_fields