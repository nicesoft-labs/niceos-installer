#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
© 2025 ООО "НАЙС СОФТ ГРУПП" (ИНН 5024245440)
Контакты: <niceos@ncsgp.ru>
"""


import os
import sys
import re
import secrets
import requests
import cracklib
import curses
import getopt
import json
import logging
from custompartition import CustomPartition
from packageselector import PackageSelector
from windowstringreader import WindowStringReader
from confirmwindow import ConfirmWindow
from selectdisk import SelectDisk
from license import License
from linuxselector import LinuxSelector
from ostreeserverselector import OSTreeServerSelector
from ostreewindowstringreader import OSTreeWindowStringReader
from commandutils import CommandUtils
from filedownloader import FileDownloader
from netconfig import NetworkConfigure
from stigenable import StigEnable
from wheelselector import WheelSelector
from timezoneselector import TimezoneSelector


class IsoConfig(object):
    g_ostree_repo_url = None
    """Класс для управления конфигурацией установщика ISO."""

    def __init__(self, root_dir="/", logger=None):
        """
        Инициализация конфигурации установщика ISO.

        Аргументы:
        - root_dir (str): Корневая директория (по умолчанию "/").
        - logger (logging.Logger, optional): Логгер для записи событий. Если None, логирование не выполняется.
        """
        self.logger = logger
        if self.logger is not None:
            self.logger.debug(f"Инициализация IsoConfig: root_dir={root_dir}")

        # Проверка входных параметров
        if not isinstance(root_dir, str) or not root_dir:
            if self.logger is not None:
                self.logger.error(f"Недопустимый root_dir: {root_dir}")
            raise ValueError("root_dir должен быть непустой строкой")

        self.alpha_chars = list(range(65, 91))
        self.alpha_chars.extend(range(97, 123))
        self.hostname_accepted_chars = self.alpha_chars[:]
        self.hostname_accepted_chars.extend(range(48, 58))
        self.hostname_accepted_chars.extend([ord('.'), ord('-')])
        self.random_id = '%12x' % secrets.randbelow(16**12)
        self.random_hostname = "niceos-" + self.random_id.strip()
        self.root_dir = root_dir
        if self.logger is not None:
            self.logger.debug(f"Установлены параметры: random_hostname={self.random_hostname}")

    @staticmethod
    def validate_hostname(hostname):
        """
        Валидация имени хоста.

        Аргументы:
        - hostname (str): Имя хоста для проверки.

        Возвращает:
        - tuple: (bool, str): True и None, если валидно, иначе False и сообщение об ошибке.
        """
        error_empty = "Пустое имя хоста или домен не допускаются"
        error_dash = "Имя хоста или домен не должны начинаться или заканчиваться на '-'"
        error_hostname = "Имя хоста должно начинаться с буквы и быть <= 64 символов"
        error_length = "Общая длина имени хоста не должна превышать 255 символов"

        if hostname is None or not hostname:
            return False, error_empty

        if len(hostname) > 255:
            return False, error_length

        fields = hostname.split('.')
        for field in fields:
            if not field:
                return False, error_empty
            if field[0] == '-' or field[-1] == '-':
                return False, error_dash

        machinename = fields[0]
        if not (1 <= len(machinename) <= 64 and machinename[0].isalpha()):
            return False, error_hostname

        return True, None

    @staticmethod
    def validate_ostree_url_input(ostree_repo_url):
        """
        Валидация URL репозитория OSTree.

        Аргументы:
        - ostree_repo_url (str): URL репозитория для проверки.

        Возвращает:
        - tuple: (bool, str): True и None, если валидно, иначе False и сообщение об ошибке.
        """
        if not ostree_repo_url:
            return False, "Ошибка: Пустой URL"

        if not re.match(r'^https?://[\w\.-]+(:\d+)?(/.*)?$', ostree_repo_url):
            return False, "Ошибка: Некорректный формат URL"

        exception_text = "Ошибка: Невалидный или недоступный URL"
        error_text = "Ошибка: Репозиторий недоступен"

        try:
            # Проверка основного URL
            ret = IsoConfig.validate_http_response(ostree_repo_url, [], exception_text, error_text)
            if ret != "":
                return False, ret

            # Проверка конфигурации репозитория
            exception_text = "Ошибка: Репозиторий не содержит конфигурацию"
            ret = IsoConfig.validate_http_response(
                ostree_repo_url + "/config",
                [
                    [r".*\[core\]\s*", 1, "Ошибка: Ожидается группа 'core' в конфигурации"],
                    [r"\s*mode[ \t]*=[ \t]*archive-z2[^ \t]", 1, "Ошибка: Репозиторий в режиме 'bare', требуется 'archive-z2'"]
                ],
                exception_text, exception_text
            )
            if ret != "":
                return False, ret

            # Проверка refs
            exception_text = "Ошибка: Репозиторий не содержит refs"
            ret = IsoConfig.validate_http_response(ostree_repo_url + "/refs/heads", [], exception_text, exception_text)
            if ret != "":
                return False, ret

            # Проверка objects
            exception_text = "Ошибка: Репозиторий не содержит objects"
            ret = IsoConfig.validate_http_response(ostree_repo_url + "/objects", [], exception_text, exception_text)
            if ret != "":
                return False, ret

            IsoConfig.g_ostree_repo_url = ostree_repo_url
            return True, None
        except Exception as e:
            return False, f"Ошибка: {str(e)}"

    @staticmethod
    def validate_ostree_refs_input(ostree_repo_ref):
        """
        Валидация refspec OSTree.

        Аргументы:
        - ostree_repo_ref (str): Refspec для проверки.

        Возвращает:
        - tuple: (bool, str): True и None, если валидно, иначе False и сообщение об ошибке.
        """
        if not ostree_repo_ref:
            return False, "Ошибка: Пустой refspec"

        if not re.match(r'^[\w/.-]+$', ostree_repo_ref):
            return False, "Ошибка: Refspec содержит недопустимые символы"

        if not IsoConfig.g_ostree_repo_url:
            return False, "Ошибка: URL репозитория OSTree не установлен"

        ret = IsoConfig.validate_http_response(
            f"{IsoConfig.g_ostree_repo_url}/refs/heads/{ostree_repo_ref}",
            [[r"^\s*[0-9A-Fa-f]{64}\s*$", 1, "Ошибка: Некорректный формат refspec или путь"]],
            "Ошибка: Некорректный путь refspec",
            "Ошибка: Refspec недоступен"
        )
        if ret != "":
            return False, ret

        return True, None

    @staticmethod
    def validate_http_response(url, checks, exception_text, error_text):
        """
        Проверка HTTP-ответа для валидации URL.

        Аргументы:
        - url (str): URL для проверки.
        - checks (list): Список проверок (паттерн, количество совпадений, текст ошибки).
        - exception_text (str): Текст ошибки при исключении.
        - error_text (str): Текст ошибки при неверном статусе ответа.

        Возвращает:
        - str: Пустая строка, если проверка успешна, иначе сообщение об ошибке.
        """
        try:
            response = requests.get(url, verify=True, stream=True, timeout=5.0)
            if response.status_code != 200:
                return error_text

            html = response.content.decode('utf-8', errors="replace")
            for pattern, count, failed_check_text in checks:
                match = re.findall(pattern, html)
                if len(match) != count:
                    return failed_check_text

            return ""
        except requests.exceptions.RequestException as e:
            return f"{exception_text}: {str(e)}"

    @staticmethod
    def validate_password(text, min_length=8):
        """
        Валидация пароля с использованием cracklib.

        Аргументы:
        - text (str): Пароль для проверки.
        - min_length (int): Минимальная длина пароля (по умолчанию 8).

        Возвращает:
        - tuple: (bool, str): True и None, если валидно, иначе False и сообщение об ошибке.
        """
        if not text or len(text) < min_length:
            return False, f"Ошибка: Пароль должен быть не короче {min_length} символов"

        try:
            password = cracklib.VeryFascistCheck(text)
            return password == text, None
        except ValueError as e:
            return False, f"Ошибка: {str(e)}"

    @staticmethod
    def validate_username(text, max_length=32):
        """
        Валидация имени пользователя.

        Аргументы:
        - text (str): Имя пользователя для проверки.
        - max_length (int): Максимальная длина имени пользователя (по умолчанию 32).

        Возвращает:
        - tuple: (bool, str): True и None, если валидно, иначе False и сообщение об ошибке.
        """
        if not text:
            return False, "Ошибка: Пустое имя пользователя"

        if len(text) > max_length:
            return False, f"Ошибка: Имя пользователя не должно превышать {max_length} символов"

        pattern = r'^[a-z_][a-z0-9_-]*[$]?$'
        if re.match(pattern, text):
            return True, None
        return False, "Ошибка: Некорректное имя пользователя (должно начинаться с буквы или '_', содержать a-z, 0-9, '_', '-')"

    def configure(self, stdscreen, ui_config):
        """
        Настройка конфигурации через пользовательский интерфейс.

        Аргументы:
        - stdscreen: Экран curses.
        - ui_config (dict): Конфигурация UI.

        Возвращает:
        - dict: Конфигурация установки.
        """
        if self.logger is not None:
            self.logger.debug("Запуск настройки конфигурации через UI")

        try:
            curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)
            curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)
            curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_GREEN)
            curses.init_pair(4, curses.COLOR_RED, curses.COLOR_WHITE)
            stdscreen.bkgd(' ', curses.color_pair(1))
            maxy, maxx = stdscreen.getmaxyx()
            stdscreen.addstr(maxy - 1, 0, ' © 2025 ООО "НАЙС СОФТ ГРУПП" | НАЙС.ОС | https://niceos.ru | Стрелки для выбора; <Enter> для подтверждения.')
            curses.curs_set(0)
            if self.logger is not None:
                self.logger.debug(f"Инициализирован curses: maxy={maxy}, maxx={maxx}")

            install_config = {'ui': True}
            items = self.add_ui_pages(install_config, ui_config, maxy, maxx)
            if self.logger is not None:
                self.logger.debug(f"Создано {len(items)} страниц UI")

            index = 0
            go_next = True
            while True:
                if self.logger is not None:
                    self.logger.debug(f"Отображение страницы {index}: {items[index][0].__name__}")
                    if index == len(items) - 1:
                        self.logger.info(
                            "Собранная конфигурация: %s",
                            json.dumps(install_config, ensure_ascii=False, indent=2),
                        )
                ar = items[index][0]()
                if ar.result and ar.result.get('inactive_screen', False):
                    ar.success = go_next
                    if self.logger is not None:
                        self.logger.debug(f"Пропущена неактивная страница: success={ar.success}")
                go_next = ar.success
                if ar.success:
                    index += 1
                    if index == len(items):
                        if ar.result.get('yes', False):
                            if self.logger is not None:
                                self.logger.info("Конфигурация завершена, пользователь подтвердил установку")
                            break
                        else:
                            if self.logger is not None:
                                self.logger.info("Пользователь отменил установку")
                            exit(0)
                else:
                    index -= 1
                    while index >= 0 and items[index][1] is False:
                        index -= 1
                    if index < 0:
                        index = 0
                    if self.logger is not None:
                        self.logger.debug(f"Возврат на страницу {index}")

            if self.logger is not None:
                self.logger.info("Конфигурация успешно завершена")
            return install_config
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при настройке конфигурации: {str(e)}")
            raise

    def add_ui_pages(self, install_config, ui_config, maxy, maxx):
        """
        Добавление страниц UI для конфигурации.

        Аргументы:
        - install_config (dict): Конфигурация установки.
        - ui_config (dict): Конфигурация UI.
        - maxy (int): Максимальная координата Y экрана.
        - maxx (int): Максимальная координата X экрана.

        Возвращает:
        - list: Список страниц UI с функциями отображения и флагами возврата.
        """
        if self.logger is not None:
            self.logger.debug("Добавление страниц UI")

        try:
            items = []
            license_agreement = License(maxy, maxx, ui_config['eula_file_path'], ui_config['license_display_title'], logger=self.logger)
            timezone_selector = TimezoneSelector(maxy, maxx, install_config, logger=self.logger)
            select_disk = SelectDisk(maxy, maxx, install_config, logger=self.logger)
            custom_partition = CustomPartition(maxy, maxx, install_config, logger=self.logger)
            package_selector = PackageSelector(maxy, maxx, install_config, ui_config['options_file'], logger=self.logger)
            hostname_reader = WindowStringReader(
                maxy, maxx, 10, 70, 'hostname', None, None, self.hostname_accepted_chars,
                IsoConfig.validate_hostname, None, 'Выберите имя хоста для системы', 'Имя хоста:', 2,
                install_config, self.random_hostname, True
            )
            root_password_reader = WindowStringReader(
                maxy, maxx, 10, 70, 'shadow_password', None, '*', None, IsoConfig.validate_password,
                None, 'Установите пароль root', 'Пароль root:', 2, install_config
            )
            confirm_password_reader = WindowStringReader(
                maxy, maxx, 10, 70, 'shadow_password', "Пароли не совпадают, попробуйте снова.",
                '*', None, None, CommandUtils.generate_password_hash, 'Подтвердите пароль root',
                'Подтверждение пароля root:', 2, install_config
            )
            user_name_reader = WindowStringReader(
                maxy, maxx, 10, 70, 'user_name', None, None, None, IsoConfig.validate_username,
                None, 'Создайте пользователя', 'Имя пользователя:', 2, install_config
            )
            user_password_reader = WindowStringReader(
                maxy, maxx, 10, 70, 'user_shadow_password', None, '*', None, IsoConfig.validate_password,
                None, 'Установите пароль пользователя', 'Пароль пользователя:', 2, install_config
            )
            confirm_user_password_reader = WindowStringReader(
                maxy, maxx, 10, 70, 'user_shadow_password', "Пароли не совпадают, попробуйте снова.",
                '*', None, None, CommandUtils.generate_password_hash, 'Подтвердите пароль пользователя',
                'Подтверждение пароля пользователя:', 2, install_config
            )
            wheel_selector = WheelSelector(maxy, maxx, install_config, logger=self.logger)
            ostree_server_selector = OSTreeServerSelector(maxy, maxx, install_config, logger=self.logger)
            ostree_url_reader = OSTreeWindowStringReader(
                maxy, maxx, 10, 80, 'repo_url', None, None, None, IsoConfig.validate_ostree_url_input,
                None, 'Укажите URL репозитория OSTree', 'URL репозитория OSTree:', 2, install_config, "http://"
            )
            ostree_ref_reader = OSTreeWindowStringReader(
                maxy, maxx, 10, 70, 'repo_ref', None, None, None, IsoConfig.validate_ostree_refs_input,
                None, 'Укажите Refspec в репозитории OSTree', 'Refspec репозитория OSTree:', 2, install_config,
                "niceos/5.2/x86_64/minimal"
            )
            confirm_window = ConfirmWindow(
                11,
                60,
                maxy,
                maxx,
                (maxy - 11) // 2 + 7,
                "Начать установку? Все данные на выбранном диске будут потеряны.\n\nНажмите <Да> для подтверждения или <Нет> для выхода",
                logger=self.logger,
            )

            items.append((license_agreement.display, False))
            items.append((timezone_selector.display, True))
            items.append((select_disk.display, True))
            items.append((custom_partition.display, False))
            items.append((package_selector.display, True))
            net_cfg = NetworkConfigure(maxy, maxx, install_config, logger=self.logger)
            items.append((net_cfg.display, True))

            if 'download_screen' in ui_config:
                title = ui_config['download_screen'].get('title', None)
                intro = ui_config['download_screen'].get('intro', None)
                dest = ui_config['download_screen'].get('destination', None)
                fd = FileDownloader(maxy, maxx, install_config, title, intro, dest, True, root_dir=self.root_dir, logger=self.logger)
                items.append((fd.display, True))

            linux_selector = LinuxSelector(maxy, maxx, install_config, logger=self.logger)
            items.append((linux_selector.display, True))
            stig_enable = StigEnable(maxy, maxx, install_config, logger=self.logger)
            items.append((stig_enable.display, True))
            items.append((hostname_reader.get_user_string, True))
            items.append((root_password_reader.get_user_string, True))
            items.append((confirm_password_reader.get_user_string, False))
            items.append((user_name_reader.get_user_string, True))
            items.append((user_password_reader.get_user_string, True))
            items.append((confirm_user_password_reader.get_user_string, True))
            items.append((wheel_selector.display, True))
            items.append((ostree_server_selector.display, True))
            items.append((ostree_url_reader.get_user_string, True))
            items.append((ostree_ref_reader.get_user_string, True))
            items.append((confirm_window.do_action, True))

            if self.logger is not None:
                self.logger.info(f"Добавлено {len(items)} страниц UI")
            return items
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при добавлении страниц UI: {str(e)}")
            raise

# for debugging
def main():
    """
    Основная функция для отладки конфигурации ISO.
    """
    config_file = None
    root_dir = "/"
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.DEBUG)

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'D:f:')
        if logger is not None:
            logger.debug(f"Получены аргументы командной строки: {sys.argv[1:]}")
    except getopt.GetoptError as e:
        if logger is not None:
            logger.error(f"Неверная опция командной строки: {str(e)}")
        print("invalid option")
        sys.exit(2)

    for o, a in opts:
        if o == '-D':
            root_dir = a
        elif o == '-f':
            config_file = a
        else:
            if logger is not None:
                logger.error(f"Необработанная опция: {o}")
            assert False, "unhandled option 'o'"

    try:
        if config_file is not None:
            with open(config_file, 'r') as f:
                ui_config = json.load(f)
                if logger is not None:
                    logger.debug(f"Загружен конфигурационный файл: {config_file}")
        else:
            ui_config = json.load(sys.stdin)
            if logger is not None:
                logger.debug("Загружена конфигурация из stdin")
    except Exception as e:
        if logger is not None:
            logger.error(f"Ошибка загрузки конфигурации: {str(e)}")
        sys.exit(2)

    ui_config['options_file'] = "input.json"
    if logger is not None:
        logger.debug("Установлен options_file=input.json")

    try:
        ui = IsoConfig(root_dir=root_dir, logger=logger)
        config = curses.wrapper(ui.configure, ui_config)
        print(json.dumps(config, indent=4))
        if logger is not None:
            logger.info("Конфигурация успешно завершена и выведена")
    except Exception as e:
        if logger is not None:
            logger.error(f"Ошибка при выполнении конфигурации: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
