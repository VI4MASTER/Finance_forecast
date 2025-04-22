import asyncio
from django.core.management.base import BaseCommand
from forecast.api import fetch_budget_dict_data, fetch_region_dict_data, fetch_incomes_dict_data
from forecast.utils import load_budgets_dict, load_regions_dict, load_incomes_dict
from asgiref.sync import sync_to_async

class Command(BaseCommand):
    help = 'Завантажує/оновлює довідники з API у базу даних асинхронно'

    async def async_handle(self):
        try:
            # Виконуємо всі запити паралельно
            budg_data, region_data, incomes_data = await asyncio.gather(
                fetch_budget_dict_data(),
                fetch_region_dict_data(),
                fetch_incomes_dict_data()
            )

            # Завантажуємо дані в базу послідовно, використовуючи sync_to_async
            await sync_to_async(load_incomes_dict)(incomes_data)
            await sync_to_async(load_budgets_dict)(budg_data)
            await sync_to_async(load_regions_dict)(region_data)

            self.stdout.write(self.style.SUCCESS('Дані успішно завантажено'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Помилка: {e}'))

    def handle(self, *args, **options):
        # Запускаємо асинхронну функцію з синхронного контексту
        asyncio.run(self.async_handle())