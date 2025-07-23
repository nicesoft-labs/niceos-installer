#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
© 2025 ООО "НАЙС СОФТ ГРУПП" (ИНН 5024245440)
Контакты: <niceos@ncsgp.ru>
"""

"""Простое окно выбора типа файловой системы."""

import logging
from menu import Menu
from window import Window
from actionresult import ActionResult


class FilesystemSelector(object):
    """Представляет пользователю меню для выбора типа файловой системы."""

    FS_TYPES = ["ext3", "ext4", "xfs", "btrfs", "swap"]

    def __init__(self, maxy, maxx, logger=None):
        """
        Инициализация селектора файловой системы.

        Аргументы:
        - maxy (int): Максимальная координата Y экрана.
        - maxx (int): Максимальная координата X экрана.
        - logger (logging.Logger, optional): Логгер для записи событий. Если None, логирование не выполняется.
        """
        self.logger = logger
        if self.logger is not None:
            self.logger.debug(f"Инициализация FilesystemSelector: maxy={maxy}, maxx={maxx}")

        # Проверка входных параметров
        if not isinstance(maxy, int) or not isinstance(maxx, int) or maxy <= 0 or maxx <= 0:
            if self.logger is not None:
                self.logger.error(f"Недопустимые размеры окна: maxy={maxy}, maxx={maxx}")
            raise ValueError("Параметры maxy и maxx должны быть положительными целыми числами")
        
        if not self.FS_TYPES:
            if self.logger is not None:
                self.logger.error("Список FS_TYPES пуст")
            raise ValueError("Список типов файловых систем не должен быть пустым")

        self.maxy = maxy
        self.maxx = maxx
        self.selected_fs = None

        # Настройка размеров и положения окна
        win_width = 40
        win_height = 12
        win_starty = (maxy - win_height) // 2
        menu_starty = win_starty + 3
        if self.logger is not None:
            self.logger.debug(f"Параметры окна: win_width={win_width}, win_height={win_height}, "
                             f"win_starty={win_starty}, menu_starty={menu_starty}")

        try:
            # Создание элементов меню
            menu_items = [(fs, self._set_fs, fs) for fs in self.FS_TYPES]
            if self.logger is not None:
                self.logger.debug(f"Создано меню с элементами: {menu_items}")

            # Инициализация меню
            self.menu = Menu(menu_starty, maxx, menu_items, default_selected=0, tab_enable=False)
            if self.logger is not None:
                self.logger.debug(f"Меню инициализировано: menu_starty={menu_starty}, maxx={maxx}")

            # Инициализация окна
            FILESYSTEM_HELP_TEXT = (
                "Выберите файловую систему для нового раздела:\n\n"
                "ext4  — Надёжная и проверенная система. Рекомендуется по умолчанию для большинства случаев.\n"
                "xfs   — Подходит для серверов и хранения больших файлов. Высокая производительность.\n"
                "btrfs — Поддерживает снимки (snapshots), сжатие и другие возможности. Для опытных пользователей.\n"
                "ext3  — Старый формат. Используйте только при необходимости совместимости.\n"
                "swap  — Раздел подкачки. Используется системой, а не для хранения файлов.\n\n"
                "Рекомендуется выбрать 'ext4', если вы не уверены."
            )
            
            self.window = Window(
                win_height,
                win_width,
                maxy,
                maxx,
                "Выбор файловой системы",
                True,
                self.menu,
                can_go_next=True,
                help_text=FILESYSTEM_HELP_TEXT
            )
            if self.logger is not None:
                self.logger.debug("Окно инициализировано")
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при инициализации FilesystemSelector: {str(e)}")
            raise

    def _set_fs(self, fs):
        """
        Установка выбранного типа файловой системы.

        Аргументы:
        - fs (str): Выбранный тип файловой системы.

        Возвращает:
        - ActionResult: Результат операции.
        """
        if self.logger is not None:
            self.logger.debug(f"Установка типа файловой системы: {fs}")
        
        self.selected_fs = fs
        result = ActionResult(True, None)
        if self.logger is not None:
            self.logger.info(f"Выбрана файловая система: {fs}")
        return result

    def display(self):
        """
        Отображение окна для выбора файловой системы.

        Возвращает:
        - ActionResult: Результат операции с выбранной файловой системой или ошибкой.
        """
        if self.logger is not None:
            self.logger.debug("Запуск метода display для выбора файловой системы")

        try:
            result = self.window.do_action()
            if self.logger is not None:
                self.logger.debug(f"Результат do_action: success={result.success}, result={result.result}")
            
            if result.success:
                if self.selected_fs is None:
                    if self.logger is not None:
                        self.logger.warning("Файловая система не выбрана")
                    return ActionResult(False, {"error": "Файловая система не выбрана"})
                
                if self.logger is not None:
                    self.logger.info(f"Успешно выбрана файловая система: {self.selected_fs}")
                return ActionResult(True, {"filesystem": self.selected_fs})
            
            if self.logger is not None:
                self.logger.info("Пользователь отменил выбор файловой системы")
            return result
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при отображении окна выбора: {str(e)}")
            return ActionResult(False, {"error": str(e)})
