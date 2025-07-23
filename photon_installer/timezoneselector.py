#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
© 2025 ООО "НАЙС СОФТ ГРУПП" (ИНН 5024245440)
Контакты: <niceos@ncsgp.ru>
"""

import os
from zoneinfo import available_timezones
import logging
from menu import Menu
from window import Window
from actionresult import ActionResult


class TimezoneSelector(object):
    def __init__(self, maxy, maxx, install_config, logger=None):
        """
        Инициализация селектора часовых поясов.

        Аргументы:
        - maxy (int): Максимальная координата Y экрана.
        - maxx (int): Максимальная координата X экрана.
        - install_config (dict): Конфигурация установки.
        - logger (logging.Logger, optional): Логгер для записи событий. Если None, логирование не выполняется.
        """
        self.logger = logger
        if self.logger is not None:
            self.logger.debug(f"Инициализация TimezoneSelector: maxy={maxy}, maxx={maxx}, install_config={install_config}")

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
        self.maxx = maxx
        self.maxy = maxy
        self.win_width = min(80, maxx - 4)  # Ограничение ширины окна
        self.win_height = min(18, maxy - 4)  # Ограничение высоты окна
        self.win_starty = max(0, (self.maxy - self.win_height) // 2)
        self.win_startx = max(0, (self.maxx - self.win_width) // 2)
        self.menu_starty = self.win_starty + 3
        self.menu_height = self.win_height - 6  # Оставляем место для кнопок
        self.menu_width = min(self.win_width - 4, maxx - self.win_startx - 8)  # Учет отступов и границ

        self._load_timezones()
        self._selected_group = None
        self._selected_zone = None
        self.default_zone = "Europe/Moscow"

        try:
            self._create_main_menu()
            if self.logger is not None:
                self.logger.debug("Главное меню создано")
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при создании главного меню: {str(e)}")
            raise

    def _load_timezones(self):
        """
        Загрузка списка часовых поясов из zone.tab или zoneinfo.
        """
        if self.logger is not None:
            self.logger.debug("Загрузка часовых поясов")

        self.ru_zones = []
        self.grouped_zones = {}
        zone_tab = "/usr/share/zoneinfo/zone.tab"

        try:
            if os.path.exists(zone_tab):
                with open(zone_tab, "rt", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("#") or line.strip() == "":
                            continue
                        fields = line.split()
                        if len(fields) < 3:
                            continue
                        country = fields[0]
                        zone = fields[2]
                        if country == "RU":
                            self.ru_zones.append(zone)
                        region = zone.split("/")[0]
                        self.grouped_zones.setdefault(region, []).append(zone)
                if self.logger is not None:
                    self.logger.debug(f"Загружено {len(self.ru_zones)} российских зон из zone.tab")
            else:
                zones = available_timezones()
                for z in zones:
                    region = z.split("/")[0]
                    self.grouped_zones.setdefault(region, []).append(z)
                if self.logger is not None:
                    self.logger.debug(f"Загружено {len(zones)} зон из zoneinfo")

            for k in self.grouped_zones:
                self.grouped_zones[k] = sorted(self.grouped_zones[k])
            self.ru_zones = sorted(self.ru_zones)
            if "Europe/Moscow" in self.ru_zones:
                self.ru_zones.insert(0, self.ru_zones.pop(self.ru_zones.index("Europe/Moscow")))
                if self.logger is not None:
                    self.logger.debug("Europe/Moscow перемещен в начало списка российских зон")
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при загрузке часовых поясов: {str(e)}")
            raise

    def _create_main_menu(self):
        """
        Создание главного меню с российскими часовыми поясами.
        """
        if self.logger is not None:
            self.logger.debug("Создание главного меню")

        menu_items = []
        max_item_length = 0
        for tz in self.ru_zones:
            menu_items.append((tz, self._set_timezone, tz))
            max_item_length = max(max_item_length, len(tz))
        menu_items.append(("Другие регионы...", self._other_timezones, None))
        max_item_length = max(max_item_length, len("Другие регионы..."))

        # Ограничение ширины меню с учетом границ
        menu_width = min(self.menu_width, max_item_length + 4)
        default_selected = 0
        if self.default_zone in self.ru_zones:
            default_selected = self.ru_zones.index(self.default_zone)
            if self.logger is not None:
                self.logger.debug(f"Установлен default_selected={default_selected} для {self.default_zone}")

        try:
            self.menu = Menu(self.menu_starty, menu_width, menu_items, self.menu_height,
                             default_selected=default_selected, tab_enable=False, logger=self.logger)
            # Корректировка позиции панели
            menu_x = self.win_startx + max(0, (self.win_width - self.menu.width) // 2)
            menu_x = min(menu_x, self.maxx - self.menu.width)
            self.menu.panel.move(self.menu_starty, menu_x)
            self.window = Window(self.win_height, self.win_width, self.maxy, self.maxx,
                                "Выберите часовой пояс", True, self.menu,
                                can_go_next=True, position=1, logger=self.logger)
            self.install_config["timezone"] = self.default_zone
            if self.logger is not None:
                self.logger.debug(f"Создано главное меню: ширина={menu_width}, высота={self.menu_height}")
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при создании главного меню: {str(e)}")
            raise

    def _set_timezone(self, timezone):
        """
        Установка выбранного часового пояса.

        Аргументы:
        - timezone (str): Выбранный часовой пояс.

        Возвращает:
        - ActionResult: Результат действия.
        """
        if self.logger is not None:
            self.logger.info(f"Установлен часовой пояс: {timezone}")
        self.install_config["timezone"] = timezone
        return ActionResult(True, None)

    def _select_group(self, group):
        """
        Выбор региона.

        Аргументы:
        - group (str): Выбранный регион.

        Возвращает:
        - ActionResult: Результат действия.
        """
        if self.logger is not None:
            self.logger.debug(f"Выбран регион: {group}")
        self._selected_group = group
        return ActionResult(True, None)

    def _select_zone(self, zone):
        """
        Выбор часового пояса в регионе.

        Аргументы:
        - zone (str): Выбранный часовой пояс.

        Возвращает:
        - ActionResult: Результат действия.
        """
        if self.logger is not None:
            self.logger.debug(f"Выбран часовой пояс: {zone}")
        self._selected_zone = zone
        return ActionResult(True, None)

    def _other_timezones(self, _):
        """
        Отображение меню для выбора других регионов и часовых поясов.

        Аргументы:
        - _ (None): Заглушка для соответствия сигнатуре.

        Возвращает:
        - ActionResult: Результат действия.
        """
        if self.logger is not None:
            self.logger.debug("Открытие меню других регионов")

        try:
            groups = sorted(self.grouped_zones.keys())
            group_items = [(g, self._select_group, g) for g in groups]
            max_group_length = max(len(g) for g in groups) if groups else 0
            group_menu_width = min(self.menu_width, max_group_length + 4)
            group_menu_width = min(group_menu_width, self.maxx - self.win_startx - 8)

            group_menu = Menu(self.menu_starty, group_menu_width, group_items, self.menu_height,
                              default_selected=0, tab_enable=False, logger=self.logger)
            # Корректировка позиции панели
            group_menu_x = self.win_startx + max(0, (self.win_width - group_menu.width) // 2)
            group_menu_x = min(group_menu_x, self.maxx - group_menu.width)
            group_menu.panel.move(self.menu_starty, group_menu_x)
            group_window = Window(self.win_height, self.win_width, self.maxy, self.maxx,
                                 "Выберите регион", True, group_menu,
                                 can_go_next=True, position=1, logger=self.logger)
            ar = group_window.do_action()
            if self.logger is not None:
                self.logger.debug(f"Результат выбора региона: {ar}")
            if not ar.success:
                if self.logger is not None:
                    self.logger.info("Возврат назад из меню регионов")
                return ActionResult(False, {"goBack": True})

            zones = self.grouped_zones[self._selected_group]
            zone_items = [(z, self._select_zone, z) for z in zones]
            max_zone_length = max(len(z) for z in zones) if zones else 0
            zone_menu_width = min(self.menu_width, max_zone_length + 4)
            zone_menu_width = min(zone_menu_width, self.maxx - self.win_startx - 8)

            zone_menu = Menu(self.menu_starty, zone_menu_width, zone_items, self.menu_height,
                             default_selected=0, tab_enable=False, logger=self.logger)
            # Корректировка позиции панели
            zone_menu_x = self.win_startx + max(0, (self.win_width - zone_menu.width) // 2)
            zone_menu_x = min(zone_menu_x, self.maxx - zone_menu.width)
            zone_menu.panel.move(self.menu_starty, zone_menu_x)
            zone_window = Window(self.win_height, self.win_width, self.maxy, self.maxx,
                                "Выберите часовой пояс", True, zone_menu,
                                can_go_next=True, position=1, logger=self.logger)
            ar = zone_window.do_action()
            if self.logger is not None:
                self.logger.debug(f"Результат выбора часового пояса: {ar}")
            if not ar.success:
                if self.logger is not None:
                    self.logger.info("Возврат назад из меню часовых поясов")
                return ActionResult(False, {"goBack": True})

            self.install_config["timezone"] = self._selected_zone
            if self.logger is not None:
                self.logger.info(f"Установлен часовой пояс: {self._selected_zone}")
            return ActionResult(True, None)
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при выборе других регионов: {str(e)}")
            return ActionResult(False, {"error": str(e)})

    def display(self):
        """
        Отображение окна выбора часового пояса.

        Возвращает:
        - ActionResult: Результат действия.
        """
        if self.logger is not None:
            self.logger.debug("Запуск отображения окна выбора часового пояса")
        try:
            result = self.window.do_action()
            if self.logger is not None:
                self.logger.info(f"Результат отображения: {result}")
            return result
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при отображении окна: {str(e)}")
            return ActionResult(False, {"error": str(e)})
