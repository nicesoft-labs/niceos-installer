#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
© 2025 ООО "НАЙС СОФТ ГРУПП" (ИНН 5024245440)
Контакты: <niceos@ncsgp.ru>

Описание:
Модуль для настройки пароля root в системе NiceOS в процессе пост-установки.
Включает обновление файлов /etc/passwd и /etc/shadow, запуск pwconv/grpconv,
а также установку политики срока действия пароля, если указана.
"""

import os
import commons

install_phase = commons.POST_INSTALL
enabled = True


def execute(installer):
    """
    Настраивает root-пароль и срок его действия в системе NiceOS.

    Args:
        installer: Объект установщика NiceOS.

    Raises:
        OSError: При ошибке доступа к файлам.
        RuntimeError: При сбое команд chroot или замене строк.
    """
    try:
        shadow_password = installer.install_config['shadow_password']
        installer.logger.info("Установка пароля root")

        passwd_filename = os.path.join(installer.niceos_root, "etc/passwd")
        shadow_filename = os.path.join(installer.niceos_root, "etc/shadow")

        # Обновление /etc/passwd: замена пустого пароля на ссылку в shadow
        installer.logger.debug(f"Обновление файла {passwd_filename}")
        commons.replace_string_in_file(passwd_filename, "root::", "root:x:")

        # Обновление /etc/shadow: установка пароля
        if not os.path.isfile(shadow_filename):
            installer.logger.debug(f"Файл {shadow_filename} не найден, создается новый")
            with open(shadow_filename, "w") as destination:
                destination.write("root:" + shadow_password + ":")
                installer.logger.debug("Файл shadow успешно создан")
        else:
            installer.logger.debug(f"Обновление файла {shadow_filename} с новым хешем пароля")
            commons.replace_string_in_file(
                shadow_filename, "root::", f"root:{shadow_password}:"
            )
            commons.replace_string_in_file(
                shadow_filename, "root:x:", f"root:{shadow_password}:"
            )

        # Синхронизация passwd/shadow
        installer.logger.debug("Выполнение pwconv и grpconv в chroot")
        installer.cmd.run_in_chroot(installer.niceos_root, "/usr/sbin/pwconv")
        installer.cmd.run_in_chroot(installer.niceos_root, "/usr/sbin/grpconv")
        installer.logger.info("pwconv и grpconv успешно выполнены")

        # Обработка настройки срока действия пароля, если указано
        password_cfg = installer.install_config.get('password', {})
        if 'age' in password_cfg:
            age = password_cfg['age']
            login_defs_filename = os.path.join(installer.niceos_root, "etc/login.defs")
            installer.logger.debug(f"Настройка срока действия пароля: age={age}")

            if age == -1:
                # Без ограничений
                installer.cmd.run_in_chroot(
                    installer.niceos_root,
                    "chage -I -1 -m 0 -M 99999 -E -1 -W 7 root"
                )
                commons.replace_string_in_file(
                    login_defs_filename,
                    r'(PASS_MAX_DAYS)\s+\d+\s*',
                    'PASS_MAX_DAYS\t99999\n'
                )
                installer.logger.info("Установлен неограниченный срок действия пароля")
            elif age == 0:
                # Требуется смена при первом входе
                installer.cmd.run_in_chroot(installer.niceos_root, "chage -d 0 root")
                installer.logger.info("Требуется смена пароля при первом входе")
            else:
                # Указан срок действия в днях
                installer.cmd.run_in_chroot(
                    installer.niceos_root,
                    f"chage -M {age} root"
                )
                commons.replace_string_in_file(
                    login_defs_filename,
                    r'(PASS_MAX_DAYS)\s+\d+\s*',
                    f'PASS_MAX_DAYS\t{age}\n'
                )
                installer.logger.info(f"Установлен срок действия пароля: {age} дней")

    except OSError as e:
        installer.logger.error(f"Ошибка при работе с файлами конфигурации: {str(e)}")
        raise OSError(f"Не удалось обновить конфигурацию пароля: {str(e)}") from e
    except RuntimeError as e:
        installer.logger.error(f"Ошибка выполнения команд в chroot: {str(e)}")
        raise RuntimeError(f"Ошибка настройки пароля root: {str(e)}") from e
