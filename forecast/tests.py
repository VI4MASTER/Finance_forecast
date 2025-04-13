# # from django.test import TestCase
#
# import requests
#
# BASE_URL = "https://api.openbudget.gov.ua/"
#
#
# def data():
#     #Отримуємо із публічного АПІ json із довідником бюджетів України станом на сьогодні
#     response = requests.get(f"{BASE_URL}api/public/localBudgetData",
#                                     params={"budgetCode": "1654000000",
#                                             "budgetItem": "INCOMES",
#                                             "classificationType": None,
#                                             "period": "MONTH",
#                                             "year": 2023})
#
#     if response.status_code == 200:
#         return response.json()
#     else:
#         raise Exception(f"Помилка при отриманні даних із {BASE_URL}items/BUDG станом на "
#                         f"{date.today().strftime('%Y-%m-%d')}: {response.status_code}")
#
