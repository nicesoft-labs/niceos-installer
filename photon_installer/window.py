#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
© 2025 ООО "НАЙС СОФТ ГРУПП" (ИНН 5024245440)
Контакты: <niceos@ncsgp.ru>
"""

import curses
import logging
from actionresult import ActionResult
from action import Action


class Window(Action):
    def __init__(self, height, width, maxy, maxx, title, can_go_back,
                 action_panel=None, items=None, menu_helper=None, position=0,
                 tab_enabled=True, can_go_next=False, read_text=False, logger=None):
        """
        Инициализация окна пользовательского интерфейса.

        Аргументы:
        - height (int): Высота окна.
        - width (int): Ширина окна.
        - maxy (int): Максимальная координата Y экрана.
        - maxx (int): Максимальная координата X экрана.
        - title (str): Заголовок окна.
        - can_go_back (bool): Разрешить кнопку "Назад".
        - action_panel (Action, optional): Панель действия (например, Menu).
        - items (list, optional): Список элементов меню (кортежи: текст, функция, аргумент).
        - menu_helper (callable, optional): Функция-обработчик для меню.
        - position (int): Начальная позиция выбора.
        - tab_enabled (bool): Разрешить навигацию клавишей Tab.
        - can_go_next (bool): Разрешить кнопку "Далее".
        - read_text (bool): Режим чтения текста.
        - logger (logging.Logger, optional): Логгер для записи событий.
        """
        super().__init__()
        self.logger = logger
        if self.logger is not None:
            self.logger.debug(f"Инициализация Window: height={height}, width={width}, maxy={maxy}, maxx={maxx}, "
                             f"title={title}, can_go_back={can_go_back}, can_go_next={can_go_next}, "
                             f"position={position}, tab_enabled={tab_enabled}, read_text={read_text}")

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
        if items is not None and (not isinstance(items, list) or
                                  not all(isinstance(item, tuple) and len(item) >= 2 for item in items)):
            if self.logger is not None:
                self.logger.error(f"Недопустимый список элементов: {items}")
            raise ValueError("items должен быть списком кортежей с минимум 2 элементами")
        if height > maxy or width > maxx:
            if self.logger is not None:
                self.logger.error(f"Размеры окна превышают экран: height={height}>maxy={maxy}, width={width}>maxx={maxx}")
            raise ValueError("Размеры окна не должны превышать размеры экрана")

        self.can_go_back = can_go_back
        self.can_go_next = can_go_next
        self.height = min(height, maxy - 2)  # Ограничение размеров окна
        self.width = min(width, maxx - 2)
        self.y = (maxy - self.height) // 2
        self.x = (maxx - self.width) // 2
        title = f' {title} '
        self.tab_enabled = tab_enabled
        self.read_text = read_text
        self.position = position
        self.items = items if items else []
        self.menu_helper = menu_helper
        self.action_panel = action_panel

        try:
            self.contentwin = curses.newwin(self.height - 1, self.width - 1)
            self.contentwin.bkgd(' ', curses.color_pair(2))
            self.contentwin.erase()
            self.contentwin.box()
            self.contentwin.addstr(0, (self.width - 1 - len(title)) // 2, title)
            self.contentwin.keypad(1)

            self.textwin = curses.newwin(self.height - 5, self.width - 5)
            self.textwin.bkgd(' ', curses.color_pair(2))

            self.shadowwin = curses.newwin(self.height - 1, self.width - 1)
            self.shadowwin.bkgd(' ', curses.color_pair(0))

            self.contentpanel = curses.panel.new_panel(self.contentwin)
            self.textpanel = curses.panel.new_panel(self.textwin)
            self.shadowpanel = curses.panel.new_panel(self.shadowwin)

            self.dist = 0
            if self.can_go_back:
                self.contentwin.addstr(self.height - 3, 5, '<Назад>')
            if self.can_go_next and self.can_go_back:
                self.update_next_item()

            if self.items:
                self.dist = self.width - 11 - len('<Назад>')
                count = len(self.items)
                for item in self.items:
                    self.dist -= len(item[0])
                self.dist = self.dist // (count + 1) if count > 0 else 0
                newy = 5 + len('<Назад>') + self.dist
                for item in self.items:
                    self.contentwin.addstr(self.height - 3, newy, item[0])
                    newy += len(item[0]) + self.dist

            self.hide_window()
            if self.logger is not None:
                self.logger.debug(f"Окно инициализировано: y={self.y}, x={self.x}, dist={self.dist}")
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при создании окна: {str(e)}")
            raise

    def update_next_item(self):
        """
        Добавление элемента "<Далее>" в меню.
        """
        if self.logger is not None:
            self.logger.debug("Добавление элемента <Далее>")
        self.position = 1
        self.items.append(('<Далее>', self.next_function, False))
        self.tab_enabled = False
        if self.logger is not None:
            self.logger.debug("Элемент <Далее> добавлен, tab_enabled=False")

    def next_function(self):
        """
        Обработка выбора "<Далее>".

        Возвращает:
        - ActionResult: Результат действия.
        """
        if self.logger is not None:
            self.logger.debug("Обработка выбора <Далее>")
        return ActionResult(True, None)

    def set_action_panel(self, action_panel):
        """
        Установка панели действия.

        Аргументы:
        - action_panel (Action): Панель действия (например, Menu).
        """
        if self.logger is not None:
            self.logger.debug(f"Установка панели действия: {action_panel}")
        self.action_panel = action_panel

    def update_menu(self, action_result):
        """
        Обновление меню на основе результата действия.

        Аргументы:
        - action_result (ActionResult): Результат действия от панели.

        Возвращает:
        - ActionResult: Результат действия.
        """
        if self.logger is not None:
            self.logger.debug(f"Обновление меню: action_result={action_result}")

        try:
            if action_result.result and 'goNext' in action_result.result and action_result.result['goNext']:
                if self.logger is not None:
                    self.logger.info("Переход вперед")
                return ActionResult(True, None)

            if self.position == 0:
                self.contentwin.addstr(self.height - 3, 5, '<Назад>')
                self.contentwin.refresh()
                self.hide_window()
                self.action_panel.hide()
                if self.logger is not None:
                    self.logger.info("Выбран <Назад>")
                return ActionResult(False, None)

            if action_result.result and 'diskIndex' in action_result.result:
                params = action_result.result['diskIndex']
                if self.menu_helper:
                    self.menu_helper(params)
                    if self.logger is not None:
                        self.logger.debug(f"Вызван menu_helper с параметрами: {params}")

            result = self.items[self.position - 1][1]()
            if result.success:
                self.hide_window()
                self.action_panel.hide()
                if self.logger is not None:
                    self.logger.info(f"Успешное выполнение действия: {result}")
                return result
            if 'goBack' in result.result and result.result['goBack']:
                self.contentwin.refresh()
                self.hide_window()
                self.action_panel.hide()
                if self.logger is not None:
                    self.logger.info("Возврат назад")
                return ActionResult(False, None)
            return result
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
                    self.logger.warning("Панель действия отсутствует")
                return ActionResult(False, {"error": "Панель действия не установлена"})

            action_result = self.action_panel.do_action()

            if action_result.success:
                if action_result.result and 'goNext' in action_result.result and action_result.result['goNext']:
                    if self.logger is not None:
                        self.logger.info("Переход вперед")
                    return ActionResult(True, None)
                if self.position != 0:
                    self.items[self.position - 1][1]()
                if self.items:
                    return self.update_menu(action_result)
                self.hide_window()
                if self.logger is not None:
                    self.logger.info(f"Результат действия: {action_result}")
                return action_result

            if not self.tab_enabled and action_result.result and 'direction' in action_result.result:
                self.refresh(action_result.result['direction'], True)
            if action_result.result and 'goBack' in action_result.result and action_result.result['goBack']:
                self.hide_window()
                self.action_panel.hide()
                if self.logger is not None:
                    self.logger.info("Возврат назад")
                return action_result

            while not action_result.success:
                if self.read_text:
                    is_go_back = self.position == 0
                    action_result = self.action_panel.do_action(returned=True, go_back=is_go_back)
                    if action_result.success:
                        if self.items:
                            return self.update_menu(action_result)
                        self.hide_window()
                        if self.logger is not None:
                            self.logger.info(f"Успешное выполнение действия: {action_result}")
                        return action_result
                    if action_result.result and 'goBack' in action_result.result and action_result.result['goBack']:
                        self.hide_window()
                        self.action_panel.hide()
                        if self.logger is not None:
                            self.logger.info("Возврат назад")
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
                                self.logger.info("Выбран <Назад>")
                            return ActionResult(False, None)
                        else:
                            if action_result.result and 'diskIndex' in action_result.result:
                                params = action_result.result['diskIndex']
                                if self.menu_helper:
                                    self.menu_helper(params)
                                    if self.logger is not None:
                                        self.logger.debug(f"Вызван menu_helper с параметрами: {params}")
                            result = self.items[self.position - 1][1]()
                            if result.success:
                                self.hide_window()
                                self.action_panel.hide()
                                if self.logger is not None:
                                    self.logger.info(f"Успешное выполнение действия: {result}")
                                return result
                            if 'goBack' in result.result and result.result['goBack']:
                                self.contentwin.refresh()
                                self.hide_window()
                                self.action_panel.hide()
                                if self.logger is not None:
                                    self.logger.info("Возврат назад")
                                return ActionResult(False, None)
                    elif key == ord('\t'):
                        if not self.tab_enabled:
                            continue
                        self.refresh(0, False)
                        action_result = self.action_panel.do_action()
                        if action_result.success:
                            self.hide_window()
                            if self.logger is not None:
                                self.logger.info(f"Успешное выполнение действия: {action_result}")
                            return action_result
                        self.refresh(0, True)
                    elif key in [curses.KEY_UP, curses.KEY_LEFT]:
                        if key == curses.KEY_UP and not self.tab_enabled:
                            self.action_panel.navigate(-1)
                            action_result = self.action_panel.do_action()
                            if action_result.success:
                                if self.items:
                                    return self.update_menu(action_result)
                                self.hide_window()
                                if self.logger is not None:
                                    self.logger.info(f"Успешное выполнение действия: {action_result}")
                                return action_result
                            if action_result.result and 'direction' in action_result.result:
                                self.refresh(action_result.result['direction'], True)
                        else:
                            self.refresh(-1, True)
                    elif key in [curses.KEY_DOWN, curses.KEY_RIGHT]:
                        if key == curses.KEY_DOWN and not self.tab_enabled:
                            self.action_panel.navigate(1)
                            action_result = self.action_panel.do_action()
                            if action_result.success:
                                if self.items:
                                    return self.update_menu(action_result)
                                self.hide_window()
                                if self.logger is not None:
                                    self.logger.info(f"Успешное выполнение действия: {action_result}")
                                return action_result
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
        - n (int): Смещение позиции (положительное — вниз, отрицательное — вверх).
        - select (bool): Флаг подсветки выбранного элемента.
        """
        if not self.can_go_back:
            if self.logger is not None:
                self.logger.debug("Обновление меню пропущено: can_go_back=False")
            return

        if self.logger is not None:
            self.logger.debug(f"Обновление меню: смещение={n}, select={select}")

        try:
            self.position += n
            if self.position < 0:
                self.position = 0
            elif self.items and self.position > len(self.items):
                self.position = len(self.items)
            if not self.items and not self.can_go_next:
                self.position = 0

            # Очистка строки кнопок
            self.contentwin.addstr(self.height - 2, 0, " " * (self.width - 1))

            # Размещение кнопок в нижней строке
            back_x = 5
            if self.can_go_back:
                mode = curses.color_pair(3) if self.position == 0 and select else curses.color_pair(1) if self.items else 0
                self.contentwin.addstr(self.height - 2, back_x, '<Назад>', mode)

            if self.can_go_next:
                next_x = self.width - 5 - len('<Далее>')
                if next_x > back_x + len('<Назад>') + 2:  # Проверка на пересечение
                    mode = curses.color_pair(3) if self.position == 1 and select else curses.color_pair(1)
                    self.contentwin.addstr(self.height - 2, next_x, '<Далее>', mode)

            # Обновление action_panel, если он существует
            if self.action_panel:
                self.action_panel.refresh()

            self.contentwin.refresh()
            if self.logger is not None:
                self.logger.debug(f"Меню обновлено: position={self.position}, back_x={back_x}, next_x={next_x}")
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
            self.shadowpanel.top()
            self.contentpanel.top()
            self.textpanel.top()
            self.shadowpanel.move(self.y + 1, self.x + 1)
            self.contentpanel.move(self.y, self.x)
            self.textpanel.move(self.y + 2, self.x + 2)
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
        - str (str): Добавляемая строка.
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
        Добавление сообщения об ошибке в текстовое окно.

        Аргументы:
        - str (str): Сообщение об ошибке.
        """
        if self.logger is not None:
            self.logger.debug(f"Добавление ошибки: {str}")

        try:
            self.textwin.addstr(self.height - 7, 0, str, curses.color_pair(4))
            self.textwin.refresh()
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при добавлении сообщения об ошибке: {str(e)}")
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
