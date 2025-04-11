from django.core.management.base import BaseCommand
from forecast.api import fetch_dict_data
from forecast.utils import load_data

class Command(BaseCommand):
    help = 'Завантажує/оновлює довідники з API у базу даних'

    def handle(self, *args, **options):
        try:
            data = fetch_dict_data()  # Отримуємо дані з вашого api.py
            load_data(data)  # Завантажуємо їх у базу
            self.stdout.write(self.style.SUCCESS('Дані успішно завантажено'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Помилка: {e}'))