from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Повертає значення словника за ключем."""
    return dictionary.get(key)

@register.filter
def split(value, delimiter=' '):
    """Розбиває рядок на список за вказаним роздільником."""
    return value.split(delimiter)