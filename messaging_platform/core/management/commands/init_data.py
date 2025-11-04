from django.core.management.base import BaseCommand
from core.models import Platform, APIConfiguration, User


class Command(BaseCommand):
    help = 'Inicializa datos básicos de la aplicación'

    def handle(self, *args, **options):
        # Crear plataformas
        platforms = ['whatsapp', 'facebook', 'telegram']
        
        for platform_name in platforms:
            platform, created = Platform.objects.get_or_create(
                name=platform_name,
                defaults={'is_active': True}
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'Plataforma {platform_name} creada'))
                
                # Crear configuración API vacía
                APIConfiguration.objects.get_or_create(platform=platform)
            else:
                self.stdout.write(f'Plataforma {platform_name} ya existe')
        
        # Crear usuario admin si no existe
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin123',
                role='admin'
            )
            self.stdout.write(self.style.SUCCESS('Usuario admin creado (admin/admin123)'))
        else:
            self.stdout.write('Usuario admin ya existe')
        
        self.stdout.write(self.style.SUCCESS('Inicialización completada'))

