from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Platform, Template, APIConfiguration, User
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Inicializa datos básicos del sistema: plataformas, plantillas y configuraciones iniciales'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Elimina datos existentes antes de crear nuevos',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🚀 Iniciando configuración del sistema...')
        )

        if options['reset']:
            self.stdout.write('⚠️  Eliminando datos existentes...')
            self.reset_data()

        with transaction.atomic():
            # Crear plataformas
            self.create_platforms()
            
            # Crear plantillas predefinidas
            self.create_templates()
            
            # Crear configuraciones API básicas
            self.create_api_configurations()

        self.stdout.write(
            self.style.SUCCESS('✅ Configuración inicial completada exitosamente!')
        )
        self.print_next_steps()

    def reset_data(self):
        """Elimina datos existentes"""
        Template.objects.all().delete()
        APIConfiguration.objects.all().delete()
        Platform.objects.all().delete()
        self.stdout.write('📝 Datos existentes eliminados')

    def create_platforms(self):
        """Crea las plataformas de mensajería por defecto"""
        platforms_data = [
            {'name': 'whatsapp', 'is_active': True},
            {'name': 'facebook', 'is_active': False},
            {'name': 'telegram', 'is_active': False},
        ]

        for platform_data in platforms_data:
            platform, created = Platform.objects.get_or_create(
                name=platform_data['name'],
                defaults={'is_active': platform_data['is_active']}
            )
            
            status = "✅ Creada" if created else "📋 Ya existe"
            self.stdout.write(f'{status}: Plataforma {platform.name}')

    def create_templates(self):
        """Crea plantillas de respuesta predefinidas"""
        # Obtener usuario admin para asignar como creador
        try:
            admin_user = User.objects.filter(is_superuser=True).first()
        except:
            admin_user = None

        templates_data = [
            # Saludo y bienvenida
            {
                'name': 'Saludo Inicial',
                'content': '¡Hola! 👋 Gracias por contactarnos. ¿En qué podemos ayudarte hoy?',
                'category': 'saludo',
                'platform': None,  # Para todas las plataformas
            },
            {
                'name': 'Bienvenida Empresa',
                'content': '¡Bienvenido/a a [NOMBRE_EMPRESA]! 🎉\n\nEstamos aquí para ayudarte. Por favor, cuéntanos qué necesitas y te asistiremos lo antes posible.',
                'category': 'saludo',
                'platform': None,
            },
            
            # Información de productos/servicios
            {
                'name': 'Información General',
                'content': 'Te comparto información sobre nuestros productos y servicios:\n\n📋 [DESCRIPCIÓN_SERVICIOS]\n💰 Precios desde $[PRECIO]\n📞 Para más detalles: [CONTACTO]\n\n¿Te interesa alguno en particular?',
                'category': 'informacion',
                'platform': None,
            },
            {
                'name': 'Horarios de Atención',
                'content': '🕐 Nuestros horarios de atención son:\n\n📅 Lunes a Viernes: 9:00 AM - 6:00 PM\n📅 Sábados: 9:00 AM - 2:00 PM\n📅 Domingos: Cerrado\n\nSi escribes fuera de horario, te responderemos lo antes posible. 😊',
                'category': 'informacion',
                'platform': None,
            },
            
            # Seguimiento y ventas
            {
                'name': 'Seguimiento Interés',
                'content': 'Veo que estás interesado/a en nuestros servicios. 🎯\n\n¿Te gustaría que agendemos una llamada para conversarlo mejor? Podemos encontrar la mejor solución para ti.',
                'category': 'ventas',
                'platform': None,
            },
            {
                'name': 'Cotización Solicitada',
                'content': '📋 Para preparar tu cotización personalizada necesito algunos datos:\n\n• Nombre completo\n• Empresa (si aplica)\n• Servicio de interés\n• Presupuesto aproximado\n• Fecha requerida\n\n¿Podrías ayudarme con esta información?',
                'category': 'ventas',
                'platform': None,
            },
            
            # Soporte técnico
            {
                'name': 'Soporte Técnico',
                'content': '🔧 Para brindarte el mejor soporte técnico, por favor compárteme:\n\n• Descripción detallada del problema\n• Capturas de pantalla (si es posible)\n• ¿Cuándo comenzó el problema?\n• ¿Has intentado alguna solución?\n\nEstaré aquí para ayudarte a resolverlo. 💪',
                'category': 'soporte',
                'platform': None,
            },
            
            # Despedida y cierre
            {
                'name': 'Despedida Cordial',
                'content': '¡Muchas gracias por contactarnos! 😊\n\nHa sido un placer atenderte. Si necesitas algo más, no dudes en escribirnos.\n\n¡Que tengas un excelente día! 🌟',
                'category': 'despedida',
                'platform': None,
            },
            {
                'name': 'Seguimiento Futuro',
                'content': 'Perfecto, quedamos en contacto. 📞\n\nTe escribiré en [TIEMPO] para dar seguimiento. Mientras tanto, si surge alguna duda, estaré aquí para ayudarte.\n\n¡Hasta pronto! 👋',
                'category': 'despedida',
                'platform': None,
            },
            
            # Plantillas específicas de WhatsApp
            {
                'name': 'Confirmación WhatsApp',
                'content': '✅ Mensaje recibido correctamente.\n\nTe responderé en breve. Si es urgente, puedes llamar al [TELÉFONO].\n\nGracias por tu paciencia. 🙏',
                'category': 'confirmacion',
                'platform': 'whatsapp',
            },
            {
                'name': 'Fuera de Horario',
                'content': '🌙 Gracias por tu mensaje.\n\nActualmente estamos fuera de horario de atención. Te responderemos mañana a primera hora.\n\n⏰ Horario: Lunes a Viernes 9:00 AM - 6:00 PM\n\n¡Que descanses! 😴',
                'category': 'automatica',
                'platform': 'whatsapp',
            },
        ]

        platforms = {p.name: p for p in Platform.objects.all()}
        
        for template_data in templates_data:
            platform = None
            if template_data['platform']:
                platform = platforms.get(template_data['platform'])
            
            template, created = Template.objects.get_or_create(
                name=template_data['name'],
                defaults={
                    'content': template_data['content'],
                    'category': template_data['category'],
                    'platform': platform,
                    'is_active': True,
                    'created_by': admin_user,
                }
            )
            
            status = "✅ Creada" if created else "📋 Ya existe"
            self.stdout.write(f'{status}: Plantilla "{template.name}"')

    def create_api_configurations(self):
        """Crea configuraciones API básicas para cada plataforma"""
        platforms = Platform.objects.all()
        
        for platform in platforms:
            config, created = APIConfiguration.objects.get_or_create(
                platform=platform,
                defaults={
                    'is_active': False,  # Se activará cuando se configuren las credenciales
                }
            )
            
            status = "✅ Creada" if created else "📋 Ya existe"
            self.stdout.write(f'{status}: Configuración API para {platform.name}')

    def print_next_steps(self):
        """Muestra los próximos pasos a seguir"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.WARNING('📋 PRÓXIMOS PASOS:'))
        self.stdout.write('='*60)
        
        self.stdout.write('\n1. 🔑 Configurar credenciales de WhatsApp Business API:')
        self.stdout.write('   - Ve al admin panel: http://localhost:8000/admin/')
        self.stdout.write('   - Busca "API Configurations" > WhatsApp')
        self.stdout.write('   - Agrega tus credenciales de Meta Business')
        
        self.stdout.write('\n2. 🌐 Configurar webhook público:')
        self.stdout.write('   - Instala ngrok: https://ngrok.com/')
        self.stdout.write('   - Ejecuta: ngrok http 8000')
        self.stdout.write('   - Webhook URL: https://[ID].ngrok.io/webhooks/whatsapp/')
        
        self.stdout.write('\n3. 📱 Probar conexión:')
        self.stdout.write('   - Envía un mensaje a tu número de WhatsApp Business')
        self.stdout.write('   - Verifica que aparezca en el dashboard')
        
        self.stdout.write('\n4. 👤 Gestionar plantillas:')
        self.stdout.write('   - Ve a: http://localhost:8000/templates/')
        self.stdout.write('   - Personaliza las plantillas según tu negocio')
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('🎉 ¡Sistema listo para configurar WhatsApp!'))
        self.stdout.write('='*60 + '\n')