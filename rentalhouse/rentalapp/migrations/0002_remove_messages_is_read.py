# Generated migration to remove is_read field from Messages model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rentalapp', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='messages',
            name='is_read',
        ),
    ]
