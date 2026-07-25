import core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('farmacia', '0007_lecturacomprafarmacia'),
    ]

    operations = [
        migrations.AlterField(
            model_name='lecturarecetafarmacia',
            name='imagen',
            field=models.ImageField(
                max_length=255,
                upload_to='recetas_farmacia/%Y/%m/%d/',
                validators=[core.validators.validate_image_upload],
            ),
        ),
    ]
