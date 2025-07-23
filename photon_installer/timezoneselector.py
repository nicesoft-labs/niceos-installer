#/*
# * Copyright © 2024 VMware, Inc.
# * SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only
# */

import os
from zoneinfo import available_timezones

from menu import Menu
from window import Window
from actionresult import ActionResult


class TimezoneSelector(object):
    def __init__(self, maxy, maxx, install_config):
        self.install_config = install_config
        self.maxx = maxx
        self.maxy = maxy
        self.win_width = 60
        self.win_height = 15

        self.win_starty = (self.maxy - self.win_height) // 2
        self.menu_starty = self.win_starty + 3

        self._load_timezones()
        self._selected_group = None
        self._selected_zone = None
        self.default_zone = "Europe/Moscow"

        self._create_main_menu()

    def _load_timezones(self):
        self.ru_zones = []
        self.grouped_zones = {}
        zone_tab = "/usr/share/zoneinfo/zone.tab"
        if os.path.exists(zone_tab):
            with open(zone_tab, "rt", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("#") or line.strip() == "":
                        continue
                    fields = line.split()
                    if len(fields) < 3:
                        continue
                    country = fields[0]
                    zone = fields[2]
                    if country == "RU":
                        self.ru_zones.append(zone)
                    region = zone.split("/")[0]
                    self.grouped_zones.setdefault(region, []).append(zone)
        else:
            zones = available_timezones()
            for z in zones:
                region = z.split("/")[0]
                self.grouped_zones.setdefault(region, []).append(z)
                if z.startswith("Europe/") or z.startswith("Asia/"):
                    if "Moscow" in z or "Volgograd" in z or "Irkutsk" in z:
                        pass
        for k in self.grouped_zones:
            self.grouped_zones[k] = sorted(self.grouped_zones[k])
        self.ru_zones = sorted(self.ru_zones)

    def _create_main_menu(self):
        menu_items = []
        for tz in self.ru_zones:
            menu_items.append((tz, self._set_timezone, tz))
        menu_items.append(("Other regions...", self._other_timezones, None))
        default_selected = 0
        if self.default_zone in self.ru_zones:
            default_selected = self.ru_zones.index(self.default_zone)
        self.menu = Menu(self.menu_starty, self.maxx, menu_items,
                         default_selected=default_selected, tab_enable=False)
        self.window = Window(self.win_height, self.win_width, self.maxy, self.maxx,
                             "Select Timezone", True, self.menu,
                             can_go_next=True, position=1)
        self.install_config["timezone"] = self.default_zone

    def _set_timezone(self, timezone):
        self.install_config["timezone"] = timezone
        return ActionResult(True, None)

    def _select_group(self, group):
        self._selected_group = group
        return ActionResult(True, None)

    def _select_zone(self, zone):
        self._selected_zone = zone
        return ActionResult(True, None)

    def _other_timezones(self, _):
        groups = sorted(self.grouped_zones.keys())
        group_items = [(g, self._select_group, g) for g in groups]
        group_menu = Menu(self.menu_starty, self.maxx, group_items,
                          default_selected=0, tab_enable=False)
        group_window = Window(self.win_height, self.win_width, self.maxy, self.maxx,
                              "Select Region", True, group_menu,
                              can_go_next=True, position=1)
        ar = group_window.do_action()
        if not ar.success:
            return ActionResult(False, {"goBack": True})
        zones = self.grouped_zones[self._selected_group]
        zone_items = [(z, self._select_zone, z) for z in zones]
        zone_menu = Menu(self.menu_starty, self.maxx, zone_items,
                         default_selected=0, tab_enable=False)
        zone_window = Window(self.win_height, self.win_width, self.maxy, self.maxx,
                             "Select Timezone", True, zone_menu,
                             can_go_next=True, position=1)
        ar = zone_window.do_action()
        if not ar.success:
            return ActionResult(False, {"goBack": True})
        self.install_config["timezone"] = self._selected_zone
        return ActionResult(True, None)

    def display(self):
        return self.window.do_action()
