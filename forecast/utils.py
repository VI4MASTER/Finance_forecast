import time
from forecast.models import Budgets, Regions, Incomes
from django.db import transaction

def load_budgets_dict(data):
    start_time = time.time()
    print("Початок обробки словника бюджетів...")

    # Визначаємо допустимі значення для signBudg
    valid_sign_budg = {'gm', 'gs', 'gss'}#gm, gs, gss

    # Фільтруємо записи
    filtered_budgets = [
        budget_data for budget_data in data
        if budget_data.get('signBudg') in valid_sign_budg  # Фільтр по signBudg
        and budget_data.get('cntBudg') == 1  # Фільтр по cntBudg
    ]

    total = len(filtered_budgets)
    print(f"Знайдено {len(data)} записів, відфільтровано до {total}")

    # Створюємо об'єкти для bulk_create
    objects = [
        Budgets(
            code_budg=budget_data['codebudg'],
            name_local_gov=budget_data['nameLocalGov'],
            code_region=budget_data['codeRegion'],
            name_budg=budget_data['namebudg'],
            katottg=budget_data['katottg'],
            sign_budg=budget_data['signBudg']
        )
        for budget_data in filtered_budgets
    ]

    # Зберігаємо у базу одним запитом
    with transaction.atomic():
        Budgets.objects.all().delete() #Очищаємо довідник перед заповненням новими даними
        Budgets.objects.bulk_create(objects, ignore_conflicts=False)
        recorded = Budgets.objects.count()

    elapsed = time.time() - start_time
    print(f"Записано в базу: {recorded} бюджетів")
    print(f"Завантажено {total} бюджетів за {elapsed:.2f} секунд")


def load_regions_dict(data):
    start_time = time.time()
    print("Початок обробки довідника областей...")

    print(f"Знайдено {len(data)} записів")

    # Створюємо об'єкти
    objects = [
        Regions(
            code_region=region_data['coderegion'],
            name=region_data['name']
        )
        for region_data in data
    ]

    # Зберігаємо
    with transaction.atomic():
        Regions.objects.all().delete()
        Regions.objects.bulk_create(objects, ignore_conflicts=False)
        recorded = Regions.objects.count()

    elapsed = time.time() - start_time
    print(f"Записано областей: {recorded}")
    print(f"Завантажено {recorded} областей за {elapsed:.2f} секунд")


def load_incomes_dict(data):
    start_time = time.time()
    print("Початок обробки словника кодів доходів...")

    # Фільтруємо записи
    filtered_incomes = [
        budget_data for budget_data in data
        if budget_data.get('details') == 1  # Фільтр по ознака "1" - детальний код ("0" для групуючих)
    ]

    total = len(filtered_incomes)
    print(f"Знайдено {len(data)} записів, відфільтровано до {total}")

    # Створюємо об'єкти для bulk_create
    objects = [
        Incomes(
            kdb_code=budget_data['code'],
            kdb_name=budget_data['name'],
        )
        for budget_data in filtered_incomes
    ]

    # Зберігаємо у базу одним запитом
    with transaction.atomic():
        Incomes.objects.all().delete() #Очищаємо довідник перед заповненням новими даними
        Incomes.objects.bulk_create(objects, ignore_conflicts=False)
        recorded = Incomes.objects.count()

    elapsed = time.time() - start_time
    print(f"Записано в базу: {recorded} кодів доходів")
    print(f"Завантажено {total} кодів доходів за {elapsed:.2f} секунд")