#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
© 2025 ООО "НАЙС СОФТ ГРУПП" (ИНН 5024245440)
Контакты: <niceos@ncsgp.ru>
"""

import os
import tempfile
import logging
import curses
from commandutils import CommandUtils
from window import Window
from windowstringreader import WindowStringReader
from actionresult import ActionResult
from networkmanager import NetworkManager
from confirmwindow import ConfirmWindow


class FileDownloader(object):
    def __init__(self, maxy, maxx, install_config, title, intro, dest, setup_network=False, root_dir="/", logger=None):
        """
        Инициализация загрузчика файлов.

        Аргументы:
        - maxy (int): Максимальная координата Y экрана.
        - maxx (int): Максимальная координата X экрана.
        - install_config (dict): Конфигурация установки.
        - title (str): Заголовок окна.
        - intro (str): Вводное сообщение для окна.
        - dest (str): Путь назначения для загруженного файла.
        - setup_network (bool): Если True, настраивается сетевое соединение.
        - root_dir (str): Корневая директория для операций (по умолчанию "/").
        - logger (logging.Logger, optional): Логгер для записи событий. Если None, логирование не выполняется.
        """
        self.logger = logger
        if self.logger is not None:
            self.logger.debug(f"Инициализация FileDownloader: maxy={maxy}, maxx={maxx}, title='{title}', "
                             f"intro='{intro}', dest='{dest}', setup_network={setup_network}, root_dir='{root_dir}'")

        # Проверка входных параметров
        if not isinstance(maxy, int) or not isinstance(maxx, int) or maxy <= 0 or maxx <= 0:
            if self.logger is not None:
                self.logger.error(f"Недопустимые размеры окна: maxy={maxy}, maxx={maxx}")
            raise ValueError("Параметры maxy и maxx должны быть положительными целыми числами")
        if not isinstance(install_config, dict):
            if self.logger is not None:
                self.logger.error(f"Некорректный тип install_config: {type(install_config)}")
            raise ValueError("install_config должен быть словарем")
        if not isinstance(dest, str) or not dest:
            if self.logger is not None:
                self.logger.error(f"Недопустимый путь назначения: {dest}")
            raise ValueError("dest должен быть непустой строкой")
        if not isinstance(root_dir, str) or not root_dir:
            if self.logger is not None:
                self.logger.error(f"Недопустимый root_dir: {root_dir}")
            raise ValueError("root_dir должен быть непустой строкой")

        self.install_config = install_config
        self.maxy = maxy
        self.maxx = maxx
        self.title = title
        self.intro = intro
        self.netmgr = None
        self.dest = dest
        self.setup_network = setup_network
        self.root_dir = root_dir
        if self.logger is not None:
            self.logger.debug("Все параметры инициализированы успешно")

    def ask_proceed_unsafe_download(self, fingerprint):
        """
        Запрос подтверждения для небезопасной загрузки при неподтвержденном сертификате.

        Аргументы:
        - fingerprint (str): Отпечаток сертификата сервера.

        Возвращает:
        - bool: True, если пользователь подтвердил, иначе False.
        """
        if self.logger is not None:
            self.logger.debug(f"Запрос подтверждения для небезопасной загрузки, отпечаток: {fingerprint}")

        msg = ('Сервер не смог подтвердить свою подлинность. Его отпечаток:\n\n' + fingerprint +
               '\n\nЖелаете продолжить?\n')
        conf_message_height = 12
        conf_message_width = 80
        conf_message_button_y = (self.maxy - conf_message_height) // 2 + 8
        
        try:
            r = ConfirmWindow(conf_message_height, conf_message_width, self.maxy, self.maxx,
                              conf_message_button_y, msg, logger=self.logger).do_action()
            if self.logger is not None:
                self.logger.debug(f"Результат ConfirmWindow: success={r.success}, result={r.result}")
            
            result = r.success and r.result.get('yes', False)
            if self.logger is not None:
                self.logger.info(f"Пользователь {'подтвердил' if result else 'отклонил'} небезопасную загрузку")
            return result
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при запросе подтверждения: {str(e)}")
            return False

    def do_setup_network(self):
        """
        Настройка сетевого соединения.

        Возвращает:
        - bool: True, если настройка успешна, иначе False.
        """
        if self.logger is not None:
            self.logger.debug(f"Настройка сети: root_dir={self.root_dir}")

        try:
            self.netmgr = NetworkManager(self.install_config['network'], self.root_dir)
            if self.logger is not None:
                self.logger.debug("NetworkManager инициализирован")
            
            if not self.netmgr.setup_network():
                msg = 'Не удалось настроить сетевое соединение!'
                conf_message_height = 12
                conf_message_width = 80
                conf_message_button_y = (self.maxy - conf_message_height) // 2 + 8
                if self.logger is not None:
                    self.logger.error("Ошибка настройки сети")
                
                ConfirmWindow(conf_message_height, conf_message_width, self.maxy, self.maxx,
                              conf_message_button_y, msg, logger=self.logger, info=True).do_action()
                return False
            
            self.netmgr.set_perms()
            if self.logger is not None:
                self.logger.debug("Права сети установлены")
            
            if self.root_dir == "/":
                self.netmgr.restart_networkd()
                if self.logger is not None:
                    self.logger.debug("Служба networkd перезапущена")
            
            if self.logger is not None:
                self.logger.info("Сеть успешно настроена")
            return True
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при настройке сети: {str(e)}")
            return False

    def display(self):
        """
        Отображение окна для ввода URL и загрузки файла.

        Возвращает:
        - ActionResult: Результат операции (успех или ошибка с флагом goBack).
        """
        if self.logger is not None:
            self.logger.debug("Запуск метода display для загрузки файла")

        # Настройка сети, если требуется
        if self.setup_network:
            if self.logger is not None:
                self.logger.debug("Запуск настройки сети")
            if not self.do_setup_network():
                if self.logger is not None:
                    self.logger.error("Не удалось настроить сеть, возврат с ошибкой")
                return ActionResult(False, {'goBack': True})

        # Запрос URL у пользователя
        file_source = {}
        accepted_chars = list(range(ord('a'), ord('z')+1))
        accepted_chars.extend(range(ord('A'), ord('Z')+1))
        accepted_chars.extend(range(ord('0'), ord('9')+1))
        accepted_chars.extend([ord('-'), ord('_'), ord('.'), ord('~'), ord(':'), ord('/')])
        if self.logger is not None:
            self.logger.debug(f"Создание WindowStringReader для ввода URL, title='{self.title}', intro='{self.intro}'")
        
        try:
            result = WindowStringReader(self.maxy, self.maxx, 18, 78, 'url',
                                       None, None, accepted_chars, None, None,
                                       self.title, self.intro, 10, file_source, 'https://',
                                       True).get_user_string(None)
            if self.logger is not None:
                self.logger.debug(f"Результат ввода URL: success={result.success}, result={result.result}")
            
            if not result.success:
                if self.logger is not None:
                    self.logger.info("Пользователь отменил ввод URL")
                return result
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при получении URL: {str(e)}")
            return ActionResult(False, {'goBack': True})

        # Отображение окна статуса загрузки
        try:
            status_window = Window(10, 70, self.maxy, self.maxx, 'Установка Nice.OS', False)
            status_window.addstr(1, 0, 'Загрузка файла...')
            status_window.show_window()
            if self.logger is not None:
                self.logger.debug("Окно статуса загрузки отображено")
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при отображении окна статуса: {str(e)}")
            return ActionResult(False, {'goBack': True})

        # Загрузка файла
        try:
            fd, temp_file = tempfile.mkstemp()
            if self.logger is not None:
                self.logger.debug(f"Создан временный файл: {temp_file}")
            
            result, msg = CommandUtils.wget(file_source['url'], temp_file, logger=self.logger,
                                            ask_fn=self.ask_proceed_unsafe_download)
            os.close(fd)
            if self.logger is not None:
                self.logger.debug(f"Результат загрузки: success={result}, message={msg}")
            
            if not result:
                status_window.adderror(f'Ошибка: {msg} Нажмите любую клавишу для возврата...')
                if self.logger is not None:
                    self.logger.error(f"Ошибка загрузки файла: {msg}")
                while True:
                    ch = status_window.content_window().getch()
                    if ch == curses.KEY_F1:
                        status_window.show_help()
                    else:
                        break
                status_window.clearerror()
                status_window.hide_window()
                return ActionResult(False, {'goBack': True})
            
            # Обновление конфигурации
            if 'additional_files' not in self.install_config:
                self.install_config['additional_files'] = []
            copy = {temp_file: self.dest}
            self.install_config['additional_files'].append(copy)
            if self.logger is not None:
                self.logger.debug(f"Добавлен файл в install_config: {copy}")
            
            status_window.hide_window()
            if self.logger is not None:
                self.logger.info(f"Файл успешно загружен и добавлен в конфигурацию: {file_source['url']} -> {self.dest}")
            return ActionResult(True, None)
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при загрузке файла или обновлении конфигурации: {str(e)}")
            status_window.adderror(f'Ошибка: {str(e)} Нажмите любую клавишу для возврата...')
            while True:
                ch = status_window.content_window().getch()
                if ch == curses.KEY_F1:
                    status_window.show_help()
                else:
                    break
            status_window.clearerror()
            status_window.hide_window()
            return ActionResult(False, {'goBack': True})
