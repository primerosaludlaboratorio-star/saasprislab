# Shim de grafo: en producción algunas BD aplicaron 0008 antes de que existiera 0007b.
# Las columnas nullable + backfill + NOT NULL viven en 0008; esta migración no hace nada.
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('lims', '0008_tenant_empresa_row_isolation'),
    ]

    operations = []
