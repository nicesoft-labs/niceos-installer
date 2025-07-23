#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
© 2025 ООО "НАЙС СОФТ ГРУПП" (ИНН 5024245440)
Контакты: <niceos@ncsgp.ru>
"""

import curses
import curses.panel
import logging
from actionresult import ActionResult
from action import Action


class Menu(Action):
    def __init__(self, starty, maxx, items, height=0, selector_menu=False,
                 can_navigate_outside=True, horizontal=False, default_selected=0,
                 save_sel=False, tab_enable=True, logger=None):
        """
        Инициализация меню пользовательского интерфейса.

        Аргументы:
        - starty (int): Начальная координата Y меню.
        - maxx (int): Максимальная координата X экрана.
        - items (list): Список элементов меню (кортежи: текст, функция, аргумент).
        - height (int): Высота меню (0 для автоопределения).
        - selector_menu (bool): Режим селекторного меню (множественный выбор).
        - can_navigate_outside (bool): Разрешить навигацию за пределы меню.
        - horizontal (bool): Горизонтальное отображение меню.
        - default_selected (int): Индекс элемента по умолчанию.
        - save_sel (bool): Сохранять выбор при навигации.
        - tab_enable (bool): Разрешить навигацию клавишей Tab.
        - logger (logging.Logger, optional): Логгер для записи событий. Если None, логирование не выполняется.
        """
        super().__init__()
        self.logger = logger
        if self.logger is not None:
            self.logger.debug(f"Инициализация Menu: starty={starty}, maxx={maxx}, items_count={len(items)}, "
                             f"height={height}, selector_menu={selector_menu}, can_navigate_outside={can_navigate_outside}, "
                             f"horizontal={horizontal}, default_selected={default_selected}, save_sel={save_sel}, "
                             f"tab_enable={tab_enable}")

        # Проверка входных параметров
        if not isinstance(starty, int) or starty < 0:
            if self.logger is not None:
                self.logger.error(f"Недопустимая начальная координата Y: {starty}")
            raise ValueError("starty должен быть неотрицательным целым числом")
        if not isinstance(maxx, int) or maxx <= 0:
            if self.logger is not None:
                self.logger.error(f"Недопустимая максимальная ширина: {maxx}")
            raise ValueError("maxx должен быть положительным целым числом")
        if not isinstance(items, list) or not items:
            if self.logger is not None:
                self.logger.error(f"Недопустимый список элементов: {items}")
            raise ValueError("items должен быть непустым списком")
        if not all(isinstance(item, tuple) and len(item) >= 2 for item in items):
            if self.logger is not None:
                self.logger.error("Элементы меню должны быть кортежами с минимум 2 элементами (текст, функция)")
            raise ValueError("Каждый элемент меню должен быть кортежем с текстом и функцией")
        if not isinstance(height, int) or height < 0:
            if self.logger is not None:
                self.logger.error(f"Недопустимая высота меню: {height}")
            raise ValueError("height должен быть неотрицательным целым числом")
        if not isinstance(default_selected, int) or default_selected < 0 or default_selected >= len(items):
            if self.logger is not None:
                self.logger.error(f"Недопустимый default_selected: {default_selected}")
            raise ValueError("default_selected должен быть в пределах количества элементов")

        self.can_navigate_outside = can_navigate_outside
        self.horizontal = horizontal
        self.horizontal_padding = 10
        self.position = default_selected
        self.head_position = 0  # Начальная позиция прокрутки
        self.items = items
        self.items_strings = []
        self.num_items = len(self.items)
        self.save_sel = save_sel
        self.tab_enable = tab_enable

        # Установка высоты меню
        if height == 0 or height > self.num_items:
            self.height = self.num_items
        else:
            self.height = height

        try:
            self.width = self.lengthen_items()
            if self.logger is not None:
                self.logger.debug(f"Рассчитана ширина меню: {self.width}")

            # Проверка необходимости полосы прокрутки
            self.show_scroll = self.num_items > self.height
            if self.show_scroll:
                self.width += 2
                if self.logger is not None:
                    self.logger.debug("Добавлена полоса прокрутки")

            # Расчет заполненной части полосы прокрутки
            self.filled = int(round(self.height * self.height / float(self.num_items)))
            if self.filled == 0:
                self.filled += 1
            for i in [1, 2]:
                if (self.num_items - self.height) >= i and (self.height - self.filled) == (i - 1):
                    self.filled -= 1
            if self.logger is not None:
                self.logger.debug(f"Рассчитана заполненная часть полосы прокрутки: filled={self.filled}")

            # Увеличение ширины для селекторного меню
            self.selector_menu = selector_menu
            if self.selector_menu:
                self.width += 4
                self.selected_items = set([])
                if self.logger is not None:
                    self.logger.debug("Включен режим селекторного меню")

            # Расчет ширины окна меню
            menu_win_width = (self.width + self.horizontal_padding) * self.num_items if self.horizontal else self.width

            self.window = curses.newwin(self.height, menu_win_width)
            self.window.bkgd(' ', curses.color_pair(2))
            self.window.keypad(1)
            self.panel = curses.panel.new_panel(self.window)
            self.panel.move(starty, (maxx - menu_win_width) // 2)
            self.panel.hide()
            curses.panel.update_panels()
            if self.logger is not None:
                self.logger.debug(f"Создано окно меню: height={self.height}, width={menu_win_width}")
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при инициализации меню: {str(e)}")
            raise

    def can_save_sel(self, can_save_sel):
        """
        Установка флага сохранения выбора.

        Аргументы:
        - can_save_sel (bool): Флаг сохранения выбора.
        """
        if self.logger is not None:
            self.logger.debug(f"Установка save_sel={can_save_sel}")
        self.save_sel = can_save_sel

    def lengthen_items(self):
        """
        Выравнивание элементов меню по максимальной длине.

        Возвращает:
        - int: Ширина меню (максимальная длина элемента + 1).
        """
        if self.logger is not None:
            self.logger.debug("Выравнивание элементов меню")
        width = 0
        for item in self.items:
            if len(item[0]) > width:
                width = len(item[0])

        self.items_strings = []
        for item in self.items:
            spaces = ' ' * (width - len(item[0]))
            self.items_strings.append(item[0] + spaces)
        if self.logger is not None:
            self.logger.debug(f"Выровнено {len(self.items_strings)} элементов, ширина={width + 1}")
        return width + 1

    def navigate(self, n):
        """
        Навигация по меню.

        Аргументы:
        - n (int): Смещение позиции (положительное — вниз, отрицательное — вверх).
        """
        if self.logger is not None:
            self.logger.debug(f"Навигация: смещение={n}, текущая позиция={self.position}")

        try:
            self.position += n
            if self.position < 0:
                self.position = 0
            elif self.position >= len(self.items):
                self.position = len(self.items) - 1

            if self.position >= self.head_position + self.height:
                self.head_position = self.position - self.height + 1
            if self.position < self.head_position:
                self.head_position = self.position
            if self.logger is not None:
                self.logger.debug(f"Новая позиция={self.position}, head_position={self.head_position}")
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при навигации: {str(e)}")
            raise

    def render_scroll_bar(self):
        """
        Рендеринг полосы прокрутки.
        """
        if not self.show_scroll:
            return
        if self.logger is not None:
            self.logger.debug("Рендеринг полосы прокрутки")

        try:
            remaining_above = self.head_position
            remaining_down = self.num_items - self.height - self.head_position
            up = int(round(remaining_above * self.height / float(self.num_items)))
            down = self.height - up - self.filled

            if up == 0 and remaining_above > 0:
                up += 1
                down -= 1
            if down == 0 and remaining_down > 0:
                up -= 1
                down += 1
            if remaining_down == 0 and down != 0:
                up += down
                down = 0

            for index in range(up):
                self.window.addch(index, self.width - 2, curses.ACS_CKBOARD)
            for index in range(self.filled):
                self.window.addstr(index + up, self.width - 2, ' ', curses.A_REVERSE)
            for index in range(down):
                self.window.addch(index + up + self.filled, self.width - 2, curses.ACS_CKBOARD)
            if self.logger is not None:
                self.logger.debug(f"Полоса прокрутки отрендерена: up={up}, filled={self.filled}, down={down}")
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при рендеринге полосы прокрутки: {str(e)}")
            raise

    def refresh(self, highlight=True):
        """
        Обновление отображения меню.

        Аргументы:
        - highlight (bool): Флаг подсветки выбранного элемента.
        """
        if self.logger is not None:
            self.logger.debug(f"Обновление меню: highlight={highlight}")

        try:
            self.window.clear()
            for index, item in enumerate(self.items_strings):
                if index < self.head_position or index > self.head_position + self.height - 1:
                    continue
                mode = curses.color_pair(3) if index == self.position and highlight else curses.color_pair(2)
                display_item = item
                if self.selector_menu:
                    display_item = '[x] ' + item if index in self.selected_items else '[ ] ' + item
                x = self.horizontal_padding // 2 + index * (self.width + self.horizontal_padding) if self.horizontal else 0
                y = 0 if self.horizontal else index - self.head_position
                self.window.addstr(y, x, display_item, mode)

            self.render_scroll_bar()
            self.window.refresh()
            self.panel.top()
            self.panel.show()
            curses.panel.update_panels()
            curses.doupdate()
            if self.logger is not None:
                self.logger.debug("Меню обновлено")
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при обновлении меню: {str(e)}")
            raise

    def hide(self):
        """
        Скрытие меню.
        """
        if self.logger is not None:
            self.logger.debug("Скрытие меню")
        try:
            self.panel.hide()
            curses.panel.update_panels()
            curses.doupdate()
            if self.logger is not None:
                self.logger.debug("Меню скрыто")
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при скрытии меню: {str(e)}")
            raise

    def do_action(self):
        """
        Выполнение действия меню.

        Возвращает:
        - ActionResult: Результат действия.
        """
        if self.logger is not None:
            self.logger.debug("Запуск метода do_action")

        try:
            while True:
                self.refresh()
                key = self.window.getch()
                if self.logger is not None:
                    self.logger.debug(f"Получена клавиша: {key}")

                if key in [curses.KEY_ENTER, ord('\n')]:
                    if self.selector_menu:
                        result = self.items[self.position][1](self.selected_items)
                    else:
                        result = self.items[self.position][1](self.items[self.position][2])
                    if self.logger is not None:
                        self.logger.info(f"Выполнено действие: {result}")
                    if result.success:
                        self.hide()
                        return result

                if key == ord(' ') and self.selector_menu:
                    if self.position in self.selected_items:
                        self.selected_items.remove(self.position)
                        if self.logger is not None:
                            self.logger.debug(f"Снят выбор с элемента: {self.position}")
                    else:
                        self.selected_items.add(self.position)
                        if self.logger is not None:
                            self.logger.debug(f"Выбран элемент: {self.position}")
                    continue

                if key == ord('\t') and self.can_navigate_outside:
                    if not self.tab_enable:
                        continue
                    self.refresh(False)
                    if self.logger is not None:
                        self.logger.debug("Навигация по Tab")
                    if self.save_sel:
                        return ActionResult(False, {'diskIndex': self.position})
                    return ActionResult(False, None)

                if key in [curses.KEY_UP, curses.KEY_LEFT]:
                    if not self.tab_enable and key == curses.KEY_LEFT:
                        if self.logger is not None:
                            self.logger.debug("Навигация влево")
                        if self.save_sel:
                            return ActionResult(False, {'diskIndex': self.position, 'direction': -1})
                        elif self.selector_menu:
                            result = self.items[self.position][1](self.selected_items)
                        else:
                            result = self.items[self.position][1](self.items[self.position][2])
                        return ActionResult(False, {'direction': -1})
                    self.navigate(-1)

                elif key in [curses.KEY_DOWN, curses.KEY_RIGHT]:
                    if not self.tab_enable and key == curses.KEY_RIGHT:
                        if self.logger is not None:
                            self.logger.debug("Навигация вправо")
                        if self.save_sel:
                            return ActionResult(False, {'diskIndex': self.position, 'direction': 1})
                        return ActionResult(False, {'direction': 1})
                    self.navigate(1)

                elif key == curses.KEY_NPAGE:
                    if self.logger is not None:
                        self.logger.debug("Навигация Page Down")
                    self.navigate(self.height)

                elif key == curses.KEY_PPAGE:
                    if self.logger is not None:
                        self.logger.debug("Навигация Page Up")
                    self.navigate(-self.height)

                elif key == curses.KEY_HOME:
                    if self.logger is not None:
                        self.logger.debug("Навигация Home")
                    self.navigate(-self.position)
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка в do_action: {str(e)}")
            return ActionResult(False, {"error": str(e)})
