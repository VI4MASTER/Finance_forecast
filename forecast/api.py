import aiohttp
import pandas
import io
import logging
from datetime import date
import requests
import asyncio


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = "https://api.openbudget.gov.ua/"

async def fetch_budget_dict_data():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{BASE_URL}items/BUDG",
                params={"dateFrom": date.today().strftime('%Y-%m-%d')},
                timeout=30
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Помилка при отриманні даних із {BASE_URL}items/BUDG: {response.status}")
                    raise Exception(f"Помилка при отриманні даних із {BASE_URL}items/BUDG: {response.status}")
    except Exception as e:
        logger.error(f"Загальна помилка при отриманні даних бюджетів: {e}")
        raise

async def fetch_region_dict_data():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{BASE_URL}items/CODEREGION",
                params={"dateFrom": date.today().strftime('%Y-%m-%d')},
                timeout=30
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Помилка при отриманні даних із {BASE_URL}items/CODEREGION: {response.status}")
                    raise Exception(f"Помилка при отриманні даних із {BASE_URL}items/CODEREGION: {response.status}")
    except Exception as e:
        logger.error(f"Загальна помилка при отриманні даних регіонів: {e}")
        raise

async def fetch_incomes_dict_data():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{BASE_URL}items/KDB",
                params={"dateFrom": date.today().strftime('%Y-%m-%d')},
                timeout=30
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Помилка при отриманні даних із {BASE_URL}items/KDB: {response.status}")
                    raise Exception(f"Помилка при отриманні даних із {BASE_URL}items/KDB: {response.status}")
    except Exception as e:
        logger.error(f"Загальна помилка при отриманні даних доходів: {e}")
        raise

async def fetch_budget_incomes_data(budget_code, years, period="MONTH", budget_item="INCOMES"):
    all_results = []
    for year in years:
        if int(year) < 2023:
            adjusted_code = str(budget_code) + "0"
        else:
            adjusted_code = str(budget_code)

        try:
            # Change to async pattern to match other functions
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{BASE_URL}api/public/localBudgetData",
                    params={
                        "budgetCode": adjusted_code,
                        "budgetItem": budget_item,
                        "period": period,
                        "year": year
                    },
                    timeout=30
                ) as response:
                    if response.status == 200:
                        text = await response.text()
                        try:
                            df = pandas.read_csv(
                                io.StringIO(text),
                                sep=';',
                                encoding='utf-8',
                                dtype_backend="numpy_nullable",
                                on_bad_lines='skip'
                            )
                        except Exception:
                            try:
                                df = pandas.read_csv(
                                    io.StringIO(text),
                                    sep=';',
                                    encoding='cp1251',
                                    dtype_backend="numpy_nullable",
                                    on_bad_lines='skip'
                                )
                            except Exception as e:
                                logger.error(f"Помилка парсингу CSV для року {year}: {e}")
                                continue

                        # Rename columns to lowercase
                        df = df.rename(columns={
                            'REP_PERIOD': 'rep_period',
                            'FUND_TYP': 'fund_typ',
                            'COD_INCO': 'cod_inco',
                            'FAKT_AMT': 'fakt_amt'
                        })

                        # Process rep_period to MM.YYYY format
                        if 'rep_period' in df.columns:
                            df['rep_period'] = df['rep_period'].apply(
                                lambda x: f"{int(x.split('.')[0]):02d}.{int(x.split('.')[1])}" if isinstance(x, str) and '.' in x else f"{int(x):02d}.{int(year)}"
                            )

                        # Filter records, excluding income codes starting with '4' or '5'
                        if 'cod_inco' in df.columns:
                            df = df[~df['cod_inco'].astype(str).str.startswith(('4', '5'))]

                        # Filter records, keeping only fund_typ in ['C', 'S']
                        if 'fund_typ' in df.columns:
                            df = df[df['fund_typ'].isin(['C', 'S'])]

                        # Select needed columns
                        columns = ['rep_period', 'fund_typ', 'cod_inco', 'fakt_amt']
                        df = df[[col for col in columns if col in df.columns]]

                        # Convert numeric columns
                        if 'fakt_amt' in df.columns:
                            df['fakt_amt'] = pandas.to_numeric(df['fakt_amt'], errors='coerce')

                        # Calculate monthly differences for fakt_amt
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
                        logger.error(f"Помилка API для року {year}: {response.status}")
        except Exception as e:
            logger.error(f"Загальна помилка для року {year}: {e}")

    logger.info(f"Отримано {len(all_results)} записів для бюджету {budget_code}")
    return all_results


def sync_fetch_budget_incomes_data(budget_code, years, period="MONTH", budget_item="INCOMES"):
    """Синхронна обгортка для fetch_budget_incomes_data"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(
            fetch_budget_incomes_data(budget_code, years, period, budget_item)
        )
        return result
    finally:
        loop.close()