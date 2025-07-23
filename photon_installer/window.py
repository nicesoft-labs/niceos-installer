#/*
# * Copyright © 2020 VMware, Inc.
# * SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only
# */
#
# Автор: Mahmoud Bassiouny <mbassiouny@vmware.com>
# Описание: Класс Window для создания и управления окном интерфейса с использованием библиотеки curses.

import curses
from typing import Optional, List, Callable, Tuple, Dict, Any
from actionresult import ActionResult
from action import Action


class Window(Action):
    """Класс для создания и управления окном пользовательского интерфейса."""

    def __init__(
        self,
        height: int,
        width: int,
        maxy: int,
        maxx: int,
        title: str,
        can_go_back: bool,
        action_panel: Optional[Any] = None,
        items: Optional[List[Tuple[str, Callable, Any]]] = None,
        menu_helper: Optional[Callable] = None,
        position: int = 0,
        tab_enabled: bool = True,
        can_go_next: bool = False,
        read_text: bool = False,
        logger: Optional[Any] = None,
        help_text: str = "Справка пока недоступна",
        help_url: Optional[str] = None,
    ):
        """Инициализация окна с заданными параметрами."""
        self.can_go_back = can_go_back
        self.can_go_next = can_go_next
        self.height = height
        self.width = width
        self.maxy = maxy
        self.maxx = maxx
        self.y = (maxy - height) // 2
        self.x = (maxx - width) // 2
        self.title = f" {title} "
        self.position = position
        self.tab_enabled = tab_enabled
        self.read_text = read_text
        self.action_panel = action_panel
        self.items = items if items else []
        self.menu_helper = menu_helper
        self.help_text = help_text
        self.help_url = help_url
        self.logger = logger

        # Создание окна содержимого
        self.contentwin = curses.newwin(height - 1, width - 1)
        self.contentwin.bkgd(" ", curses.color_pair(2))  # Цвет фона окна (светлый)
        self.contentwin.erase()
        self.contentwin.box()
        self.contentwin.keypad(True)
        self.contentwin.addstr(0, (width - 1 - len(self.title)) // 2, self.title)

        # Создание текстового окна
        self.textwin = curses.newwin(height - 5, width - 5)
        self.textwin.bkgd(" ", curses.color_pair(2))  # Цвет фона текстового окна

        # Создание тени окна
        self.shadowwin = curses.newwin(height - 1, width - 1)
        self.shadowwin.bkgd(" ", curses.color_pair(0))  # Цвет тени

        # Создание панелей
        self.contentpanel = curses.panel.new_panel(self.contentwin)
        self.textpanel = curses.panel.new_panel(self.textwin)
        self.shadowpanel = curses.panel.new_panel(self.shadowwin)

        self._setup_menu()
        self.hide_window()

    def _setup_menu(self) -> None:
        """Настройка меню с элементами и кнопкой 'Назад'."""
        if self.can_go_back:
            self.contentwin.addstr(self.height - 3, 5, "<Назад>")

        if self.can_go_next and self.can_go_back:
            self.update_next_item()

        self.dist = 0
        if self.items:
            self.dist = self.width - 11 - len("<Назад>")
            self.dist -= sum(len(item[0]) for item in self.items)
            self.dist //= len(self.items)

            newy = 5 + len("<Назад>") + self.dist
            for item in self.items:
                self.contentwin.addstr(self.height - 3, newy, item[0])
                newy += len(item[0]) + self.dist

    def update_next_item(self) -> None:
        """Добавление элемента 'Далее' в меню."""
        self.position = 1
        self.items.append(("<Далее>", self.next_function, False))
        self.tab_enabled = False

    def next_function(self) -> ActionResult:
        """Функция для обработки действия 'Далее'."""
        return ActionResult(True, None)

    def set_action_panel(self, action_panel: Any) -> None:
        """Установка панели действий."""
        self.action_panel = action_panel
        if hasattr(self.action_panel, "set_help_callback"):
            self.action_panel.set_help_callback(self.show_help)

    def update_menu(self, action_result: ActionResult) -> ActionResult:
        """Обновление меню на основе результата действия."""
        if action_result.result and action_result.result.get("goNext"):
            return ActionResult(True, None)

        if self.position == 0:
            self.contentwin.addstr(self.height - 3, 5, "<Назад>")
            self.contentwin.refresh()
            self.hide_window()
            self.action_panel.hide()
            return ActionResult(False, None)

        if action_result.result and "diskIndex" in action_result.result:
            params = action_result.result["diskIndex"]
            if self.menu_helper:
                self.menu_helper(params)

        result = self.items[self.position - 1][1]()
        if result.success:
            self.hide_window()
            self.action_panel.hide()
            return result

        if result.result and result.result.get("goBack"):
            self.contentwin.refresh()
            self.hide_window()
            self.action_panel.hide()
            return ActionResult(False, None)

    def do_action(self) -> ActionResult:
        """Выполнение действия окна и обработка пользовательского ввода."""
        self.show_window()
        self.refresh(0, not self.tab_enabled)
        action_result = self.action_panel.do_action()

        if action_result.success:
            if action_result.result and action_result.result.get("goNext"):
                return ActionResult(True, None)
            if self.position != 0:
                self.items[self.position - 1][1]()
            if self.items:
                return self.update_menu(action_result)
            self.hide_window()
            return action_result

        if not self.tab_enabled and action_result.result and "direction" in action_result.result:
            self.refresh(action_result.result["direction"], True)
        if action_result.result and action_result.result.get("goBack"):
            self.hide_window()
            self.action_panel.hide()
            return action_result

        while not action_result.success:
            if self.read_text:
                is_go_back = self.position == 0
                action_result = self.action_panel.do_action(returned=True, go_back=is_go_back)
                if action_result.success:
                    if self.items:
                        return self.update_menu(action_result)
                    self.hide_window()
                    return action_result
                if action_result.result and action_result.result.get("goBack"):
                    self.hide_window()
                    self.action_panel.hide()
                    return action_result
                if action_result.result and "direction" in action_result.result:
                    self.refresh(action_result.result["direction"], True)
            else:
                key = self.contentwin.getch()
                if key == curses.KEY_F1:
                    self.show_help()
                    continue
                if key in (curses.KEY_ENTER, ord("\n")):
                    if self.position == 0:
                        self.contentwin.addstr(self.height - 3, 5, "<Назад>")
                        self.contentwin.refresh()
                        self.hide_window()
                        self.action_panel.hide()
                        return ActionResult(False, None)
                    if action_result.result and "diskIndex" in action_result.result:
                        params = action_result.result["diskIndex"]
                        if self.menu_helper:
                            self.menu_helper(params)
                    result = self.items[self.position - 1][1]()
                    if result.success:
                        self.hide_window()
                        self.action_panel.hide()
                        return result
                    if result.result and result.result.get("goBack"):
                        self.contentwin.refresh()
                        self.hide_window()
                        self.action_panel.hide()
                        return ActionResult(False, None)
                elif key == ord("\t"):
                    if not self.tab_enabled:
                        continue
                    self.refresh(0, False)
                    action_result = self.action_panel.do_action()
                    if action_result.success:
                        self.hide_window()
                        return action_result
                    self.refresh(0, True)
                elif key in (curses.KEY_UP, curses.KEY_LEFT):
                    if key == curses.KEY_UP and not self.tab_enabled:
                        self.action_panel.navigate(-1)
                        action_result = self.action_panel.do_action()
                        if action_result.success:
                            if self.items:
                                return self.update_menu(action_result)
                            self.hide_window()
                            return action_result
                        if action_result.result and "direction" in action_result.result:
                            self.refresh(action_result.result["direction"], True)
                    else:
                        self.refresh(-1, True)
                elif key in (curses.KEY_DOWN, curses.KEY_RIGHT):
                    if key == curses.KEY_DOWN and not self.tab_enabled:
                        self.action_panel.navigate(1)
                        action_result = self.action_panel.do_action()
                        if action_result.success:
                            if self.items:
                                return self.update_menu(action_result)
                            self.hide_window()
                            return action_result
                        if action_result.result and "direction" in action_result.result:
                            self.refresh(action_result.result["direction"], True)
                    else:
                        self.refresh(1, True)

    def refresh(self, direction: int, select: bool) -> None:
        """Обновление отображения меню с учетом выделения."""
        if not self.can_go_back:
            return

        self.position += direction
        self.position = max(0, min(self.position, len(self.items) if self.items else 0))

        newy = 5
        if self.position == 0:
            color = curses.color_pair(3) if select else curses.color_pair(1) if self.items else 0
            self.contentwin.addstr(self.height - 3, 5, "<Назад>", color)
            newy += len("<Назад>") + self.dist
            for item in self.items:
                self.contentwin.addstr(self.height - 3, newy, item[0])
                newy += len(item[0]) + self.dist
        else:
            self.contentwin.addstr(self.height - 3, 5, "<Назад>")
            newy += len("<Назад>") + self.dist
            for index, item in enumerate(self.items, 1):
                color = curses.color_pair(3) if select and index == self.position else curses.color_pair(1) if index == self.position else 0
                self.contentwin.addstr(self.height - 3, newy, item[0], color)
                newy += len(item[0]) + self.dist

        self.contentwin.refresh()

    def show_window(self) -> None:
        """Отображение окна и его панелей."""
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

    def hide_window(self) -> None:
        """Скрытие окна и его панелей."""
        self.shadowpanel.hide()
        self.contentpanel.hide()
        self.textpanel.hide()
        curses.panel.update_panels()
        curses.doupdate()

    def addstr(self, y: int, x: int, text: str, mode: int = 0) -> None:
        """Добавление текста в текстовое окно."""
        self.textwin.addstr(y, x, text, mode)

    def adderror(self, text: str) -> None:
        """Отображение сообщения об ошибке."""
        self.textwin.addstr(self.height - 7, 0, text, curses.color_pair(4))
        self.textwin.refresh()

    def clearerror(self) -> None:
        """Очистка сообщения об ошибке."""
        spaces = " " * (self.width - 6)
        self.textwin.addstr(self.height - 7, 0, spaces)
        self.textwin.refresh()

    def content_window(self) -> Any:
        """Возвращает окно содержимого."""
        return self.textwin

    def show_help(self) -> None:
        """Отобразить окно справки с тенью и улучшенным цветом."""
        lines = self.help_text.splitlines()

        # Рассчет размеров окна справки
        text_width = max((len(line) for line in lines), default=0)
        width = min(max(40, text_width) + 4, self.maxx - 2)
        height = min(max(7, len(lines) + 4), self.maxy - 2)
        starty = max(0, (self.maxy - height) // 2)
        startx = max(0, (self.maxx - width) // 2)

        # Проверка допустимости размеров
        if width <= 0 or height <= 0 or starty + height > self.maxy or startx + width > self.maxx:
            if self.logger:
                self.logger.error(
                    f"Недопустимые размеры окна справки: "
                    f"width={width}, height={height}, starty={starty}, startx={startx}, "
                    f"maxy={self.maxy}, maxx={self.maxx}"
                )
            self.adderror("Ошибка: Невозможно отобразить справку из-за ограничений терминала")
            return

        try:
            # Инициализация цветовой пары для окна справки, если поддерживаются цвета
            if curses.has_colors():
                try:
                    curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLUE)  # Белый текст на синем фоне
                    help_color = curses.color_pair(5)
                except curses.error:
                    if self.logger:
                        self.logger.warning("Не удалось инициализировать цветовую пару для окна справки, используется стандартный цвет")
                    help_color = curses.color_pair(2)  # Фallback на цвет основного окна
            else:
                help_color = curses.color_pair(2)  # Fallback, если цвета не поддерживаются

            # Создание окна справки
            helpwin = curses.newwin(height, width, starty, startx)
            helppanel = curses.panel.new_panel(helpwin)
            helpwin.bkgd(' ', help_color)  # Темно-синий фон с белым текстом
            helpwin.box()
            title = ' Справка '
            helpwin.addstr(0, (width - len(title)) // 2, title, curses.color_pair(3))  # Яркий заголовок

            # Создание тени для окна справки
            help_shadowwin = curses.newwin(height, width, starty + 1, startx + 1)
            help_shadowpanel = curses.panel.new_panel(help_shadowwin)
            help_shadowwin.bkgd(' ', curses.color_pair(0))  # Цвет тени (темный)

            # Добавление текста справки
            for idx, line in enumerate(lines):
                if idx + 2 < height - 2:
                    helpwin.addstr(2 + idx, 2, line[:width - 4], curses.color_pair(5))

            # Добавление кнопки OK
            helpwin.addstr(height - 2, (width - len('<OK>')) // 2, '<OK>', curses.color_pair(3))

            # Отображение панелей (тень внизу, затем окно справки)
            help_shadowpanel.top()
            helppanel.top()
            help_shadowpanel.show()
            helppanel.show()
            curses.panel.update_panels()
            curses.doupdate()

            # Ожидание ввода пользователя
            helpwin.getch()

            # Скрытие окон
            helppanel.hide()
            help_shadowpanel.hide()
            curses.panel.update_panels()
            curses.doupdate()

        except curses.error as e:
            if self.logger:
                self.logger.error(f"Ошибка создания окна справки или тени: {e}")
            self.adderror("Ошибка: Не удалось отобразить окно справки")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Неожиданная ошибка в show_help: {e}")
            self.adderror("Ошибка: Не удалось отобразить окно справки")

    def __del__(self) -> None:
        """Очистка ресурсов окна."""
        self.hide_window()
