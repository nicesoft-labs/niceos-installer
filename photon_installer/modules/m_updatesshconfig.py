#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
© 2025 ООО "НАЙС СОФТ ГРУПП" (ИНН 5024245440)
Контакты: <niceos@ncsgp.ru>

Запрещается любое изменение, копирование или распространение данного программного обеспечения
без письменного разрешения ООО "НАЙС СОФТ ГРУПП".

Описание:
Модуль для добавления публичного ключа и разрешения root-доступа по SSH
в системе NiceOS в процессе пост-установки.
"""

import os
import commons

install_phase = commons.POST_INSTALL
enabled = True


def execute(installer):
    """
    Добавляет публичный ключ root-пользователю и разрешает SSH-доступ от root.

    Args:
        installer: Объект установщика NiceOS.

    Raises:
        AssertionError: Если структура конфигурации public_key некорректна.
        OSError: Если произошла ошибка при работе с файлами.
    """
    try:
        if 'public_key' not in installer.install_config:
            installer.logger.debug("Параметр 'public_key' не задан — пропуск")
            return

        pubkey_config = installer.install_config['public_key']

        # Проверка структуры
        assert isinstance(pubkey_config, dict), (
            "'public_key' должен быть словарём с ключами 'key' и 'reason'"
        )
        assert 'reason' in pubkey_config, "Необходимо указать причину добавления ключа ('reason')"

        reason = pubkey_config['reason']
        key = pubkey_config.get('key', '').strip()

        if not key:
            raise ValueError("Ключ 'key' в 'public_key' не должен быть пустым")

        installer.logger.info(f"Добавление публичного ключа по причине: '{reason}'")

        # Пути к .ssh и authorized_keys
        ssh_dir = os.path.join(installer.niceos_root, "root/.ssh")
        authorized_keys_file = os.path.join(ssh_dir, "authorized_keys")

        if not os.path.exists(ssh_dir):
            os.makedirs(ssh_dir, mode=0o700)
            installer.logger.debug(f"Создан каталог: {ssh_dir}")

        with open(authorized_keys_file, "a", encoding="utf-8") as f:
            f.write(key + "\n")
            installer.logger.debug(f"Публичный ключ добавлен в {authorized_keys_file}")

        os.chmod(authorized_keys_file, 0o600)

        # Разрешение входа root по SSH через отдельный файл в sshd_config.d
        sshd_override_dir = os.path.join(installer.niceos_root, "etc/ssh/sshd_config.d")
        sshd_override_file = os.path.join(sshd_override_dir, "200-allow-root-login.conf")

        if not os.path.exists(sshd_override_dir):
            os.makedirs(sshd_override_dir, exist_ok=True)
            installer.logger.debug(f"Создан каталог конфигурации SSH: {sshd_override_dir}")

        with open(sshd_override_file, "w", encoding="utf-8") as f:
            f.write("PermitRootLogin yes\n")
            installer.logger.debug(f"Разрешён root-доступ через SSH: {sshd_override_file}")

        installer.logger.info("Настройка SSH-доступа для root завершена успешно")

    except AssertionError as e:
        installer.logger.error(f"Ошибка конфигурации public_key: {str(e)}")
        raise
    except (OSError, ValueError) as e:
        installer.logger.error(f"Ошибка при настройке SSH-доступа: {str(e)}")
        raise
