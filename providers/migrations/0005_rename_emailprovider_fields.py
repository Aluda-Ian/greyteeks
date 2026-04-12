from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('providers', '0004_merge_0002_whatsapptemplate_0003_email_provider'),
    ]

    operations = [
        migrations.RenameField(
            model_name='emailprovider',
            old_name='host',
            new_name='smtp_host',
        ),
        migrations.RenameField(
            model_name='emailprovider',
            old_name='port',
            new_name='smtp_port',
        ),
        migrations.RenameField(
            model_name='emailprovider',
            old_name='username',
            new_name='smtp_username',
        ),
        migrations.RenameField(
            model_name='emailprovider',
            old_name='password',
            new_name='smtp_password',
        ),
    ]
