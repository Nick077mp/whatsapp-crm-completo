from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, Platform, Contact, Lead, Conversation, 
    Message, Template, Reminder, ActivityLog, APIConfiguration, RecoveryCase
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'role', 'is_active_chat', 'is_staff']
    list_filter = ['role', 'is_active_chat', 'is_staff', 'is_active']
    
    # Campos para editar usuarios existentes
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Información Adicional', {'fields': ('phone', 'role', 'is_active_chat')}),
    )
    
    # Campos para crear nuevos usuarios
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Información Adicional', {
            'fields': ('email', 'phone', 'role', 'is_active_chat')
        }),
    )


@admin.register(Platform)
class PlatformAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active']
    list_filter = ['is_active']


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ['name', 'platform', 'phone', 'email', 'country', 'created_at']
    list_filter = ['platform', 'country', 'created_at']
    search_fields = ['name', 'phone', 'email', 'platform_user_id']
    date_hierarchy = 'created_at'


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ['id', 'contact', 'case_type', 'status', 'assigned_to', 'created_at']
    list_filter = ['case_type', 'status', 'created_at']
    search_fields = ['contact__name', 'notes']
    date_hierarchy = 'created_at'
    raw_id_fields = ['contact', 'assigned_to']


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['id', 'contact', 'status', 'funnel_type', 'funnel_stage', 'assigned_to', 'is_answered', 'created_at']
    list_filter = ['status', 'funnel_type', 'funnel_stage', 'is_answered', 'created_at']
    search_fields = ['contact__name']
    date_hierarchy = 'created_at'
    raw_id_fields = ['contact', 'assigned_to', 'lead']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversation', 'sender_type', 'message_type', 'is_read', 'created_at']
    list_filter = ['sender_type', 'message_type', 'is_read', 'created_at']
    search_fields = ['content', 'platform_message_id']
    date_hierarchy = 'created_at'
    raw_id_fields = ['conversation', 'sender_user']


@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'platform', 'is_active', 'created_by', 'created_at']
    list_filter = ['platform', 'category', 'is_active', 'created_at']
    search_fields = ['name', 'content']
    date_hierarchy = 'created_at'
    raw_id_fields = ['created_by']


@admin.register(Reminder)
class ReminderAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'lead', 'user', 'reminder_date', 'is_completed', 'created_at']
    list_filter = ['is_completed', 'reminder_date', 'created_at']
    search_fields = ['title', 'description']
    date_hierarchy = 'reminder_date'
    raw_id_fields = ['lead', 'user']


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'action', 'conversation', 'created_at']
    list_filter = ['action', 'created_at']
    search_fields = ['action', 'description']
    date_hierarchy = 'created_at'
    raw_id_fields = ['user', 'conversation']


@admin.register(APIConfiguration)
class APIConfigurationAdmin(admin.ModelAdmin):
    list_display = ['platform', 'is_active', 'created_at', 'updated_at']
    list_filter = ['is_active', 'platform']
    
    fieldsets = (
        ('Plataforma', {
            'fields': ('platform', 'is_active')
        }),
        ('WhatsApp Business API', {
            'fields': ('whatsapp_phone_number_id', 'whatsapp_business_account_id', 
                      'whatsapp_access_token', 'whatsapp_webhook_verify_token'),
            'classes': ('collapse',)
        }),
        ('Facebook Messenger', {
            'fields': ('facebook_page_id', 'facebook_page_access_token', 
                      'facebook_app_secret', 'facebook_verify_token'),
            'classes': ('collapse',)
        }),
        ('Telegram', {
            'fields': ('telegram_bot_token', 'telegram_webhook_url'),
            'classes': ('collapse',)
        }),
    )


@admin.register(RecoveryCase)
class RecoveryCaseAdmin(admin.ModelAdmin):
    list_display = ['id', 'contact', 'reason', 'status', 'assigned_to', 'attempts_count', 'target_recovery_date', 'created_at']
    list_filter = ['reason', 'status', 'created_at', 'target_recovery_date']
    search_fields = ['contact__name', 'reason_notes', 'recovery_strategy']
    date_hierarchy = 'created_at'
    raw_id_fields = ['contact', 'conversation', 'created_by', 'assigned_to']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('contact', 'conversation', 'created_by', 'assigned_to', 'status')
        }),
        ('Detalles del Caso', {
            'fields': ('reason', 'reason_notes', 'recovery_strategy')
        }),
        ('Seguimiento', {
            'fields': ('attempts_count', 'last_attempt_at', 'target_recovery_date')
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']

