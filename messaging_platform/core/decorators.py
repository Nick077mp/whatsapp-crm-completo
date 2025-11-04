from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from functools import wraps
from django.shortcuts import redirect


def role_required(*roles):
    """
    Decorador que requiere que el usuario tenga uno de los roles especificados
    Los admins siempre tienen acceso a todo
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            
            # Admin siempre tiene acceso
            if request.user.role == 'admin' or request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            
            # Verificar si tiene el rol requerido
            if request.user.role not in roles:
                raise PermissionDenied("No tienes permisos para acceder a esta página.")
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def admin_required(view_func):
    """Decorador que requiere rol de administrador"""
    return role_required('admin')(view_func)


def support_or_sales_required(view_func):
    """Decorador que permite acceso a soporte y ventas (admin siempre tiene acceso)"""
    return role_required('support', 'sales')(view_func)


def sales_required(view_func):
    """Decorador que requiere rol de ventas/recuperación (admin siempre tiene acceso)"""
    return role_required('sales')(view_func)


def support_required(view_func):
    """Decorador que requiere rol de soporte"""
    return role_required('support')(view_func)