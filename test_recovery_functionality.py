#!/usr/bin/env python3
"""
Script de prueba para verificar la funcionalidad de casos de recuperación
"""
import os
import sys
import django

# Setup Django
sys.path.append('/home/nickpy777/plataforma_mensajeria_completa/proyecto_completo/messaging_platform')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Contact, Conversation, Platform, User, RecoveryCase
from django.contrib.auth import get_user_model

def test_recovery_case_creation():
    print("🧪 Iniciando prueba de creación de casos de recuperación...")
    
    # Verificar que existan usuarios
    users = User.objects.all()
    print(f"📊 Usuarios encontrados: {users.count()}")
    
    # Verificar que existan plataformas
    platforms = Platform.objects.all()
    print(f"📊 Plataformas encontradas: {platforms.count()}")
    
    # Verificar que existan contactos
    contacts = Contact.objects.all()
    print(f"📊 Contactos encontrados: {contacts.count()}")
    
    # Verificar que existan conversaciones
    conversations = Conversation.objects.all()
    print(f"📊 Conversaciones encontradas: {conversations.count()}")
    
    # Verificar casos de recuperación existentes
    recovery_cases = RecoveryCase.objects.all()
    print(f"📊 Casos de recuperación existentes: {recovery_cases.count()}")
    
    # Mostrar choices del modelo
    print(f"📋 Razones disponibles: {RecoveryCase.REASON_CHOICES}")
    print(f"📋 Estados disponibles: {RecoveryCase.STATUS_CHOICES}")
    
    print("✅ Verificación completada!")

if __name__ == "__main__":
    test_recovery_case_creation()