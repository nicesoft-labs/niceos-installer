#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
© 2025 ООО "НАЙС СОФТ ГРУПП" (ИНН 5024245440)
Контакты: <niceos@ncsgp.ru>
"""

from window import Window
from actionresult import ActionResult
from textpane import TextPane
from os.path import join, dirname
import os
import markdown

class License(object):
    def __init__(self, maxy, maxx, eula_file_path, display_title, logger=None):
        """
        Инициализация окна лицензионного соглашения.

        Аргументы:
        - maxy (int): Максимальная координата Y экрана.
        - maxx (int): Максимальная координата X экрана.
        - eula_file_path (str): *Игнорируется*. Лицензия всегда читается из
          ``niceos_installer/EULA.txt``.
        - display_title (str): Заголовок лицензии.
        """
        self.maxx = maxx
        self.maxy = maxy
        self.win_width = maxx - 4  # Ширина окна с учетом отступов
        self.win_height = maxy - 4  # Высота окна с учетом отступов

        self.win_starty = (self.maxy - self.win_height) // 2  # Начальная Y-координата окна
        self.win_startx = (self.maxx - self.win_width) // 2  # Начальная X-координата окна

        self.text_starty = self.win_starty + 4  # Начальная Y-координата текста
        self.text_height = self.win_height - 6  # Высота области текста
        self.text_width = self.win_width - 6  # Ширина области текста

        self.window = Window(self.win_height, self.win_width, self.maxy, self.maxx,
                             'Добро пожаловать в установщик НАЙС.ОС', False)  # Создание основного окна

        # Always use bundled EULA; ignore incoming path
        self.eula_file_path = join(dirname(__file__), 'EULA.txt')
        if not os.path.exists(self.eula_file_path):
            raise Exception('EULA file not found at %s' % self.eula_file_path)

        if display_title:
            self.title = display_title  # Пользовательский заголовок
        else:
            self.title = 'ЛИЦЕНЗИОННОЕ СОГЛАШЕНИЕ ООО "НАЙС СОФТ ГРУПП"'  # Заголовок по умолчанию

    def display(self):
        """
        Отображение окна лицензионного соглашения.

        Возвращает:
        - ActionResult: Результат действия (принятие или отказ).
        """
        accept_decline_items = [('<Принять>', self.accept_function),  # Элемент для принятия
                                ('<Отменить>', self.exit_function)]  # Элемент для отмены

        self.window.addstr(0, (self.win_width - len(self.title)) // 2, self.title)  # Добавление заголовка
        self.text_pane = TextPane(self.text_starty, self.maxx, self.text_width,
                                  self.eula_file_path, self.text_height, accept_decline_items)  # Создание панели текста
        self.window.set_action_panel(self.text_pane)  # Установка панели действия

        return self.window.do_action()  # Выполнение действия окна

    def accept_function(self):
        """
        Обработка принятия лицензии.

        Возвращает:
        - ActionResult: Успешный результат.
        """
        return ActionResult(True, None)  # Возвращает успех

    def exit_function(self):
        """
        Обработка отмены лицензии.

        Выполняет выход из программы.
        """
        exit(0)  # Завершение программы
