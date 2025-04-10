from django.conf import settings
from forecast.models import Budget


def load_data(data):
    # Перевіряємо, чи data — словник із ключем 'budgets'
    budgets = data.get('budgets', data)  # Якщо немає 'budgets', беремо весь data
    if isinstance(budgets, str):  # Якщо budgets — рядок, парсимо його як JSON
        import json
        budgets = json.loads(budgets)

    # Перевіряємо, чи budgets — список
    if not isinstance(budgets, list):
        raise ValueError("Очікувався список бюджетів, отримано: " + str(type(budgets)))

    for budget_data in budgets:
        Budget.objects.update_or_create(
            code=budget_data['codebudg'],
            defaults={'name': budget_data['namebudg']}
        )
    print(f"Завантажено {len(budgets)} бюджетів")