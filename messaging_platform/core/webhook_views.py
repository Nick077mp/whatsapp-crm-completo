from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from .services.whatsapp_service import WhatsAppService
from .services.facebook_service import FacebookService
from .services.telegram_service import TelegramService
from .services import ContactClassificationService


@csrf_exempt
@require_http_methods(["GET", "POST"])
def whatsapp_webhook(request):
    """Webhook para WhatsApp Business API"""
    
    if request.method == 'GET':
        # Verificación del webhook
        mode = request.GET.get('hub.mode')
        token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')
        
        service = WhatsAppService()
        result = service.verify_webhook(mode, token, challenge)
        
        if result:
            return HttpResponse(result, content_type='text/plain')
        else:
            return HttpResponse('Verification failed', status=403)
    
    elif request.method == 'POST':
        # Procesar mensaje entrante
        try:
            print(f"🔍 DEBUG Webhook entrante - Headers: {dict(request.headers)}")
            print(f"🔍 DEBUG Webhook entrante - Body raw: {request.body}")
            
            body = json.loads(request.body.decode('utf-8'))
            print(f"🔍 DEBUG Webhook entrante - Body parsed: {body}")
            
            service = WhatsAppService()
            result = service.process_webhook(body)
            
            print(f"🔍 DEBUG Webhook entrante - Result: {result}")
            
            if result.get('success'):
                return JsonResponse({'status': 'success'})
            else:
                return JsonResponse({'status': 'error', 'message': result.get('error')}, status=400)
        except Exception as e:
            print(f"❌ ERROR en webhook entrante: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def facebook_webhook(request):
    """Webhook para Facebook Messenger"""
    
    if request.method == 'GET':
        # Verificación del webhook
        mode = request.GET.get('hub.mode')
        token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')
        
        service = FacebookService()
        result = service.verify_webhook(mode, token, challenge)
        
        if result:
            return HttpResponse(result, content_type='text/plain')
        else:
            return HttpResponse('Verification failed', status=403)
    
    elif request.method == 'POST':
        # Verificar firma
        signature = request.headers.get('X-Hub-Signature-256', '')
        body = request.body.decode('utf-8')
        
        service = FacebookService()
        
        # Verificar firma si está configurada
        if service.is_configured() and service.config.facebook_app_secret:
            if not service.verify_signature(body, signature):
                return JsonResponse({'status': 'error', 'message': 'Invalid signature'}, status=403)
        
        # Procesar mensaje entrante
        try:
            body_data = json.loads(body)
            
            result = service.process_webhook(body_data)
            
            if result.get('success'):
                return JsonResponse({'status': 'success'})
            else:
                return JsonResponse({'status': 'error', 'message': result.get('error')}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def telegram_webhook(request):
    """Webhook para Telegram Bot API"""
    
    try:
        body = json.loads(request.body.decode('utf-8'))
        
        service = TelegramService()
        result = service.process_webhook(body)
        
        if result.get('success'):
            return JsonResponse({'status': 'success'})
        else:
            return JsonResponse({'status': 'error', 'message': result.get('error')}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def send_message_api(request):
    """API unificada para enviar mensajes a cualquier plataforma"""
    try:
        data = json.loads(request.body.decode('utf-8'))
        
        platform = data.get('platform')  # whatsapp, facebook, telegram
        recipient = data.get('recipient')  # phone number, user id, chat id
        message = data.get('message')
        conversation_id = data.get('conversation_id')
        
        # Obtener conversación si se proporciona
        conversation = None
        if conversation_id:
            from .models import Conversation
            try:
                conversation = Conversation.objects.get(id=conversation_id)
            except Conversation.DoesNotExist:
                pass
        
        # Enviar según la plataforma
        if platform == 'whatsapp':
            service = WhatsAppService()
            result = service.send_message(recipient, message, conversation)
        elif platform == 'facebook':
            service = FacebookService()
            result = service.send_message(recipient, message, conversation)
        elif platform == 'telegram':
            service = TelegramService()
            result = service.send_message(recipient, message, conversation)
        else:
            return JsonResponse({'success': False, 'error': 'Plataforma no válida'}, status=400)
        
        if result.get('success'):
            return JsonResponse(result)
        else:
            return JsonResponse(result, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def whatsapp_outgoing_webhook(request):
    """Webhook para mensajes salientes de WhatsApp (enviados desde WhatsApp directamente)"""
    
    try:
        print(f"🔍 DEBUG Webhook saliente - Headers: {dict(request.headers)}")
        print(f"🔍 DEBUG Webhook saliente - Body raw: {request.body}")
        
        body = json.loads(request.body.decode('utf-8'))
        print(f"🔍 DEBUG Webhook saliente - Body parsed: {body}")
        
        service = WhatsAppService()
        result = service.process_outgoing_webhook(body)
        
        print(f"🔍 DEBUG Webhook saliente - Result: {result}")
        
        if result.get('success'):
            return JsonResponse({'status': 'success'})
        else:
            return JsonResponse({'status': 'error', 'message': result.get('error')}, status=400)
    except Exception as e:
        print(f"❌ ERROR en webhook saliente: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

