#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
© 2025 ООО "НАЙС СОФТ ГРУПП" (ИНН 5024245440)
Контакты: <niceos@ncsgp.ru>
"""

import logging
from menu import Menu
from window import Window
from actionresult import ActionResult


class WheelSelector(object):
    def __init__(self, maxy, maxx, install_config, logger=None):
        """
        Инициализация селектора для добавления пользователя в группу wheel.

        Аргументы:
        - maxy (int): Максимальная координата Y экрана.
        - maxx (int): Максимальная координата X экрана.
        - install_config (dict): Конфигурация установки.
        - logger (logging.Logger, optional): Логгер для записи событий. Если None, логирование не выполняется.
        """
        self.logger = logger
        if self.logger is not None:
            self.logger.debug(f"Инициализация WheelSelector: maxy={maxy}, maxx={maxx}, install_config={install_config}")

        # Проверка входных параметров
        if not isinstance(maxy, int) or not isinstance(maxx, int) or maxy <= 0 or maxx <= 0:
            if self.logger is not None:
                self.logger.error(f"Недопустимые размеры экрана: maxy={maxy}, maxx={maxx}")
            raise ValueError("maxy и maxx должны быть положительными целыми числами")
        if not isinstance(install_config, dict):
            if self.logger is not None:
                self.logger.error(f"Недопустимая конфигурация: {install_config}")
            raise ValueError("install_config должен быть словарем")

        self.install_config = install_config
        self.win_width = min(50, maxx - 4)  # Ограничение ширины окна
        self.win_height = min(12, maxy - 4)  # Ограничение высоты окна
        self.win_starty = (maxy - self.win_height) // 2
        self.menu_starty = self.win_starty + 3

        menu_items = [
            ("Нет", self.set_wheel, False),
            ("Да", self.set_wheel, True)
        ]

        try:
            max_item_length = max(len(item[0]) for item in menu_items)
            menu_width = min(self.win_width - 4, max_item_length + 4)
            self.menu = Menu(self.menu_starty, menu_width, menu_items, default_selected=0,
                             tab_enable=False, logger=self.logger)
            self.window = Window(self.win_height, self.win_width, maxy, maxx,
                                "Добавить пользователя в группу wheel", True, self.menu,
                                can_go_next=True, logger=self.logger)
            if self.logger is not None:
                self.logger.debug(f"Меню и окно инициализированы: menu_width={menu_width}")
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при инициализации: {str(e)}")
            raise

    def set_wheel(self, is_enabled):
        """
        Установка параметра добавления пользователя в группу wheel.

        Аргументы:
        - is_enabled (bool): Флаг включения пользователя в группу wheel.

        Возвращает:
        - ActionResult: Результат действия.
        """
        if self.logger is not None:
            self.logger.debug(f"Установка user_wheel: {is_enabled}")

        try:
            if not isinstance(is_enabled, bool):
                if self.logger is not None:
                    self.logger.error(f"Недопустимое значение is_enabled: {is_enabled}")
                return ActionResult(False, {"error": "is_enabled должен быть булевым значением"})

            self.install_config['user_wheel'] = is_enabled
            if self.logger is not None:
                self.logger.info(f"Пользователь {'добавлен' if is_enabled else 'не добавлен'} в группу wheel")
            return ActionResult(True, None)
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при установке user_wheel: {str(e)}")
            return ActionResult(False, {"error": str(e)})

    def display(self):
        """
        Отображение окна выбора добавления пользователя в группу wheel.

        Возвращает:
        - ActionResult: Результат действия.
        """
        if self.logger is not None:
            self.logger.debug("Запуск отображения окна WheelSelector")

        try:
            result = self.window.do_action()
            if self.logger is not None:
                self.logger.info(f"Результат выбора: {result}")
            return result
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при отображении окна: {str(e)}")
            return ActionResult(False, {"error": str(e)})
