from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

@login_required
def test_auth_status(request):
    """Vista de prueba para verificar el estado de autenticación"""
    return JsonResponse({
        'authenticated': request.user.is_authenticated,
        'user_id': request.user.id if request.user.is_authenticated else None,
        'username': request.user.username if request.user.is_authenticated else None,
        'session_key': request.session.session_key
    })