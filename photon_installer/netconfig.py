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
    """Класс для интерактивной настройки сетевых параметров в установщике Nice OS."""

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
            "Эта опция позволяет автоматически получить IP-адрес, маску подсети, шлюз и DNS\n"
            "от DHCP-сервера. Подходит для большинства сетей с активным DHCP-сервером.\n\n"
            "Пример: IP-адрес будет назначен автоматически, например, 192.168.1.100.\n\n"
            "Нажмите <Enter> для подтверждения или <F1> для возврата к меню."
        ),
        NET_CONFIG_OPTION_DHCP_HOSTNAME: (
            "Автоматическая настройка сети с именем хоста DHCP\n\n"
            "Настройка через DHCP с указанием пользовательского имени хоста.\n"
            "Требования к имени хоста:\n"
            "  - Начинается с буквы;\n"
            "  - Содержит только буквы, цифры, точки и дефисы;\n"
            "  - Имя машины не длиннее 64 символов;\n"
            "  - Не начинается и не заканчивается дефисом.\n\n"
            "Пример: myhost.example.com\n\n"
            "Нажмите <Enter> для ввода имени хоста или <F1> для возврата."
        ),
        NET_CONFIG_OPTION_MANUAL: (
            "Ручная настройка сети\n\n"
            "Укажите вручную сетевые параметры:\n"
            "  - IP-адрес (например, 192.168.1.100 или 192.168.1.100/24);\n"
            "  - Маска подсети (например, 255.255.255.0);\n"
            "  - Шлюз (например, 192.168.1.1);\n"
            "  - Сервер имен (DNS, например, 8.8.8.8).\n\n"
            "Все адреса должны быть в формате xxx.xxx.xxx.xxx, числа от 0 до 255.\n"
            "Нажмите <Enter> для ввода параметров или <F1> для возврата."
        ),
        NET_CONFIG_OPTION_VLAN: (
            "Настройка сети с использованием VLAN\n\n"
            "Настройка виртуальной локальной сети (VLAN) с указанием идентификатора VLAN.\n"
            "Требования к идентификатору VLAN:\n"
            "  - Число от 1 до 4094.\n\n"
            "Пример: 100\n\n"
            "VLAN разделяет физическую сеть на логические домены для изоляции трафика.\n"
            "Нажмите <Enter> для ввода идентификатора VLAN или <F1> для возврата."
        ),
    }

    VLAN_READ_STRING = (
        "Виртуальные локальные сети IEEE 802.1Q (VLAN) позволяют разделять физическую сеть "
        "на отдельные широковещательные домены. Пакеты помечаются идентификаторами VLAN, "
        "что позволяет использовать одну 'магистральную' линию для передачи данных.\n"
        "\n"
        "Если интерфейс подключен к магистральному порту VLAN, укажите идентификатор VLAN.\n"
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

        Raises:
            RuntimeError: Если нет доступных сетевых интерфейсов или терминал слишком мал.
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
        self.install_config['network'] = {'version': '2'}  # Инициализация с версией 2
        self.network_manager = NetworkManager(config=self.install_config['network'], logger=logger)

        # Проверка размеров терминала
        if self.win_width < 40 or self.win_height < 7:
            if self.logger:
                self.logger.error(f"Терминал слишком мал: maxx={maxx}, maxy={maxy}")
            raise RuntimeError("Терминал слишком мал для отображения интерфейса")

        # Проверка доступности сетевых интерфейсов
        if not self._check_network_interfaces():
            if self.logger:
                self.logger.error("Нет доступных сетевых интерфейсов")
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
            help_text=self.HELP_TEXTS[self.NET_CONFIG_OPTION_DHCP],
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
                if not (0 < int(cidr) <= 32):  # CIDR до 32 включительно
                    return False, "Недействительный номер CIDR; должен быть в диапазоне (1-32)"
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
            network_config = {'version': '2'}
            interface = self._get_default_interface()

            if selection == self.NET_CONFIG_OPTION_DHCP:
                network_config['ethernets'] = {
                    'dhcp-en': {
                        'match': {'name': interface},
                        'dhcp4': True
                    }
                }
                self.install_config['network'] = network_config
                self.network_manager.config = network_config
                if self.logger:
                    self.logger.info(f"Выбрана автоматическая настройка сети (DHCP) на интерфейсе {interface}")

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

                network_config['ethernets'] = {
                    'dhcp-en': {
                        'match': {'name': interface},
                        'dhcp4': True
                    }
                }
                network_config['hostname'] = network_config.pop('hostname')
                self.install_config['network'] = network_config
                self.network_manager.config = network_config
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

                ip_addr = network_config.pop('_conf_0')
                netmask = network_config.pop('_conf_1')
                gateway = network_config.pop('_conf_2')
                nameserver = network_config.pop('_conf_3')
                cidr = self.network_manager.netmask_to_cidr(netmask)
                network_config['ethernets'] = {
                    'static-en': {
                        'match': {'name': interface},
                        'dhcp4': False,
                        'addresses': [f'{ip_addr}/{cidr}'],
                        'gateway': gateway,
                        'nameservers': {'addresses': [nameserver]}
                    }
                }
                self.install_config['network'] = network_config
                self.network_manager.config = network_config
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

                vlan_id = network_config.pop('vlan_id')
                vlan_if_id = f'dhcp-en.vlan_{vlan_id}'
                network_config['ethernets'] = {
                    'dhcp-en': {
                        'match': {'name': interface},
                        'dhcp4': True
                    }
                }
                network_config['vlans'] = {
                    vlan_if_id: {
                        'id': int(vlan_id),
                        'link': 'dhcp-en',
                        'match': {'name': f'{interface}.{vlan_id}'},
                        'dhcp4': True
                    }
                }
                self.install_config['network'] = network_config
                self.network_manager.config = network_config
                if self.logger:
                    self.logger.info(f"VLAN ID установлен: {vlan_id}")

            # Применение конфигурации через NetworkManager
            try:
                self.network_manager.setup_network()
                if self.logger:
                    self.logger.info("Сетевая конфигурация успешно применена")
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Ошибка при применении сетевой конфигурации: {e}")
                self.window.adderror(f"Ошибка: Не удалось применить сетевую конфигурацию: {e}")
                return ActionResult(False, {'custom': False})

            return ActionResult(True, {'custom': False})

        except Exception as e:
            if self.logger:
                self.logger.error(f"Ошибка при настройке сети: {e}")
            self.window.adderror(f"Ошибка: {str(e)}")
            return ActionResult(False, {'custom': False})

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
