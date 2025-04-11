from django.contrib import admin
from .models import Budgets

@admin.register(Budgets)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ('code_budg', 'name_budg', 'name_local_gov', 'code_region', 'koatuu', 'sign_budg')
    search_fields = ('code_budg', 'name_budg')