#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
© 2025 ООО "НАЙС СОФТ ГРУПП" (ИНН 5024245440)
Контакты: <niceos@ncsgp.ru>
"""

import os
import platform
import logging
from jsonwrapper import JsonWrapper
from menu import Menu
from window import Window
from actionresult import ActionResult


class PackageSelector(object):
    def __init__(self, maxy, maxx, install_config, options_file, logger=None):
        """
        Инициализация селектора пакетов для установки.

        Аргументы:
        - maxy (int): Максимальная координата Y экрана.
        - maxx (int): Максимальная координата X экрана.
        - install_config (dict): Конфигурация установки.
        - options_file (str): Путь к JSON-файлу с опциями установки.
        - logger (logging.Logger, optional): Логгер для записи событий. Если None, логирование не выполняется.
        """
        self.logger = logger
        if self.logger is not None:
            self.logger.debug(f"Инициализация PackageSelector: maxy={maxy}, maxx={maxx}, "
                             f"install_config={install_config}, options_file={options_file}")

        # Проверка входных параметров
        if not isinstance(maxy, int) or not isinstance(maxx, int) or maxy <= 0 or maxx <= 0:
            if self.logger is not None:
                self.logger.error(f"Недопустимые размеры экрана: maxy={maxy}, maxx={maxx}")
            raise ValueError("maxy и maxx должны быть положительными целыми числами")
        if not isinstance(install_config, dict):
            if self.logger is not None:
                self.logger.error(f"Недопустимая конфигурация: {install_config}")
            raise ValueError("install_config должен быть словарем")
        if not isinstance(options_file, str) or not os.path.isfile(options_file):
            if self.logger is not None:
                self.logger.error(f"Недопустимый или несуществующий файл опций: {options_file}")
            raise ValueError("options_file должен быть существующим файлом")

        self.install_config = install_config
        self.inactive_screen = False
        self.maxx = maxx
        self.maxy = maxy
        self.win_width = min(50, maxx - 4)  # Ограничение ширины окна
        self.win_height = min(13, maxy - 4)  # Ограничение высоты окна
        self.win_starty = (self.maxy - self.win_height) // 2
        self.win_startx = (self.maxx - self.win_width) // 2
        self.menu_starty = self.win_starty + 3

        try:
            self.load_package_list(options_file)
            if not self.inactive_screen:
                self.window = Window(self.win_height, self.win_width, self.maxy, self.maxx,
                                    'Выберите установку', True, action_panel=self.package_menu,
                                    can_go_next=True, position=1, logger=self.logger)
                if self.logger is not None:
                    self.logger.debug("Окно инициализировано")
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при инициализации: {str(e)}")
            raise

    @staticmethod
    def get_packages_to_install(option, output_data_path):
        """
        Получение списка пакетов для выбранной опции установки.

        Аргументы:
        - option (dict): Опция установки из JSON.
        - output_data_path (str): Путь к директории с файлами пакетов.

        Возвращает:
        - list: Список пакетов для установки.

        Выбрасывает:
        - Exception: Если опция не содержит 'packagelist_file' или 'packages'.
        """
        try:
            if 'packagelist_file' in option:
                json_wrapper_package_list = JsonWrapper(os.path.join(output_data_path,
                                                                    option['packagelist_file']))
                package_list_json = json_wrapper_package_list.read()
                platform_packages = f"packages_{platform.machine()}"
                if platform_packages in package_list_json:
                    return package_list_json["packages"] + package_list_json[platform_packages]
                return package_list_json["packages"]
            elif 'packages' in option:
                return option["packages"]
            else:
                raise Exception(f"Опция установки '{option.get('title', 'unknown')}' должна содержать "
                                "'packagelist_file' или 'packages'")
        except Exception as e:
            raise Exception(f"Ошибка при получении списка пакетов: {str(e)}")

    def load_package_list(self, options_file):
        """
        Загрузка списка пакетов из JSON-файла.

        Аргументы:
        - options_file (str): Путь к JSON-файлу с опциями.
        """
        if self.logger is not None:
            self.logger.debug(f"Загрузка списка пакетов из {options_file}")

        try:
            json_wrapper_option_list = JsonWrapper(options_file)
            option_list_json = json_wrapper_option_list.read()
            options_sorted = option_list_json.items()
            self.package_menu_items = []
            base_path = os.path.dirname(options_file)
            package_list = []

            if len(options_sorted) == 1:
                self.inactive_screen = True
                list(options_sorted)[0][1]['visible'] = True
                if self.logger is not None:
                    self.logger.info("Найдена единственная опция, автоматический выбор")

            if platform.machine() == "aarch64" and 'realtime' in dict(options_sorted):
                dict(options_sorted)['realtime']['visible'] = False
                if self.logger is not None:
                    self.logger.debug("Отключена опция 'realtime' для архитектуры aarch64")

            default_selected = 0
            visible_options_cnt = 0
            for install_option in options_sorted:
                if install_option[1].get("visible", True):
                    package_list = self.get_packages_to_install(install_option[1], base_path)
                    if not isinstance(package_list, list):
                        if self.logger is not None:
                            self.logger.error(f"Список пакетов для {install_option[1]['title']} не является списком")
                        raise ValueError(f"Список пакетов для {install_option[1]['title']} должен быть списком")
                    self.package_menu_items.append((install_option[1]["title"],
                                                   self.exit_function,
                                                   [install_option[0], package_list]))
                    if install_option[0] == 'minimal':
                        default_selected = visible_options_cnt
                    visible_options_cnt += 1
                    if self.logger is not None:
                        self.logger.debug(f"Добавлена опция: {install_option[1]['title']}, пакетов: {len(package_list)}")

            if not self.package_menu_items:
                if self.logger is not None:
                    self.logger.error("Не найдено видимых опций установки")
                raise ValueError("Не найдено видимых опций установки")

            max_item_length = max(len(item[0]) for item in self.package_menu_items) if self.package_menu_items else 0
            menu_width = min(self.win_width - 4, max_item_length + 4)

            if self.inactive_screen:
                self.exit_function(self.package_menu_items[0][2])
            else:
                self.package_menu = Menu(self.menu_starty, menu_width, self.package_menu_items,
                                        default_selected=default_selected, tab_enable=False,
                                        logger=self.logger)
                if self.logger is not None:
                    self.logger.debug(f"Меню создано: ширина={menu_width}, элементов={len(self.package_menu_items)}")
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при загрузке списка пакетов: {str(e)}")
            raise

    def exit_function(self, selected_item_params):
        """
        Обработка выбора пакета.

        Аргументы:
        - selected_item_params (list): Параметры выбранной опции [ключ, список пакетов].

        Возвращает:
        - ActionResult: Результат действия.
        """
        if self.logger is not None:
            self.logger.debug(f"Выбор пакета: {selected_item_params}")

        try:
            if selected_item_params[0] == 'ostree':
                self.install_config['ostree'] = {}
                if self.logger is not None:
                    self.logger.info("Выбрана опция ostree")
            else:
                self.install_config.pop('ostree', None)
                if self.logger is not None:
                    self.logger.debug("Опция ostree удалена из конфигурации")
            self.install_config['packages'] = selected_item_params[1]
            if self.logger is not None:
                self.logger.info(f"Сохранено пакетов: {len(selected_item_params[1])}")
            return ActionResult(True, {'custom': False})
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при выборе пакета: {str(e)}")
            return ActionResult(False, {"error": str(e)})

    def custom_packages(self):
        """
        Обработка выбора пользовательских пакетов.

        Возвращает:
        - ActionResult: Результат действия.
        """
        if self.logger is not None:
            self.logger.debug("Выбор пользовательских пакетов")
        return ActionResult(True, {'custom': True})

    def display(self):
        """
        Отображение окна выбора пакетов.

        Возвращает:
        - ActionResult: Результат действия.
        """
        if self.logger is not None:
            self.logger.debug("Запуск отображения окна выбора пакетов")

        try:
            if self.inactive_screen:
                if self.logger is not None:
                    self.logger.info("Экран неактивен, возврат результата")
                return ActionResult(None, {"inactive_screen": True})
            result = self.window.do_action()
            if self.logger is not None:
                self.logger.info(f"Результат выбора пакетов: {result}")
            return result
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при отображении окна: {str(e)}")
            return ActionResult(False, {"error": str(e)})
