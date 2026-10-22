import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('smartbids', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Licitacion',
            fields=[
                ('lic_codigo', models.CharField(max_length=20, primary_key=True, serialize=False)),
                ('lic_nombre', models.CharField(blank=True, max_length=300, null=True)),
                ('lic_descripcion', models.TextField(blank=True, null=True)),
                ('lic_fecha_cierre', models.DateField(blank=True, db_comment='date sin tiempo', null=True)),
                ('lic_hora_cierre', models.TimeField(blank=True, null=True)),
                ('lic_toma_razon', models.BooleanField(blank=True, null=True)),
                ('lic_fecha_public', models.DateField(blank=True, db_comment='esta es date con tiempo', null=True)),
                ('lic_fecha_preguntas', models.DateTimeField(blank=True, db_comment='date con tiempo', null=True)),
                ('lic_fecha_respuestas', models.DateTimeField(blank=True, db_comment='fecha sin hora', null=True)),
                ('lic_tipo_licitacion', models.CharField(blank=True, max_length=2, null=True)),
                ('lic_moneda', models.CharField(blank=True, max_length=20, null=True)),
                ('lic_presupuesto', models.DecimalField(blank=True, db_comment='numero con deciamles', decimal_places=2, max_digits=18, null=True)),
                ('lic_items_cantidad', models.IntegerField(blank=True, null=True)),
                ('lic_codigos_producto', models.TextField(blank=True, null=True)),
                ('lic_diccionario_palabras', models.TextField(blank=True, null=True)),
                ('lic_texto', models.TextField(blank=True, null=True)),
                ('lic_url', models.TextField(blank=True, null=True)),
                ('lic_plazo', models.IntegerField(blank=True, null=True)),
                ('lic_codigo_ucom', models.ForeignKey(
                    blank=True,
                    db_column='lic_codigo_ucom',
                    null=True,
                    on_delete=django.db.models.deletion.DO_NOTHING,
                    to='smartbids.unidadcompra',
                )),
            ],
            options={
                'db_table': '"procurement"."licitacion"',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='LicitacionDocumento',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=255)),
                ('url', models.URLField(max_length=2000)),
                ('fecha_publicacion', models.DateTimeField(blank=True, null=True)),
                ('licitacion', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='documentos',
                    to='smartbids.licitacion',
                )),
            ],
            options={
                'db_table': 'smartbids_licitacion_documento',
                'ordering': ('-fecha_publicacion', 'titulo'),
            },
        ),
        migrations.CreateModel(
            name='LicitacionPregunta',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pregunta', models.TextField()),
                ('respuesta', models.TextField(blank=True)),
                ('fecha_pregunta', models.DateTimeField(blank=True, null=True)),
                ('fecha_respuesta', models.DateTimeField(blank=True, null=True)),
                ('licitacion', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='preguntas_respuestas',
                    to='smartbids.licitacion',
                )),
            ],
            options={
                'db_table': 'smartbids_licitacion_pregunta',
                'ordering': ('fecha_pregunta', 'id'),
            },
        ),
        migrations.CreateModel(
            name='SeguimientoLicitacion',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('estado_actual', models.CharField(
                    choices=[
                        ('publicada', 'Publicada'),
                        ('preguntas', 'Período de preguntas'),
                        ('ofertas', 'Recepción de ofertas'),
                        ('cerrada', 'Cerrada'),
                    ],
                    max_length=20,
                )),
                ('seguimiento_activo', models.BooleanField(default=True)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
                ('dejado_de_seguir_en', models.DateTimeField(blank=True, null=True)),
                ('cerrada_en', models.DateTimeField(blank=True, null=True)),
                ('licitacion', models.ForeignKey(
                    db_column='id_licitacion',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='seguimientos',
                    to='smartbids.licitacion',
                )),
                ('usuario', models.ForeignKey(
                    db_column='id_usuario',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='seguimientos_licitaciones',
                    to='smartbids.suscriptor',
                )),
            ],
            options={
                'db_table': 'smartbids_seguimiento_licitacion',
            },
        ),
        migrations.CreateModel(
            name='NotificacionLicitacion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('estado_anterior', models.CharField(max_length=20)),
                ('estado_nuevo', models.CharField(max_length=20)),
                ('mensaje', models.CharField(max_length=300)),
                ('leida', models.BooleanField(default=False)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('licitacion', models.ForeignKey(
                    db_column='id_licitacion',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='notificaciones',
                    to='smartbids.licitacion',
                )),
                ('seguimiento', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='notificaciones',
                    to='smartbids.seguimientolicitacion',
                )),
                ('usuario', models.ForeignKey(
                    db_column='id_usuario',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='notificaciones_licitaciones',
                    to='smartbids.suscriptor',
                )),
            ],
            options={
                'db_table': 'smartbids_notificacion_licitacion',
                'ordering': ('-creado_en',),
            },
        ),
        migrations.AddConstraint(
            model_name='seguimientolicitacion',
            constraint=models.UniqueConstraint(
                fields=('usuario', 'licitacion'),
                name='uniq_seguimiento_usuario_licitacion',
            ),
        ),
    ]
