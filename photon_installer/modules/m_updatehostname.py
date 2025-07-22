#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
© 2025 ООО "НАЙС СОФТ ГРУПП" (ИНН 5024245440)
Контакты: <niceos@ncsgp.ru>

Запрещается любое изменение, копирование или распространение данного программного обеспечения
без письменного разрешения ООО "НАЙС СОФТ ГРУПП".

Описание:
Модуль для настройки имени хоста в системе NiceOS в процессе пост-установки.
Устанавливает имя хоста в файле /etc/hostname и обновляет /etc/hosts.
"""

import os
import commons

install_phase = commons.POST_INSTALL
enabled = True


def execute(installer):
    """
    Настраивает имя хоста в системе NiceOS.

    Args:
        installer: Объект установщика NiceOS.

    Raises:
        OSError: Если произошла ошибка при записи файлов.
        RuntimeError: Если замена строки в файле hosts завершилась с ошибкой.
    """
    try:
        hostname = installer.install_config['hostname']
        installer.logger.info(f"Установка имени хоста в /etc/hostname: {hostname}")

        # Запись имени хоста в /etc/hostname
        hostname_file = os.path.join(installer.niceos_root, "etc/hostname")
        with open(hostname_file, "wb") as outfile:
            outfile.write(hostname.encode())
            installer.logger.debug(f"Файл {hostname_file} успешно обновлен")

        # Обновление файла /etc/hosts
        hosts_file = os.path.join(installer.niceos_root, "etc/hosts")
        pattern = r'(127\.0\.0\.1)(\s+)(localhost)\s*\Z'
        replace = r'\1\2\3\n\1\2' + hostname
        installer.logger.debug(f"Обновление файла {hosts_file} с добавлением имени хоста {hostname}")
        commons.replace_string_in_file(hosts_file, pattern, replace)
        installer.logger.info(f"Имя хоста {hostname} успешно добавлено в /etc/hosts")

    except OSError as e:
        installer.logger.error(f"Ошибка при записи файлов: {str(e)}")
        raise OSError(f"Не удалось записать файлы конфигурации хоста: {str(e)}") from e
    except RuntimeError as e:
        installer.logger.error(f"Ошибка при обновлении файла hosts: {str(e)}")
        raise RuntimeError(f"Не удалось обновить файл /etc/hosts: {str(e)}") from e
