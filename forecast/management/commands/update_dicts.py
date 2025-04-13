from django.core.management.base import BaseCommand
from forecast.api import fetch_budget_dict_data, fetch_region_dict_data
from forecast.utils import load_budgets_dict, load_regions_dict

class Command(BaseCommand):
    help = 'Завантажує/оновлює довідники з API у базу даних'

    def handle(self, *args, **options):
        try:
            budg_data = fetch_budget_dict_data()  # Отримуємо дані з вашого api.py
            region_data = fetch_region_dict_data()

            load_budgets_dict(budg_data)  # Завантажуємо їх у базу
            load_regions_dict(region_data)

            self.stdout.write(self.style.SUCCESS('Дані успішно завантажено'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Помилка: {e}'))