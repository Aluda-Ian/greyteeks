from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('providers', '0007_emailtemplate_owner_alter_emailtemplate_provider_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='whatsappprovider',
            name='provider_type',
            field=models.CharField(
                default='meta',
                help_text='Select the WhatsApp gateway provider',
                max_length=20,
                choices=[('meta', 'Meta Cloud API'), ('infobip', 'Infobip WhatsApp')],
            ),
        ),
        migrations.AddField(
            model_name='whatsappprovider',
            name='infobip_base_url',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Infobip base URL e.g. xyz.api.infobip.com',
                max_length=255,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='whatsappprovider',
            name='infobip_sender',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Infobip WhatsApp sender number',
                max_length=20,
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='whatsappprovider',
            name='phone_number_id',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AlterField(
            model_name='whatsappprovider',
            name='waba_id',
            field=models.CharField(blank=True, max_length=100, verbose_name='WhatsApp Business Account ID'),
        ),
        migrations.AddField(
            model_name='whatsapptemplate',
            name='owner',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.CASCADE,
                related_name='whatsapp_templates',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
