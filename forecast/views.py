from django.shortcuts import render
from django.http import JsonResponse
from .forms import BudgetQueryForm
from .api import fetch_budget_incomes_data
from .models import Budgets
import pandas as pd
import os


def budget_incomes_view(request):
    form = BudgetQueryForm()
    results = None
    error = None

    if request.method == 'POST':
        form = BudgetQueryForm(request.POST)
        if form.is_valid():
            try:
                budget_code = form.cleaned_data['budget'].code_budg
                year = form.cleaned_data['year']
                period = form.cleaned_data['period']

                # Отримуємо дані з API
                results = fetch_budget_incomes_data(
                    budget_code=budget_code,
                    year=year,
                    period=period
                )

                # Опціонально: збереження у файл
                if results:
                    df = pd.DataFrame(results)
                    output_file = f"budget_incomes_{budget_code}_{year}.csv"
                    df.to_csv(output_file, index=False, encoding='utf-8')
                    print(f"Дані збережено у {output_file}")

            except Exception as e:
                error = str(e)

    return render(request, 'forecast/budget_incomes.html', {
        'form': form,
        'results': results,
        'error': error
    })


def get_budgets_by_region(request):
    region_code = request.GET.get('region_code')
    budgets = Budgets.objects.filter(code_region=region_code).order_by('name_budg')
    budget_list = [{'code_budg': b.code_budg, 'name_budg': b.name_budg} for b in budgets]
    return JsonResponse({'budgets': budget_list})