# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_alter_conversation_funnel_stage_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='conversation',
            name='needs_response',
            field=models.BooleanField(
                default=False, 
                help_text='Indica si la conversación necesita respuesta del agente'
            ),
        ),
        # Marcar conversaciones sin respuesta como que necesitan respuesta
        migrations.RunSQL(
            "UPDATE conversations SET needs_response = true WHERE is_answered = false AND status = 'active';",
            reverse_sql="UPDATE conversations SET needs_response = false;"
        ),
    ]