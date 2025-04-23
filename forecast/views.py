from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from .forms import BudgetQueryForm
from .api import fetch_budget_incomes_data, sync_fetch_budget_incomes_data
from .models import Budgets, IncomeHistory, Incomes
from .forecasting import prophet_forecast, sarima_forecast, gradient_boosting_forecast, prepare_data
import pandas as pd
from datetime import datetime
import logging
from io import BytesIO

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

    current_year = datetime.now().year
    years = list(range(2018, current_year + 1))

    if request.method == 'POST' and form.is_valid():
        try:
            budget_code = form.cleaned_data['budget'].code_budg
            period = form.cleaned_data['period']
            load_missing = request.POST.get('load_missing')

            all_data = []
            years_to_fetch = []
            available_data = {}
            for year in years:
                existing_data = IncomeHistory.objects.filter(
                    budget__code_budg=budget_code,
                    rep_period__regex=r'^\d{2}\.' + str(year) + '$'
                ).values('rep_period', 'fund_typ', 'cod_inco', 'fakt_amt')

                if existing_data.exists():
                    months = sorted(set(
                        int(row['rep_period'].split('.')[0])
                        for row in existing_data
                        if row['rep_period'] and '.' in row['rep_period']
                    ))
                    available_data[year] = months
                    all_data.extend(existing_data)
                    logger.debug(
                        f"Знайдено дані за {year} для бюджету {budget_code}: {len(existing_data)} записів, місяці: {months}")
                    if year == current_year:
                        last_year_month = max(months) if months else None
                else:
                    years_to_fetch.append(year)
                    available_data[year] = []
                    logger.debug(f"Дані за {year} для бюджету {budget_code} відсутні")

            if years_to_fetch or (last_year_month and last_year_month < datetime.now().month):
                missing_years = years_to_fetch
                show_load_button = True

            if load_missing and (years_to_fetch or (last_year_month and last_year_month < datetime.now().month)):
                if last_year_month and last_year_month < datetime.now().month and current_year not in years_to_fetch:
                    years_to_fetch.append(current_year)

                api_results = sync_fetch_budget_incomes_data(
                    budget_code=budget_code,
                    years=years_to_fetch,
                    period=period
                )
                if api_results:
                    success_api = True
                    all_data.extend(api_results)

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
                            defaults={'fakt_amt': row['fakt_amt']}
                        )
                    success_db = True

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

                    show_load_button = bool(
                        years_to_fetch or (last_year_month and last_year_month < datetime.now().month))
                    missing_years = years_to_fetch if years_to_fetch else None

            if all_data:
                required_keys = {'rep_period', 'fund_typ', 'cod_inco', 'fakt_amt'}
                all_data = [row for row in all_data if all(key in row for key in required_keys)]

                if not all_data:
                    raise ValueError("Немає даних із усіма необхідними полями")

                df = pd.DataFrame(all_data)
                df['rep_period'] = df['rep_period'].astype(str)
                df = df[df['rep_period'].str.contains(r'^\d{2}\.\d{4}$', na=False)]

                if df.empty:
                    raise ValueError("Немає даних із коректним форматом rep_period (MM.YYYY)")

                df['year'] = df['rep_period'].str.split('.').str[1]
                df['month'] = df['rep_period'].str.split('.').str[0].astype(int)
                df = df.sort_values(by=['year', 'cod_inco', 'fund_typ', 'month'])

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

        budget = Budgets.objects.get(code_budg=budget_code)

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

        income_codes = IncomeHistory.objects.filter(
            budget__code_budg=budget_code
        ).values('cod_inco').distinct()
        income_codes_list = [item['cod_inco'] for item in income_codes]

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
        'error': error,
        'years': years
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

