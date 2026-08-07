from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def role_required(*roles):
    # Unpack list if user passes @role_required(['admin', 'doctor'])
    if len(roles) == 1 and isinstance(roles[0], (list, tuple)):
        roles = roles[0]
    roles = [str(r).lower().strip() for r in roles]

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

            user_role = str(profile.role).lower().strip()
            print(f"DEBUG: user={request.user.username} | role='{user_role}' | allowed={roles}")

            if user_role in roles:
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, f'Permission denied. Your role: {profile.role} not allowed.')
                return redirect('dashboard')
        return _wrapped_view
    return decorator

admin_required = role_required('admin')
doctor_required = role_required('doctor')
receptionist_required = role_required('receptionist')
patient_required = role_required('patient')