#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
© 2025 ООО "НАЙС СОФТ ГРУПП" (ИНН 5024245440)
Контакты: <niceos@ncsgp.ru>

Описание:
Модуль для добавления публичного ключа и разрешения root-доступа по SSH
в системе NiceOS в процессе пост-установки.
"""


class Action(object):

    def do_action(self, params):
        raise NameError('Abstract method, this should be implemented in the child class')

    def hide(self, params):
        raise NameError('Abstract method, this should be implemented in the child class')
