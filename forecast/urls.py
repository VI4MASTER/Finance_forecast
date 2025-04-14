from django.urls import path
from . import views

urlpatterns = [
    path('budget-incomes/', views.budget_incomes_view, name='budget_incomes'),
    path('get_budgets_by_region/', views.get_budgets_by_region, name='get_budgets_by_region'),
]