#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

"""
© 2025 ООО "НАЙС СОФТ ГРУПП" (ИНН 5024245440)
Контакты: <niceos@ncsgp.ru>

Описание:
Модуль для настройки локали системы NiceOS в процессе пост-установки.
Устанавливает локаль ru_RU.UTF-8 и создает соответствующий конфигурационный файл.
"""

import os
import commons
from typing import Optional

# Константы
install_phase = commons.POST_INSTALL
enabled = True
LOCALE_CONF_PATH = "etc/locale.conf"
LOCALE_CONF_CONTENT = "LANG=ru_RU.UTF-8\n"
LOCALEDEF_COMMAND = "/usr/bin/localedef -c -i ru_RU -f UTF-8 ru_RU.UTF-8"


def execute(installer: commons.Installer) -> None:
    """
    Настраивает локаль системы NiceOS.

    Args:
        installer: Объект установщика NiceOS.

    Raises:
        OSError: Если произошла ошибка при записи файла конфигурации.
        RuntimeError: Если команда localedef завершилась с ошибкой.
    """
    try:
        # Создание и запись конфигурационного файла локали
        installer.logger.debug("Создание файла конфигурации локали")
        locale_conf_path = os.path.join(installer.niceos_root, LOCALE_CONF_PATH)
        with open(locale_conf_path, "w", encoding="utf-8") as locale_conf:
            locale_conf.write(LOCALE_CONF_CONTENT)
            installer.logger.debug(f"Файл {LOCALE_CONF_PATH} успешно создан")

        # Выполнение команды localedef для настройки локали
        # Прямой вызов localedef, так как glibc-lang может отсутствовать
        installer.logger.debug("Выполнение команды localedef для настройки ru_RU.UTF-8")
        installer.cmd.run_in_chroot(
            installer.niceos_root,
            LOCALEDEF_COMMAND
        )
        installer.logger.info("Локаль ru_RU.UTF-8 успешно настроена")

    except OSError as e:
        installer.logger.error(f"Ошибка при настройке локали: {str(e)}")
        raise OSError(f"Не удалось настроить локаль: {str(e)}") from e
    except RuntimeError as e:
        installer.logger.error(f"Ошибка выполнения localedef: {str(e)}")
        raise RuntimeError(f"Ошибка команды localedef: {str(e)}") from e
