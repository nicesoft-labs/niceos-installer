# /*
# * Copyright © 2020 VMware, Inc.
# * SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only
# */
#
#    Author: Mahmoud Bassiouny <mbassiouny@vmware.com>

import curses
import logging
from actionresult import ActionResult
from action import Action


class TextPane(Action):
    def __init__(self, starty, maxx, width, text_file_path, height, menu_items, logger=None):
        """
        Инициализация панели текстового отображения.

        Аргументы:
        - starty (int): Начальная координата Y панели.
        - maxx (int): Максимальная координата X экрана.
        - width (int): Ширина панели.
        - text_file_path (str): Путь к файлу с текстом.
        - height (int): Высота панели.
        - menu_items (list): Список элементов меню (кортежи: текст, функция).
        - logger (logging.Logger, optional): Логгер для записи событий.
        """
        self.logger = logger
        if self.logger is not None:
            self.logger.debug(f"Инициализация TextPane: starty={starty}, maxx={maxx}, width={width}, "
                             f"text_file_path={text_file_path}, height={height}, menu_items={menu_items}")

        # Проверка входных параметров
        if not isinstance(starty, int) or not isinstance(maxx, int) or starty < 0 or maxx <= 0:
            if self.logger is not None:
                self.logger.error(f"Недопустимые координаты: starty={starty}, maxx={maxx}")
            raise ValueError("starty должен быть неотрицательным, maxx — положительным целым числом")
        if not isinstance(width, int) or not isinstance(height, int) or width <= 0 or height <= 0:
            if self.logger is not None:
                self.logger.error(f"Недопустимые размеры: width={width}, height={height}")
            raise ValueError("width и height должны быть положительными целыми числами")
        if not isinstance(text_file_path, str) or not os.path.isfile(text_file_path):
            if self.logger is not None:
                self.logger.error(f"Недопустимый или несуществующий файл: {text_file_path}")
            raise ValueError("text_file_path должен быть существующим файлом")
        if not isinstance(menu_items, list) or not all(isinstance(item, tuple) and len(item) >= 2 for item in menu_items):
            if self.logger is not None:
                self.logger.error(f"Недопустимый список элементов меню: {menu_items}")
            raise ValueError("menu_items должен быть списком кортежей с минимум 2 элементами")

        self.head_position = 0
        self.menu_position = 0
        self.lines = []
        self.menu_items = menu_items
        self.width = width
        self.text_height = height - 2

        try:
            self.read_file(text_file_path, self.width - 3)
            self.num_items = len(self.lines)

            self.show_scroll = self.num_items > self.text_height
            self.filled = int(round(self.text_height * self.text_height / float(self.num_items))) if self.num_items > 0 else 0
            if self.filled == 0 and self.num_items > 0:
                self.filled = 1
            for i in [1, 2]:
                if (self.num_items - self.text_height) >= i and (self.text_height - self.filled) == (i - 1):
                    self.filled -= 1

            self.window = curses.newwin(height, self.width)
            self.window.bkgd(' ', curses.color_pair(2))
            self.popupWindow = False
            self.window.keypad(1)
            self.panel = curses.panel.new_panel(self.window)
            self.panel.move(starty, (maxx - self.width) // 2)
            self.panel.hide()
            curses.panel.update_panels()
            if self.logger is not None:
                self.logger.debug(f"TextPane инициализирован: num_items={self.num_items}, show_scroll={self.show_scroll}")
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при создании TextPane: {str(e)}")
            raise

    def read_file(self, text_file_path, line_width):
        """
        Чтение и форматирование текста из файла.

        Аргументы:
        - text_file_path (str): Путь к файлу.
        - line_width (int): Максимальная ширина строки.
        """
        if self.logger is not None:
            self.logger.debug(f"Чтение файла: {text_file_path}, line_width={line_width}")

        try:
            with open(text_file_path, "rb") as f:
                for line in f:
                    try:
                        line = line.decode(encoding='latin1')
                    except UnicodeDecodeError as e:
                        if self.logger is not None:
                            self.logger.warning(f"Ошибка декодирования строки, используется latin1: {str(e)}")
                        continue
                    line = line.expandtabs(8)
                    indent = len(line) - len(line.lstrip())
                    actual_line_width = max(line_width - indent, 1)
                    line = line.strip()

                    while len(line) > actual_line_width:
                        sep_index = actual_line_width
                        while sep_index > 0 and line[sep_index-1] != ' ' and line[sep_index] != ' ':
                            sep_index -= 1
                        current_line_width = sep_index if sep_index > 0 else actual_line_width
                        currLine = line[:current_line_width]
                        line = line[current_line_width:].strip()
                        self.lines.append(' ' * indent + currLine + ' ' * (actual_line_width - len(currLine)))

                    self.lines.append(' ' * indent + line + ' ' * (actual_line_width - len(line)))
            if not self.lines:
                if self.logger is not None:
                    self.logger.warning(f"Файл {text_file_path} пуст")
                self.lines.append(" " * line_width)
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при чтении файла {text_file_path}: {str(e)}")
            raise

    def navigate(self, n):
        """
        Навигация по тексту (прокрутка).

        Аргументы:
        - n (int): Смещение (положительное — вниз, отрицательное — вверх).
        """
        if self.logger is not None:
            self.logger.debug(f"Навигация по тексту: смещение={n}")

        if self.show_scroll:
            self.head_position += n
            if self.head_position < 0:
                self.head_position = 0
            elif self.head_position > (len(self.lines) - self.text_height + 1):
                self.head_position = len(self.lines) - self.text_height + 1
            if self.logger is not None:
                self.logger.debug(f"Новая позиция head_position: {self.head_position}")

    def navigate_menu(self, n):
        """
        Навигация по меню.

        Аргументы:
        - n (int): Смещение (положительное — влево, отрицательное — вправо).
        """
        if self.logger is not None:
            self.logger.debug(f"Навигация по меню: смещение={n}")

        self.menu_position += n
        if self.menu_position < 0:
            self.menu_position = 0
        elif self.menu_position >= len(self.menu_items):
            self.menu_position = len(self.menu_items) - 1
        if self.logger is not None:
            self.logger.debug(f"Новая позиция menu_position: {self.menu_position}")

    def render_scroll_bar(self):
        """
        Отрисовка полосы прокрутки.
        """
        if self.logger is not None:
            self.logger.debug("Отрисовка полосы прокрутки")

        try:
            if self.show_scroll:
                remaining_above = self.head_position
                remaining_down = self.num_items - self.text_height - self.head_position
                up = int(round(remaining_above * self.text_height / float(self.num_items)))
                down = self.text_height - up - self.filled

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
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при отрисовке полосы прокрутки: {str(e)}")
            raise

    def refresh(self):
        """
        Обновление отображения панели.
        """
        if self.logger is not None:
            self.logger.debug("Обновление TextPane")

        try:
            self.window.erase()
            for index, line in enumerate(self.lines):
                if index < self.head_position or index > self.head_position + self.text_height - 1:
                    continue
                self.window.addstr(index - self.head_position, 0, line)

            xpos = self.width
            for index, item in enumerate(self.menu_items):
                mode = curses.color_pair(3) if index == self.menu_position else curses.color_pair(2)
                self.window.addstr(self.text_height + 1, xpos - len(item[0]) - 4, item[0], mode)
                xpos -= len(item[0]) + 4

            self.render_scroll_bar()
            self.window.refresh()
            self.panel.top()
            self.panel.show()
            curses.panel.update_panels()
            curses.doupdate()
            if self.logger is not None:
                self.logger.debug("TextPane обновлен")
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при обновлении TextPane: {str(e)}")
            raise

    def hide(self):
        """
        Скрытие панели.
        """
        if self.logger is not None:
            self.logger.debug("Скрытие TextPane")

        try:
            self.panel.hide()
            curses.panel.update_panels()
            curses.doupdate()
            if self.logger is not None:
                self.logger.debug("TextPane скрыт")
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при скрытии TextPane: {str(e)}")
            raise

    def do_action(self):
        """
        Выполнение действия панели.

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
                    self.hide()
                    result = self.menu_items[self.menu_position][1]()
                    if self.logger is not None:
                        self.logger.info(f"Выбрано действие: {self.menu_items[self.menu_position][0]}, результат: {result}")
                    return result
                elif key == curses.KEY_UP:
                    self.navigate(-1)
                elif key == curses.KEY_DOWN:
                    self.navigate(1)
                elif key == curses.KEY_LEFT:
                    self.navigate_menu(1)
                elif key == curses.KEY_RIGHT:
                    self.navigate_menu(-1)
                elif key == curses.KEY_NPAGE:
                    self.navigate(self.text_height)
                elif key == curses.KEY_PPAGE:
                    self.navigate(-self.text_height)
                elif key == curses.KEY_HOME:
                    self.head_position = 0
                    if self.logger is not None:
                        self.logger.debug("Переход к началу текста")
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка в do_action: {str(e)}")
            return ActionResult(False, {"error": str(e)})
