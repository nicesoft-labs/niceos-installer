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

        lines = [
            "\u0420\u0435\u0436\u0438\u043c \u0441\u0436\u0430\u0442\u0438\u044f (Compression)",
            "\u041f\u043e\u0437\u0432\u043e\u043b\u044f\u0435\u0442 \u0432\u043a\u043b\u044e\u0447\u0438\u0442\u044c \u0441\u0436\u0430\u0442\u0438\u0435 \u0434\u0430\u043d\u043d\u044b\u0445 \u043d\u0430 \u0443\u0440\u043e\u0432\u043d\u0435 \u0444\u0430\u0439\u043b\u043e\u0432\u043e\u0439 \u0441\u0438\u0441\u0442\u0435\u043c\u044b."
        ] + [desc for _n, desc in self.MODES]

        max_len = max(len(l) for l in lines)
        win_width = min(max_len + 4, maxx - 2)

        text_height = len(lines)
        win_height = min(text_height + 7, maxy - 2)
        
        win_starty = (maxy - win_height) // 2
        menu_starty = win_starty + text_height + 2

        menu_items = [
            (m[0], self._set_mode, m[0]) for m in self.MODES
        ]

        self.menu = Menu(menu_starty, maxx, menu_items,
                         default_selected=2, tab_enable=False)
        self.window = Window(win_height, win_width, maxy, maxx,
                             "\u0420\u0435\u0436\u0438\u043c \u0441\u0436\u0430\u0442\u0438\u044f", True,
                             self.menu, can_go_next=True)

        y = 0
        self.window.addstr(y, 0, lines[0])
        y += 2
        self.window.addstr(y, 0, lines[1])
        y += 2
        for desc in lines[2:]:
            self.window.addstr(y, 0, desc)
            y += 1

    def _set_mode(self, mode):
        self.selected = mode
        return ActionResult(True, None)

    def display(self):
        result = self.window.do_action()
        if result.success:
            return ActionResult(True, {"compress": self.selected})
        return result
