from django.db import models

class Budgets(models.Model):
    name_local_gov = models.CharField(
        max_length=2000,
        verbose_name="Найменування органу місцевого самоврядування"
    )
    code_region = models.CharField(
        max_length=2,
        verbose_name="Код області"
    )
    name_budg = models.CharField(
        max_length=2000,
        verbose_name="Найменування бюджету"
    )
    katottg = models.CharField(
        max_length=20,
        blank=True,  # Дозволяємо порожні значення
        null=True,  # Дозволяємо NULL у базі
        verbose_name="КАТОТТГ"
    )
    code_budg = models.CharField(
        max_length=11,
        primary_key=True,
        verbose_name="Код бюджету"
    )
    sign_budg = models.CharField(
        max_length=16,
        verbose_name="Ознака бюджету"
    )

    def __str__(self):
        return self.name_budg

    class Meta:
        verbose_name = "Бюджет"
        verbose_name_plural = "Бюджети"


class Regions(models.Model):
    code_region = models.CharField(
        max_length=2,
        primary_key=True,
        verbose_name="Код області"
    )
    name = models.CharField(
        max_length=100,
        verbose_name="Назва області"
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Області"
        verbose_name_plural = "Області"