import requests, json, pandas, openpyxl
from datetime import date

BASE_URL = "https://api.openbudget.gov.ua/"


def fetch_dict_data():
    #Отримуємо із публічного АПІ json із довідником бюджетів України станом на сьогодні
    budgets_response = requests.get(f"{BASE_URL}items/BUDG",
                                    params={"dateFrom": date.today().strftime('%Y-%m-%d')})

    if budgets_response.status_code == 200:
        return budgets_response.json()
    else:
        raise Exception(f"Помилка при отриманні даних із {BASE_URL}items/BUDG станом на "
                        f"{date.today().strftime('%Y-%m-%d')}: {budgets_response.status_code}")





# a = fetch_data()
# with open('budgets.json', 'w', encoding='utf-8') as f:
#     json.dump(a, f, ensure_ascii=False, indent=4)
# print("Дані збережено у budgets.json")
# for i in a:
#     for key, value in i.items():
#         print(f"Ключ: {key}, Значення: {value}")
# with open('budgets.json', 'r', encoding='utf-8') as f:
#     data = json.load(f)
# df = pandas.DataFrame(data)
#
# df.to_excel('forecast.xlsx', index=False, engine='openpyxl')
# print(f"Дані збережено")