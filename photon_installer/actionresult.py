#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
© 2025 ООО "НАЙС СОФТ ГРУПП" (ИНН 5024245440)
Контакты: <niceos@ncsgp.ru>

Описание:
Модуль для добавления публичного ключа и разрешения root-доступа по SSH
в системе NiceOS в процессе пост-установки.
"""

class ActionResult(object):
    def __init__(self, success, result):
        self.success = success
        self.result = result
