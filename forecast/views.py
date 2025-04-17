from django.shortcuts import render
from django.http import JsonResponse
from .forms import BudgetQueryForm
from .api import fetch_budget_incomes_data
from .models import Budgets, IncomeHistory, Incomes
import pandas as pd
from datetime import datetime
import logging

# Налаштування логування
logger = logging.getLogger(__name__)

def budget_incomes_view(request):
    form = BudgetQueryForm(request.POST or None)
    results = None
    error = None
    available_data = None
    missing_years = None
    show_load_button = False
    last_year_month = None
    success_api = False
    success_db = False
    current_month = datetime.now().month

    # Визначаємо діапазон років (2018 – поточний рік)
    current_year = datetime.now().year
    years = list(range(2018, current_year + 1))

    if request.method == 'POST' and form.is_valid():
        try:
            budget_code = form.cleaned_data['budget'].code_budg
            period = form.cleaned_data['period']
            load_missing = request.POST.get('load_missing')

            # Перевіряємо базу даних
            all_data = []
            years_to_fetch = []
            available_data = {}
            for year in years:
                existing_data = IncomeHistory.objects.filter(
                    budget__code_budg=budget_code,
                    rep_period__regex=r'^\d{2}\.' + str(year) + '$'
                ).values('rep_period', 'fund_typ', 'cod_inco', 'zat_amt', 'fakt_amt')

                if existing_data.exists():
                    # Збираємо місяці для року
                    months = sorted(set(
                        int(row['rep_period'].split('.')[0])
                        for row in existing_data
                        if row['rep_period'] and '.' in row['rep_period']
                    ))
                    available_data[year] = months
                    all_data.extend(existing_data)
                    logger.debug(f"Знайдено дані за {year} для бюджету {budget_code}: {len(existing_data)} записів, місяці: {months}")
                    if year == current_year:
                        last_year_month = max(months) if months else None
                else:
                    years_to_fetch.append(year)
                    available_data[year] = []
                    logger.debug(f"Дані за {year} для бюджету {budget_code} відсутні")

            # Визначаємо, чи потрібно показувати кнопку завантаження
            if years_to_fetch or (last_year_month and last_year_month < datetime.now().month):
                missing_years = years_to_fetch
                show_load_button = True

            if load_missing and (years_to_fetch or (last_year_month and last_year_month < datetime.now().month)):
                # Якщо дані за поточний рік неповні, додаємо його до запиту
                if last_year_month and last_year_month < datetime.now().month and current_year not in years_to_fetch:
                    years_to_fetch.append(current_year)

                # Завантажуємо відсутні роки з API
                api_results = fetch_budget_incomes_data(
                    budget_code=budget_code,
                    years=years_to_fetch,
                    period=period
                )
                if api_results:
                    success_api = True
                    all_data.extend(api_results)

                    # Зберігаємо нові дані в базу
                    budget_obj = Budgets.objects.get(code_budg=budget_code)
                    for row in api_results:
                        rep_period = str(row['rep_period'])
                        if not rep_period or '.' not in rep_period:
                            continue
                        IncomeHistory.objects.update_or_create(
                            budget=budget_obj,
                            rep_period=rep_period,
                            fund_typ=row['fund_typ'],
                            cod_inco=row['cod_inco'],
                            defaults={
                                'zat_amt': row['zat_amt'],
                                'fakt_amt': row['fakt_amt']
                            }
                        )
                    success_db = True

                    # Оновлюємо available_data, missing_years і show_load_button
                    available_data = {}
                    years_to_fetch = []
                    for year in years:
                        existing_data = IncomeHistory.objects.filter(
                            budget__code_budg=budget_code,
                            rep_period__regex=r'^\d{2}\.' + str(year) + '$'
                        ).values('rep_period')
                        months = sorted(set(
                            int(row['rep_period'].split('.')[0])
                            for row in existing_data
                            if row['rep_period'] and '.' in row['rep_period']
                        ))
                        available_data[year] = months
                        if not months:
                            years_to_fetch.append(year)
                        if year == current_year:
                            last_year_month = max(months) if months else None

                    # Перевіряємо, чи потрібно показувати кнопку завантаження
                    show_load_button = bool(years_to_fetch or (last_year_month and last_year_month < datetime.now().month))
                    missing_years = years_to_fetch if years_to_fetch else None

            # Обробляємо дані
            if all_data:
                required_keys = {'rep_period', 'fund_typ', 'cod_inco', 'zat_amt', 'fakt_amt'}
                all_data = [row for row in all_data if all(key in row for key in required_keys)]

                if not all_data:
                    raise ValueError("Немає даних із усіма необхідними полями")

                df = pd.DataFrame(all_data)
                df['rep_period'] = df['rep_period'].astype(str)
                df = df[df['rep_period'].str.contains(r'^\d{2}\.\d{4}$', na=False)]

                if df.empty:
                    raise ValueError("Немає даних із коректним форматом rep_period (MM.YYYY)")

                # Витягуємо рік і місяць
                df['year'] = df['rep_period'].str.split('.').str[1]
                df['month'] = df['rep_period'].str.split('.').str[0].astype(int)

                # Сортуємо дані
                df = df.sort_values(by=['year', 'cod_inco', 'fund_typ', 'month'])

                # Обчислюємо різницю для fakt_amt
                df['fakt_amt_diff'] = df.groupby(['year', 'cod_inco', 'fund_typ'])['fakt_amt'].diff().fillna(df['fakt_amt'])
                df['fakt_amt'] = df['fakt_amt_diff']
                df = df.drop(columns=['fakt_amt_diff'])

                # Створюємо зведену таблицю
                pivot_df = df.pivot_table(
                    values='fakt_amt',
                    index=['cod_inco', 'fund_typ', 'year'],
                    columns='month',
                    aggfunc='first'
                ).reset_index()
                pivot_df.columns = ['cod_inco', 'fund_typ', 'year'] + [f"{month:02d}" for month in range(1, 13)]
                pivot_df = pivot_df.fillna('—')
                results = pivot_df.to_dict('records')

            if not results:
                error = "Дані за вибраний бюджет не знайдено."

        except Exception as e:
            logger.error(f"Помилка обробки: {str(e)}")
            error = str(e)

    return render(request, 'forecast/budget_incomes.html', {
        'form': form,
        'results': results,
        'error': error,
        'available_data': available_data,
        'missing_years': missing_years,
        'show_load_button': show_load_button,
        'last_year_month': last_year_month,
        'current_year': current_year,
        'current_month': current_month,
        'success_api': success_api,
        'success_db': success_db
    })

