import django.contrib.gis.db.models.fields
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='District',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('geometry', django.contrib.gis.db.models.fields.MultiPolygonField(srid=4326)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='FireCause',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('category', models.CharField(max_length=50, choices=[
                    ('natural', 'Природная'),
                    ('human_negligent', 'Неосторожность'),
                    ('human_deliberate', 'Умышленная'),
                    ('technical', 'Техногенная'),
                    ('unknown', 'Не установлена'),
                ])),
                ('display_order', models.PositiveSmallIntegerField(default=100)),
            ],
            options={
                'ordering': ['display_order', 'name'],
            },
        ),
        migrations.CreateModel(
            name='WeatherStation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=20, unique=True)),
                ('name', models.CharField(max_length=100)),
                ('location', django.contrib.gis.db.models.fields.PointField(srid=4326)),
                ('is_active', models.BooleanField(default=True)),
                ('district', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='weather_stations', to='fires.district')),
            ],
        ),
        migrations.CreateModel(
            name='ImportBatch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file_name', models.CharField(max_length=255)),
                ('category', models.CharField(max_length=20, choices=[('forest', 'Лесной'), ('techno', 'Техносферный')])),
                ('strategy', models.CharField(default='report', max_length=20, choices=[
                    ('skip', 'Пропустить'),
                    ('update', 'Обновить существующие'),
                    ('report', 'Пометить как возможный дубль'),
                ])),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('total_rows', models.PositiveIntegerField(default=0)),
                ('created_count', models.PositiveIntegerField(default=0)),
                ('updated_count', models.PositiveIntegerField(default=0)),
                ('skipped_count', models.PositiveIntegerField(default=0)),
                ('duplicates_count', models.PositiveIntegerField(default=0)),
                ('error_count', models.PositiveIntegerField(default=0)),
                ('errors_json', models.JSONField(blank=True, default=list)),
                ('source_file', models.FileField(blank=True, null=True, upload_to='imports/%Y/%m/')),
                ('is_reverted', models.BooleanField(default=False)),
                ('reverted_at', models.DateTimeField(blank=True, null=True)),
                ('uploaded_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ('reverted_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reverted_batches', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-uploaded_at'],
            },
        ),
        migrations.CreateModel(
            name='Fire',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category', models.CharField(max_length=20, choices=[('forest', 'Лесной'), ('techno', 'Техносферный')])),
                ('location', django.contrib.gis.db.models.fields.PointField(srid=4326)),
                ('settlement', models.CharField(blank=True, max_length=255, verbose_name='Населённый пункт')),
                ('occurred_at', models.DateTimeField(verbose_name='Дата и время')),
                ('area_hectares', models.DecimalField(decimal_places=4, default=0, max_digits=12, verbose_name='Площадь, га')),
                ('area_original_value', models.DecimalField(blank=True, decimal_places=4, max_digits=12, null=True)),
                ('area_original_unit', models.CharField(default='ha', max_length=10, choices=[('m2', 'м²'), ('ha', 'га'), ('km2', 'км²')])),
                ('fatalities_count', models.PositiveIntegerField(default=0, verbose_name='Погибших')),
                ('cause_raw', models.TextField(blank=True, verbose_name='Причина (исходный текст)')),
                ('inaction_reason', models.TextField(blank=True, verbose_name='Причина непринятия мер')),
                ('commander', models.CharField(blank=True, max_length=255, verbose_name='Руководитель тушения (ФИО)')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('district', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='fires', to='fires.district')),
                ('cause', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='fires', to='fires.firecause')),
                ('import_batch', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='fires', to='fires.importbatch')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-occurred_at'],
            },
        ),
        migrations.CreateModel(
            name='FireCauseAlias',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.CharField(max_length=255, unique=True)),
                ('cause', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='aliases', to='fires.firecause')),
            ],
        ),
        migrations.CreateModel(
            name='ForestFireProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('detection_location', django.contrib.gis.db.models.fields.PointField(blank=True, null=True, srid=4326)),
                ('detection_method', models.CharField(blank=True, max_length=100)),
                ('protection_zone', models.CharField(blank=True, max_length=100)),
                ('land_category', models.CharField(blank=True, max_length=100)),
                ('dominant_species', models.CharField(blank=True, max_length=255)),
                ('designated_purpose', models.CharField(blank=True, max_length=255)),
                ('state', models.CharField(default='detected', max_length=20, choices=[
                    ('detected', 'Обнаружен'),
                    ('active', 'Действующий'),
                    ('localized', 'Локализован'),
                    ('extinguished', 'Ликвидирован'),
                ])),
                ('wind_speed', models.DecimalField(blank=True, decimal_places=1, max_digits=4, null=True)),
                ('personnel_count', models.PositiveIntegerField(default=0)),
                ('equipment_count', models.PositiveIntegerField(default=0)),
                ('quantity', models.PositiveIntegerField(default=0)),
                ('suppression_started_at', models.DateTimeField(blank=True, null=True)),
                ('localized_at', models.DateTimeField(blank=True, null=True)),
                ('extinguished_at', models.DateTimeField(blank=True, null=True)),
                ('damage_rub', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ('suppression_cost_rub', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ('fire', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='forest_profile', to='fires.fire')),
            ],
        ),
        migrations.CreateModel(
            name='PossibleDuplicate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('resolved', models.BooleanField(default=False)),
                ('resolved_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('new_fire', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='fires.fire')),
                ('existing_fire', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='fires.fire')),
                ('batch', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='fires.importbatch')),
                ('resolved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='DailyWeatherObservation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('temperature_14', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('dew_point_14', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('precipitation_mm', models.DecimalField(decimal_places=1, default=0, max_digits=5)),
                ('fetched_at', models.DateTimeField(auto_now=True)),
                ('station', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='observations', to='fires.weatherstation')),
            ],
        ),
        migrations.CreateModel(
            name='FireDangerForecast',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('danger_class', models.PositiveSmallIntegerField(choices=[
                    (1, 'Отсутствует'),
                    (2, 'Малая'),
                    (3, 'Средняя'),
                    (4, 'Высокая'),
                    (5, 'Чрезвычайная'),
                ])),
                ('source', models.CharField(max_length=20, choices=[
                    ('manual', 'Ручной ввод'),
                    ('nesterov', 'Расчёт по Нестерову'),
                ])),
                ('nesterov_index', models.DecimalField(blank=True, decimal_places=1, max_digits=9, null=True)),
                ('note', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('district', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='danger_forecasts', to='fires.district')),
                ('entered_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddIndex(
            model_name='fire',
            index=models.Index(fields=['category', 'occurred_at'], name='fires_fire_cat_occ_idx'),
        ),
        migrations.AddIndex(
            model_name='fire',
            index=models.Index(fields=['district'], name='fires_fire_district_idx'),
        ),
        migrations.AddIndex(
            model_name='dailyweatherobservation',
            index=models.Index(fields=['station', '-date'], name='fires_dwo_stn_date_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='dailyweatherobservation',
            unique_together={('station', 'date')},
        ),
        migrations.AddIndex(
            model_name='firedangerforecast',
            index=models.Index(fields=['date'], name='fires_fdf_date_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='firedangerforecast',
            unique_together={('district', 'date')},
        ),
    ]
