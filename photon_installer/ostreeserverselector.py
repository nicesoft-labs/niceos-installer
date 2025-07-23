#!/usr/bin/python2
#/*
# * Copyright © 2020 VMware, Inc.
# * SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only
# */
#
#    Author: Mahmoud Bassiouny <mbassiouny@vmware.com>

import json
import os
import curses
from jsonwrapper import JsonWrapper
from menu import Menu
from window import Window
from actionresult import ActionResult

class OSTreeServerSelector(object):
    def __init__(self, maxy, maxx, install_config, logger=None):
        """
        Инициализация выбора OSTree сервера.

        Аргументы:
        - maxy, maxx: размеры экрана
        - install_config: конфигурация установки
        - logger (optional): объект логгера
        """
        self.logger = logger
        self.install_config = install_config

        if self.logger:
            self.logger.debug("Инициализация OSTreeServerSelector")

        win_width = 50
        win_height = 12
        win_starty = (maxy - win_height) // 2
        win_startx = (maxx - win_width) // 2
        menu_starty = win_starty + 3

        ostree_host_menu_items = [
            ("Default RPM-OSTree Server", self.set_default_repo_installation, True),
            ("Custom RPM-OSTree Server", self.set_default_repo_installation, False)
        ]

        host_menu = Menu(
            menu_starty, maxx, ostree_host_menu_items,
            default_selected=0, tab_enable=False,
            logger=self.logger
        )

        self.window = Window(
            win_height, win_width, maxy, maxx,
            'Select OSTree Server',
            True, host_menu,
            can_go_next=True,
            logger=self.logger
        )

    def set_default_repo_installation(self, is_default_repo):
        """
        Обработка выбора сервера.

        Аргументы:
        - is_default_repo (bool): использовать ли сервер по умолчанию

        Возвращает:
        - ActionResult
        """
        if self.logger:
            self.logger.info(f"Выбран OSTree сервер: {'default' if is_default_repo else 'custom'}")
        self.install_config['ostree']['default_repo'] = is_default_repo
        return ActionResult(True, None)

    def display(self):
        """
        Отображение экрана выбора OSTree сервера.

        Возвращает:
        - ActionResult
        """
        if self.logger:
            self.logger.debug("Отображение окна выбора OSTree сервера")
        if 'ostree' in self.install_config:
            return self.window.do_action()
        return ActionResult(True, None)
