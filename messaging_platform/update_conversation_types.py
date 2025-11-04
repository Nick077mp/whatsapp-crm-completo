#!/usr/bin/env python3
"""
Script para actualizar el funnel_type de conversaciones existentes
"""

import os
import sys
import django

# Configurar Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Conversation

def update_conversation_types():
    """Actualiza conversaciones sin funnel_type definido"""
    
    # Buscar conversaciones sin tipo o con 'none'
    conversations_to_update = Conversation.objects.filter(
        funnel_type__in=['none', '', None]
    )
    
    print(f"📊 Conversaciones encontradas sin tipo: {conversations_to_update.count()}")
    
    updated_count = 0
    for conversation in conversations_to_update:
        # Por defecto, asignar a soporte
        conversation.funnel_type = 'support'
        conversation.save()
        updated_count += 1
        print(f"✅ Conversación {conversation.id} actualizada a 'support'")
    
    print(f"\n🎉 Total de conversaciones actualizadas: {updated_count}")

if __name__ == '__main__':
    update_conversation_types()