def get_income_data(request):
    budget_code = request.GET.get('budget_code')
    income_code = request.GET.get('income_code')
    try:
        if not budget_code or not income_code:
            return JsonResponse({'error': 'Не вказано код бюджету або код доходу'}, status=400)

        data = IncomeHistory.objects.filter(
            budget__code_budg=budget_code,
            cod_inco=income_code
        ).values('rep_period', 'fund_typ', 'fakt_amt')

        if not data.exists():
            return JsonResponse({'error': 'Дані для цього коду доходу відсутні'}, status=404)

        df = pd.DataFrame(data)
        df['rep_period'] = df['rep_period'].astype(str)
        df = df[df['rep_period'].str.contains(r'^\d{2}\.\d{4}$', na=False)]

        if df.empty:
            return JsonResponse({'error': 'Немає даних із коректним форматом rep_period'}, status=404)

        df['year'] = df['rep_period'].str.split('.').str[1]
        df['month'] = df['rep_period'].str.split('.').str[0].astype(int)
        df = df.sort_values(by=['year', 'fund_typ', 'month'])

        pivot_df = df.pivot_table(
            values='fakt_amt',
            index=['year', 'fund_typ'],
            columns='month',
            aggfunc='first'
        ).reset_index()
        pivot_df.columns = ['year', 'fund_typ'] + [f"{month:02d}" for month in range(1, 13)]
        pivot_df = pivot_df.fillna('—')

        results = pivot_df.to_dict('records')
        return JsonResponse({'data': results})

    except Exception as e:
        logger.error(f"Помилка отримання даних доходу: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

def get_forecast_data(request):
    budget_code = request.GET.get('budget_code')
    income_code = request.GET.get('income_code')
    years = request.GET.getlist('years', [])
    forecast_periods = int(request.GET.get('forecast_periods', 12))
    test_mode = request.GET.get('test_mode', 'false').lower() == 'true'

    try:
        if not budget_code or not income_code or not years:
            return JsonResponse({'error': 'Не вказано код бюджету, код доходу або роки'}, status=400)

        # Обробка параметра years
        if len(years) == 1 and ',' in years[0]:
            years = years[0].split(',')
        selected_years = [int(y.strip()) for y in years if y.strip().isdigit()]

        if not selected_years:
            return JsonResponse({'error': 'Невалідні роки'}, status=400)

        logger.debug(
            f"Запит для budget_code={budget_code}, income_code={income_code}, years={selected_years}, test_mode={test_mode}")

        data = IncomeHistory.objects.filter(
            budget__code_budg=budget_code,
            cod_inco=income_code
        ).values('rep_period', 'fakt_amt', 'fund_typ')

        if not data.exists():
            logger.error(f"Дані відсутні для budget_code={budget_code}, income_code={income_code}")
            return JsonResponse({'error': 'Дані для цього коду доходу відсутні'}, status=404)

        df = pd.DataFrame(data)
        logger.debug(f"Отримано {len(df)} записів із IncomeHistory")

        df['rep_period'] = df['rep_period'].astype(str)
        df = df[df['rep_period'].str.contains(r'^\d{2}\.\d{4}$', na=False)]

        if df.empty:
            logger.error(
                f"Немає даних із коректним форматом rep_period для budget_code={budget_code}, income_code={income_code}")
            return JsonResponse({'error': 'Немає даних із коректним форматом rep_period'}, status=404)

        # Прогноз для кожного fund_typ окремо
        results = {}
        fund_types = df['fund_typ'].unique()
        logger.debug(f"Знайдено fund_typ: {fund_types}")

        for fund_typ in fund_types:
            fund_df = df[df['fund_typ'] == fund_typ]
            logger.debug(f"Обробка fund_typ={fund_typ}, записів: {len(fund_df)}")

            train_df, test_df = prepare_data(fund_df, selected_years, test_mode, fund_typ)

            if train_df.empty:
                logger.warning(f"Порожній train_df для fund_typ={fund_typ}")
                continue

            fund_results = {}
            for method in ['prophet', 'sarima', 'gradient_boosting']:
                logger.debug(f"Виконання {method} для fund_typ={fund_typ}")
                if method == 'prophet':
                    forecast, metrics = prophet_forecast(train_df, test_df, forecast_periods)
                elif method == 'sarima':
                    forecast, metrics = sarima_forecast(train_df, test_df, forecast_periods)
                else:
                    forecast, metrics = gradient_boosting_forecast(train_df, test_df, forecast_periods)

                if forecast is not None:
                    forecast['date'] = forecast['date'].dt.strftime('%m.%Y')
                    fund_results[method] = {
                        'forecast': forecast.to_dict('records'),
                        'metrics': metrics
                    }
                else:
                    logger.warning(f"Прогноз {method} не виконано для fund_typ={fund_typ}")

            if fund_results:
                results[fund_typ] = fund_results

        if not results:
            logger.error("Жоден прогноз не виконано")
            return JsonResponse({'error': 'Не вдалося виконати жоден прогноз через брак даних'}, status=404)

        return JsonResponse({'results': results})

    except Exception as e:
        logger.error(f"Помилка прогнозування: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

def download_excel(request):
    try:
        # Отримуємо параметри з запиту
        budget_code = request.GET.get('budget_code')
        income_code = request.GET.get('income_code')
        years = request.GET.getlist('years', [])
        forecast_periods = int(request.GET.get('forecast_periods', 12))
        test_mode = request.GET.get('test_mode', 'false').lower() == 'true'

        if not budget_code or not income_code or not years:
            return JsonResponse({'error': 'Не вказано код бюджету, код доходу або роки'}, status=400)

        # Обробка параметра years
        if len(years) == 1 and ',' in years[0]:
            years = years[0].split(',')
        selected_years = [int(y.strip()) for y in years if y.strip().isdigit()]

        if not selected_years:
            return JsonResponse({'error': 'Невалідні роки'}, status=400)

        # Отримуємо історичні дані
        data = IncomeHistory.objects.filter(
            budget__code_budg=budget_code,
            cod_inco=income_code
        ).values('rep_period', 'fakt_amt', 'fund_typ')

        if not data.exists():
            return JsonResponse({'error': 'Дані для цього коду доходу відсутні'}, status=404)

        df = pd.DataFrame(data)
        df['rep_period'] = df['rep_period'].astype(str)
        df = df[df['rep_period'].str.contains(r'^\d{2}\.\d{4}$', na=False)]

        if df.empty:
            return JsonResponse({'error': 'Немає даних із коректним форматом rep_period'}, status=404)

        # Створюємо Excel-файл у пам'яті
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # 1. Лист із історичними даними
            df['year'] = df['rep_period'].str.split('.').str[1]
            df['month'] = df['rep_period'].str.split('.').str[0].astype(int)
            pivot_df = df.pivot_table(
                values='fakt_amt',
                index=['year', 'fund_typ'],
                columns='month',
                aggfunc='first'
            ).reset_index()
            pivot_df.columns = ['Рік', 'Тип фонду'] + [f"Місяць {month:02d}" for month in range(1, 13)]
            pivot_df.to_excel(writer, sheet_name='Historical_Data', index=False)

            # 2. Лист із прогнозами
            fund_types = df['fund_typ'].unique()
            for fund_typ in fund_types:
                fund_df = df[df['fund_typ'] == fund_typ]
                train_df, test_df = prepare_data(fund_df, selected_years, test_mode, fund_typ)

                if train_df.empty:
                    continue

                # Виконуємо прогнози для кожного методу
                for method in ['prophet', 'sarima', 'gradient_boosting']:
                    if method == 'prophet':
                        forecast, _ = prophet_forecast(train_df, test_df, forecast_periods)
                    elif method == 'sarima':
                        forecast, _ = sarima_forecast(train_df, test_df, forecast_periods)
                    else:
                        forecast, _ = gradient_boosting_forecast(train_df, test_df, forecast_periods)

                    if forecast is not None:
                        forecast['date'] = forecast['date'].dt.strftime('%m.%Y')
                        forecast_df = forecast[['date', 'forecast']].copy()
                        forecast_df.columns = ['Дата', f'Прогноз ({method})']
                        forecast_df['Тип фонду'] = fund_typ
                        sheet_name = f'Forecast_{fund_typ}_{method}'
                        forecast_df.to_excel(writer, sheet_name=sheet_name, index=False)

        # Повертаємо Excel-файл як відповідь
        output.seek(0)
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="forecast_{income_code}_{datetime.now().strftime("%Y%m%d")}.xlsx"'
        return response

    except Exception as e:
        logger.error(f"Помилка створення Excel-файлу: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)