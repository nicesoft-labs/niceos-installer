#/*
# * Copyright © 2024 VMware, Inc.
# * SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only
# */
"""Selector window to choose BTRFS compression mode."""

from menu import Menu
from window import Window
from actionresult import ActionResult


class BtrfsCompressionSelector(object):
    """Show menu to choose BTRFS compression algorithm."""

    MODES = [
        ("zlib",
         "zlib: \u043a\u043b\u0430\u0441\u0441\u0438\u0447\u0435\u0441\u043a\u0438\u0439, \u0445\u043e\u0440\u043e\u0448\u043e \u0441\u0436\u0438\u043c\u0430\u0435\u0442, \u043d\u043e \u043c\u0435\u0434\u043b\u0435\u043d\u043d\u0435\u0435."),
        ("lzo",
         "lzo: \u0431\u044b\u0441\u0442\u0440\u044b\u0439, \u043d\u043e \u0441\u0436\u0438\u043c\u0430\u0435\u0442 \u0441\u043b\u0430\u0431\u0435\u0435."),
        ("zstd",
         "zstd: \u0445\u043e\u0440\u043e\u0448\u0438\u0439 \u043a\u043e\u043c\u043f\u0440\u043e\u043c\u0438\u0441\u0441 \u043c\u0435\u0436\u0434\u0443 \u0441\u043a\u043e\u0440\u043e\u0441\u0442\u044c\u044e \u0438 \u0443\u0440\u043e\u0432\u043d\u0435\u043c \u0441\u0436\u0430\u0442\u0438\u044f. \u0420\u0435\u043a\u043e\u043c\u0435\u043d\u0434\u0443\u0435\u0442\u0441\u044f \u043f\u043e \u0443\u043c\u043e\u043b\u0447\u0430\u043d\u0438\u044e.")
    ]

    def __init__(self, maxy, maxx):
        self.maxy = maxy
        self.maxx = maxx
        self.selected = None

        win_width = 70
        win_height = 35
        win_starty = (maxy - win_height) // 2
        menu_starty = win_starty + 8

        menu_items = [
            (m[0], self._set_mode, m[0]) for m in self.MODES
        ]

        self.menu = Menu(menu_starty, maxx, menu_items,
                         default_selected=2, tab_enable=False)
        self.window = Window(win_height, win_width, maxy, maxx,
                             "\u0420\u0435\u0436\u0438\u043c \u0441\u0436\u0430\u0442\u0438\u044f", True,
                             self.menu, can_go_next=True)

        self.window.addstr(0, 0,
            "\u0420\u0435\u0436\u0438\u043c \u0441\u0436\u0430\u0442\u0438\u044f (Compression)")
        self.window.addstr(2, 0,
            "\u041f\u043e\u0437\u0432\u043e\u043b\u044f\u0435\u0442 \u0432\u043a\u043b\u044e\u0447\u0438\u0442\u044c \u0441\u0436\u0430\u0442\u0438\u0435 \u0434\u0430\u043d\u043d\u044b\u0445 \u043d\u0430 \u0443\u0440\u043e\u0432\u043d\u0435 \u0444\u0430\u0439\u043b\u043e\u0432\u043e\u0439 \u0441\u0438\u0441\u0442\u0435\u043c\u044b.")
        for idx, (_name, desc) in enumerate(self.MODES, start=4):
            self.window.addstr(idx, 0, desc)

    def _set_mode(self, mode):
        self.selected = mode
        return ActionResult(True, None)

    def display(self):
        result = self.window.do_action()
        if result.success:
            return ActionResult(True, {"compress": self.selected})
        return result
