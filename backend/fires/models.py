from django.contrib.gis.db import models
from django.conf import settings


class FireCategory(models.TextChoices):
    FOREST = 'forest', 'Лесной'
    TECHNO = 'techno', 'Техносферный'


class FireState(models.TextChoices):
    DETECTED = 'detected', 'Обнаружен'
    ACTIVE = 'active', 'Действующий'
    LOCALIZED = 'localized', 'Локализован'
    EXTINGUISHED = 'extinguished', 'Ликвидирован'


class AreaUnit(models.TextChoices):
    SQ_METERS = 'm2', 'м²'
    HECTARES = 'ha', 'га'
    SQ_KILOMETERS = 'km2', 'км²'


class DuplicateStrategy(models.TextChoices):
    SKIP = 'skip', 'Пропустить'
    UPDATE = 'update', 'Обновить существующие'
    REPORT = 'report', 'Пометить как возможный дубль'


class FireDangerClass(models.IntegerChoices):
    ABSENT = 1, 'Отсутствует'
    LOW = 2, 'Малая'
    MEDIUM = 3, 'Средняя'
    HIGH = 4, 'Высокая'
    EXTREME = 5, 'Чрезвычайная'


AREA_TO_HECTARES = {
    AreaUnit.SQ_METERS: 0.0001,
    AreaUnit.HECTARES: 1,
    AreaUnit.SQ_KILOMETERS: 100,
}


class District(models.Model):
    name = models.CharField(max_length=100)
    geometry = models.MultiPolygonField(srid=4326)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class FireCause(models.Model):
    name = models.CharField(max_length=255, unique=True)
    category = models.CharField(max_length=50, choices=[
        ('natural', 'Природная'),
        ('human_negligent', 'Неосторожность'),
        ('human_deliberate', 'Умышленная'),
        ('technical', 'Техногенная'),
        ('unknown', 'Не установлена'),
    ])
    display_order = models.PositiveSmallIntegerField(default=100)

    class Meta:
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name


class FireCauseAlias(models.Model):
    cause = models.ForeignKey(FireCause, on_delete=models.CASCADE, related_name='aliases')
    text = models.CharField(max_length=255, unique=True)


class Fire(models.Model):
    category = models.CharField(max_length=20, choices=FireCategory.choices)
    location = models.PointField(srid=4326)
    settlement = models.CharField('Населённый пункт', max_length=255, blank=True)
    district = models.ForeignKey(District, on_delete=models.PROTECT,
                                  null=True, blank=True, related_name='fires')
    occurred_at = models.DateTimeField('Дата и время')

    area_hectares = models.DecimalField('Площадь, га', max_digits=12,
                                        decimal_places=4, default=0)
    area_original_value = models.DecimalField(max_digits=12, decimal_places=4,
                                               null=True, blank=True)
    area_original_unit = models.CharField(max_length=10,
                                           choices=AreaUnit.choices,
                                           default=AreaUnit.HECTARES)
    fatalities_count = models.PositiveIntegerField('Погибших', default=0)

    cause_raw = models.TextField('Причина (исходный текст)', blank=True)
    cause = models.ForeignKey(FireCause, on_delete=models.SET_NULL,
                               null=True, blank=True, related_name='fires')
    inaction_reason = models.TextField('Причина непринятия мер', blank=True)
    commander = models.CharField('Руководитель тушения (ФИО)',
                                  max_length=255, blank=True)

    import_batch = models.ForeignKey('ImportBatch', on_delete=models.SET_NULL,
                                      null=True, blank=True, related_name='fires')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['category', 'occurred_at']),
            models.Index(fields=['district']),
        ]
        ordering = ['-occurred_at']


class ForestFireProfile(models.Model):
    fire = models.OneToOneField(Fire, on_delete=models.CASCADE,
                                 related_name='forest_profile')
    detection_location = models.PointField(srid=4326, null=True, blank=True)
    detection_method = models.CharField(max_length=100, blank=True)
    protection_zone = models.CharField(max_length=100, blank=True)
    land_category = models.CharField(max_length=100, blank=True)
    dominant_species = models.CharField(max_length=255, blank=True)
    designated_purpose = models.CharField(max_length=255, blank=True)
    state = models.CharField(max_length=20, choices=FireState.choices,
                              default=FireState.DETECTED)
    wind_speed = models.DecimalField(max_digits=4, decimal_places=1,
                                      null=True, blank=True)
    personnel_count = models.PositiveIntegerField(default=0)
    equipment_count = models.PositiveIntegerField(default=0)
    quantity = models.PositiveIntegerField(default=0)
    suppression_started_at = models.DateTimeField(null=True, blank=True)
    localized_at = models.DateTimeField(null=True, blank=True)
    extinguished_at = models.DateTimeField(null=True, blank=True)
    damage_rub = models.DecimalField(max_digits=14, decimal_places=2,
                                      null=True, blank=True)
    suppression_cost_rub = models.DecimalField(max_digits=14, decimal_places=2,
                                                 null=True, blank=True)


