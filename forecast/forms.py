from django import forms
from .models import Budgets, Regions

class BudgetQueryForm(forms.Form):
    region = forms.ModelChoiceField(
        queryset=Regions.objects.all().order_by('name'),
        label="Область",
        empty_label="Оберіть регіон",
        to_field_name="code_region",
        required=True
    )
    budget = forms.ModelChoiceField(
        queryset=Budgets.objects.all().order_by('name_budg'),
        label="Бюджет",
        empty_label="Оберіть бюджет",
        to_field_name="code_budg",
        required=True
    )
    years = forms.MultipleChoiceField(
        choices=[(year, year) for year in range(2018, 2026)],
        label="Роки",
        initial=[2023],
        widget=forms.CheckboxSelectMultiple
    )
    period = forms.ChoiceField(
        choices=[
            ('MONTH', 'По місяцях'),
        ],
        label="Період",
        initial='MONTH'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['budget'].queryset = Budgets.objects.all().order_by('name_budg')
        if 'region' in self.data:
            try:
                region_id = self.data.get('region')
                self.fields['budget'].queryset = Budgets.objects.filter(code_region=region_id).order_by('name_budg')
            except (ValueError, TypeError):
                pass