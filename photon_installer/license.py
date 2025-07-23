# /*
# * Copyright © 2020 VMware, Inc.
# * SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only
# */
#
#    Author: Mahmoud Bassiouny <mbassiouny@vmware.com>

import os
import logging
from window import Window
from actionresult import ActionResult
from textpane import TextPane
from os.path import join, dirname


class License(object):
    def __init__(self, maxy, maxx, eula_file_path, display_title, logger=None):
        """
        Инициализация окна лицензионного соглашения.

        Аргументы:
        - maxy (int): Максимальная координата Y экрана.
        - maxx (int): Максимальная координата X экрана.
        - eula_file_path (str): Путь к файлу лицензионного соглашения.
        - display_title (str): Заголовок лицензии.
        - logger (logging.Logger, optional): Логгер для записи событий.
        """
        self.logger = logger
        if self.logger is not None:
            self.logger.debug(f"Инициализация License: maxy={maxy}, maxx={maxx}, "
                             f"eula_file_path={eula_file_path}, display_title={display_title}")

        self.maxx = maxx
        self.maxy = maxy
        self.win_width = maxx - 4
        self.win_height = maxy - 4
        self.win_starty = (self.maxy - self.win_height) // 2
        self.win_startx = (self.maxx - self.win_width) // 2
        self.text_starty = self.win_starty + 4
        self.text_height = self.win_height - 6
        self.text_width = self.win_width - 6

        try:
            self.window = Window(self.win_height, self.win_width, self.maxy, self.maxx,
                                'Добро пожаловать в установщик Photon', False, logger=self.logger)
            if self.logger is not None:
                self.logger.debug("Окно инициализировано")
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при создании окна: {str(e)}")
            raise

        self.eula_file_path = eula_file_path if eula_file_path else join(dirname(__file__), 'EULA.txt')
        self.title = display_title if display_title else 'ЛИЦЕНЗИОННОЕ СОГЛАШЕНИЕ VMWARE'

    def display(self):
        """
        Отображение окна лицензионного соглашения.

        Возвращает:
        - ActionResult: Результат действия.
        """
        if self.logger is not None:
            self.logger.debug("Запуск отображения окна лицензии")

        try:
            accept_decline_items = [('<Принять>', self.accept_function),
                                    ('<Отменить>', self.exit_function)]
            self.window.addstr(0, (self.win_width - len(self.title)) // 2, self.title)
            self.text_pane = TextPane(self.text_starty, self.maxx, self.text_width,
                                      self.eula_file_path, self.text_height, accept_decline_items,
                                      logger=self.logger)
            self.window.set_action_panel(self.text_pane)
            result = self.window.do_action()
            if self.logger is not None:
                self.logger.info(f"Результат отображения лицензии: {result}")
            return result
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при отображении окна: {str(e)}")
            return ActionResult(False, {"error": str(e)})

    def accept_function(self):
        """
        Обработка принятия лицензии.

        Возвращает:
        - ActionResult: Результат действия.
        """
        if self.logger is not None:
            self.logger.info("Лицензия принята")
        return ActionResult(True, None)

    def exit_function(self):
        """
        Обработка отмены лицензии.

        Возвращает:
        - ActionResult: Результат действия.
        """
        if self.logger is not None:
            self.logger.info("Лицензия отклонена, выход")
        return ActionResult(False, {"exit": True})
