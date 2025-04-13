import requests
from datetime import date

BASE_URL = "https://api.openbudget.gov.ua/"


def fetch_budget_dict_data():
    #Отримуємо із публічного АПІ json із довідником бюджетів України станом на сьогодні
    response = requests.get(f"{BASE_URL}items/BUDG",
                                    params={"dateFrom": date.today().strftime('%Y-%m-%d')})

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Помилка при отриманні даних із {BASE_URL}items/BUDG станом на "
                        f"{date.today().strftime('%Y-%m-%d')}: {response.status_code}")


def fetch_region_dict_data():
    #Отримуємо із публічного АПІ json із довідником областей України станом на сьогодні
    response = requests.get(f"{BASE_URL}items/CODEREGION",
                                    params={"dateFrom": date.today().strftime('%Y-%m-%d')})

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Помилка при отриманні даних із {BASE_URL}items/CODEREGION станом на "
                        f"{date.today().strftime('%Y-%m-%d')}: {response.status_code}")


def fetch_budget_incomes_data(budget_code, year, period="MONTH", budget_item="INCOMES"):
    response = requests.get(
        f"{BASE_URL}api/public/localBudgetData",
        params={
            "budgetCode": budget_code,
            "budgetItem": budget_item,
            "period": period,
            "year": year
        },
        timeout=30
    )
    if response.status_code == 200:
        # Парсимо CSV у список словників
        df = pandas.read_csv(pandas.io.common.StringIO(response.text), sep=',')
        return df.to_dict('records')
    else:
        raise Exception(f"Помилка при отриманні даних із {BASE_URL}api/public/localBudgetData: "
                        f"{response.status_code}")