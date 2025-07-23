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
    """Класс для настройки сетевых параметров в интерфейсе установщика Nice OS."""

    # Константы для опций конфигурации сети
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

    # Текст справки для каждого варианта конфигурации
    HELP_TEXTS = {
        NET_CONFIG_OPTION_DHCP: (
            "Автоматическая настройка сети (DHCP)\n\n"
            "Выберите эту опцию, чтобы автоматически получить IP-адрес и другие сетевые параметры\n"
            "от DHCP-сервера. Это рекомендуется для большинства сетевых окружений, где\n"
            "DHCP-сервер доступен.\n\n"
            "Нажмите <Enter> для подтверждения или <F1> для возврата к меню."
        ),
        NET_CONFIG_OPTION_DHCP_HOSTNAME: (
            "Автоматическая настройка сети с именем хоста DHCP\n\n"
            "Эта опция позволяет настроить сеть через DHCP с указанием пользовательского имени хоста.\n"
            "Имя хоста должно:\n"
            "  - начинаться с буквы;\n"
            "  - содержать только буквы, цифры, точки и дефисы;\n"
            "  - не превышать 64 символов для имени машины;\n"
            "  - не начинаться или заканчиваться дефисом.\n\n"
            "Пример: myhost.example.com\n"
            "Нажмите <Enter> для ввода имени хоста или <F1> для возврата."
        ),
        NET_CONFIG_OPTION_MANUAL: (
            "Ручная настройка сети\n\n"
            "Выберите эту опцию для ручного ввода сетевых параметров:\n"
            "  - IP-адрес (например, 192.168.1.100);\n"
            "  - Маска подсети (например, 255.255.255.0);\n"
            "  - Шлюз (например, 192.168.1.1);\n"
            "  - Сервер имен (DNS, например, 8.8.8.8).\n\n"
            "Все адреса должны быть в формате xxx.xxx.xxx.xxx, где каждое число от 0 до 255.\n"
            "Нажмите <Enter> для ввода параметров или <F1> для возврата."
        ),
        NET_CONFIG_OPTION_VLAN: (
            "Настройка сети с использованием VLAN\n\n"
            "Эта опция позволяет настроить сеть с использованием виртуальной локальной сети (VLAN).\n"
            "Требуется указать идентификатор VLAN (число от 1 до 4094).\n\n"
            "Пример: 100\n\n"
            "VLAN разделяет физическую сеть на логические домены, что полезно для изоляции трафика.\n"
            "Нажмите <Enter> для ввода идентификатора VLAN или <F1> для возврата."
        ),
    }

    VLAN_READ_STRING = (
        "Виртуальные локальные сети IEEE 802.1Q (VLAN) позволяют разделять физическую сеть "
        "на отдельные широковещательные домены. Пакеты могут быть помечены различными "
        "идентификаторами VLAN, что позволяет использовать одну 'магистральную' линию "
        "для передачи данных для разных VLAN.\n"
        "\n"
        "Если сетевой интерфейс напрямую подключен к магистральному порту VLAN,\n"
        "указание идентификатора VLAN может быть необходимо для рабочего соединения.\n"
        "\n"
        "Идентификатор VLAN (1-4094): "
    )

    def __init__(self, maxy: int, maxx: int, install_config: Dict, logger=None):
        """
        Инициализация класса для настройки сетевых параметров.

        Args:
            maxy (int): Максимальная высота терминала.
            maxx (int): Максимальная ширина терминала.
            install_config (Dict): Словарь для хранения конфигурации установки.
            logger: Объект логгера для записи сообщений об ошибках и событиях.
        """
        self.logger = logger
        self.maxx = maxx
        self.maxy = maxy
        self.win_width = min(80, maxx - 4)  # Ограничение ширины окна
        self.win_height = min(13, maxy - 4)  # Ограничение высоты окна
        self.win_starty = (maxy - self.win_height) // 2
        self.win_startx = (maxx - self.win_width) // 2
        self.menu_starty = self.win_starty + 3
        self.package_menu_items = []
        self.install_config = install_config
        self.install_config['network'] = {}
        self.network_manager = NetworkManager(logger=logger)  # Инициализация NetworkManager

        # Проверка доступности сетевых интерфейсов
        if not self._check_network_interfaces():
            raise RuntimeError("Нет доступных сетевых интерфейсов")

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
            can_go_back=True,
            action_panel=self.package_menu,
            can_go_next=True,
            position=1,
            help_text=self.HELP_TEXTS[self.NET_CONFIG_OPTION_DHCP],  # Начальная справка
            logger=logger
        )

    def _check_network_interfaces(self) -> bool:
        """
        Проверка наличия доступных сетевых интерфейсов.

        Returns:
            bool: True, если есть хотя бы один интерфейс, иначе False.
        """
        try:
            interfaces = self.network_manager.get_interfaces()
            if not interfaces:
                if self.logger:
                    self.logger.error("Не найдены сетевые интерфейсы")
                return False
            return True
        except Exception as e:
            if self.logger:
                self.logger.error(f"Ошибка при проверке сетевых интерфейсов: {e}")
            return False

    @staticmethod
    def validate_hostname(hostname: Optional[str]) -> Tuple[bool, Optional[str]]:
        """
        Валидация имени хоста.

        Args:
            hostname (Optional[str]): Имя хоста для проверки.

        Returns:
            Tuple[bool, Optional[str]]: True и None, если валидно, иначе False и сообщение об ошибке.
        """
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
        """
        Валидация IP-адреса.

        Args:
            ip (Optional[str]): IP-адрес для проверки.
            can_have_cidr (bool): Разрешить маску подсети в формате CIDR.

        Returns:
            Tuple[bool, Optional[str]]: True и None, если валидно, иначе False и сообщение об ошибке.
        """
        if not ip:
            return False, "IP-адрес не может быть пустым"

        cidr = None
        if can_have_cidr and '/' in ip:
            ip, cidr = ip.split('/')

        octets = ip.split('.')
        if len(octets) != 4:
            return False, "Недействительный IP; должен быть в формате: xxx.xxx.xxx.xxx"

        for octet in octets:
            try:
                if not octet or not (0 <= int(octet) <= 255):
                    return False, "Недействительный IP; число должно быть в диапазоне (0 <= x <= 255)"
            except ValueError:
                return False, "Недействительный IP; ожидаются числовые октеты"

        if cidr is not None:
            try:
                if not (0 < int(cidr) < 32):
                    return False, "Недействительный номер CIDR; должен быть в диапазоне (1-31)"
            except ValueError:
                return False, "Недействительный номер CIDR; ожидается число"

        return True, None

    def validate_static_conf(self, vals: List[str]) -> Tuple[bool, Optional[str]]:
        """
        Валидация статической конфигурации сети.

        Args:
            vals (List[str]): Список значений (IP, маска, шлюз, DNS).

        Returns:
            Tuple[bool, Optional[str]]: True и None, если валидно, иначе False и сообщение об ошибке.
        """
        if len(vals) != 4:
            return False, "Требуется указать IP-адрес, маску подсети, шлюз и сервер имен"

        for i, val in enumerate(vals):
            field_name = ['IP-адрес', 'Маска подсети', 'Шлюз', 'Сервер имен'][i]
            res, msg = self.validate_ipaddr(val, can_have_cidr=(i == 0))  # CIDR только для IP
            if not res:
                return False, f"Ошибка в поле '{field_name}': {msg}"
        return True, None

    @staticmethod
    def validate_vlan_id(vlan_id: Optional[str]) -> Tuple[bool, Optional[str]]:
        """
        Валидация идентификатора VLAN.

        Args:
            vlan_id (Optional[str]): Идентификатор VLAN для проверки.

        Returns:
            Tuple[bool, Optional[str]]: True и None, если валидно, иначе False и сообщение об ошибке.
        """
        if not vlan_id:
            return False, 'Пустой идентификатор VLAN не допускается'

        try:
            vlan_num = int(vlan_id)
            if not (1 <= vlan_num <= 4094):
                return False, 'Некорректный идентификатор VLAN; должен быть в диапазоне (1-4094)'
        except ValueError:
            return False, 'Некорректный идентификатор VLAN; ожидается число'

        return True, None

    def _exit_function(self, selected_item_params: List[str]) -> ActionResult:
        """
        Обработка выбора опции конфигурации сети.

        Args:
            selected_item_params (List[str]): Параметры выбранного элемента меню.

        Returns:
            ActionResult: Результат действия (успех или ошибка).
        """
        try:
            selection = self.NET_CONFIG_OPTION_STRINGS.index(selected_item_params[0])
            self.window.help_text = self.HELP_TEXTS[selection]  # Обновление справки

            if selection == self.NET_CONFIG_OPTION_DHCP:
                self.install_config['network']['type'] = 'dhcp'
                self.install_config['network']['interface'] = self._get_default_interface()
                if self.logger:
                    self.logger.info("Выбрана автоматическая настройка сети (DHCP)")

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
                    if self.logger:
                        self.logger.warning("Ошибка ввода имени хоста DHCP")
                    self.window.adderror("Ошибка: Неверное имя хоста DHCP")
                    return ActionResult(False, {'custom': False})

                self.install_config['network'] = network_config
                self.install_config['network']['type'] = 'dhcp'
                self.install_config['network']['interface'] = self._get_default_interface()
                if self.logger:
                    self.logger.info(f"Имя хоста DHCP установлено: {network_config['hostname']}")

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
                    if self.logger:
                        self.logger.warning("Ошибка ввода статической конфигурации")
                    self.window.adderror("Ошибка: Неверные параметры статической конфигурации")
                    return ActionResult(False, {'goBack': True})

                for i, item in enumerate(items):
                    network_config[keys[i]] = network_config.pop(f'_conf_{i}', None)
                self.install_config['network'] = network_config
                self.install_config['network']['type'] = 'static'
                self.install_config['network']['interface'] = self._get_default_interface()
                if self.logger:
                    self.logger.info("Статическая конфигурация сети установлена")

            elif selection == self.NET_CONFIG_OPTION_VLAN:
                network_config = {}
                result = WindowStringReader(
                    self.maxy, self.maxx, 18, 75, 'vlan_id', None, None,
                    list(range(ord('0'), ord('9') + 1)), self.validate_vlan_id, None,
                    '[!] Настройка сети', self.VLAN_READ_STRING, 6, network_config, '', True
                ).get_user_string(True)
                if not result.success:
                    if self.logger:
                        self.logger.warning("Ошибка ввода идентификатора VLAN")
                    self.window.adderror("Ошибка: Неверный идентификатор VLAN")
                    return ActionResult(False, {'goBack': True})

                self.install_config['network'] = network_config
                self.install_config['network']['type'] = 'vlan'
                self.install_config['network']['interface'] = self._get_default_interface()
                if self.logger:
                    self.logger.info(f"VLAN ID установлен: {network_config['vlan_id']}")

            return ActionResult(True, {'custom': False})

        except Exception as e:
            if self.logger:
                self.logger.error(f"Ошибка при настройке сети: {e}")
            self.window.adderror(f"Ошибка: {str(e)}")
            return ActionResult(False, {'custom': False})

    def _get_default_interface(self) -> str:
        """
        Получение имени сетевого интерфейса по умолчанию.

        Returns:
            str: Имя интерфейса или 'eth0' по умолчанию.
        """
        try:
            interfaces = self.network_manager.get_interfaces()
            return interfaces[0] if interfaces else 'eth0'
        except Exception as e:
            if self.logger:
                self.logger.error(f"Ошибка при получении сетевого интерфейса: {e}")
            return 'eth0'  # Fallback

    def display(self) -> ActionResult:
        """
        Отображение окна настройки сети и обработка пользовательского ввода.

        Returns:
            ActionResult: Результат действия (успех или ошибка).
        """
        try:
            result = self.window.do_action()
            if not result.success:
                if self.logger:
                    self.logger.warning("Настройка сети отменена пользователем")
                self.window.adderror("Настройка сети отменена")
            return result
        except KeyboardInterrupt:
            if self.logger:
                self.logger.info("Прерывание пользователем в окне настройки сети")
            self.window.cleanup()  # Очистка терминала
            raise  # Пропустить прерывание наверх для обработки в IsoInstaller
        except Exception as e:
            if self.logger:
                self.logger.error(f"Ошибка при отображении окна настройки сети: {e}")
            self.window.adderror(f"Ошибка: {str(e)}")
            self.window.cleanup()
            return ActionResult(False, {'custom': False})
