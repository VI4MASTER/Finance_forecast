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