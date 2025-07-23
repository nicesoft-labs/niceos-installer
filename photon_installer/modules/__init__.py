#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
© 2025 ООО "НАЙС СОФТ ГРУПП" (ИНН 5024245440)
Контакты: <niceos@ncsgp.ru>

Описание:
Автоматически импортирует все модули Python в текущем каталоге,
за исключением __init__.py. Используется для регистрации модулей установки.
"""

import glob
import os

from os.path import dirname, basename, isfile, join

# Получаем путь к текущей директории (где находится __init__.py)
_current_dir = dirname(__file__)

# Ищем все .py файлы, кроме __init__.py
_modules = glob.glob(join(_current_dir, "*.py"))

__all__ = [
    basename(f)[:-3]
    for f in _modules
    if isfile(f) and not f.endswith("__init__.py")
]
