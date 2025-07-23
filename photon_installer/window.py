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


class Window(Action):
    def __init__(self, height, width, maxy, maxx, title, can_go_back, action_panel=None, items=None,
                 menu_helper=None, position=0, tab_enabled=True, can_go_next=False, read_text=False, logger=None):
        """
        Инициализация окна пользовательского интерфейса.

        Аргументы:
        - height (int): Высота окна.
        - width (int): Ширина окна.
        - maxy (int): Максимальная координата Y экрана.
        - maxx (int): Максимальная координата X экрана.
        - title (str): Заголовок окна.
        - can_go_back (bool): Возможность возврата назад.
        - action_panel (object, optional): Панель действий (например, TextPane или Menu).
        - items (list, optional): Список элементов меню (кортежи с текстом и функцией).
        - menu_helper (callable, optional): Функция-обработчик для меню.
        - position (int): Начальная позиция выделения.
        - tab_enabled (bool): Разрешить навигацию клавишей Tab.
        - can_go_next (bool): Разрешить переход к следующей странице.
        - read_text (bool): Режим чтения текста.
        - logger (logging.Logger, optional): Логгер для записи событий. Если None, логирование не выполняется.
        """
        super().__init__()
        self.logger = logger
        if self.logger is not None:
            self.logger.debug(f"Инициализация Window: height={height}, width={width}, maxy={maxy}, maxx={maxx}, "
                             f"title={title}, can_go_back={can_go_back}, can_go_next={can_go_next}")

        # Проверка входных параметров
        if not isinstance(height, int) or not isinstance(width, int) or height <= 0 or width <= 0:
            if self.logger is not None:
                self.logger.error(f"Недопустимые размеры окна: height={height}, width={width}")
            raise ValueError("height и width должны быть положительными целыми числами")
        if not isinstance(maxy, int) or not isinstance(maxx, int) or maxy <= 0 or maxx <= 0:
            if self.logger is not None:
                self.logger.error(f"Недопустимые размеры экрана: maxy={maxy}, maxx={maxx}")
            raise ValueError("maxy и maxx должны быть положительными целыми числами")
        if not isinstance(title, str):
            if self.logger is not None:
                self.logger.error(f"Недопустимый заголовок: {title}")
            raise ValueError("title должен быть строкой")
        if items is not None and not isinstance(items, list):
            if self.logger is not None:
                self.logger.error(f"Недопустимый список элементов: {items}")
            raise ValueError("items должен быть списком или None")

        self.can_go_back = can_go_back
        self.can_go_next = can_go_next
        self.height = height
        self.width = width
        self.y = (maxy - height) // 2
        self.x = (maxx - width) // 2
        title = ' ' + title + ' '
        self.items = items if items else []
        self.menu_helper = menu_helper
        self.position = position
        self.tab_enabled = tab_enabled
        self.read_text = read_text

        try:
            self.contentwin = curses.newwin(height - 1, width - 1)
            self.contentwin.bkgd(' ', curses.color_pair(2))
            self.contentwin.erase()
            self.contentwin.box()
            self.contentwin.addstr(0, (width - 1 - len(title)) // 2, title)
            self.contentwin.keypad(1)
            if self.logger is not None:
                self.logger.debug("Окно contentwin инициализировано")

            self.textwin = curses.newwin(height - 5, width - 5)
            self.textwin.bkgd(' ', curses.color_pair(2))
            if self.logger is not None:
                self.logger.debug("Окно textwin инициализировано")

            self.shadowwin = curses.newwin(height - 1, width - 1)
            self.shadowwin.bkgd(' ', curses.color_pair(0))
            if self.logger is not None:
                self.logger.debug("Окно shadowwin инициализировано")

            self.contentpanel = curses.panel.new_panel(self.contentwin)
            self.textpanel = curses.panel.new_panel(self.textwin)
            self.shadowpanel = curses.panel.new_panel(self.shadowwin)
            if self.logger is not None:
                self.logger.debug("Панели contentpanel, textpanel, shadowpanel созданы")

            self.action_panel = action_panel
            self.dist = 0
            newy = 5

            if self.can_go_back:
                self.contentwin.addstr(height - 3, 5, '<Назад>')
                newy += len('<Назад>')
            if self.can_go_next and self.can_go_back:
                self.update_next_item()

            if self.items:
                self.dist = self.width - 11 - len('<Назад>')
                count = len(self.items)
                for item in self.items:
                    self.dist -= len(item[0])
                self.dist = self.dist // count if count > 0 else 0
                newy += self.dist
                for item in self.items:
                    self.contentwin.addstr(height - 3, newy, item[0])
                    newy += len(item[0]) + self.dist
                if self.logger is not None:
                    self.logger.debug(f"Создано меню с {len(self.items)} элементами, dist={self.dist}")
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при инициализации окна: {str(e)}")
            raise

        # Hide window after initialization to match previous behavior
        self.hide_window()
    
    def update_next_item(self):
        """
        Добавление элемента '<Далее>' в меню.
        """
        if self.logger is not None:
            self.logger.debug("Добавление элемента '<Далее>'")
        self.position = 1
        self.items.append(('<Далее>', self.next_function, False))
        self.tab_enabled = False
        if self.logger is not None:
            self.logger.debug("Элемент '<Далее>' добавлен, tab_enabled=False")

    def next_function(self):
        """
        Обработка действия перехода вперед.

        Возвращает:
        - ActionResult: Результат действия.
        """
        if self.logger is not None:
            self.logger.info("Пользователь выбрал '<Далее>'")
        return ActionResult(True, None)

    def set_action_panel(self, action_panel):
        """
        Установка панели действий.

        Аргументы:
        - action_panel (object): Панель действий (например, TextPane или Menu).
        """
        if self.logger is not None:
            self.logger.debug(f"Установка панели действий: {action_panel}")
        self.action_panel = action_panel

    def update_menu(self, action_result):
        """
        Обновление меню на основе результата действия.

        Аргументы:
        - action_result (ActionResult): Результат предыдущего действия.

        Возвращает:
        - ActionResult: Результат обработки меню.
        """
        if self.logger is not None:
            self.logger.debug(f"Обновление меню: action_result={action_result}")

        try:
            if action_result.result and 'goNext' in action_result.result and action_result.result['goNext']:
                if self.logger is not None:
                    self.logger.info("Переход вперед по goNext")
                return ActionResult(True, None)

            if self.position == 0:
                self.contentwin.addstr(self.height - 3, 5, '<Назад>')
                self.contentwin.refresh()
                self.hide_window()
                if self.action_panel:
                    self.action_panel.hide()
                if self.logger is not None:
                    self.logger.info("Пользователь выбрал '<Назад>'")
                return ActionResult(False, None)

            if action_result.result and 'diskIndex' in action_result.result:
                params = action_result.result['diskIndex']
                if self.menu_helper:
                    if self.logger is not None:
                        self.logger.debug(f"Вызов menu_helper с параметрами: {params}")
                    self.menu_helper(params)

            result = self.items[self.position - 1][1]()
            if result.success:
                self.hide_window()
                if self.action_panel:
                    self.action_panel.hide()
                if self.logger is not None:
                    self.logger.info(f"Успешное выполнение действия: {result}")
                return result
            else:
                if 'goBack' in result.result and result.result['goBack']:
                    self.contentwin.refresh()
                    self.hide_window()
                    if self.action_panel:
                        self.action_panel.hide()
                    if self.logger is not None:
                        self.logger.info("Возврат назад по goBack")
                    return ActionResult(False, None)
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при обновлении меню: {str(e)}")
            return ActionResult(False, {"error": str(e)})

    def do_action(self):
        """
        Выполнение действия окна.

        Возвращает:
        - ActionResult: Результат действия.
        """
        if self.logger is not None:
            self.logger.debug("Запуск метода do_action")

        try:
            self.show_window()
            if self.tab_enabled:
                self.refresh(0, False)
            else:
                self.refresh(0, True)

            if not self.action_panel:
                if self.logger is not None:
                    self.logger.warning("action_panel не установлен")
                return ActionResult(False, {"error": "action_panel не установлен"})

            action_result = self.action_panel.do_action()
            if self.logger is not None:
                self.logger.debug(f"Результат action_panel.do_action: {action_result}")

            if action_result.success:
                if action_result.result and 'goNext' in action_result.result and action_result.result['goNext']:
                    if self.logger is not None:
                        self.logger.info("Переход вперед по goNext")
                    return ActionResult(True, None)
                if self.position != 0:
                    self.items[self.position - 1][1]()
                if self.items:
                    return self.update_menu(action_result)
                self.hide_window()
                if self.logger is not None:
                    self.logger.info(f"Действие успешно, результат: {action_result}")
                return action_result
            else:
                if not self.tab_enabled and action_result.result and 'direction' in action_result.result:
                    self.refresh(action_result.result['direction'], True)
                if action_result.result and 'goBack' in action_result.result and action_result.result['goBack']:
                    self.hide_window()
                    self.action_panel.hide()
                    if self.logger is not None:
                        self.logger.info("Возврат назад по goBack")
                    return action_result
                else:
                    self.refresh(0, True)

            while not action_result.success:
                if self.read_text:
                    is_go_back = self.position == 0
                    action_result = self.action_panel.do_action(returned=True, go_back=is_go_back)
                    if self.logger is not None:
                        self.logger.debug(f"Результат action_panel.do_action (read_text): {action_result}")
                    if action_result.success:
                        if self.items:
                            return self.update_menu(action_result)
                        self.hide_window()
                        if self.logger is not None:
                            self.logger.info(f"Действие успешно (read_text): {action_result}")
                        return action_result
                    else:
                        if action_result.result and 'goBack' in action_result.result and action_result.result['goBack']:
                            self.hide_window()
                            self.action_panel.hide()
                            if self.logger is not None:
                                self.logger.info("Возврат назад по goBack (read_text)")
                            return action_result
                        if action_result.result and 'direction' in action_result.result:
                            self.refresh(action_result.result['direction'], True)
                else:
                    key = self.contentwin.getch()
                    if self.logger is not None:
                        self.logger.debug(f"Получена клавиша: {key}")
                    if key in [curses.KEY_ENTER, ord('\n')]:
                        if self.position == 0:
                            self.contentwin.addstr(self.height - 3, 5, '<Назад>')
                            self.contentwin.refresh()
                            self.hide_window()
                            self.action_panel.hide()
                            if self.logger is not None:
                                self.logger.info("Пользователь выбрал '<Назад>'")
                            return ActionResult(False, None)
                        else:
                            if action_result.result and 'diskIndex' in action_result.result:
                                params = action_result.result['diskIndex']
                                if self.menu_helper:
                                    if self.logger is not None:
                                        self.logger.debug(f"Вызов menu_helper с параметрами: {params}")
                                    self.menu_helper(params)
                            result = self.items[self.position - 1][1]()
                            if result.success:
                                self.hide_window()
                                self.action_panel.hide()
                                if self.logger is not None:
                                    self.logger.info(f"Успешное выполнение действия: {result}")
                                return result
                            else:
                                if 'goBack' in result.result and result.result['goBack']:
                                    self.contentwin.refresh()
                                    self.hide_window()
                                    self.action_panel.hide()
                                    if self.logger is not None:
                                        self.logger.info("Возврат назад по goBack")
                                    return ActionResult(False, None)
                    elif key == ord('\t'):
                        if not self.tab_enabled:
                            continue
                        self.refresh(0, False)
                        action_result = self.action_panel.do_action()
                        if self.logger is not None:
                            self.logger.debug(f"Результат action_panel.do_action (Tab): {action_result}")
                        if action_result.success:
                            self.hide_window()
                            if self.logger is not None:
                                self.logger.info(f"Действие успешно (Tab): {action_result}")
                            return action_result
                        else:
                            self.refresh(0, True)
                    elif key in [curses.KEY_UP, curses.KEY_LEFT]:
                        if key == curses.KEY_UP and not self.tab_enabled:
                            self.action_panel.navigate(-1)
                            action_result = self.action_panel.do_action()
                            if self.logger is not None:
                                self.logger.debug(f"Результат action_panel.do_action (Up): {action_result}")
                            if action_result.success:
                                if self.items:
                                    return self.update_menu(action_result)
                                self.hide_window()
                                if self.logger is not None:
                                    self.logger.info(f"Действие успешно (Up): {action_result}")
                                return action_result
                            else:
                                if action_result.result and 'direction' in action_result.result:
                                    self.refresh(action_result.result['direction'], True)
                        else:
                            self.refresh(-1, True)
                    elif key in [curses.KEY_DOWN, curses.KEY_RIGHT]:
                        if key == curses.KEY_DOWN and not self.tab_enabled:
                            self.action_panel.navigate(1)
                            action_result = self.action_panel.do_action()
                            if self.logger is not None:
                                self.logger.debug(f"Результат action_panel.do_action (Down): {action_result}")
                            if action_result.success:
                                if self.items:
                                    return self.update_menu(action_result)
                                self.hide_window()
                                if self.logger is not None:
                                    self.logger.info(f"Действие успешно (Down): {action_result}")
                                return action_result
                            else:
                                if action_result.result and 'direction' in action_result.result:
                                    self.refresh(action_result.result['direction'], True)
                        else:
                            self.refresh(1, True)
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка в do_action: {str(e)}")
            return ActionResult(False, {"error": str(e)})

    def refresh(self, n, select):
        """
        Обновление отображения меню.

        Аргументы:
        - n (int): Смещение позиции выделения.
        - select (bool): Флаг выделения элемента.
        """
        if self.logger is not None:
            self.logger.debug(f"Обновление меню: n={n}, select={select}")

        try:                
            self.position += n
            if self.can_go_back:
                if self.position < 0:
                    self.position = 0
                elif self.items and self.position > len(self.items):
                    self.position = len(self.items)
            else:
                if self.position < 0:
                    self.position = 0
                elif self.items and self.position >= len(self.items):
                    self.position = len(self.items) - 1 if self.items else 0

            if not self.items and not self.can_go_next:
                self.position = 0

            newy = 5
            if self.can_go_back:
                if self.position == 0:
                    if select:
                        self.contentwin.addstr(self.height - 3, 5, '<Назад>', curses.color_pair(3))
                    elif self.items:
                        self.contentwin.addstr(self.height - 3, 5, '<Назад>', curses.color_pair(1))
                    else:
                        self.contentwin.addstr(self.height - 3, 5, '<Назад>')
                    newy += len('<Назад>') + self.dist
                    if self.items:
                        for item in self.items:
                            self.contentwin.addstr(self.height - 3, newy, item[0])
                            newy += len(item[0]) + self.dist
                else:
                    self.contentwin.addstr(self.height - 3, 5, '<Назад>')
                    newy += len('<Назад>') + self.dist
                    index = 1
                    for item in self.items:
                        if index == self.position and select:
                            self.contentwin.addstr(self.height - 3, newy, item[0], curses.color_pair(3))
                        else:
                            self.contentwin.addstr(self.height - 3, newy, item[0], curses.color_pair(1) if self.items else 0)
                        newy += len(item[0]) + self.dist
                        index += 1
                        newy += len(item[0]) + self.dist
            else:
                index = 0
                for item in self.items:
                    if index == self.position and select:
                        self.contentwin.addstr(self.height - 3, newy, item[0], curses.color_pair(3))
                    else:
                        self.contentwin.addstr(self.height - 3, newy, item[0], curses.color_pair(1) if self.items else 0)
                    newy += len(item[0]) + self.dist
                    index += 1

            self.contentwin.refresh()
            if self.logger is not None:
                self.logger.debug(f"Меню обновлено: position={self.position}")
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при обновлении меню: {str(e)}")
            raise

    def show_window(self):
        """
        Отображение окна.
        """
        if self.logger is not None:
            self.logger.debug("Отображение окна")

        try:
            y, x = self.y, self.x
            self.shadowpanel.top()
            self.contentpanel.top()
            self.textpanel.top()
            self.shadowpanel.move(y + 1, x + 1)
            self.contentpanel.move(y, x)
            self.textpanel.move(y + 2, x + 2)
            self.shadowpanel.show()
            self.contentpanel.show()
            self.textpanel.show()
            curses.panel.update_panels()
            curses.doupdate()
            if self.can_go_next:
                self.position = 1
            if self.logger is not None:
                self.logger.debug("Окно отображено")
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при отображении окна: {str(e)}")
            raise

    def hide_window(self):
        """
        Скрытие окна.
        """
        if self.logger is not None:
            self.logger.debug("Скрытие окна")

        try:
            self.shadowpanel.hide()
            self.contentpanel.hide()
            self.textpanel.hide()
            curses.panel.update_panels()
            curses.doupdate()
            if self.logger is not None:
                self.logger.debug("Окно скрыто")
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при скрытии окна: {str(e)}")
            raise

    def addstr(self, y, x, str, mode=0):
        """
        Добавление строки в текстовое окно.

        Аргументы:
        - y (int): Координата Y.
        - x (int): Координата X.
        - str (str): Строка для добавления.
        - mode (int): Режим отображения (цвет).
        """
        if self.logger is not None:
            self.logger.debug(f"Добавление строки: y={y}, x={x}, str={str}, mode={mode}")
        try:
            self.textwin.addstr(y, x, str, mode)
            self.textwin.refresh()
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при добавлении строки: {str(e)}")
            raise

    def adderror(self, str):
        """
        Добавление сообщения об ошибке.

        Аргументы:
        - str (str): Сообщение об ошибке.
        """
        if self.logger is not None:
            self.logger.warning(f"Отображение ошибки: {str}")
        try:
            self.textwin.addstr(self.height - 7, 0, str, curses.color_pair(4))
            self.textwin.refresh()
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при отображении ошибки: {str(e)}")
            raise

    def clearerror(self):
        """
        Очистка сообщения об ошибке.
        """
        if self.logger is not None:
            self.logger.debug("Очистка сообщения об ошибке")
        try:
            spaces = ' ' * (self.width - 6)
            self.textwin.addstr(self.height - 7, 0, spaces)
            self.textwin.refresh()
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при очистке сообщения об ошибке: {str(e)}")
            raise

    def content_window(self):
        """
        Получение текстового окна.

        Возвращает:
        - curses.window: Текстовое окно.
        """
        if self.logger is not None:
            self.logger.debug("Получение текстового окна")
        return self.textwin
