#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
© 2025 ООО "НАЙС СОФТ ГРУПП" (ИНН 5024245440)
Контакты: <niceos@ncsgp.ru>
"""

import os
from os.path import join, dirname
import logging
from window import Window
from actionresult import ActionResult
from textpane import TextPane


class License(object):
    def __init__(self, maxy, maxx, eula_file_path, display_title, logger=None):
        """
        Инициализация окна для отображения лицензионного соглашения.

        Аргументы:
        - maxy (int): Максимальная координата Y экрана.
        - maxx (int): Максимальная координата X экрана.
        - eula_file_path (str): Путь к файлу лицензионного соглашения (EULA).
        - display_title (str): Заголовок лицензии.
        - logger (logging.Logger, optional): Логгер для записи событий. Если None, логирование не выполняется.
        """
        self.logger = logger
        if self.logger is not None:
            self.logger.debug(f"Инициализация License: maxy={maxy}, maxx={maxx}, eula_file_path={eula_file_path}, "
                             f"display_title={display_title}")

        # Проверка входных параметров
        if not isinstance(maxy, int) or not isinstance(maxx, int) or maxy <= 0 or maxx <= 0:
            if self.logger is not None:
                self.logger.error(f"Недопустимые размеры окна: maxy={maxy}, maxx={maxx}")
            raise ValueError("Параметры maxy и maxx должны быть положительными целыми числами")
        
        if not eula_file_path or not isinstance(eula_file_path, str):
            if self.logger is not None:
                self.logger.error(f"Недопустимый путь к файлу EULA: {eula_file_path}")
            raise ValueError("eula_file_path должен быть непустой строкой")

        self.maxx = maxx
        self.maxy = maxy
        self.win_width = maxx - 4
        self.win_height = maxy - 4
        self.win_starty = (self.maxy - self.win_height) // 2
        self.win_startx = (self.maxx - self.win_width) // 2
        self.text_starty = self.win_starty + 4
        self.text_height = self.win_height - 6
        self.text_width = self.win_width - 6

        # Установка пути к файлу EULA
        self.eula_file_path = eula_file_path if eula_file_path else join(dirname(__file__), 'EULA.txt')
        if not os.path.exists(self.eula_file_path):
            if self.logger is not None:
                self.logger.error(f"Файл EULA не найден: {self.eula_file_path}")
            raise FileNotFoundError(f"Файл EULA не найден: {self.eula_file_path}")

        # Установка заголовка
        self.title = display_title if display_title else 'ЛИЦЕНЗИОННОЕ СОГЛАШЕНИЕ ООО "НАЙС СОФТ ГРУПП"'
        if self.logger is not None:
            self.logger.debug(f"Установлен заголовок: {self.title}")

        try:
            self.window = Window(self.win_height, self.win_width, self.maxy, self.maxx,
                                'Добро пожаловать в установщик НАЙС.ОС', False, logger=self.logger)
            if self.logger is not None:
                self.logger.debug("Окно инициализировано")
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при создании окна: {str(e)}")
            raise

    def display(self):
        """
        Отображение окна лицензионного соглашения.

        Возвращает:
        - ActionResult: Результат действия пользователя (принятие или выход).
        """
        if self.logger is not None:
            self.logger.debug("Запуск отображения лицензионного соглашения")

        try:
            accept_decline_items = [('<Принять>', self.accept_function),
                                    ('<Отменить>', self.exit_function)]
            if self.logger is not None:
                self.logger.debug(f"Создано меню действий: {accept_decline_items}")

            self.window.addstr(0, (self.win_width - len(self.title)) // 2, self.title)
            self.text_pane = TextPane(self.text_starty, self.maxx, self.text_width,
                                      self.eula_file_path, self.text_height, accept_decline_items,
                                      logger=self.logger)
            if self.logger is not None:
                self.logger.debug("TextPane инициализирован")

            self.window.set_action_panel(self.text_pane)
            result = self.window.do_action()
            if self.logger is not None:
                self.logger.info(f"Результат отображения: success={result.success}, result={result.result}")
            
            return result
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при отображении лицензии: {str(e)}")
            return ActionResult(False, {"error": str(e)})

    def accept_function(self):
        """
        Обработка принятия лицензии.

        Возвращает:
        - ActionResult: Результат принятия.
        """
        if self.logger is not None:
            self.logger.info("Пользователь принял лицензию")
        return ActionResult(True, None)

    def exit_function(self):
        """
        Обработка отмены (выхода).

        Завершает выполнение программы.
        """
        if self.logger is not None:
            self.logger.info("Пользователь отменил установку")
        exit(0)
