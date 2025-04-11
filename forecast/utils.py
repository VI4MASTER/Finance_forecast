# import json
# from forecast.models import Budgets
#
# def load_data(data):
#     if isinstance(data, str):
#         with open(data, 'r', encoding='utf-8') as f:
#             budgets = json.load(f)
#     else:
#         budgets = data
#
#     for budget_data in budgets:
#         Budgets.objects.get_or_create(
#             code_budg=budget_data['codebudg'],
#             defaults={
#                 'name_local_gov': budget_data['nameLocalGov'],
#                 'code_region': budget_data['codeRegion'],
#                 'name_budg': budget_data['namebudg'],
#                 'koatuu': budget_data['katottg'],
#                 'sign_budg': budget_data['signBudg']
#             }
#         )
#     print(f"Завантажено {len(budgets)} бюджетів")
import json
import time
from forecast.models import Budgets
from django.db import transaction

def load_data(data):
    start_time = time.time()
    print("Початок обробки...")

    if isinstance(data, str):
        with open(data, 'r', encoding='utf-8') as f:
            budgets = json.load(f)
    else:
        budgets = data

    # Визначаємо допустимі значення для signBudg
    valid_sign_budg = {'gm', 'gs', 'gss', 'v'}

    # Фільтруємо записи
    filtered_budgets = [
        budget_data for budget_data in budgets
        if budget_data.get('signBudg') in valid_sign_budg  # Фільтр по signBudg
        and budget_data.get('cntBudg') == 1  # Фільтр по cntBudg
    ]

    total = len(filtered_budgets)
    print(f"Знайдено {len(budgets)} записів, відфільтровано до {total}")

    # Створюємо об'єкти для bulk_create
    objects = [
        Budgets(
            code_budg=budget_data['codebudg'],
            name_local_gov=budget_data['nameLocalGov'],
            code_region=budget_data['codeRegion'],
            name_budg=budget_data['namebudg'],
            koatuu=budget_data['katottg'],
            sign_budg=budget_data['signBudg']
        )
        for budget_data in filtered_budgets
    ]

    # Зберігаємо у базу одним запитом
    with transaction.atomic():
        Budgets.objects.bulk_create(objects, ignore_conflicts=True)

    elapsed = time.time() - start_time
    print(f"Завантажено {total} бюджетів за {elapsed:.2f} секунд")