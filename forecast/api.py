import requests
import pandas
import io
import logging
from datetime import date

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = "https://api.openbudget.gov.ua/"

def fetch_budget_dict_data():
    try:
        budgets_response = requests.get(
            f"{BASE_URL}items/BUDG",
            params={"dateFrom": date.today().strftime('%Y-%m-%d')},
            timeout=30
        )
        if budgets_response.status_code == 200:
            return budgets_response.json()
        else:
            logger.error(f"Помилка при отриманні даних із {BASE_URL}items/BUDG: {budgets_response.status_code}")
            raise Exception(f"Помилка при отриманні даних із {BASE_URL}items/BUDG: {budgets_response.status_code}")
    except Exception as e:
        logger.error(f"Загальна помилка при отриманні даних бюджетів: {e}")
        raise

def fetch_region_dict_data():
    try:
        regions_response = requests.get(
            f"{BASE_URL}items/CODEREGION",
            params={"dateFrom": date.today().strftime('%Y-%m-%d')},
            timeout=30
        )
        if regions_response.status_code == 200:
            return regions_response.json()
        else:
            logger.error(f"Помилка при отриманні даних із {BASE_URL}items/CODEREGION: {regions_response.status_code}")
            raise Exception(f"Помилка при отриманні даних із {BASE_URL}items/CODEREGION: {regions_response.status_code}")
    except Exception as e:
        logger.error(f"Загальна помилка при отриманні даних регіонів: {e}")
        raise

def fetch_incomes_dict_data():
    try:
        incomes_response = requests.get(
            f"{BASE_URL}items/KDB",
            params={"dateFrom": date.today().strftime('%Y-%m-%d')},
            timeout=30
        )
        if incomes_response.status_code == 200:
            return incomes_response.json()
        else:
            logger.error(f"Помилка при отриманні даних із {BASE_URL}items/KDB: {incomes_response.status_code}")
            raise Exception(f"Помилка при отриманні даних із {BASE_URL}items/KDB: {incomes_response.status_code}")
    except Exception as e:
        logger.error(f"Загальна помилка при отриманні даних доходів: {e}")
        raise

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
                try:
                    df = pandas.read_csv(
                        io.StringIO(response.text),
                        sep=';',
                        encoding='utf-8',
                        dtype_backend="numpy_nullable",
                        on_bad_lines='skip'
                    )
                except Exception:
                    try:
                        df = pandas.read_csv(
                            io.StringIO(response.text),
                            sep=';',
                            encoding='cp1251',
                            dtype_backend="numpy_nullable",
                            on_bad_lines='skip'
                        )
                    except Exception as e:
                        logger.error(f"Помилка парсингу CSV для року {year}: {e}")
                        continue

                # Перейменовуємо стовпці в нижній регістр
                df = df.rename(columns={
                    'REP_PERIOD': 'rep_period',
                    'FUND_TYP': 'fund_typ',
                    'COD_INCO': 'cod_inco',
                    'FAKT_AMT': 'fakt_amt'
                })

                # Нормалізуємо rep_period до формату MM.YYYY
                if 'rep_period' in df.columns:
                    df['rep_period'] = df['rep_period'].apply(
                        lambda x: f"{int(x.split('.')[0]):02d}.{int(x.split('.')[1])}" if isinstance(x, str) and '.' in x else f"{int(x):02d}.{int(year)}"
                    )

                # Фільтруємо записи, виключаючи коди доходів, що починаються з '4' або '5'
                if 'cod_inco' in df.columns:
                    df = df[~df['cod_inco'].astype(str).str.startswith(('4', '5'))]

                # Фільтруємо записи, залишаючи лише fund_typ у ['C', 'S']
                if 'fund_typ' in df.columns:
                    df = df[df['fund_typ'].isin(['C', 'S'])]

                # Вибираємо потрібні стовпці
                columns = ['rep_period', 'fund_typ', 'cod_inco', 'fakt_amt']
                df = df[[col for col in columns if col in df.columns]]

                # Перетворюємо числові стовпці
                if 'fakt_amt' in df.columns:
                    df['fakt_amt'] = pandas.to_numeric(df['fakt_amt'], errors='coerce')

                # Обчислюємо помісячні різниці для fakt_amt
                if 'fakt_amt' in df.columns and not df.empty:
                    df['year'] = df['rep_period'].str.split('.').str[1]
                    df['month'] = df['rep_period'].str.split('.').str[0].astype(int)
                    df = df.sort_values(by=['year', 'cod_inco', 'fund_typ', 'month'])
                    df['fakt_amt_diff'] = df.groupby(['year', 'cod_inco', 'fund_typ'])['fakt_amt'].diff().fillna(df['fakt_amt'])
                    df['fakt_amt'] = df['fakt_amt_diff']
                    df = df.drop(columns=['fakt_amt_diff', 'year', 'month'])

                if not df.empty:
                    all_results.extend(df.to_dict('records'))
            else:
                logger.error(f"Помилка API для року {year}: {response.status_code}")
        except Exception as e:
            logger.error(f"Загальна помилка для року {year}: {e}")

    logger.info(f"Отримано {len(all_results)} записів для бюджету {budget_code}")
    return all_results