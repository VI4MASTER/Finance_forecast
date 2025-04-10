from django.db import models

class Budget(models.Model):
    name = models.CharField(max_length=255)  # Назва бюджету
    code = models.CharField(max_length=50, unique=True)  # Унікальний код бюджетуpython manage.py

    def __str__(self):
        return self.name

class Transaction(models.Model):
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE)  # Зв’язок із бюджетом
    date = models.DateField()  # Дата транзакції
    amount = models.DecimalField(max_digits=15, decimal_places=2)  # Сума
    transaction_type = models.CharField(
        max_length=10,
        choices=[('income', 'Дохід'), ('expense', 'Видаток')]  # Тип: дохід чи видаток
    )

    def __str__(self):
        return f"{self.transaction_type} {self.amount} для {self.budget} від {self.date}"