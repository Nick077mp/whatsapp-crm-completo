from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Count, Q, Avg, Min, Max, Subquery, OuterRef
from django.db import models
from django.utils import timezone
from datetime import timedelta
from .models import (
    User, Platform, Contact, Lead, Conversation, 
    Message, Template, Reminder, ActivityLog, APIConfiguration, RecoveryCase
)
from .decorators import admin_required, support_or_sales_required, sales_required, support_required
from .services import ContactClassificationService
import json


def login_view(request):
    """Vista de login"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        # Buscar usuario por email
        try:
            user = User.objects.get(email=email)
            user = authenticate(request, username=user.username, password=password)
            if user is not None:
                login(request, user)
                ActivityLog.objects.create(
                    user=user,
                    action='login',
                    description=f'Usuario {user.username} inició sesión'
                )
                return redirect('dashboard')
            else:
                return render(request, 'login.html', {'error': 'Credenciales inválidas'})
        except User.DoesNotExist:
            return render(request, 'login.html', {'error': 'Usuario no encontrado'})
    
    return render(request, 'login.html')


def logout_view(request):
    """Vista de logout"""
    if request.user.is_authenticated:
        ActivityLog.objects.create(
            user=request.user,
            action='logout',
            description=f'Usuario {request.user.username} cerró sesión'
        )
    logout(request)
    return redirect('login')


@login_required
def dashboard_view(request):
    """Dashboard principal con métricas y segregación por usuario"""
    
    # Tiempos de respuesta (para todos los usuarios)
    conversations_with_response = Conversation.objects.filter(
        first_response_at__isnull=False
    )
    
    response_times = []
    for conv in conversations_with_response:
        rt = conv.calculate_response_time()
        if rt:
            response_times.append(rt)
    
    min_response_time = min(response_times) if response_times else 0
    max_response_time = max(response_times) if response_times else 0
    avg_response_time = sum(response_times) / len(response_times) if response_times else 0
    
    # Recordatorios pendientes del usuario
    pending_reminders = Reminder.objects.filter(
        user=request.user,
        is_completed=False,
        reminder_date__gte=timezone.now()
    ).order_by('reminder_date')[:5]
    
    # Filtrar conversaciones según el rol del usuario
    if request.user.role == 'admin':
        # Admin ve todas las conversaciones
        base_conversations = Conversation.objects.filter(status='active')
    elif request.user.role == 'sales':
        # Ventas ve solo conversaciones de ventas/recuperación
        base_conversations = Conversation.objects.filter(status='active', funnel_type='sales')
    else:  # support
        # Soporte ve solo conversaciones de soporte
        base_conversations = Conversation.objects.filter(status='active', funnel_type='support')
    
    if request.user.role == 'admin' or request.user.is_superuser:
        # Admin ve todas las conversaciones
        total_conversations = base_conversations.count()
        unanswered_conversations = base_conversations.filter(needs_response=True).count()
        
        # Conversaciones recientes - ordenadas por actualización más reciente primero
        recent_conversations = base_conversations.select_related(
            'contact', 'contact__platform', 'assigned_to'
        ).order_by('-updated_at', '-needs_response', '-last_message_at')[:50]
        
        # Para compatibilidad con template
        assigned_conversations = []
        unassigned_conversations = []
        available_count = 0
        
    else:
        # Para usuarios de soporte y ventas: ver todas las conversaciones de su departamento
        
        # Todas las conversaciones del departamento (asignadas y sin asignar)
        total_conversations = base_conversations.count()
        unanswered_conversations = base_conversations.filter(needs_response=True).count()
        
        # Conversaciones asignadas a este usuario - ordenadas por actualización reciente
        assigned_conversations = base_conversations.select_related(
            'contact', 'contact__platform', 'assigned_to'
        ).filter(assigned_to=request.user).order_by(
            '-updated_at', '-needs_response', '-last_message_at'
        )
        
        # Conversaciones disponibles (sin asignar) de su departamento
        available_conversations_queryset = base_conversations.select_related(
            'contact', 'contact__platform', 'assigned_to'
        ).filter(assigned_to__isnull=True)
        
        # Conversaciones disponibles para mostrar - ordenadas por actualización reciente
        unassigned_conversations = available_conversations_queryset.order_by(
            '-updated_at', '-needs_response', '-last_message_at'
        )
        
        # Conversaciones recientes: ordenadas por actualización más reciente primero
        recent_conversations = base_conversations.select_related(
            'contact', 'contact__platform', 'assigned_to'
        ).order_by('-updated_at', '-needs_response', '-last_message_at')[:100]
        
        # Conteo de conversaciones disponibles
        available_count = available_conversations_queryset.count()
        
        # Conteo de conversaciones disponibles
        available_count = available_conversations_queryset.count()
    

    
    context = {
        'total_conversations': total_conversations,
        'unanswered_conversations': unanswered_conversations,
        'min_response_time': int(min_response_time),
        'max_response_time': int(max_response_time),
        'avg_response_time': int(avg_response_time),
        'recent_conversations': recent_conversations,
        'assigned_conversations': assigned_conversations,
        'unassigned_conversations': unassigned_conversations,
        'available_count': available_count if request.user.role != 'admin' and not request.user.is_superuser else 0,
        'pending_reminders': pending_reminders,
    }
    
    return render(request, 'dashboard.html', context)


@login_required
def leads_view(request):
    """Vista de gestión de leads - ADMIN/VENTAS SOLAMENTE"""
    
    # 🔒 Solo admin y ventas pueden acceder a leads
    if request.user.role not in ['admin', 'sales'] and not request.user.is_superuser:
        return redirect('dashboard')
    
    # Migrar leads existentes de 'sale' a 'sales' para consistencia
    Lead.objects.filter(case_type='sale').update(case_type='sales')
    
    # Crear leads automáticamente para conversaciones que están en embudos pero no tienen lead
    conversations_without_leads = Conversation.objects.filter(
        status='active',
        funnel_type__in=['sales', 'support', 'recovery'],
        assigned_to__isnull=False,  # Solo conversaciones asignadas
        lead__isnull=True
    ).select_related('contact', 'assigned_to')
    
    print(f"🔍 Encontradas {conversations_without_leads.count()} conversaciones sin lead que necesitan uno")
    
    for conv in conversations_without_leads:
        # Mapear el tipo de embudo al tipo de caso del lead
        case_type_mapping = {
            'sales': 'sales',
            'support': 'support', 
            'recovery': 'recovery'
        }
        
        # Verificar si ya existe un lead para este contacto y tipo
        existing_lead = Lead.objects.filter(
            contact=conv.contact,
            case_type=case_type_mapping[conv.funnel_type]
        ).first()
        
        if not existing_lead:
            lead = Lead.objects.create(
                contact=conv.contact,
                case_type=case_type_mapping[conv.funnel_type],
                assigned_to=conv.assigned_to,
                status='active',
                notes=f'Lead creado automáticamente desde embudo de {conv.funnel_type} el {timezone.now().strftime("%Y-%m-%d %H:%M")}'
            )
            # Asociar la conversación al lead
            conv.lead = lead
            conv.save()
            print(f"📈 Lead {lead.id} creado automáticamente para conversación {conv.id} - {conv.contact.display_name}")
    
    # Obtener todos los leads ordenados por última actividad
    leads = Lead.objects.select_related(
        'contact', 'contact__platform', 'assigned_to'
    ).order_by('-updated_at', '-created_at')
    
    # 🎯 Filtrar leads según el rol del usuario
    if request.user.role == 'sales':
        # Usuarios de ventas ven solo leads de sales y recovery
        leads = leads.filter(case_type__in=['sales', 'recovery'])
        print(f"🎯 Filtro VENTAS: mostrando {leads.count()} leads de sales/recovery")
    elif request.user.role == 'admin' or request.user.is_superuser:
        # Admin puede ver TODOS los leads (sales, support, recovery)
        print(f"👑 Filtro ADMIN: mostrando {leads.count()} leads de todos los tipos")
        # No filtrar - mostrar todos
    else:
        # Otros roles no tienen acceso (ya se redirigen arriba)
        leads = leads.none()
    
    # Filtros adicionales por parámetros GET
    case_type = request.GET.get('case_type')
    status = request.GET.get('status')  # Este será el funnel_stage de la conversación
    
    if case_type:
        leads = leads.filter(case_type=case_type)
    
    # Filtrar por estado del embudo (funnel_stage de la conversación)
    if status:
        # Filtrar leads cuyas conversaciones activas tengan el funnel_stage específico
        leads = leads.filter(
            contact__conversations__status='active',
            contact__conversations__funnel_stage=status
        ).distinct()
    
    # Contar totales para mostrar estadísticas (según los leads filtrados)
    total_leads = leads.count()
    sales_count = leads.filter(case_type='sales').count()
    support_count = leads.filter(case_type='support').count()
    recovery_count = leads.filter(case_type='recovery').count()
    
    print(f"📊 Estadísticas de leads - Total: {total_leads}, Sales: {sales_count}, Support: {support_count}, Recovery: {recovery_count}")
    
    # Opciones limpias para el dropdown (solo las tres principales)
    clean_case_types = [
        ('sales', 'Ventas'),
        ('support', 'Soporte'),
        ('recovery', 'Recuperación')
    ]
    
    context = {
        'leads': leads,
        'case_types': Lead.CASE_TYPE_CHOICES,
        # Los estados ahora son dinámicos basados en el tipo de embudo
        'total_leads': total_leads,
        'sales_count': sales_count,
        'support_count': support_count,
        'recovery_count': recovery_count,
    }
    
    return render(request, 'leads.html', context)


@login_required
def lead_detail_view(request, lead_id):
    """Vista de detalle de un lead"""
    lead = get_object_or_404(Lead, id=lead_id)
    reminders = lead.reminders.all().order_by('reminder_date')
    conversations = lead.conversations.all().order_by('-created_at')
    
    context = {
        'lead': lead,
        'reminders': reminders,
        'conversations': conversations,
    }
    
    return render(request, 'lead_detail.html', context)


@login_required
def chat_view(request):
    """Vista de chat con búsqueda"""
    conversations = Conversation.objects.select_related(
        'contact', 'contact__platform', 'assigned_to'
    ).filter(status='active')
    
    # Filtrar por departamento según el rol del usuario
    from .services.classification_service import ContactClassificationService
    classification_service = ContactClassificationService()
    
    if request.user.role == 'admin' or request.user.is_superuser:
        # Admin ve todas las conversaciones
        pass  # No aplicar filtro adicional
    elif request.user.role == 'support':
        # Soporte ve solo conversaciones de soporte
        conversations = conversations.filter(funnel_type='support')
    elif request.user.role == 'sales':
        # Ventas ve solo conversaciones de ventas
        conversations = conversations.filter(funnel_type='sales')
    
    # Búsqueda avanzada por nombre o número de teléfono
    search_query = request.GET.get('search', '').strip()
    if search_query:
            # Limpiar el número de búsqueda (quitar espacios, guiones, paréntesis, etc.)
            clean_search = ''.join(filter(str.isdigit, search_query))
            
            # Filtro por nombre (siempre incluido)
            filters = Q(contact__name__icontains=search_query)
            
            # Si hay dígitos en la búsqueda, agregar filtros de número inteligentes
            if clean_search:
                # Convertir número limpio a patrón regex flexible
                # Ejemplo: "3001234567" -> "3.*0.*0.*1.*2.*3.*4.*5.*6.*7"
                digit_pattern = '.*'.join(clean_search)
                
                phone_filters = (
                    # Búsqueda exacta en phone y platform_user_id
                    Q(contact__phone__icontains=search_query) |
                    Q(contact__platform_user_id__icontains=search_query) |
                    Q(contact__platform_user_id__icontains=clean_search) |
                    # Búsqueda flexible por dígitos individuales (ignora espacios/formatos)
                    Q(contact__phone__regex=digit_pattern) |
                    Q(contact__platform_user_id__regex=digit_pattern)
                )
                
                # Para búsquedas numéricas cortas, ser más estricto
                if len(clean_search) >= 4:
                    phone_filters |= Q(contact__phone__contains=clean_search)
                
                filters |= phone_filters
            else:
                # Si no hay dígitos, buscar también en campos de texto de teléfono
                filters |= (
                    Q(contact__phone__icontains=search_query) |
                    Q(contact__platform_user_id__icontains=search_query)
                )
            
            conversations = conversations.filter(filters)
    
    # Ordenar: primero las que necesitan respuesta, luego por último mensaje
    conversations = conversations.order_by('-needs_response', '-last_message_at')
    platforms = Platform.objects.filter(is_active=True)
    
    # Calcular estadísticas correctas
    total_conversations = conversations.count()
    conversations_needing_response = conversations.filter(needs_response=True).count()
    
    # Marcar conversaciones vencidas (más de 5 minutos sin respuesta)
    conversations_with_overdue = []
    for conv in conversations:
        conv.is_overdue_5min = conv.is_overdue(minutes=5)
        conversations_with_overdue.append(conv)
    
    # Contar conversaciones vencidas
    overdue_conversations_count = sum(1 for conv in conversations_with_overdue if conv.is_overdue_5min)
    
    context = {
        'conversations': conversations_with_overdue,
        'platforms': platforms,
        'search_query': search_query,
        'total_conversations': total_conversations,
        'conversations_needing_response': conversations_needing_response,
        'overdue_conversations_count': overdue_conversations_count,
    }
    
    return render(request, 'chat.html', context)


@login_required
def conversation_detail_view(request, conversation_id):
    """Vista de detalle de conversación con mensajes"""
    conversation = get_object_or_404(Conversation, id=conversation_id)
    messages = conversation.messages.select_related('sender_user').order_by('created_at')
    
    # Marcar mensajes como leídos
    messages.filter(is_read=False, sender_type='contact').update(is_read=True)
    
    # Agregar información del remitente para cada mensaje
    for message in messages:
        if message.sender_type == 'agent':
            message.sender_name = message.sender_user.username if message.sender_user else 'Agente'
        else:
            message.sender_name = conversation.contact.display_name
    
    # Si hay un parámetro test, usar template de prueba
    if request.GET.get('test') == '1':
        return render(request, 'test_conversation.html', {
            'conversation': conversation,
            'messages': messages,
        })

    context = {
        'conversation': conversation,
        'messages': messages,
    }
    
    return render(request, 'conversation_detail.html', context)
@login_required
def api_conversation_messages(request, conversation_id):
    """API para obtener mensajes de una conversación (para auto-refresh)"""
    try:
        conversation = get_object_or_404(Conversation, id=conversation_id)
        messages = conversation.messages.select_related('sender_user').order_by('created_at')
        
        messages_data = []
        for msg in messages:
            messages_data.append({
                'id': msg.id,
                'content': msg.content,
                'sender_type': msg.sender_type,
                'message_type': msg.message_type,
                'media_url': msg.media_url,
                'created_at': msg.created_at.isoformat(),
                'sender_name': msg.sender_user.username if msg.sender_user else conversation.contact.display_name
            })
        
        return JsonResponse({
            'success': True,
            'messages': messages_data,
            'conversation_status': {
                'needs_response': conversation.needs_response,
                'is_answered': conversation.is_answered
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@support_or_sales_required
def templates_view(request):
    """Vista de plantillas - Lectura para todos, edición solo admin"""
    templates = Template.objects.select_related('platform', 'created_by').order_by('-created_at')
    platforms = Platform.objects.filter(is_active=True)
    
    context = {
        'templates': templates,
        'platforms': platforms,
        'can_edit': request.user.role == 'admin' or request.user.is_superuser,  # Admin puede editar
    }
    
    return render(request, 'templates.html', context)


@support_or_sales_required
def funnels_view(request):
    """Vista de embudos de ventas, soporte y recuperación"""
    # Determinar tipo de embudo según el rol del usuario
    if request.user.role == 'admin' or request.user.is_superuser:
        funnel_type = request.GET.get('type', 'sales')  # Admin puede ver todos
    elif request.user.role == 'sales':
        funnel_type = request.GET.get('type', 'sales')  # Solo ventas y recuperación
        # Limitar a sales y recovery para usuarios de ventas
        if funnel_type not in ['sales', 'recovery']:
            funnel_type = 'sales'
    else:  # support
        funnel_type = 'support'  # Solo soporte
    
    if funnel_type == 'sales':
        stages = [
            ('sales_initial', 'Chat Inicial'),
            ('sales_negotiation', 'Negociación'),
            ('sales_debate', 'Debate'),
            ('sales_closing', 'Finalización'),
        ]
    elif funnel_type == 'recovery':
        stages = [
            ('recovery_initial', 'Contacto Inicial'),
            ('recovery_evaluation', 'Evaluación'),
            ('recovery_proposal', 'Propuesta'),
            ('recovery_followup', 'Seguimiento'),
            ('recovery_closing', 'Cierre'),
        ]
    else:  # support
        stages = [
            ('support_initial', 'Contacto Inicial'),
            ('support_process', 'Proceso de Soporte'),
            ('support_closing', 'Finalización'),
        ]
    
    # Incluir TODAS las conversaciones del embudo - tanto asignadas como no asignadas
    
    funnel_data = []
    for i, (stage_code, stage_name) in enumerate(stages):
        conversations = Conversation.objects.filter(
            funnel_type=funnel_type,
            funnel_stage=stage_code,
            status='active'
        ).select_related('contact', 'contact__platform', 'assigned_to').annotate(
            last_message_preview=Subquery(
                Message.objects.filter(
                    conversation=OuterRef('pk')
                ).order_by('-created_at').values('content')[:1]
            )
        )
        
        # Determinar etapas anterior y siguiente para los botones de navegación
        prev_stage = stages[i-1][0] if i > 0 else None
        next_stage = stages[i+1][0] if i < len(stages)-1 else None
        
        funnel_data.append({
            'stage_code': stage_code,
            'stage_name': stage_name,
            'conversations': conversations,
            'count': conversations.count(),
            'prev_stage': prev_stage,
            'next_stage': next_stage
        })
    
    context = {
        'funnel_type': funnel_type,
        'funnel_data': funnel_data,
    }
    
    return render(request, 'funnels.html', context)


@login_required
def inbox_view(request):
    """Vista independiente para clasificar conversaciones sin asignar"""
    # Filtrar conversaciones según el rol del usuario
    if request.user.role == 'admin' or request.user.is_superuser:
        # Admin ve todas las conversaciones sin asignar
        base_conversations = Conversation.objects.filter(status='active')
    elif request.user.role == 'support':
        # Soporte ve solo conversaciones de soporte sin asignar
        base_conversations = Conversation.objects.filter(status='active', funnel_type='support')
    elif request.user.role == 'sales':
        # Ventas ve solo conversaciones de ventas sin asignar
        base_conversations = Conversation.objects.filter(status='active', funnel_type='sales')
    else:
        # Otros roles no ven nada
        base_conversations = Conversation.objects.none()
    
    # Obtener solo conversaciones sin asignar a usuario
    unassigned_conversations = base_conversations.filter(
        assigned_to__isnull=True
    ).select_related('contact', 'contact__platform', 'assigned_to')
    
    # Búsqueda avanzada por nombre o número de teléfono (igual que en chat_view)
    search_query = request.GET.get('search', '').strip()
    if search_query:
            # Limpiar el número de búsqueda (quitar espacios, guiones, paréntesis, etc.)
            clean_search = ''.join(filter(str.isdigit, search_query))
            
            # Filtro por nombre (siempre incluido)
            filters = Q(contact__name__icontains=search_query)
            
            # Si hay dígitos en la búsqueda, agregar filtros de número inteligentes
            if clean_search:
                # Convertir número limpio a patrón regex flexible
                # Ejemplo: "3001234567" -> "3.*0.*0.*1.*2.*3.*4.*5.*6.*7"
                digit_pattern = '.*'.join(clean_search)
                
                phone_filters = (
                    # Búsqueda exacta en phone y platform_user_id
                    Q(contact__phone__icontains=search_query) |
                    Q(contact__platform_user_id__icontains=search_query) |
                    Q(contact__platform_user_id__icontains=clean_search) |
                    # Búsqueda flexible por dígitos individuales (ignora espacios/formatos)
                    Q(contact__phone__regex=digit_pattern) |
                    Q(contact__platform_user_id__regex=digit_pattern)
                )
                
                # Para búsquedas numéricas cortas, ser más estricto
                if len(clean_search) >= 4:
                    phone_filters |= Q(contact__phone__contains=clean_search)
                
                filters |= phone_filters
            else:
                # Si no hay dígitos, buscar también en campos de texto de teléfono
                filters |= (
                    Q(contact__phone__icontains=search_query) |
                    Q(contact__platform_user_id__icontains=search_query)
                )
            
            unassigned_conversations = unassigned_conversations.filter(filters)
    
    unassigned_conversations = unassigned_conversations.annotate(
        last_message_preview=Subquery(
            Message.objects.filter(
                conversation=OuterRef('pk')
            ).order_by('-created_at').values('content')[:1]
        )
    ).order_by('-last_message_at')
    
    # Obtener agentes disponibles según el departamento
    if request.user.role == 'admin' or request.user.is_superuser:
        # Admin puede asignar a cualquier usuario
        available_agents = User.objects.filter(
            is_active=True,
            role__in=['admin', 'support', 'sales']
        ).values('id', 'username', 'first_name', 'last_name', 'role')
    elif request.user.role == 'support':
        # Soporte puede asignar a usuarios de soporte
        available_agents = User.objects.filter(
            is_active=True,
            role__in=['admin', 'support']
        ).values('id', 'username', 'first_name', 'last_name', 'role')
    elif request.user.role == 'sales':
        # Ventas puede asignar a usuarios de ventas
        available_agents = User.objects.filter(
            is_active=True,
            role__in=['admin', 'sales']
        ).values('id', 'username', 'first_name', 'last_name', 'role')
    else:
        available_agents = []
    
    # Estadísticas básicas
    total_unassigned = unassigned_conversations.count()
    unresponded_count = unassigned_conversations.filter(is_answered=False).count()
    responded_count = max(total_unassigned - unresponded_count, 0)
    
    # Convertir agentes a formato JSON para JavaScript
    import json
    available_agents_json = json.dumps([
        {
            'id': agent['id'],
            'username': agent['username'],
            'first_name': agent['first_name'] or '',
            'last_name': agent['last_name'] or '',
            'role': agent['role']
        }
        for agent in available_agents
    ])
    
    context = {
        'unassigned_conversations': unassigned_conversations,
        'available_agents': available_agents,
        'available_agents_json': available_agents_json,  # Versión JSON para JavaScript
        'total_unassigned': total_unassigned,
        'unresponded_count': unresponded_count,
        'responded_count': responded_count,
        'user_role': request.user.role,  # Agregar rol del usuario para JavaScript
        'user_id': request.user.id,  # Agregar ID del usuario para auto-asignación
    }
    
    return render(request, 'inbox.html', context)


@login_required
def recovery_dashboard_view(request):
    """Dashboard específico para casos de recuperación"""
    # Estadísticas generales
    total_recovery_cases = RecoveryCase.objects.count()
    active_cases = RecoveryCase.objects.filter(status='active').count()
    recovered_cases = RecoveryCase.objects.filter(status='recovered').count()
    lost_cases = RecoveryCase.objects.filter(status='lost').count()
    
    # Tasa de recuperación
    recovery_rate = (recovered_cases / total_recovery_cases * 100) if total_recovery_cases > 0 else 0
    
    # Casos por razón
    cases_by_reason = RecoveryCase.objects.values('reason').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Casos próximos a vencer (fecha objetivo en los próximos 7 días)
    upcoming_cases = RecoveryCase.objects.filter(
        status='active',
        target_recovery_date__gte=timezone.now().date(),
        target_recovery_date__lte=timezone.now().date() + timedelta(days=7)
    ).select_related('contact', 'assigned_to')
    
    # Cases vencidos
    overdue_cases = RecoveryCase.objects.filter(
        status='active',
        target_recovery_date__lt=timezone.now().date()
    ).select_related('contact', 'assigned_to')
    
    # Casos activos por agente
    cases_by_agent = RecoveryCase.objects.filter(
        status='active'
    ).values('assigned_to__username').annotate(
        count=Count('id')
    ).order_by('-count')
    
    context = {
        'total_recovery_cases': total_recovery_cases,
        'active_cases': active_cases,
        'recovered_cases': recovered_cases,
        'lost_cases': lost_cases,
        'recovery_rate': round(recovery_rate, 1),
        'cases_by_reason': cases_by_reason,
        'upcoming_cases': upcoming_cases,
        'overdue_cases': overdue_cases,
        'cases_by_agent': cases_by_agent,
    }
    
    return render(request, 'recovery_dashboard.html', context)


@login_required
def reports_view(request):
    """Vista de reportes y estadísticas"""
    # Rango de fechas
    days = int(request.GET.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)
    
    # Contactos por plataforma
    contacts_by_platform = Contact.objects.filter(
        created_at__gte=start_date
    ).values('platform__name').annotate(count=Count('id'))
    
    # Conversaciones por plataforma
    conversations_by_platform = Conversation.objects.filter(
        created_at__gte=start_date
    ).values('contact__platform__name').annotate(count=Count('id'))
    
    # Leads por tipo de caso
    leads_by_type = Lead.objects.filter(
        created_at__gte=start_date
    ).values('case_type').annotate(count=Count('id'))
    
    # Leads por estado
    leads_by_status = Lead.objects.filter(
        created_at__gte=start_date
    ).values('status').annotate(count=Count('id'))
    
    # Conversaciones por país
    conversations_by_country = Conversation.objects.filter(
        created_at__gte=start_date
    ).values('contact__country').annotate(count=Count('id')).order_by('-count')[:10]
    
    # Actividad por usuario
    activity_by_user = ActivityLog.objects.filter(
        created_at__gte=start_date
    ).values('user__username').annotate(count=Count('id')).order_by('-count')
    
    context = {
        'days': days,
        'contacts_by_platform': list(contacts_by_platform),
        'conversations_by_platform': list(conversations_by_platform),
        'leads_by_type': list(leads_by_type),
        'leads_by_status': list(leads_by_status),
        'conversations_by_country': list(conversations_by_country),
        'activity_by_user': list(activity_by_user),
    }
    
    return render(request, 'reports.html', context)


# API Views para AJAX

@login_required
@require_http_methods(["POST"])
def api_create_lead(request):
    """API para crear un nuevo lead"""
    try:
        data = json.loads(request.body)
        contact_id = data.get('contact_id')
        case_type = data.get('case_type')
        notes = data.get('notes', '')
        
        contact = get_object_or_404(Contact, id=contact_id)
        
        lead = Lead.objects.create(
            contact=contact,
            assigned_to=request.user,
            case_type=case_type,
            notes=notes
        )
        
        ActivityLog.objects.create(
            user=request.user,
            action='create_lead',
            description=f'Lead creado para {contact.name}'
        )
        
        return JsonResponse({
            'success': True,
            'lead_id': lead.id,
            'message': 'Lead creado exitosamente'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
@require_http_methods(["POST"])
def api_update_lead(request, lead_id):
    """API para actualizar un lead"""
    try:
        lead = get_object_or_404(Lead, id=lead_id)
        data = json.loads(request.body)
        
        if 'case_type' in data:
            lead.case_type = data['case_type']
        if 'status' in data:
            lead.status = data['status']
        if 'notes' in data:
            lead.notes = data['notes']
        
        lead.save()
        
        ActivityLog.objects.create(
            user=request.user,
            action='update_lead',
            description=f'Lead {lead.id} actualizado'
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Lead actualizado exitosamente'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def api_create_recovery_case(request):
    """API para crear un caso de recuperación"""
    try:
        data = json.loads(request.body)
        conversation_id = data.get('conversation_id')
        reason = data.get('reason')
        reason_notes = data.get('reason_notes', '')
        recovery_strategy = data.get('recovery_strategy', '')
        assigned_to_id = data.get('assigned_to_id')
        target_recovery_date = data.get('target_recovery_date')
        
        # Validar campos requeridos
        if not conversation_id:
            return JsonResponse({
                'success': False,
                'error': 'ID de conversación es requerido'
            }, status=400)
            
        if not reason:
            return JsonResponse({
                'success': False,
                'error': 'Razón de pérdida es requerida'
            }, status=400)
        
        conversation = get_object_or_404(Conversation, id=conversation_id)
        assigned_to = None
        if assigned_to_id:
            assigned_to = get_object_or_404(User, id=assigned_to_id)
        
        # Procesar la fecha objetivo
        parsed_date = None
        if target_recovery_date:
            try:
                from datetime import datetime
                parsed_date = datetime.strptime(target_recovery_date, '%Y-%m-%d').date()
            except ValueError:
                parsed_date = None
        
        # Crear el caso de recuperación
        recovery_case = RecoveryCase.objects.create(
            contact=conversation.contact,
            conversation=conversation,
            created_by=request.user,
            assigned_to=assigned_to,
            reason=reason,
            reason_notes=reason_notes,
            recovery_strategy=recovery_strategy,
            target_recovery_date=parsed_date
        )
        
        # Actualizar la conversación para moverla al embudo de recuperación
        conversation.funnel_type = 'recovery'
        conversation.funnel_stage = 'recovery_initial'
        conversation.save()
        
        # Crear un lead de tipo recuperación si no existe
        if not conversation.lead or conversation.lead.case_type != 'recovery':
            Lead.objects.create(
                contact=conversation.contact,
                assigned_to=assigned_to or request.user,
                case_type='recovery',
                notes=f'Caso de recuperación: {reason_notes}'
            )
        
        ActivityLog.objects.create(
            user=request.user,
            conversation=conversation,
            action='create_recovery_case',
            description=f'Caso de recuperación creado para {conversation.contact.display_name} - Razón: {reason}'
        )
        
        return JsonResponse({
            'success': True,
            'recovery_case_id': recovery_case.id,
            'message': 'Caso de recuperación creado exitosamente'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
@require_http_methods(["POST"])
def api_create_reminder(request):
    """API para crear un recordatorio"""
    try:
        data = json.loads(request.body)
        lead_id = data.get('lead_id')
        title = data.get('title')
        description = data.get('description', '')
        reminder_date = data.get('reminder_date')
        
        lead = get_object_or_404(Lead, id=lead_id)
        
        reminder = Reminder.objects.create(
            lead=lead,
            user=request.user,
            title=title,
            description=description,
            reminder_date=reminder_date
        )
        
        return JsonResponse({
            'success': True,
            'reminder_id': reminder.id,
            'message': 'Recordatorio creado exitosamente'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
@require_http_methods(["POST"])
def api_complete_reminder(request, reminder_id):
    """API para marcar un recordatorio como completado"""
    try:
        reminder = get_object_or_404(Reminder, id=reminder_id, user=request.user)
        reminder.is_completed = True
        reminder.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Recordatorio completado'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
@require_http_methods(["POST"])
def api_create_template(request):
    """API para crear una plantilla"""
    try:
        data = json.loads(request.body)
        name = data.get('name')
        content = data.get('content')
        category = data.get('category', '')
        platform_id = data.get('platform_id')
        
        platform = None
        if platform_id:
            platform = get_object_or_404(Platform, id=platform_id)
        
        template = Template.objects.create(
            name=name,
            content=content,
            category=category,
            platform=platform,
            created_by=request.user
        )
        
        ActivityLog.objects.create(
            user=request.user,
            action='create_template',
            description=f'Plantilla "{name}" creada'
        )
        
        return JsonResponse({
            'success': True,
            'template_id': template.id,
            'message': 'Plantilla creada exitosamente'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def api_update_conversation_funnel(request, conversation_id):
    """API para actualizar el embudo de una conversación"""
    try:
        conversation = get_object_or_404(Conversation, id=conversation_id)
        data = json.loads(request.body)
        
        old_funnel_type = conversation.funnel_type
        
        if 'funnel_type' in data:
            conversation.funnel_type = data['funnel_type']
        if 'funnel_stage' in data:
            conversation.funnel_stage = data['funnel_stage']
        
        conversation.save()
        
        # Crear o actualizar lead automáticamente cuando se asigna a un embudo
        if conversation.funnel_type in ['sales', 'support', 'recovery']:
            # Mapear el tipo de embudo al tipo de caso del lead
            case_type_mapping = {
                'sales': 'sales',
                'support': 'support', 
                'recovery': 'recovery'
            }
            
            lead, created = Lead.objects.get_or_create(
                contact=conversation.contact,
                case_type=case_type_mapping[conversation.funnel_type],
                defaults={
                    'assigned_to': conversation.assigned_to,
                    'notes': f'Lead creado automáticamente desde embudo de {conversation.funnel_type}'
                }
            )
            
            # Si el lead ya existía pero cambió de tipo de embudo, actualizarlo
            if not created and old_funnel_type != conversation.funnel_type:
                lead.case_type = case_type_mapping[conversation.funnel_type]
                lead.assigned_to = conversation.assigned_to
                lead.save()
        
        ActivityLog.objects.create(
            user=request.user,
            conversation=conversation,
            action='update_funnel',
            description=f'Embudo actualizado: {conversation.funnel_type} - {conversation.funnel_stage}'
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Embudo actualizado exitosamente',
            'funnel_type': conversation.funnel_type,
            'funnel_stage': conversation.funnel_stage
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
def api_get_conversation_messages(request, conversation_id):
    """API para obtener mensajes de una conversación"""
    try:
        conversation = get_object_or_404(Conversation, id=conversation_id)
        messages = conversation.messages.select_related('sender_user').order_by('created_at')
        
        messages_data = [{
            'id': msg.id,
            'sender_type': msg.sender_type,
            'sender_name': msg.sender_user.username if msg.sender_user else conversation.contact.name,
            'message_type': msg.message_type,
            'content': msg.content,
            'media_url': msg.media_url,
            'is_read': msg.is_read,
            'created_at': msg.created_at.isoformat()
        } for msg in messages]
        
        return JsonResponse({
            'success': True,
            'messages': messages_data
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
def api_get_templates(request):
    """API para obtener plantillas"""
    platform_id = request.GET.get('platform_id')
    
    templates = Template.objects.filter(is_active=True)
    if platform_id:
        templates = templates.filter(Q(platform_id=platform_id) | Q(platform__isnull=True))
    
    templates_data = [{
        'id': t.id,
        'name': t.name,
        'content': t.content,
        'category': t.category
    } for t in templates]
    
    return JsonResponse({
        'success': True,
        'templates': templates_data
    })


# API Views para WhatsApp con Baileys (cuenta normal)

@login_required
def api_whatsapp_status(request):
    """API para obtener el estado de conexión de WhatsApp"""
    try:
        from .services.whatsapp_service import WhatsAppService
        service = WhatsAppService()
        
        is_configured = service.is_configured()
        is_connected = service.is_connected() if is_configured else False
        
        return JsonResponse({
            'success': True,
            'configured': is_configured,
            'connected': is_connected,
            'message': 'Estado obtenido correctamente'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def api_whatsapp_qr(request):
    """API para obtener el código QR de WhatsApp"""
    try:
        from .services.whatsapp_service import WhatsAppService
        service = WhatsAppService()
        
        qr_result = service.get_qr_code()
        
        if qr_result['success']:
            return JsonResponse({
                'success': True,
                'qr_data': qr_result['data']
            })
        else:
            return JsonResponse({
                'success': False,
                'error': qr_result['error']
            }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def api_whatsapp_restart(request):
    """API para reiniciar la conexión de WhatsApp"""
    try:
        from .services.whatsapp_service import WhatsAppService
        service = WhatsAppService()
        
        result = service.restart_connection()
        
        ActivityLog.objects.create(
            user=request.user,
            action='whatsapp_restart',
            description='Conexión de WhatsApp reiniciada'
        )
        
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def api_send_whatsapp_message(request):
    """API para enviar mensaje por WhatsApp (cuenta normal)"""
    try:
        print(f"🔍 DEBUG SEND MESSAGE: Método HTTP: {request.method}")
        print(f"🔍 DEBUG SEND MESSAGE: Headers: {dict(request.headers)}")
        print(f"🔍 DEBUG SEND MESSAGE: Body raw: {request.body}")
        
        data = json.loads(request.body)
        print(f"🔍 DEBUG SEND MESSAGE: Data parsed: {data}")
        
        to_number = data.get('to') or data.get('recipient_id')  # Aceptar ambos nombres
        message = data.get('message')
        conversation_id = data.get('conversation_id')
        
        print(f"🔍 DEBUG SEND MESSAGE: to_number={to_number}, message={message}, conversation_id={conversation_id}")
        
        if not message:
            return JsonResponse({
                'success': False,
                'error': 'Falta el parámetro message'
            }, status=400)
        
        # Si no hay to_number pero sí conversation_id, obtener el número del contacto
        if not to_number and conversation_id:
            try:
                conversation = Conversation.objects.get(id=conversation_id)
                to_number = conversation.contact.phone or conversation.contact.platform_user_id
            except Conversation.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': 'Conversación no encontrada'
                }, status=400)
        
        if not to_number:
            return JsonResponse({
                'success': False,
                'error': f'No se pudo determinar el número de destino. Datos recibidos: {list(data.keys())}'
            }, status=400)
        
        # Obtener conversación si se proporciona
        conversation = None
        if conversation_id:
            try:
                conversation = Conversation.objects.get(id=conversation_id)
            except Conversation.DoesNotExist:
                pass
        
        from .services.whatsapp_service import WhatsAppService
        service = WhatsAppService()
        result = service.send_message(to_number, message, conversation)
        
        if result['success']:
            ActivityLog.objects.create(
                user=request.user,
                conversation=conversation,
                action='send_whatsapp_message',
                description=f'Mensaje enviado a {to_number}'
            )
        
        return JsonResponse(result)
    except Exception as e:
        print(f"❌ ERROR EN API_SEND_WHATSAPP_MESSAGE: {str(e)}")
        import traceback
        print(f"📋 TRACEBACK: {traceback.format_exc()}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# Webhooks para recibir notificaciones del bridge de Baileys
@csrf_exempt
@require_http_methods(["POST"])
def api_whatsapp_qr_updated(request):
    """Webhook para recibir actualizaciones del QR code"""
    try:
        data = json.loads(request.body)
        # Aquí podrías almacenar el QR en cache o notificar a usuarios conectados
        # Por ahora solo lo registramos
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_whatsapp_connected(request):
    """Webhook para recibir notificación de conexión exitosa"""
    try:
        data = json.loads(request.body)
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# WhatsApp Baileys Integration Views
@login_required
def api_whatsapp_status(request):
    """API para obtener el estado de WhatsApp"""
    from .services.whatsapp_service import WhatsAppService
    
    service = WhatsAppService()
    
    try:
        is_configured = service.is_configured()
        is_connected = service.is_connected() if is_configured else False
        
        return JsonResponse({
            'success': True,
            'configured': is_configured,
            'connected': is_connected
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def api_whatsapp_qr(request):
    """API para obtener el código QR de WhatsApp"""
    from .services.whatsapp_service import WhatsAppService
    
    service = WhatsAppService()
    result = service.get_qr_code()
    
    if result['success']:
        return JsonResponse(result)
    else:
        return JsonResponse(result, status=404)


@login_required
@require_http_methods(["POST"])
def api_whatsapp_restart(request):
    """API para reiniciar la conexión de WhatsApp"""
    from .services.whatsapp_service import WhatsAppService
    
    service = WhatsAppService()
    result = service.restart_connection()
    
    return JsonResponse(result)


@csrf_exempt
@require_http_methods(["POST"])
def api_whatsapp_connected(request):
    """Webhook para notificar que WhatsApp se conectó"""
    try:
        data = json.loads(request.body.decode('utf-8'))
        
        # Log de conexión
        ActivityLog.objects.create(
            action='whatsapp_connected',
            description=f'WhatsApp conectado exitosamente - {data.get("timestamp")}'
        )
        
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_whatsapp_qr_updated(request):
    """Webhook para notificar actualización de QR"""
    try:
        data = json.loads(request.body.decode('utf-8'))
        
        # Log de QR actualizado
        ActivityLog.objects.create(
            action='whatsapp_qr_updated',
            description=f'Código QR actualizado - {data.get("timestamp")}'
        )
        
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def api_assign_conversation_agent(request, conversation_id):
    """API para asignar una conversación a un agente específico y clasificarla automáticamente"""
    print(f"🚀 API ASSIGN: Recibiendo request para conversación {conversation_id}")
    try:
        conversation = get_object_or_404(Conversation, id=conversation_id)
        print(f"📋 Conversación encontrada: {conversation.contact.display_name}")
        
        data = json.loads(request.body)
        print(f"📦 Data recibida: {data}")
        
        agent_id = data.get('agent_id')
        print(f"👤 Agent ID: {agent_id}")
        
        if agent_id:
            agent = get_object_or_404(User, id=agent_id, is_active=True)
            conversation.assigned_to = agent
            
            # 🎯 AUTO-CLASIFICAR SEGÚN EL ROL DEL AGENTE
            # Clasificar si no tiene embudo o si el stage está en "none"
            needs_classification = (
                conversation.funnel_type == 'none' or 
                not conversation.funnel_type or 
                conversation.funnel_stage == 'none' or 
                not conversation.funnel_stage
            )
            
            if needs_classification:
                if agent.role == 'sales':
                    conversation.funnel_type = 'sales'
                    conversation.funnel_stage = 'sales_initial'
                    print(f"🎯 Auto-clasificando conversación {conversation_id} como VENTAS para agente {agent.username}")
                elif agent.role == 'support':
                    conversation.funnel_type = 'support'
                    conversation.funnel_stage = 'support_initial'
                    print(f"🎯 Auto-clasificando conversación {conversation_id} como SOPORTE para agente {agent.username}")
                else:
                    # Para admin, usar el contexto o asignar a ventas por defecto
                    conversation.funnel_type = 'sales'
                    conversation.funnel_stage = 'sales_initial'
                    print(f"🎯 Auto-clasificando conversación {conversation_id} como VENTAS (admin) para agente {agent.username}")
            else:
                print(f"ℹ️ Conversación {conversation_id} ya tiene clasificación: {conversation.funnel_type}/{conversation.funnel_stage}")
            
            # 📈 CREAR LEAD SIEMPRE que se asigne agente (después de clasificar)
            # Para ventas, recovery Y support
            if conversation.funnel_type in ['sales', 'recovery', 'support']:
                # Mapear correctamente funnel_type a case_type
                case_type_mapping = {
                    'sales': 'sales',
                    'support': 'support', 
                    'recovery': 'recovery'
                }
                
                mapped_case_type = case_type_mapping.get(conversation.funnel_type, 'sales')
                print(f"🗺️ Mapeando {conversation.funnel_type} → {mapped_case_type}")
                
                # Buscar lead existente por contacto y case_type
                existing_lead = Lead.objects.filter(
                    contact=conversation.contact,
                    case_type=mapped_case_type
                ).first()
                
                if existing_lead:
                    # Actualizar lead existente
                    existing_lead.assigned_to = agent
                    existing_lead.status = 'active'  # Reactivar si estaba cerrado
                    existing_lead.notes = f'{existing_lead.notes}\n\nActualizado: Reasignado a {agent.username} el {timezone.now().strftime("%Y-%m-%d %H:%M")}'
                    existing_lead.save()
                    lead = existing_lead
                    print(f"📈 Lead existente {lead.id} actualizado para {conversation.contact.display_name} - Agente: {agent.username}")
                else:
                    # Crear nuevo lead
                    lead = Lead.objects.create(
                        contact=conversation.contact,
                        assigned_to=agent,
                        case_type=mapped_case_type,
                        status='new',
                        notes=f'Lead creado automáticamente al asignar conversación a {agent.username} el {timezone.now().strftime("%Y-%m-%d %H:%M")}'
                    )
                    print(f"📈 Nuevo lead {lead.id} creado para {conversation.contact.display_name} - Tipo: {mapped_case_type} - Agente: {agent.username}")
                
                # Asociar conversación al lead
                conversation.lead = lead
                print(f"🔗 Conversación {conversation_id} asociada al lead {lead.id}")
                
                # Crear ActivityLog para el lead
                ActivityLog.objects.create(
                    user=request.user,
                    action='create_lead' if not existing_lead else 'update_lead',
                    description=f'Lead {"creado" if not existing_lead else "actualizado"} automáticamente: {conversation.contact.display_name} - {mapped_case_type}'
                )
        else:
            conversation.assigned_to = None
            
        conversation.save()
        print(f"💾 Conversación guardada exitosamente")
        
        ActivityLog.objects.create(
            user=request.user,
            conversation=conversation,
            action='assign_agent',
            description=f'Conversación asignada a: {agent.username if agent_id else "Sin asignar"}{" y clasificada en " + conversation.funnel_type if agent_id and conversation.funnel_type != "none" else ""}'
        )
        print(f"📝 ActivityLog creado")
        
        response_data = {
            'success': True,
            'message': 'Agente asignado y conversación clasificada exitosamente',
            'agent_name': agent.username if agent_id else None,
            'funnel_type': conversation.funnel_type if agent_id else None,
            'funnel_stage': conversation.funnel_stage if agent_id else None
        }
        print(f"✅ Enviando respuesta exitosa: {response_data}")
        
        return JsonResponse(response_data)
    except Exception as e:
        print(f"❌ Error en api_assign_conversation_agent: {str(e)}")
        print(f"❌ Tipo de error: {type(e).__name__}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
def api_get_available_agents(request):
    """API para obtener lista de agentes disponibles"""
    try:
        agents = User.objects.filter(
            is_active=True,
            role__in=['agent', 'supervisor', 'admin']
        ).values('id', 'username', 'first_name', 'last_name', 'role')
        
        agents_list = []
        for agent in agents:
            display_name = f"{agent['first_name']} {agent['last_name']}".strip()
            if not display_name:
                display_name = agent['username']
                
            agents_list.append({
                'id': agent['id'],
                'username': agent['username'],
                'display_name': display_name,
                'role': agent['role']
            })
        
        return JsonResponse({
            'success': True,
            'agents': agents_list
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
def api_search_conversations(request):
    """API para búsqueda de conversaciones en tiempo real - Búsqueda por nombre y número"""
    try:
        search_query = request.GET.get('q', '').strip()
        
        # Filtrar conversaciones activas
        conversations = Conversation.objects.select_related(
            'contact', 'contact__platform', 'assigned_to'
        ).filter(status='active')
        
        # Filtrar por departamento según el rol del usuario
        if request.user.role == 'admin' or request.user.is_superuser:
            # Admin ve todas las conversaciones
            pass
        elif request.user.role == 'support':
            # Soporte ve solo conversaciones de soporte
            conversations = conversations.filter(funnel_type='support')
        elif request.user.role == 'sales':
            # Ventas ve solo conversaciones de ventas
            conversations = conversations.filter(funnel_type='sales')
        
        # ✅ BÚSQUEDA INTELIGENTE - Igual que chat_view
        if search_query:
            # Limpiar el número de búsqueda (quitar espacios, guiones, paréntesis, etc.)
            clean_search = ''.join(filter(str.isdigit, search_query))
            
            # 🔍 Filtro por NOMBRE (buscar en name Y google_contact_name)
            filters = (
                Q(contact__name__icontains=search_query) |
                Q(contact__google_contact_name__icontains=search_query)
            )
            
            # 🔍 Si hay dígitos, agregar filtros de NÚMERO inteligentes
            if clean_search:
                # Convertir número limpio a patrón regex flexible
                # Ejemplo: "3001234567" -> "3.*0.*0.*1.*2.*3.*4.*5.*6.*7"
                digit_pattern = '.*'.join(clean_search)
                
                phone_filters = (
                    # Búsqueda exacta en phone y platform_user_id
                    Q(contact__phone__icontains=search_query) |
                    Q(contact__platform_user_id__icontains=search_query) |
                    Q(contact__platform_user_id__icontains=clean_search) |
                    # Búsqueda flexible por dígitos individuales (ignora espacios/formatos)
                    Q(contact__phone__regex=digit_pattern) |
                    Q(contact__platform_user_id__regex=digit_pattern)
                )
                
                # Para búsquedas numéricas cortas, ser más estricto
                if len(clean_search) >= 4:
                    phone_filters |= Q(contact__phone__contains=clean_search)
                
                filters |= phone_filters
            else:
                # Si no hay dígitos, buscar también en campos de texto de teléfono
                filters |= (
                    Q(contact__phone__icontains=search_query) |
                    Q(contact__platform_user_id__icontains=search_query)
                )
            
            # Aplicar filtros
            conversations = conversations.filter(filters)
        
        # Ordenar por prioridad: primero las que necesitan respuesta
        conversations = conversations.order_by('-needs_response', '-last_message_at')[:20]
        
        # Preparar resultados para el frontend
        results = []
        for conv in conversations:
            # Calcular si está vencida (más de 5 minutos sin respuesta)
            is_overdue = False
            if hasattr(conv, 'is_overdue'):
                is_overdue = conv.is_overdue(minutes=5)
            
            results.append({
                'id': conv.id,
                'contact_name': conv.contact.display_name,
                'platform': conv.contact.platform.name,
                'last_message_at': conv.last_message_at.strftime('%d/%m %H:%M') if conv.last_message_at else '',
                'whatsapp_number': conv.contact.phone or conv.contact.platform_user_id,
                'platform_user_id': conv.contact.platform_user_id,
                'is_overdue_5min': is_overdue
            })
        
        return JsonResponse({
            'success': True,
            'conversations': results,
            'count': len(results)
        })
        
    except Exception as e:
        import traceback
        print(f"❌ Error en api_search_conversations: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
def api_search_unassigned(request):
    """API para búsqueda de conversaciones no asignadas en la bandeja de entrada"""
    try:
        search_query = request.GET.get('q', '').strip()
        
        # Filtrar solo conversaciones no asignadas a embudos
        conversations = Conversation.objects.select_related(
            'contact', 'contact__platform', 'assigned_to'
        ).filter(
            status='active',
            funnel_type__in=['none', '']  # Solo conversaciones sin asignar a embudo
        )
        
        if search_query:
            # Limpiar el número de búsqueda (quitar espacios, guiones, paréntesis, etc.)
            clean_search = ''.join(filter(str.isdigit, search_query))
            
            # Filtro por nombre (siempre incluido)
            filters = Q(contact__name__icontains=search_query)
            
            # Si hay dígitos en la búsqueda, agregar filtros de número inteligentes
            if clean_search:
                # Convertir número limpio a patrón regex flexible
                digit_pattern = '.*'.join(clean_search)
                
                phone_filters = (
                    # Búsqueda exacta en phone y platform_user_id
                    Q(contact__phone__icontains=search_query) |
                    Q(contact__platform_user_id__icontains=search_query) |
                    Q(contact__platform_user_id__icontains=clean_search) |
                    # Búsqueda flexible por dígitos individuales (ignora espacios/formatos)
                    Q(contact__phone__regex=digit_pattern) |
                    Q(contact__platform_user_id__regex=digit_pattern)
                )
                
                # Para búsquedas numéricas cortas, ser más estricto
                if len(clean_search) >= 4:
                    phone_filters |= Q(contact__phone__contains=clean_search)
                
                filters |= phone_filters
            else:
                # Si no hay dígitos, buscar también en campos de texto de teléfono
                filters |= (
                    Q(contact__phone__icontains=search_query) |
                    Q(contact__platform_user_id__icontains=search_query)
                )
            
            conversations = conversations.filter(filters)
        
        conversations = conversations.order_by('-last_message_at')[:20]  # Limitar resultados
        
        results = []
        for conv in conversations:
            # Obtener último mensaje para preview
            last_message = conv.messages.order_by('-created_at').first()
            last_message_preview = ''
            if last_message:
                if last_message.message_type == 'text':
                    last_message_preview = last_message.content[:50] + ('...' if len(last_message.content) > 50 else '')
                else:
                    last_message_preview = f"[{last_message.message_type.upper()}]"
            
            results.append({
                'id': conv.id,
                'contact_name': conv.contact.display_name,
                'contact_phone': conv.contact.phone or '',
                'platform': conv.contact.platform.name,
                'last_message_at': conv.last_message_at.strftime('%d/%m %H:%M') if conv.last_message_at else '',
                'last_message_preview': last_message_preview,
                'is_answered': conv.is_answered,
                'assigned_to_name': conv.assigned_to.username if conv.assigned_to else None,
                'platform_user_id': conv.contact.platform_user_id
            })
        
        return JsonResponse({
            'success': True,
            'conversations': results,
            'query': search_query
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
@require_http_methods(["POST"])
def api_send_file_message(request):
    """API para enviar mensajes con archivos multimedia"""
    try:
        import os
        from django.core.files.storage import default_storage
        from django.conf import settings
        
        print("📁 Upload request received")
        print(f"📋 POST data: {dict(request.POST)}")
        print(f"📎 FILES data: {list(request.FILES.keys())}")
        
        conversation_id = request.POST.get('conversation_id')
        platform = request.POST.get('platform')
        recipient = request.POST.get('recipient')
        file_type = request.POST.get('file_type')
        message_text = request.POST.get('message', '')
        uploaded_file = request.FILES.get('file')
        
        if not uploaded_file:
            return JsonResponse({'success': False, 'error': 'No se recibió archivo'})
        
        if not conversation_id:
            return JsonResponse({'success': False, 'error': 'ID de conversación requerido'})
            
        conversation = get_object_or_404(Conversation, id=conversation_id)
        
        # Validar tamaño del archivo (máximo 50MB)
        max_size = 50 * 1024 * 1024  # 50MB
        if uploaded_file.size > max_size:
            return JsonResponse({'success': False, 'error': 'El archivo es demasiado grande (máximo 50MB)'})
        
        # Validar tipo de archivo
        allowed_types = {
            'image': ['jpg', 'jpeg', 'png', 'gif', 'webp'],
            'video': ['mp4', 'avi', 'mov', 'wmv', 'webm'],
            'audio': ['mp3', 'wav', 'ogg', 'm4a', 'aac'],
            'document': ['pdf', 'doc', 'docx', 'txt', 'xlsx', 'pptx']
        }
        
        file_extension = uploaded_file.name.split('.')[-1].lower()
        if file_type not in allowed_types or file_extension not in allowed_types[file_type]:
            return JsonResponse({'success': False, 'error': f'Tipo de archivo no permitido: {file_extension}'})
        
        # Generar nombre único para el archivo
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{file_type}_{timestamp}_{uploaded_file.name}"
        
        # Guardar archivo en la carpeta media
        file_path = f"attachments/{unique_filename}"
        saved_path = default_storage.save(file_path, uploaded_file)
        
        # Crear URL del archivo
        file_url = f"{settings.MEDIA_URL}{saved_path}"
        
        # Determinar el tipo de mensaje basado en el archivo
        message_type_map = {
            'image': 'image',
            'video': 'video', 
            'audio': 'audio',
            'document': 'document'
        }
        
        message_type = message_type_map.get(file_type, 'text')
        
        # **ENVIAR ARCHIVO A TRAVÉS DEL WHATSAPP BRIDGE** 
        from .services.whatsapp_service import WhatsAppService
        
        # Obtener el número de teléfono del contacto
        contact_phone = conversation.contact.phone
        if not contact_phone:
            return JsonResponse({'success': False, 'error': 'No se encontró número de teléfono del contacto'})
        
        # Crear URL completa del archivo para el bridge
        # Como accedemos desde red local, usar la IP configurada
        base_url = "http://192.168.1.176:8000"
        full_media_url = f"{base_url}{file_url}"
        
        # Enviar a través del WhatsApp Bridge usando endpoint directo
        import requests
        bridge_url = "http://localhost:3000"
        
        payload = {
            'to': contact_phone,
            'type': file_type,  # image, video, audio, document
            'media_url': full_media_url,
            'message': message_text or f"{file_type.title()} enviado: {uploaded_file.name}",
            'filename': uploaded_file.name
        }
        
        print(f"📤 Enviando archivo a WhatsApp Bridge:")
        print(f"   📱 Destino: {contact_phone}")
        print(f"   📎 Tipo: {file_type}")
        print(f"   🔗 URL: {full_media_url}")
        print(f"   📝 Mensaje: {payload['message']}")
        
        try:
            # Enviar a WhatsApp Bridge
            response = requests.post(f"{bridge_url}/send-message", json=payload, timeout=30)
            response_data = response.json()
            
            print(f"📡 Respuesta del Bridge: {response.status_code} - {response_data}")
            
            if response.status_code == 200 and response_data.get('success'):
                # Éxito: Guardar mensaje en BD con ID del bridge
                import uuid
                platform_message_id = response_data.get('message_id', f"agent_{timestamp}_{str(uuid.uuid4())[:8]}")
                
                # Crear mensaje en la base de datos
                message = Message.objects.create(
                    conversation=conversation,
                    platform_message_id=platform_message_id,
                    sender_type='agent',
                    sender_user=request.user,
                    content=message_text or f"{file_type.title()} enviado: {uploaded_file.name}",
                    message_type=message_type,
                    media_url=file_url
                )
                
                # Actualizar conversación
                conversation.last_message_at = timezone.now()
                conversation.last_response_at = timezone.now()
                conversation.is_answered = True
                conversation.needs_response = False
                conversation.save()
                
                # Log de actividad
                ActivityLog.objects.create(
                    user=request.user,
                    conversation=conversation,
                    action='send_file',
                    description=f'Archivo enviado a WhatsApp: {uploaded_file.name} ({file_type})'
                )
                
                return JsonResponse({
                    'success': True,
                    'message': 'Archivo enviado exitosamente a WhatsApp',
                    'file_url': file_url,
                    'message_id': message.id,
                    'whatsapp_message_id': platform_message_id
                })
            else:
                # Error del Bridge: guardar solo localmente como fallback
                error_msg = response_data.get('error', 'Error desconocido del bridge')
                print(f"❌ Error del WhatsApp Bridge: {error_msg}")
                
                # Generar platform_message_id local
                import uuid
                platform_message_id = f"agent_{timestamp}_{str(uuid.uuid4())[:8]}"
                
                # Crear mensaje en la base de datos (solo local)
                message = Message.objects.create(
                    conversation=conversation,
                    platform_message_id=platform_message_id,
                    sender_type='agent',
                    sender_user=request.user,
                    content=f"⚠️ {message_text or f'{file_type.title()} enviado: {uploaded_file.name}'} (Solo guardado localmente - Error WhatsApp: {error_msg})",
                    message_type=message_type,
                    media_url=file_url
                )
                
                # Actualizar conversación parcialmente
                conversation.last_message_at = timezone.now()
                conversation.save()
                
                return JsonResponse({
                    'success': False,
                    'error': f'Error al enviar a WhatsApp: {error_msg}. Archivo guardado solo localmente.',
                    'file_url': file_url,
                    'message_id': message.id
                })
                
        except requests.RequestException as e:
            # Error de conexión: guardar solo localmente
            print(f"❌ Error de conexión con WhatsApp Bridge: {str(e)}")
            
            # Generar platform_message_id local
            import uuid
            platform_message_id = f"agent_{timestamp}_{str(uuid.uuid4())[:8]}"
            
            # Crear mensaje en la base de datos (solo local)
            message = Message.objects.create(
                conversation=conversation,
                platform_message_id=platform_message_id,
                sender_type='agent',
                sender_user=request.user,
                content=f"⚠️ {message_text or f'{file_type.title()} enviado: {uploaded_file.name}'} (Solo guardado localmente - Bridge no disponible)",
                message_type=message_type,
                media_url=file_url
            )
            
            # Actualizar conversación parcialmente
            conversation.last_message_at = timezone.now()
            conversation.save()
            
            return JsonResponse({
                'success': False,
                'error': f'WhatsApp Bridge no disponible: {str(e)}. Archivo guardado solo localmente.',
                'file_url': file_url,
                'message_id': message.id
            })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
@require_http_methods(["POST"])
@csrf_exempt
def assign_conversation_view(request, conversation_id):
    """Asignar conversación al usuario actual"""
    try:
        data = json.loads(request.body)
        conversation = get_object_or_404(Conversation, id=conversation_id)
        
        if data.get('assign_to_current_user'):
            # Verificar que la conversación no esté ya asignada
            if conversation.assigned_to is not None:
                return JsonResponse({
                    'success': False,
                    'error': 'Esta conversación ya está asignada a otro usuario'
                })
            
            # Asignar al usuario actual
            conversation.assigned_to = request.user
            
            # 🎯 AUTO-CLASIFICAR SEGÚN EL ROL DEL USUARIO
            agent = request.user
            needs_classification = (
                conversation.funnel_type == 'none' or 
                not conversation.funnel_type or 
                conversation.funnel_stage == 'none' or 
                not conversation.funnel_stage
            )
            
            if needs_classification:
                if agent.role == 'sales':
                    conversation.funnel_type = 'sales'
                    conversation.funnel_stage = 'sales_initial'
                elif agent.role == 'support':
                    conversation.funnel_type = 'support'
                    conversation.funnel_stage = 'support_initial'
                else:
                    # Para admin, usar ventas por defecto
                    conversation.funnel_type = 'sales'
                    conversation.funnel_stage = 'sales_initial'
            
            # 📈 CREAR LEAD AUTOMÁTICAMENTE
            if conversation.funnel_type in ['sales', 'recovery', 'support']:
                # Mapear correctamente funnel_type a case_type
                case_type_mapping = {
                    'sales': 'sales',
                    'support': 'support', 
                    'recovery': 'recovery'
                }
                
                mapped_case_type = case_type_mapping.get(conversation.funnel_type, 'sales')
                
                # Buscar lead existente por contacto y case_type
                existing_lead = Lead.objects.filter(
                    contact=conversation.contact,
                    case_type=mapped_case_type
                ).first()
                
                if existing_lead:
                    # Actualizar lead existente
                    existing_lead.assigned_to = agent
                    existing_lead.status = 'active'
                    existing_lead.notes = f'{existing_lead.notes}\n\nActualizado: Reasignado a {agent.username} el {timezone.now().strftime("%Y-%m-%d %H:%M")}'
                    existing_lead.save()
                    lead = existing_lead
                else:
                    # Crear nuevo lead
                    lead = Lead.objects.create(
                        contact=conversation.contact,
                        assigned_to=agent,
                        case_type=mapped_case_type,
                        status='new',
                        notes=f'Lead creado automáticamente al auto-asignarse el {timezone.now().strftime("%Y-%m-%d %H:%M")}'
                    )
                
                # Asociar conversación al lead
                conversation.lead = lead
            
            conversation.save()
            
            # Log de actividad
            ActivityLog.objects.create(
                user=request.user,
                conversation=conversation,
                action='assign_conversation',
                description=f'Conversación asignada a {request.user.username} y clasificada en {conversation.funnel_type}'
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Conversación asignada a {request.user.username}'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Acción no válida'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
@require_http_methods(["GET"])
def conversation_count_view(request):
    """API endpoint para obtener conteos actualizados de conversaciones"""
    try:
        if request.user.is_staff:
            # Para admin: todas las conversaciones
            total_conversations = Conversation.objects.filter(status='active').count()
            assigned_conversations = Conversation.objects.filter(
                status='active',
                assigned_to__isnull=False
            ).count()
            available_conversations = Conversation.objects.filter(
                status='active',
                assigned_to__isnull=True
            ).count()
            
            return JsonResponse({
                'success': True,
                'total_count': total_conversations,
                'assigned_count': assigned_conversations,
                'available_count': available_conversations,
                'user_type': 'admin'
            })
        else:
            # Para agente: sus conversaciones y las disponibles
            assigned_count = Conversation.objects.filter(
                status='active',
                assigned_to=request.user
            ).count()
            
            # Conversaciones disponibles (sin agente asignado)
            available_count = Conversation.objects.filter(
                status='active',
                assigned_to__isnull=True
            ).count()
            
            return JsonResponse({
                'success': True,
                'assigned_count': assigned_count,
                'available_count': available_count,
                'user_type': 'agent'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error interno del servidor: {str(e)}'
        })


@csrf_exempt
@require_http_methods(["POST"])
def upload_media_view(request):
    """Endpoint para subir archivos multimedia desde WhatsApp Bridge"""
    try:
        if 'media_file' not in request.FILES:
            return JsonResponse({
                'success': False,
                'error': 'No se proporcionó archivo multimedia'
            }, status=400)
        
        uploaded_file = request.FILES['media_file']
        
        # Validar tamaño del archivo (máximo 50MB)
        if uploaded_file.size > 50 * 1024 * 1024:
            return JsonResponse({
                'success': False,
                'error': 'El archivo es demasiado grande (máximo 50MB)'
            }, status=400)
        
        # Generar nombre único para el archivo
        from datetime import datetime
        from django.core.files.storage import default_storage
        from django.conf import settings
        import os
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_extension = os.path.splitext(uploaded_file.name)[1]
        unique_filename = f"whatsapp_{timestamp}_{uploaded_file.name}"
        
        # Guardar archivo en la carpeta media
        file_path = f"attachments/{unique_filename}"
        saved_path = default_storage.save(file_path, uploaded_file)
        
        # Crear URL completa del archivo
        media_url = f"{settings.MEDIA_URL}{saved_path}"
        if hasattr(settings, 'MEDIA_DOMAIN') and settings.MEDIA_DOMAIN:
            media_url = f"{settings.MEDIA_DOMAIN}{media_url}"
        elif request.get_host():
            protocol = 'https' if request.is_secure() else 'http'
            media_url = f"{protocol}://{request.get_host()}{media_url}"
        
        return JsonResponse({
            'success': True,
            'message': 'Archivo subido exitosamente',
            'media_url': media_url,
            'filename': unique_filename,
            'size': uploaded_file.size
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error subiendo archivo: {str(e)}'
        }, status=500)

