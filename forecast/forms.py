from django import forms
from .models import Budgets, Regions

class BudgetQueryForm(forms.Form):
    region = forms.ModelChoiceField(
        queryset=Regions.objects.all().order_by('name'),
        label="Регіон",
        empty_label="Оберіть регіон",
        to_field_name="code_region"
    )
    budget = forms.ModelChoiceField(
        queryset=Budgets.objects.all().order_by('name_budg'),
        label="Бюджет",
        empty_label="Оберіть бюджет",
        to_field_name="code_budg"
    )
    year = forms.ChoiceField(
        choices=[(year, year) for year in range(2020, 2026)],
        label="Рік",
        initial=2023
    )
    period = forms.ChoiceField(
        choices=[('MONTH', 'По місяцях')],
        label="Період",
        initial='MONTH'
    )