#/*
# * Copyright © 2024 VMware, Inc.
# * SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only
# */

"""Simple selector window to choose filesystem type."""

from menu import Menu
from window import Window
from actionresult import ActionResult


class FilesystemSelector(object):
    """Present user with a menu to select a filesystem type."""

    FS_TYPES = ["ext3", "ext4", "xfs", "btrfs", "swap"]

    def __init__(self, maxy, maxx):
        self.maxy = maxy
        self.maxx = maxx
        self.selected_fs = None

        win_width = 40
        win_height = 12
        win_starty = (maxy - win_height) // 2
        menu_starty = win_starty + 3

        menu_items = [
            (fs, self._set_fs, fs) for fs in self.FS_TYPES
        ]

        self.menu = Menu(menu_starty, maxx, menu_items,
                         default_selected=0, tab_enable=False)
        self.window = Window(win_height, win_width, maxy, maxx,
                             "Select filesystem", True, self.menu,
                             can_go_next=True)

    def _set_fs(self, fs):
        self.selected_fs = fs
        return ActionResult(True, None)

    def display(self):
        result = self.window.do_action()
        if result.success:
            return ActionResult(True, {"filesystem": self.selected_fs})
        return result