def forecast_view(request):
    budget_code = request.GET.get('budget_code')
    error = None
    budget = None
    available_data = None
    last_year_month = None
    incomes = None
    current_year = datetime.now().year
    current_month = datetime.now().month
    years = list(range(2018, current_year + 1))

    try:
        if not budget_code:
            raise ValueError("Код бюджету не вказано")

        # Отримуємо інформацію про бюджет
        budget = Budgets.objects.get(code_budg=budget_code)

        # Отримуємо період наявних даних
        available_data = {}
        for year in years:
            existing_data = IncomeHistory.objects.filter(
                budget__code_budg=budget_code,
                rep_period__regex=r'^\d{2}\.' + str(year) + '$'
            ).values('rep_period')
            months = sorted(set(
                int(row['rep_period'].split('.')[0])
                for row in existing_data
                if row['rep_period'] and '.' in row['rep_period']
            ))
            available_data[year] = months
            if year == current_year and months:
                last_year_month = max(months)

        # Отримуємо коди доходів із даними для цього бюджету
        income_codes = IncomeHistory.objects.filter(
            budget__code_budg=budget_code
        ).values('cod_inco').distinct()
        income_codes_list = [item['cod_inco'] for item in income_codes]

        # Отримуємо назви кодів доходів із довідника
        incomes = Incomes.objects.filter(kdb_code__in=income_codes_list).order_by('kdb_code')

        if not incomes.exists():
            error = "Немає кодів доходів із даними для цього бюджету."

    except Budgets.DoesNotExist:
        error = f"Бюджет із кодом {budget_code} не знайдено."
    except Exception as e:
        logger.error(f"Помилка обробки прогнозування: {str(e)}")
        error = str(e)

    return render(request, 'forecast/forecast.html', {
        'budget': budget,
        'available_data': available_data,
        'last_year_month': last_year_month,
        'current_year': current_year,
        'current_month': current_month,
        'incomes': incomes,
        'error': error
    })

def get_budgets_by_region(request):
    region_id = request.GET.get('region')
    budgets = Budgets.objects.filter(code_region=region_id).order_by(
        'name_budg') if region_id else Budgets.objects.all().order_by('name_budg')
    data = [
        {'code_budg': budget.code_budg, 'name_budg': budget.name_budg or "Без назви"}
        for budget in budgets
    ]
    return JsonResponse({'budgets': data})