# import json
# from django.conf import settings
#
# def fetch_data():
#     with open(settings.BASE_DIR / 'forecast' / 'test_data.json', 'r', encoding='utf-8') as f:
#         return json.load(f)

import requests

BASE_URL = "https://api.openbudget.gov.ua/"


def fetch_data():
    # Відправляємо запити без автентифікації
    budgets_response = requests.get(f"{BASE_URL}items", params={"dateFrom": "2025-01-01"})
    # transactions_response = requests.get(
    #     f"{BASE_URL}transactions",
    #     params={"start_date": "2020-01-01", "end_date": "2025-04-01"}
    # )

    # Перевіряємо статус відповідей
    if budgets_response.status_code == 200: #and transactions_response.status_code == 200:
        return {
            "budgets": budgets_response.json(),
            # "transactions": transactions_response.json()
        }
    else:
        # Виводимо деталі помилки
        raise Exception(
            f"Помилка при отриманні даних: {budgets_response.status_code} для budgets, "
            f"{transactions_response.status_code} для transactions"
        )