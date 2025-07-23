#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
© 2025 ООО "НАЙС СОФТ ГРУПП" (ИНН 5024245440)
Контакты: <niceos@ncsgp.ru>
"""

import curses
import logging
from window import Window
from menu import Menu
from actionresult import ActionResult


class ConfirmWindow(Window):
    def __init__(self, height, width, maxy, maxx, menu_starty, message, logger=None, info=False):
        """
        Инициализация окна подтверждения с меню.

        Аргументы:
        - height (int): Высота окна.
        - width (int): Ширина окна.
        - maxy (int): Максимальная координата Y экрана.
        - maxx (int): Максимальная координата X экрана.
        - menu_starty (int): Начальная позиция Y для меню.
        - message (str): Сообщение для отображения в окне.
        - logger (logging.Logger, optional): Логгер для записи событий. Если None, логирование не выполняется.
        - info (bool): Если True, отображается только кнопка "OK", иначе "Yes"/"No".
        """
        self.logger = logger
        if self.logger is not None:
            self.logger.debug(f"Инициализация ConfirmWindow: height={height}, width={width}, maxy={maxy}, maxx={maxx}, "
                             f"menu_starty={menu_starty}, message='{message}', info={info}")

        # Проверка корректности входных параметров
        if height <= 0 or width <= 0 or maxy <= 0 or maxx <= 0 or menu_starty < 0:
            if self.logger is not None:
                self.logger.error(f"Недопустимые параметры окна: height={height}, width={width}, maxy={maxy}, maxx={maxx}, "
                                 f"menu_starty={menu_starty}")
            raise ValueError("Недопустимые размеры окна или позиция меню")

        try:
            # Формирование элементов меню в зависимости от параметра info
            if info:
                items = [('OK', self.exit_function, True)]
                if self.logger is not None:
                    self.logger.debug("Создание меню с единственной опцией 'OK'")
            else:
                items = [('Да', self.exit_function, True), ('Нет', self.exit_function, False)]
                if self.logger is not None:
                    self.logger.debug("Создание меню с опциями 'Yes' и 'No'")

            # Инициализация меню
            self.menu = Menu(menu_starty, maxx, items, can_navigate_outside=False, horizontal=True)
            if self.logger is not None:
                self.logger.debug(f"Меню инициализировано: menu_starty={menu_starty}, maxx={maxx}, items={items}")

            # Вызов конструктора родительского класса
            super(ConfirmWindow, self).__init__(height, width, maxy, maxx, 'Подтверждение', False, self.menu)
            if self.logger is not None:
                self.logger.debug("Родительский класс Window инициализирован")

            # Отображение сообщения в окне
            self.addstr(0, 0, message)
            if self.logger is not None:
                self.logger.info(f"Сообщение отображено в окне: '{message}'")
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при инициализации ConfirmWindow: {str(e)}")
            raise

    def exit_function(self, yes):
        """
        Функция выхода с возвратом результата выбора.

        Аргументы:
        - yes (bool): Результат выбора (True для 'Yes'/'OK', False для 'No').

        Возвращает:
        - ActionResult: Объект с результатом действия.
        """
        if self.logger is not None:
            self.logger.debug(f"Вызов exit_function с параметром yes={yes}")
        result = ActionResult(True, {'yes': yes})
        if self.logger is not None:
            self.logger.info(f"Результат выбора: {result}")
        return result
