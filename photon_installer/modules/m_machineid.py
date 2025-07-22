#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
© 2025 ООО "НАЙС СОФТ ГРУПП" (ИНН 5024245440)
Контакты: <niceos@ncsgp.ru>

Описание:
Модуль для настройки machine-id в системе NiceOS в процессе пост-установки.
Генерирует machine-id для live-установки или создает пустой файл с состоянием
'uninitialized' для образов, чтобы machine-id генерировался при загрузке.
"""

import os
import commons

install_phase = commons.POST_INSTALL
enabled = True


def execute(installer):
    """
    Настраивает machine-id для системы NiceOS.

    Args:
        installer: Объект установщика NiceOS.

    Raises:
        OSError: Если произошла ошибка при записи файла или изменении прав.
        RuntimeError: Если команда systemd-machine-id-setup завершилась с ошибкой.
    """
    try:
        # Генерация machine-id для live-установки
        if installer.install_config['live']:
            installer.logger.debug("Генерация machine-id для live-установки")
            installer.cmd.run_in_chroot(
                installer.niceos_root, "/bin/systemd-machine-id-setup"
            )
            installer.logger.info("machine-id успешно сгенерирован для live-установки")
        else:
            # Создание пустого файла machine-id для образов
            # см. https://www.freedesktop.org/software/systemd/man/latest/machine-id.html
            machine_id_path = installer.niceos_root + "/etc/machine-id"
            installer.logger.debug("Создание файла machine-id с состоянием 'uninitialized'")
            with open(machine_id_path, "wt") as f:
                f.write("uninitialized\n")
            os.chmod(machine_id_path, 0o444)
            installer.logger.info("Файл machine-id успешно создан для образа")

    except OSError as e:
        installer.logger.error(f"Ошибка при настройке machine-id: {str(e)}")
        raise OSError(f"Не удалось настроить machine-id: {str(e)}") from e
    except RuntimeError as e:
        installer.logger.error(f"Ошибка выполнения systemd-machine-id-setup: {str(e)}")
        raise RuntimeError(f"Ошибка команды systemd-machine-id-setup: {str(e)}") from e
