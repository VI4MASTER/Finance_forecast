from django.urls import path
from forecast import views

urlpatterns = [
    path('', views.budget_incomes_view, name='budget_incomes'),
    path('forecast/', views.forecast_view, name='forecast'),
    path('get_budgets_by_region/', views.get_budgets_by_region, name='get_budgets_by_region'),
    path('get_income_data/', views.get_income_data, name='get_income_data'),
    path('get_forecast_data/', views.get_forecast_data, name='get_forecast_data'),
]