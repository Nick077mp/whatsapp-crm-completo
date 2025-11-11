from django.urls import path
from . import views, webhook_views, google_contacts_views

urlpatterns = [
    # Autenticación
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Vistas principales
    path('', views.dashboard_view, name='dashboard'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('leads/', views.leads_view, name='leads'),
    path('leads/<int:lead_id>/', views.lead_detail_view, name='lead_detail'),
    path('chat/', views.chat_view, name='chat'),
    path('chat/<int:conversation_id>/', views.conversation_detail_view, name='conversation_detail'),
    path('templates/', views.templates_view, name='templates'),
    path('inbox/', views.inbox_view, name='inbox'),
    path('funnels/', views.funnels_view, name='funnels'),
    path('recovery-dashboard/', views.recovery_dashboard_view, name='recovery_dashboard'),
    path('reports/', views.reports_view, name='reports'),
    
    # Google Contacts Integration
    path('auth/google/', google_contacts_views.google_auth_start, name='google_auth_start'),
    path('auth/google/callback/', google_contacts_views.google_auth_callback, name='google_auth_callback'),
    path('auth/google/callback-alt/', google_contacts_views.google_auth_callback_alt, name='google_auth_callback_alt'),
    path('auth/google/debug-callback/', google_contacts_views.debug_oauth_callback, name='debug_oauth_callback'),
    path('api/google-contacts/status/', google_contacts_views.google_contacts_status, name='google_contacts_status'),
    path('api/google-contacts/search/', google_contacts_views.search_google_contact, name='search_google_contact'),
    path('api/google-contacts/sync/<int:contact_id>/', google_contacts_views.sync_contact_with_google, name='sync_contact_with_google'),
    path('api/google-contacts/force-sync/<int:contact_id>/', google_contacts_views.force_sync_contact, name='force_sync_contact'),
    path('api/google-contacts/disconnect/', google_contacts_views.disconnect_google_contacts, name='disconnect_google_contacts'),
    path('api/test-auth/', google_contacts_views.test_auth_status, name='test_auth_status'),
    
    # API endpoints
    path('api/leads/create/', views.api_create_lead, name='api_create_lead'),
    path('api/leads/<int:lead_id>/update/', views.api_update_lead, name='api_update_lead'),
    path('api/recovery-cases/create/', views.api_create_recovery_case, name='api_create_recovery_case'),
    path('api/reminders/create/', views.api_create_reminder, name='api_create_reminder'),
    path('api/reminders/<int:reminder_id>/complete/', views.api_complete_reminder, name='api_complete_reminder'),
    path('api/templates/create/', views.api_create_template, name='api_create_template'),
    path('api/templates/list/', views.api_get_templates, name='api_get_templates'),
    path('api/conversations/<int:conversation_id>/funnel/', views.api_update_conversation_funnel, name='api_update_conversation_funnel'),
    path('api/send-file-message/', views.api_send_file_message, name='api_send_file_message'),
    path('api/conversations/<int:conversation_id>/messages/', views.api_conversation_messages, name='api_conversation_messages'),
    path('api/conversations/<int:conversation_id>/assign-agent/', views.api_assign_conversation_agent, name='api_assign_conversation_agent'),
    path('api/conversations/<int:conversation_id>/assign/', views.assign_conversation_view, name='assign_conversation'),
    path('api/conversations/count/', views.conversation_count_view, name='conversation_count'),
    path('api/upload-media/', views.upload_media_view, name='upload_media'),
    path('api/agents/list/', views.api_get_available_agents, name='api_get_available_agents'),
    path('api/conversations/search/', views.api_search_conversations, name='api_search_conversations'),
    path('api/search_unassigned/', views.api_search_unassigned, name='api_search_unassigned'),
    
    # WhatsApp API (Baileys - cuenta normal)
    path('api/whatsapp/status/', views.api_whatsapp_status, name='api_whatsapp_status'),
    path('api/whatsapp/qr/', views.api_whatsapp_qr, name='api_whatsapp_qr'),
    path('api/whatsapp/restart/', views.api_whatsapp_restart, name='api_whatsapp_restart'),
    path('api/whatsapp/send-message/', views.api_send_whatsapp_message, name='api_send_whatsapp_message'),
    path('api/whatsapp/qr-updated/', views.api_whatsapp_qr_updated, name='api_whatsapp_qr_updated'),
    path('api/whatsapp/connected/', views.api_whatsapp_connected, name='api_whatsapp_connected'),
    
    # Webhooks
    path('webhooks/whatsapp/', webhook_views.whatsapp_webhook, name='whatsapp_webhook'),
    path('webhooks/whatsapp-outgoing/', webhook_views.whatsapp_outgoing_webhook, name='whatsapp_outgoing_webhook'),
    path('webhooks/facebook/', webhook_views.facebook_webhook, name='facebook_webhook'),
    path('webhooks/telegram/', webhook_views.telegram_webhook, name='telegram_webhook'),
    path('api/send-message/', webhook_views.send_message_api, name='send_message_api'),
    
    # WhatsApp Baileys Integration
    path('api/whatsapp/status/', views.api_whatsapp_status, name='api_whatsapp_status'),
    path('api/whatsapp/qr/', views.api_whatsapp_qr, name='api_whatsapp_qr'),
    path('api/whatsapp/restart/', views.api_whatsapp_restart, name='api_whatsapp_restart'),
    path('api/whatsapp/connected/', views.api_whatsapp_connected, name='api_whatsapp_connected'),
    path('api/whatsapp/qr-updated/', views.api_whatsapp_qr_updated, name='api_whatsapp_qr_updated'),
]

