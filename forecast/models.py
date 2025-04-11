from django.db import models

class Budgets(models.Model):
    name_local_gov = models.CharField(
        max_length=2000,
        primary_key=True,
        verbose_name="Найменування органу місцевого самоврядування"
    )
    code_region = models.CharField(
        max_length=2,
        verbose_name="Код території"
    )
    name_budg = models.CharField(
        max_length=2000,
        verbose_name="Найменування бюджету"
    )
    koatuu = models.CharField(
        max_length=10,
        verbose_name="КОАТУУ"
    )
    code_budg = models.CharField(
        max_length=11,
        unique=True,
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