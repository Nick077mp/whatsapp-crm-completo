#!/usr/bin/env python3
"""
Script para investigar específicamente el contacto +57 300 576 2295
"""
import os
import sys
import django
from datetime import datetime, timedelta, time

# Configurar Django
sys.path.append('/home/nickpy777/plataforma_mensajeria_completa/proyecto_completo/messaging_platform')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Contact, Conversation, Message
from django.utils import timezone
from django.db import models

def investigate_specific_contact():
    print("🔍 INVESTIGANDO CONTACTO +57 300 576 2295")
    print("=" * 50)
    
    # Buscar el contacto específico
    contact = Contact.objects.filter(phone="+57 300 576 2295").first()
    
    if not contact:
        print("❌ No se encontró el contacto")
        return
    
    print(f"✅ Contacto encontrado:")
    print(f"   ID: {contact.id}")
    print(f"   Nombre: {contact.display_name}")
    print(f"   Teléfono: {contact.phone}")
    print(f"   Platform ID: {contact.platform_user_id}")
    print(f"   Creado: {contact.created_at}")
    print(f"   Actualizado: {contact.updated_at}")
    
    # Buscar conversaciones
    conversations = Conversation.objects.filter(contact=contact).order_by('-updated_at')
    print(f"\n💬 CONVERSACIONES ({conversations.count()}):")
    
    for conv in conversations:
        print(f"   Conv {conv.id}:")
        print(f"     Estado: {conv.status}")
        print(f"     Asignado a: {conv.assigned_to.username if conv.assigned_to else 'Sin asignar'}")
        print(f"     Última actualización: {conv.updated_at}")
        print(f"     Último mensaje: {conv.last_message_at}")
        print(f"     Necesita respuesta: {conv.needs_response}")
    
    # Buscar mensajes en las últimas 24 horas
    if conversations.exists():
        main_conv = conversations.first()
        
        print(f"\n📨 MENSAJES EN ÚLTIMAS 24 HORAS:")
        last_24h = timezone.now() - timedelta(hours=24)
        recent_messages = Message.objects.filter(
            conversation=main_conv,
            created_at__gte=last_24h
        ).order_by('created_at')
        
        print(f"   Total mensajes: {recent_messages.count()}")
        
        for msg in recent_messages:
            direction = "📤 Enviado" if msg.sender_type == 'agent' else "📥 Recibido"
            print(f"   {msg.created_at.strftime('%Y-%m-%d %H:%M:%S')} - {direction}")
            print(f"      Contenido: {msg.content}")
            if msg.media_url:
                print(f"      Media: {msg.media_url}")
        
        # Buscar específicamente en el período 3:00-3:30
        print(f"\n🕐 MENSAJES EN PERÍODO 3:00-3:30 (HOY):")
        today = timezone.now().date()
        start_time = timezone.datetime.combine(today, timezone.datetime.min.time().replace(hour=3, minute=0))
        end_time = timezone.datetime.combine(today, timezone.datetime.min.time().replace(hour=3, minute=30))
        
        # Hacer timezone aware
        start_time = timezone.make_aware(start_time)
        end_time = timezone.make_aware(end_time)
        
        period_messages = Message.objects.filter(
            conversation=main_conv,
            created_at__range=(start_time, end_time)
        ).order_by('created_at')
        
        print(f"   Mensajes en período problemático: {period_messages.count()}")
        
        for msg in period_messages:
            direction = "📤 Enviado" if msg.sender_type == 'agent' else "📥 Recibido"
            print(f"   {msg.created_at.strftime('%H:%M:%S')} - {direction}: {msg.content}")
        
        # Verificar si hay gaps sospechosos
        print(f"\n🔍 ANÁLISIS DE GAPS EN MENSAJES:")
        all_today_messages = Message.objects.filter(
            conversation=main_conv,
            created_at__date=today
        ).order_by('created_at')
        
        print(f"   Total mensajes hoy: {all_today_messages.count()}")
        
        if all_today_messages.count() > 1:
            for i in range(1, len(all_today_messages)):
                prev_msg = all_today_messages[i-1]
                curr_msg = all_today_messages[i]
                time_diff = curr_msg.created_at - prev_msg.created_at
                
                if time_diff.total_seconds() > 300:  # Gap mayor a 5 minutos
                    print(f"   ⚠️ GAP: {time_diff} entre {prev_msg.created_at.strftime('%H:%M:%S')} y {curr_msg.created_at.strftime('%H:%M:%S')}")
                    
                    # Si el gap coincide con el período problemático
                    if (prev_msg.created_at.time() < time(3, 20) and 
                        curr_msg.created_at.time() > time(3, 30)):
                        print(f"      🚨 ESTE GAP COINCIDE CON EL PERÍODO PROBLEMÁTICO (3:00-3:30)")

if __name__ == "__main__":
    investigate_specific_contact()