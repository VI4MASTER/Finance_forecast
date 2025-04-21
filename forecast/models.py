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

class Incomes(models.Model):
    kdb_code = models.CharField(
        max_length=8,
        primary_key=True,
        verbose_name="Код класифікації доходів бюджету"
    )
    kdb_name = models.CharField(
        max_length=2000,
        verbose_name="Найменування доходів бюджету"
    )


class IncomeHistory(models.Model):
    budget = models.ForeignKey(Budgets, on_delete=models.CASCADE, to_field='code_budg')
    rep_period = models.CharField(max_length=7)  # Формат: MM.YYYY
    fund_typ = models.CharField(max_length=1)  # C, S, T
    cod_inco = models.CharField(max_length=20)
    fakt_amt = models.FloatField(null=True)

    class Meta:
        db_table = 'income_history'
        unique_together = ('budget', 'rep_period', 'fund_typ', 'cod_inco')  # Унікальність запису

    def __str__(self):
        return f"{self.budget.code_budg} - {self.rep_period} - {self.cod_inco}"