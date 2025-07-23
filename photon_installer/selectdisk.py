#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
© 2025 ООО "НАЙС СОФТ ГРУПП" (ИНН 5024245440)
Контакты: <niceos@ncsgp.ru>
"""

import sys
import logging
from device import Device
from window import Window
from actionresult import ActionResult
from menu import Menu


class SelectDisk(object):
    def __init__(self, maxy, maxx, install_config, logger=None):
        """
        Инициализация селектора диска для установки.

        Аргументы:
        - maxy (int): Максимальная координата Y экрана.
        - maxx (int): Максимальная координата X экрана.
        - install_config (dict): Конфигурация установки.
        - logger (logging.Logger, optional): Логгер для записи событий. Если None, логирование не выполняется.
        """
        self.logger = logger
        if self.logger is not None:
            self.logger.debug(f"Инициализация SelectDisk: maxy={maxy}, maxx={maxx}, install_config={install_config}")

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
        self.menu_items = []
        self.maxx = maxx
        self.maxy = maxy
        self.win_width = 70  # Фиксированная ширина из вашей версии
        self.win_height = 16  # Фиксированная высота из вашей версии
        self.win_starty = (self.maxy - self.win_height) // 2
        self.win_startx = (self.maxx - self.win_width) // 2
        self.menu_starty = self.win_starty + 6
        self.menu_height = 5
        self.disk_buttom_items = [
            ('<Ручная>', self.custom_function, False),
            ('<Автоматическая>', self.auto_function, False)
        ]
        self.devices = None

        try:
            self.window = Window(
                self.win_height,
                self.win_width,
                self.maxy,
                self.maxx,
                'Выберите диск',
                can_go_back=True,
                items=self.disk_buttom_items,
                menu_helper=self.save_index,
                position=2,  # Начальная позиция из вашей версии
                tab_enabled=False,  # Отключаем Tab для согласованности
                logger=self.logger
            )
            if self.logger is not None:
                self.logger.debug("Окно успешно инициализировано")
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при создании окна: {str(e)}")
            raise Exception(f"Ошибка инициализации окна: {str(e)}")

    def display(self):
        """
        Отображение окна выбора диска и метода разметки.

        Возвращает:
        - ActionResult: Результат действия.
        """
        if self.logger is not None:
            self.logger.debug("Запуск отображения окна выбора диска")

        try:
            self.disk_menu_items = []
            self.devices = Device.refresh_devices()
            if self.logger is not None:
                self.logger.debug(f"Обнаружено устройств: {len(self.devices)}")

            if len(self.devices) == 0:
                err_win = Window(
                    self.win_height,
                    self.win_width,
                    self.maxy,
                    self.maxx,
                    'Ошибка',
                    can_go_back=False,
                    position=2,
                    tab_enabled=False,
                    logger=self.logger
                )
                err_win.addstr(0, 0, 'Не найдено блочных устройств для выбора\n' +
                                     'Нажмите любую клавишу для перехода в bash.')
                err_win.show_window()
                err_win.content_window().getch()
                if self.logger is not None:
                    self.logger.error("Не найдено блочных устройств, завершение программы")
                sys.exit(1)

            self.window.addstr(0, 0, 'Выберите диск и метод разметки:\n' +
                                     'Автоматическая - один раздел для /, без swap.\n' +
                                     'Ручная - для пользовательской разметки')
            for index, device in enumerate(self.devices):
                self.disk_menu_items.append(
                    (
                        f'{device.model} - {device.size} @ {device.path}',
                        lambda idx=index: self.save_index(idx),  # Лямбда для корректной передачи индекса
                        index
                    ))
            if self.logger is not None:
                self.logger.debug(f"Создано {len(self.disk_menu_items)} элементов меню для дисков")

            self.disk_menu = Menu(
                self.menu_starty,
                self.maxx,  # Используем self.maxx для корректного выравнивания, как в вашей версии
                self.disk_menu_items,
                self.menu_height,
                tab_enable=False,
                logger=self.logger
            )
            self.disk_menu.can_save_sel(True)
            if self.logger is not None:
                self.logger.debug(f"Меню создано: ширина={self.maxx}, высота={self.menu_height}")

            self.window.set_action_panel(self.disk_menu)
            result = self.window.do_action()
            if self.logger is not None:
                self.logger.info(f"Результат выбора диска: {result}")
            return result
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при отображении окна: {str(e)}")
            return ActionResult(False, {"error": f"Ошибка отображения окна: {str(e)}"})

    def save_index(self, device_index):
        """
        Сохранение выбранного диска в конфигурацию.

        Аргументы:
        - device_index (int): Индекс выбранного устройства.

        Возвращает:
        - ActionResult: Результат действия.
        """
        if self.logger is not None:
            self.logger.debug(f"Сохранение индекса устройства: {device_index}")
        try:
            self.install_config['disk'] = self.devices[device_index].path
            if self.logger is not None:
                self.logger.info(f"Выбран диск: {self.install_config['disk']}")
            return ActionResult(True, {"diskIndex": device_index})
        except IndexError:
            if self.logger is not None:
                self.logger.error(f"Недопустимый индекс устройства: {device_index}")
            return ActionResult(False, {"error": f"Недопустимый индекс устройства: {device_index}"})

    def auto_function(self):
        """
        Установка автоматической разметки.

        Возвращает:
        - ActionResult: Результат действия.
        """
        if self.logger is not None:
            self.logger.info("Выбрана автоматическая разметка")
        self.install_config['autopartition'] = True
        return ActionResult(True, {"goNext": True})

    def custom_function(self):
        """
        Установка ручной разметки.

        Возвращает:
        - ActionResult: Результат действия.
        """
        if self.logger is not None:
            self.logger.info("Выбрана ручная разметка")
        self.install_config['autopartition'] = False
        return ActionResult(True, {"goNext": True})
