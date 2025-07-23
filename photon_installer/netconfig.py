#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
© 2025 ООО "НАЙС СОФТ ГРУПП" (ИНН 5024245440)
Контакты: <niceos@ncsgp.ru>
"""

import secrets
from typing import Optional, Tuple, List, Dict
from networkmanager import NetworkManager
from menu import Menu
from window import Window
from windowstringreader import WindowStringReader
from readmultext import ReadMulText
from actionresult import ActionResult

class NetworkConfigure:
    """Класс для настройки сетевых параметров."""

    # Опции конфигурации сети
    NET_CONFIG_OPTION_DHCP = 0
    NET_CONFIG_OPTION_DHCP_HOSTNAME = 1
    NET_CONFIG_OPTION_MANUAL = 2
    NET_CONFIG_OPTION_VLAN = 3

    NET_CONFIG_OPTION_STRINGS = [
        "Настроить сеть автоматически",
        "Настроить сеть автоматически с именем хоста DHCP",
        "Настроить сеть вручную",
        "Настроить сеть с использованием VLAN",
    ]

    VLAN_READ_STRING = (
        'Виртуальные локальные сети IEEE 802.1Q (VLAN) позволяют разделять физическую сеть '
        'на отдельные широковещательные домены. Пакеты могут быть помечены различными '
        'идентификаторами VLAN, что позволяет использовать одну "магистральную" линию '
        'для передачи данных для разных VLAN.\n'
        '\n'
        'Если сетевой интерфейс напрямую подключен к магистральному порту VLAN,\n'
        'указание идентификатора VLAN может быть необходимо для рабочего соединения.\n'
        '\n'
        'Идентификатор VLAN (1-4094): '
    )

    def __init__(self, maxy: int, maxx: int, install_config: Dict, logger=None):
        self.logger = logger
        self.maxx = maxx
        self.maxy = maxy
        self.win_width = 80
        self.win_height = 13
        self.win_starty = (self.maxy - self.win_height) // 2
        self.win_startx = (self.maxx - self.win_width) // 2
        self.menu_starty = self.win_starty + 3
        self.package_menu_items = []
        self.install_config = install_config
        self.install_config['network'] = {}

        # Создание элементов меню
        for opt in self.NET_CONFIG_OPTION_STRINGS:
            self.package_menu_items.append((opt, self._exit_function, [opt]))
        self.package_menu = Menu(
            self.menu_starty,
            self.maxx,
            self.package_menu_items,
            default_selected=0,
            tab_enable=False
        )
        self.window = Window(
            self.win_height,
            self.win_width,
            self.maxy,
            self.maxx,
            'Настройка сети',
            True,
            action_panel=self.package_menu,
            can_go_next=True,
            position=1
        )

    @staticmethod
    def validate_hostname(hostname: Optional[str]) -> Tuple[bool, Optional[str]]:
        """Валидация имени хоста."""
        if not hostname:
            return False, "Пустое имя хоста или домена не допускается"

        fields = hostname.split('.')
        for field in fields:
            if not field:
                return False, "Пустое имя хоста или домена не допускается"
            if field[0] == '-' or field[-1] == '-':
                return False, "Имя хоста или домен не должны начинаться или заканчиваться '-'"

        machinename = fields[0]
        if len(machinename) > 64 or not machinename[0].isalpha():
            return False, "Имя хоста должно начинаться с буквы и быть не длиннее 64 символов"

        return True, None

    @staticmethod
    def validate_ipaddr(ip: Optional[str], can_have_cidr: bool = False) -> Tuple[bool, Optional[str]]:
        """Валидация IP-адреса."""
        if not ip:
            return False, "IP-адрес не может быть пустым"

        cidr = None
        if can_have_cidr and '/' in ip:
            ip, cidr = ip.split('/')

        octets = ip.split('.')
        if len(octets) != 4:
            return False, "Недействительный IP; должен быть в формате: xxx.xxx.xxx.xxx"

        for octet in octets:
            if not octet or not octet.isdigit() or not (0 <= int(octet) <= 255):
                return False, "Недействительный IP; число должно быть в диапазоне (0 <= x <= 255)"

        if cidr is not None:
            if not cidr.isdigit() or not (0 < int(cidr) < 32):
                return False, "Недействительный номер CIDR!"

        return True, None

    def validate_static_conf(self, vals: List[str]) -> Tuple[bool, Optional[str]]:
        """Валидация статической конфигурации."""
        for val in vals:
            res, msg = self.validate_ipaddr(val)
            if not res:
                return res, msg
        return True, None

    @staticmethod
    def validate_vlan_id(vlan_id: Optional[str]) -> Tuple[bool, Optional[str]]:
        """Валидация идентификатора VLAN."""
        if not vlan_id:
            return False, 'Пустой идентификатор VLAN не допускается!'

        try:
            vlan_num = int(vlan_id)
            if not (1 <= vlan_num <= 4094):
                return False, 'Некорректный идентификатор VLAN! Число должно быть в диапазоне (1 <= x <= 4094)'
        except ValueError:
            return False, 'Некорректный идентификатор VLAN! Требуется число'

        return True, None

    def _exit_function(self, selected_item_params: List[str]) -> ActionResult:
        """Обработка выбора опции конфигурации сети."""
        selection = self.NET_CONFIG_OPTION_STRINGS.index(selected_item_params[0])

        if selection == self.NET_CONFIG_OPTION_DHCP:
            self.install_config['network']['type'] = 'dhcp'

        elif selection == self.NET_CONFIG_OPTION_DHCP_HOSTNAME:
            network_config = {}
            random_id = f'{secrets.randbelow(16**12):12x}'.strip()
            random_hostname = f'niceos-{random_id}'
            accepted_chars = (
                list(range(ord('A'), ord('Z') + 1)) +
                list(range(ord('a'), ord('z') + 1)) +
                list(range(ord('0'), ord('9') + 1)) +
                [ord('.'), ord('-')]
            )
            result = WindowStringReader(
                self.maxy, self.maxx, 13, 80, 'hostname', None, None,
                accepted_chars, self.validate_hostname, None,
                'Выберите имя хоста DHCP для вашей системы',
                'Имя хоста DHCP:', 2, network_config, random_hostname, True
            ).get_user_string(None)
            if not result.success:
                return ActionResult(False, {'custom': False})

            self.install_config['network'] = network_config
            self.install_config['network']['type'] = 'dhcp'

        elif selection == self.NET_CONFIG_OPTION_MANUAL:
            network_config = {}
            items = ['IP-адрес', 'Маска подсети', 'Шлюз', 'Сервер имен']
            keys = ['ip_addr', 'netmask', 'gateway', 'nameserver']
            self.create_window = ReadMulText(
                self.maxy, self.maxx, 0, network_config, '_conf_',
                items, None, None, None, self.validate_static_conf, None, True
            )
            result = self.create_window.do_action()
            if not result.success:
                return ActionResult(False, {'goBack': True})

            for i, item in enumerate(items):
                network_config[keys[i]] = network_config.pop(f'_conf_{i}', None)
            self.install_config['network'] = network_config
            self.install_config['network']['type'] = 'static'

        elif selection == self.NET_CONFIG_OPTION_VLAN:
            network_config = {}
            result = WindowStringReader(
                self.maxy, self.maxx, 18, 75, 'vlan_id', None, None,
                list(range(ord('0'), ord('9') + 1)), self.validate_vlan_id, None,
                '[!] Настройка сети', self.VLAN_READ_STRING, 6, network_config, '', True
            ).get_user_string(True)

            if not result.success:
                return ActionResult(False, {'goBack': True})

            self.install_config['network'] = network_config
            self.install_config['network']['type'] = 'vlan'

        return ActionResult(True, {'custom': False})

    def display(self) -> ActionResult:
        """Отображение окна настройки сети."""
        return self.window.do_action()
