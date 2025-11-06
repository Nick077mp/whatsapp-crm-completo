#!/usr/bin/env python3
"""
Script para investigar la conversación específica 300 5762295
"""
import os
import sys
import django
from datetime import datetime, timedelta

# Configurar Django
sys.path.append('/home/nickpy777/plataforma_mensajeria_completa/proyecto_completo/messaging_platform')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Contact, Conversation, Message
from django.utils import timezone
from django.db import models

def investigate_conversation():
    print("🔍 INVESTIGANDO CONVERSACIÓN 300 5762295")
    print("=" * 50)
    
    # Buscar el contacto por número
    target_number = "+57 300 576 2295"
    alternative_formats = [
        "573005762295",
        "+57 300 576 2295", 
        "300 576 2295",
        "+573005762295"
    ]
    
    contact = None
    for format_num in alternative_formats:
        # Buscar por phone o platform_user_id
        contact = Contact.objects.filter(
            models.Q(phone__icontains=format_num.replace(" ", "")) |
            models.Q(platform_user_id__icontains=format_num.replace(" ", ""))
        ).first()
        if contact:
            print(f"✅ Contacto encontrado con formato: {format_num}")
            break
    
    if not contact:
        print("❌ No se encontró el contacto 300 5762295")
        print("\nBuscando contactos similares...")
        similar_contacts = Contact.objects.filter(
            models.Q(phone__icontains="5762295") |
            models.Q(platform_user_id__icontains="5762295")
        )
        for c in similar_contacts:
            print(f"   - {c.display_name}: {c.phone} / {c.platform_user_id}")
        return
    
    print(f"👤 Contacto: {contact.display_name}")
    print(f"📱 Número: {contact.phone}")
    print(f"🆔 Platform User ID: {contact.platform_user_id}")
    print(f"🆔 Contact ID: {contact.id}")
    
    # Buscar conversaciones del contacto
    conversations = Conversation.objects.filter(contact=contact).order_by('-updated_at')
    print(f"\n💬 Conversaciones encontradas: {conversations.count()}")
    
    for conv in conversations:
        print(f"   - Conv {conv.id}: Estado={conv.status}, Asignado a={conv.assigned_to.username if conv.assigned_to else 'No asignado'}")
        print(f"     Última actualización: {conv.updated_at}")
    
    # Buscar mensajes en el período problemático (3:00-3:30)
    # Asumiendo que es de hoy o ayer
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    
    # Probar diferentes fechas
    for date_to_check in [today, yesterday]:
        start_time = timezone.datetime.combine(date_to_check, timezone.datetime.min.time().replace(hour=3, minute=0))
        end_time = timezone.datetime.combine(date_to_check, timezone.datetime.min.time().replace(hour=3, minute=30))
        
        # Hacer timezone aware
        start_time = timezone.make_aware(start_time)
        end_time = timezone.make_aware(end_time)
        
        print(f"\n🕐 Buscando mensajes entre {start_time} y {end_time}")
        
        messages_in_period = Message.objects.filter(
            conversation__contact=contact,
            created_at__range=(start_time, end_time)
        ).order_by('created_at')
        
        print(f"📨 Mensajes encontrados en este período: {messages_in_period.count()}")
        
        for msg in messages_in_period:
            print(f"   - {msg.created_at}: {'📤' if msg.is_from_user else '📥'} {msg.content[:50]}...")
    
    # Buscar todos los mensajes del contacto en las últimas 24 horas
    last_24h = timezone.now() - timedelta(hours=24)
    recent_messages = Message.objects.filter(
        conversation__contact=contact,
        created_at__gte=last_24h
    ).order_by('created_at')
    
    print(f"\n📊 MENSAJES EN ÚLTIMAS 24 HORAS: {recent_messages.count()}")
    for msg in recent_messages:
        direction = "📤 Enviado" if msg.is_from_user else "📥 Recibido"
        print(f"   {msg.created_at.strftime('%H:%M:%S')} - {direction}: {msg.content[:100]}")
    
    # Verificar si hay gaps en los mensajes
    print(f"\n🔍 ANÁLISIS DE GAPS:")
    if recent_messages.count() > 1:
        for i in range(1, len(recent_messages)):
            prev_msg = recent_messages[i-1]
            curr_msg = recent_messages[i]
            time_diff = curr_msg.created_at - prev_msg.created_at
            
            if time_diff.total_seconds() > 600:  # Gap mayor a 10 minutos
                print(f"   ⚠️ GAP detectado: {time_diff} entre {prev_msg.created_at} y {curr_msg.created_at}")

if __name__ == "__main__":
    investigate_conversation()