class ImportBatch(models.Model):
    file_name = models.CharField(max_length=255)
    category = models.CharField(max_length=20, choices=FireCategory.choices)
    strategy = models.CharField(max_length=20, choices=DuplicateStrategy.choices,
                                 default=DuplicateStrategy.REPORT)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                     on_delete=models.PROTECT)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    total_rows = models.PositiveIntegerField(default=0)
    created_count = models.PositiveIntegerField(default=0)
    updated_count = models.PositiveIntegerField(default=0)
    skipped_count = models.PositiveIntegerField(default=0)
    duplicates_count = models.PositiveIntegerField(default=0)
    error_count = models.PositiveIntegerField(default=0)
    errors_json = models.JSONField(default=list, blank=True)
    source_file = models.FileField(upload_to='imports/%Y/%m/',
                                    null=True, blank=True)
    is_reverted = models.BooleanField(default=False)
    reverted_at = models.DateTimeField(null=True, blank=True)
    reverted_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                     on_delete=models.SET_NULL,
                                     null=True, blank=True,
                                     related_name='reverted_batches')

    class Meta:
        ordering = ['-uploaded_at']


class PossibleDuplicate(models.Model):
    new_fire = models.ForeignKey(Fire, on_delete=models.CASCADE, related_name='+')
    existing_fire = models.ForeignKey(Fire, on_delete=models.CASCADE, related_name='+')
    batch = models.ForeignKey(ImportBatch, on_delete=models.CASCADE)
    resolved = models.BooleanField(default=False)
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                     on_delete=models.SET_NULL,
                                     null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class WeatherStation(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    location = models.PointField(srid=4326)
    district = models.ForeignKey(District, on_delete=models.SET_NULL,
                                  null=True, blank=True,
                                  related_name='weather_stations')
    is_active = models.BooleanField(default=True)


class DailyWeatherObservation(models.Model):
    station = models.ForeignKey(WeatherStation, on_delete=models.CASCADE,
                                 related_name='observations')
    date = models.DateField()
    temperature_14 = models.DecimalField(max_digits=5, decimal_places=2,
                                          null=True, blank=True)
    dew_point_14 = models.DecimalField(max_digits=5, decimal_places=2,
                                        null=True, blank=True)
    precipitation_mm = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    fetched_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('station', 'date')]
        indexes = [models.Index(fields=['station', '-date'])]


class FireDangerForecast(models.Model):
    district = models.ForeignKey(District, on_delete=models.CASCADE,
                                  related_name='danger_forecasts')
    date = models.DateField()
    danger_class = models.PositiveSmallIntegerField(choices=FireDangerClass.choices)
    source = models.CharField(max_length=20, choices=[
        ('manual', 'Ручной ввод'),
        ('nesterov', 'Расчёт по Нестерову'),
    ])
    nesterov_index = models.DecimalField(max_digits=9, decimal_places=1,
                                          null=True, blank=True)
    entered_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                    on_delete=models.SET_NULL,
                                    null=True, blank=True)
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('district', 'date')]
        indexes = [models.Index(fields=['date'])]

    @classmethod
    def set_manual(cls, district, date, danger_class, user, note=''):
        obj, _ = cls.objects.update_or_create(
            district=district, date=date,
            defaults={
                'danger_class': danger_class,
                'source': 'manual',
                'entered_by': user,
                'note': note,
                'nesterov_index': None,
            }
        )
        return obj

    @classmethod
    def set_from_nesterov(cls, district, date, index_value):
        existing = cls.objects.filter(district=district, date=date).first()
        if existing and existing.source == 'manual':
            return existing
        from .services.nesterov import classify_nesterov
        danger_class = classify_nesterov(index_value)
        obj, _ = cls.objects.update_or_create(
            district=district, date=date,
            defaults={
                'danger_class': danger_class,
                'source': 'nesterov',
                'nesterov_index': index_value,
                'entered_by': None,
            }
        )
        return obj
