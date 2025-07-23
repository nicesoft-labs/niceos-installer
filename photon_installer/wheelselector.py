#/*
# * Copyright © 2024 VMware, Inc.
# * SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only
# */

from menu import Menu
from window import Window
from actionresult import ActionResult

class WheelSelector(object):
    def __init__(self, maxy, maxx, install_config):
        self.install_config = install_config
        win_width = 50
        win_height = 12

        win_starty = (maxy - win_height) // 2
        menu_starty = win_starty + 3

        menu_items = [
            ("No", self.set_wheel, False),
            ("Yes", self.set_wheel, True)
        ]

        menu = Menu(menu_starty, maxx, menu_items, default_selected=0, tab_enable=False)
        self.window = Window(win_height, win_width, maxy, maxx,
                             "Add user to wheel group", True, menu, can_go_next=True)

    def set_wheel(self, is_enabled):
        self.install_config['user_wheel'] = is_enabled
        return ActionResult(True, None)

    def display(self):
        return self.window.do_action()
