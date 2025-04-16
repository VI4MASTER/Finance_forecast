from django.shortcuts import render
from django.http import JsonResponse
from .forms import BudgetQueryForm
from .api import fetch_budget_incomes_data
from .models import Budgets, IncomeHistory
import pandas as pd


def budget_incomes_view(request):
    form = BudgetQueryForm(request.POST or None)
    results = None
    error = None

    if request.method == 'POST' and form.is_valid():
        try:
            budget_code = form.cleaned_data['budget'].code_budg
            years = form.cleaned_data['years']
            period = form.cleaned_data['period']
            save_to_db = request.POST.get('save_to_db')

            # Перевіряємо базу даних
            all_data = []
            years_to_fetch = []
            for year in years:
                existing_data = IncomeHistory.objects.filter(
                    budget__code_budg=budget_code,
                    rep_period__startswith=f"{year}"
                ).values('rep_period', 'fund_typ', 'cod_budget', 'cod_inco', 'zat_amt', 'fakt_amt')

                if existing_data.exists():
                    all_data.extend(existing_data)
                else:
                    years_to_fetch.append(year)

            # Запитуємо API для відсутніх років
            if years_to_fetch:
                api_results = fetch_budget_incomes_data(
                    budget_code=budget_code,
                    years=years_to_fetch,
                    period=period
                )
                all_data.extend(api_results)

            # Перетворюємо в DataFrame для зведеної таблиці
            if all_data:
                # Перевіряємо, чи всі записи мають потрібні ключі
                required_keys = {'rep_period', 'fund_typ', 'cod_budget', 'cod_inco', 'zat_amt', 'fakt_amt'}
                all_data = [row for row in all_data if all(key in row for key in required_keys)]

                if not all_data:
                    raise ValueError(
                        "Немає даних із усіма необхідними полями (rep_period, fund_typ, cod_budget, cod_inco, zat_amt, fakt_amt)")

                df = pd.DataFrame(all_data)

                # Перетворюємо rep_period у str і перевіряємо формат
                df['rep_period'] = df['rep_period'].astype(str)
                df = df[df['rep_period'].str.contains(r'^\d{2}\.\d{4}$', na=False)]

                if df.empty:
                    raise ValueError("Немає даних із коректним форматом rep_period (MM.YYYY)")

                # Витягуємо рік і місяць
                df['year'] = df['rep_period'].str.split('.').str[1]
                df['month'] = df['rep_period'].str.split('.').str[0]
                # Створюємо зведену таблицю
                pivot_df = df.pivot_table(
                    values='fakt_amt',
                    index=['cod_budget', 'cod_inco', 'fund_typ', 'year'],
                    columns='month',
                    aggfunc='first'
                ).reset_index()
                # Перейменовуємо стовпці
                pivot_df.columns = ['cod_budget', 'cod_inco', 'fund_typ', 'year'] + [f"{month:02d}" for month in
                                                                                     range(1, 13)]
                # Заповнюємо NaN прочерками
                pivot_df = pivot_df.fillna('—')
                results = pivot_df.to_dict('records')

            # Зберігаємо в базу, якщо натиснуто "Зберегти"
            if save_to_db and all_data:
                budget_obj = Budgets.objects.get(code_budg=budget_code)
                for row in all_data:
                    rep_period = str(row['rep_period'])
                    if not rep_period or not '.' in rep_period:
                        continue  # Пропускаємо некоректні записи
                    IncomeHistory.objects.update_or_create(
                        budget=budget_obj,
                        rep_period=rep_period,
                        fund_typ=row['fund_typ'],
                        cod_inco=row['cod_inco'],
                        defaults={
                            'cod_budget': row['cod_budget'],
                            'zat_amt': row['zat_amt'],
                            'fakt_amt': row['fakt_amt']
                        }
                    )

            if not results:
                error = "Дані за вибрані роки не знайдено."
        except Exception as e:
            error = str(e)

    return render(request, 'forecast/budget_incomes.html', {
        'form': form,
        'results': results,
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