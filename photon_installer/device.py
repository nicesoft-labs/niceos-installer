#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
© 2025 ООО "НАЙС СОФТ ГРУПП" (ИНН 5024245440)
Контакты: <niceos@ncsgp.ru>
"""

import subprocess
import os
import logging


# Список исключаемых типов устройств для lsblk (см. https://www.kernel.org/doc/Documentation/admin-guide/devices.txt)
LSBLK_EXCLUDE = "2,9,11,15,16,17,18,19,20,23,24,25,26,27,28,29,30,32,35,37,46,103,113,144,145,146"


class Device(object):
    def __init__(self, model, path, size, logger=None):
        """
        Инициализация объекта устройства.

        Аргументы:
        - model (str): Модель устройства.
        - path (str): Путь к устройству (например, /dev/sda).
        - size (str): Размер устройства (в человекочитаемом формате или байтах).
        - logger (logging.Logger, optional): Логгер для записи событий. Если None, логирование не выполняется.
        """
        self.logger = logger
        if self.logger is not None:
            self.logger.debug(f"Инициализация Device: model={model}, path={path}, size={size}")

        # Проверка входных параметров
        if not isinstance(model, str) or not isinstance(path, str) or not isinstance(size, str):
            if self.logger is not None:
                self.logger.error(f"Некорректные типы параметров: model={type(model)}, path={type(path)}, size={type(size)}")
            raise ValueError("Параметры model, path и size должны быть строками")
        if not path.startswith("/dev/"):
            if self.logger is not None:
                self.logger.warning(f"Путь устройства не начинается с /dev/: {path}")
        
        self.model = model
        self.path = path
        self.size = size

    @staticmethod
    def refresh_devices(bytes=False, logger=None, min_size=None, exclude_types=None):
        """
        Получение списка устройств с помощью lsblk.

        Аргументы:
        - bytes (bool): Если True, размер возвращается в байтах, иначе в человекочитаемом формате.
        - logger (logging.Logger, optional): Логгер для записи событий.
        - min_size (str, optional): Минимальный размер устройства (например, "1G", "500M").
        - exclude_types (str, optional): Дополнительные типы устройств для исключения.

        Возвращает:
        - list[Device]: Список объектов Device.
        """
        if logger is not None:
            logger.debug(f"Обновление списка устройств: bytes={bytes}, min_size={min_size}, exclude_types={exclude_types}")

        # Формирование аргументов для lsblk
        args = ["lsblk", "-d", "-e", LSBLK_EXCLUDE if exclude_types is None else f"{LSBLK_EXCLUDE},{exclude_types}",
                "-n", "--output", "NAME,SIZE,MODEL"]
        if bytes:
            args.append("--bytes")
            if logger is not None:
                logger.debug("Размер устройств будет возвращен в байтах")
        
        try:
            if logger is not None:
                logger.debug(f"Запуск команды: {' '.join(args)}")
            devices_list = subprocess.check_output(args, stderr=subprocess.DEVNULL)
            if logger is not None:
                logger.debug(f"Вывод lsblk: {devices_list.decode()}")
            
            # Обработка списка устройств
            devices = Device.wrap_devices_from_list(devices_list, logger)
            
            # Фильтрация по минимальному размеру
            if min_size is not None:
                try:
                    min_size_bytes = Device._convert_to_bytes(min_size, logger)
                    devices = [d for d in devices if Device._convert_to_bytes(d.size, logger) >= min_size_bytes]
                    if logger is not None:
                        logger.debug(f"Фильтрация устройств: осталось {len(devices)} устройств с размером >= {min_size}")
                except ValueError as e:
                    if logger is not None:
                        logger.error(f"Ошибка при фильтрации по размеру: {str(e)}")
                    raise
            
            if logger is not None:
                logger.info(f"Получено {len(devices)} устройств")
            return devices
        except subprocess.CalledProcessError as e:
            if logger is not None:
                logger.error(f"Ошибка выполнения lsblk: {str(e)}")
            return []
        except Exception as e:
            if logger is not None:
                logger.error(f"Ошибка при получении списка устройств: {str(e)}")
            raise

    @staticmethod
    def check_cdrom(device_path="/dev/cdrom", logger=None):
        """
        Проверка доступности устройства (по умолчанию CD-ROM).

        Аргументы:
        - device_path (str): Путь к устройству для проверки.
        - logger (logging.Logger, optional): Логгер для записи событий.

        Возвращает:
        - bool: True, если устройство доступно, иначе False.
        """
        if logger is not None:
            logger.debug(f"Проверка устройства: {device_path}")
        
        try:
            process = subprocess.Popen(["blockdev", device_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            retval = process.wait()
            if logger is not None:
                logger.debug(f"Результат проверки устройства {device_path}: код возврата {retval}")
            result = (retval == 0)
            if logger is not None:
                logger.info(f"Устройство {device_path} {'доступно' if result else 'недоступно'}")
            return result
        except Exception as e:
            if logger is not None:
                logger.error(f"Ошибка при проверке устройства {device_path}: {str(e)}")
            return False

    @staticmethod
    def wrap_devices_from_list(devices_list, logger=None):
        """
        Преобразование вывода lsblk в список объектов Device.

        Аргументы:
        - devices_list (bytes): Вывод команды lsblk.
        - logger (logging.Logger, optional): Логгер для записи событий.

        Возвращает:
        - list[Device]: Список объектов Device.
        """
        if logger is not None:
            logger.debug("Преобразование вывода lsblk в список устройств")
        
        devices = []
        try:
            deviceslines = devices_list.splitlines()
            if logger is not None:
                logger.debug(f"Получено {len(deviceslines)} строк из вывода lsblk")
            
            for deviceline in deviceslines:
                try:
                    cols = deviceline.decode().split(None, 2)
                    if logger is not None:
                        logger.debug(f"Обработка строки: {cols}")
                    
                    # Пропуск виртуальных NVDIMM
                    if cols[0].startswith("pmem"):
                        if logger is not None:
                            logger.debug(f"Пропущено устройство pmem: {cols[0]}")
                        continue
                    
                    # Проверка количества столбцов
                    if len(cols) < 2:
                        if logger is not None:
                            logger.warning(f"Некорректный формат строки lsblk: {cols}")
                        continue
                    
                    # Установка модели устройства
                    model = cols[2] if len(cols) >= 3 else "Неизвестно"
                    path = f"/dev/{cols[0]}"
                    size = cols[1]
                    
                    # Создание объекта Device
                    device = Device(model, path, size, logger)
                    devices.append(device)
                    if logger is not None:
                        logger.debug(f"Добавлено устройство: model={model}, path={path}, size={size}")
                
                except (UnicodeDecodeError, IndexError) as e:
                    if logger is not None:
                        logger.warning(f"Ошибка обработки строки lsblk: {str(e)}, строка: {deviceline}")
                    continue
            
            if logger is not None:
                logger.info(f"Создано {len(devices)} объектов Device")
            return devices
        except Exception as e:
            if logger is not None:
                logger.error(f"Ошибка при преобразовании списка устройств: {str(e)}")
            return []

    @staticmethod
    def _convert_to_bytes(size, logger=None):
        """
        Конвертация размера в байты (поддержка k, m, g, t).

        Аргументы:
        - size (str): Размер в человекочитаемом формате (например, "1G", "500M").
        - logger (logging.Logger, optional): Логгер для записи событий.

        Возвращает:
        - int: Размер в байтах.
        """
        if logger is not None:
            logger.debug(f"Конвертация размера: {size}")
        
        if not isinstance(size, str):
            if logger is not None:
                logger.debug(f"Размер не строка, возвращается как число: {int(size)}")
            return int(size)
        
        if not size or not size[-1].isalpha():
            if logger is not None:
                logger.debug(f"Размер без суффикса, возвращается как число: {int(size)}")
            return int(size)
        
        conv = {'k': 1024, 'm': 1024**2, 'g': 1024**3, 't': 1024**4}
        try:
            result = int(float(size[:-1]) * conv[size.lower()[-1]])
            if logger is not None:
                logger.debug(f"Размер конвертирован в байты: {result}")
            return result
        except (ValueError, KeyError) as e:
            if logger is not None:
                logger.error(f"Недопустимый формат размера: {size}, ошибка: {str(e)}")
            raise ValueError(f"Недопустимый формат размера: {size}")
