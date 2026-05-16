from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            
            try:
                profile = request.user.profile
            except:
                messages.error(request, 'User profile not found. Contact admin.')
                return redirect('login')
                
            if profile.role not in roles:
                messages.error(request, f'Permission denied. Your role: {profile.role} not allowed.')
                return redirect('dashboard')
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

admin_required = role_required('admin')
doctor_required = role_required('doctor')
receptionist_required = role_required('receptionist')
patient_required = role_required('patient')