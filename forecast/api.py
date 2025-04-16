import requests
import pandas
import io
import logging
from datetime import date

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = "https://api.openbudget.gov.ua/"


def fetch_budget_dict_data():
    budgets_response = requests.get(
        f"{BASE_URL}items/BUDG",
        params={"dateFrom": date.today().strftime('%Y-%m-%d')},
        timeout=30
    )
    if budgets_response.status_code == 200:
        return budgets_response.json()
    else:
        raise Exception(f"Помилка при отриманні даних із {BASE_URL}items/BUDG: {budgets_response.status_code}")


def fetch_region_dict_data():
    regions_response = requests.get(
        f"{BASE_URL}items/CODEREGION",
        params={"dateFrom": date.today().strftime('%Y-%m-%d')},
        timeout=30
    )
    if regions_response.status_code == 200:
        return regions_response.json()
    else:
        raise Exception(f"Помилка при отриманні даних із {BASE_URL}items/REGIONS: {regions_response.status_code}")


def fetch_incomes_dict_data():
    incomes_response = requests.get(
        f"{BASE_URL}items/KDB",
        params={"dateFrom": date.today().strftime('%Y-%m-%d')},
        timeout=30
    )
    if incomes_response.status_code == 200:
        return incomes_response.json()
    else:
        raise Exception(f"Помилка при отриманні даних із {BASE_URL}items/BUDG: {incomes_response.status_code}")


def fetch_budget_incomes_data(budget_code, years, period="MONTH", budget_item="INCOMES"):
    all_results = []
    for year in years:
        if int(year) < 2023:
            adjusted_code = str(budget_code) + "0"
        else:
            adjusted_code = str(budget_code)

        try:
            response = requests.get(
                f"{BASE_URL}api/public/localBudgetData",
                params={
                    "budgetCode": adjusted_code,
                    "budgetItem": budget_item,
                    "period": period,
                    "year": year
                },
                timeout=30
            )
            if response.status_code == 200:
                logger.debug(f"Сира відповідь API для року {year}:\n{response.text[:1000]}...")

                try:
                    df = pandas.read_csv(
                        io.StringIO(response.text),
                        sep=';',
                        encoding='utf-8',
                        dtype_backend="numpy_nullable",
                        on_bad_lines='skip'
                    )
                    logger.debug(f"Успішно використано utf-8 із sep=';' для року {year}")
                except Exception as parse_error:
                    logger.error(f"Помилка utf-8 із sep=';' для року {year}: {parse_error}")
                    try:
                        df = pandas.read_csv(
                            io.StringIO(response.text),
                            sep=';',
                            encoding='cp1251',
                            dtype_backend="numpy_nullable",
                            on_bad_lines='skip'
                        )
                        logger.debug(f"Успішно використано cp1251 із sep=';' для року {year}")
                    except Exception as parse_error2:
                        logger.error(f"Помилка cp1251 із sep=';' для року {year}: {parse_error2}")
                        continue

                # Перейменовуємо стовпці в нижній регістр
                df = df.rename(columns={
                    'REP_PERIOD': 'rep_period',
                    'FUND_TYP': 'fund_typ',
                    'COD_BUDGET': 'cod_budget',
                    'COD_INCO': 'cod_inco',
                    'ZAT_AMT': 'zat_amt',
                    'FAKT_AMT': 'fakt_amt'
                })

                # Нормалізуємо rep_period до формату MM.YYYY
                if 'rep_period' in df.columns:
                    df['rep_period'] = df['rep_period'].apply(
                        lambda x: f"{int(x.split('.')[0]):02d}.{int(x.split('.')[1])}" if isinstance(x,
                                                                                                     str) and '.' in x else f"{int(x):02d}.{int(year)}"
                    )

                # Вибираємо потрібні стовпці
                columns = ['rep_period', 'fund_typ', 'cod_budget', 'cod_inco', 'zat_amt', 'fakt_amt']
                df = df[[col for col in columns if col in df.columns]]

                # Перетворюємо числові стовпці
                numeric_columns = ['zat_amt', 'fakt_amt']
                for col in numeric_columns:
                    if col in df.columns:
                        df[col] = pandas.to_numeric(df[col], errors='coerce')

                if not df.empty:
                    logger.debug(f"Перший рядок після парсингу для року {year}:\n{df.iloc[0].to_dict()}")
                all_results.extend(df.to_dict('records'))
            else:
                logger.error(f"Помилка API для року {year}: {response.status_code}")
        except Exception as e:
            logger.error(f"Загальна помилка для року {year}: {e}")

    return all_results