#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
© 2025 ООО "НАЙС СОФТ ГРУПП" (ИНН 5024245440)
Контакты: <niceos@ncsgp.ru>

Описание:
Модуль для добавления публичного ключа и разрешения root-доступа по SSH
в системе NiceOS в процессе пост-установки.
"""

import sys
import glob
from importlib import metadata
from os.path import dirname, basename, isfile, join


modules = glob.glob(join(dirname(__file__), "*.py"))
__all__ = [ basename(f)[:-3] for f in modules if isfile(f) and not f.endswith('__init__.py')]
sys.path.append(dirname(__file__))

try:
    __version__ = metadata.version(__name__)
except metadata.PackageNotFoundError:  # pragma: no cover - package not installed
    __version__ = "0.0.0"
