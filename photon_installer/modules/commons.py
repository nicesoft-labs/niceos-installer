#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
© 2025 ООО "НАЙС СОФТ ГРУПП" (ИНН 5024245440)
Контакты: <niceos@ncsgp.ru>

Запрещается любое изменение, копирование или распространение данного программного обеспечения
без письменного разрешения ООО "НАЙС СОФТ ГРУПП".

Описание:
Вспомогательные функции для выполнения скриптов установки, замены строк в файлах
и определения фаз установки в системе NiceOS.
"""

import os
import re
import stat

# Константы фаз установки
PRE_INSTALL = "pre-install"
PRE_PKGS_INSTALL = "pre-pkgs-install"
POST_INSTALL = "post-install"


def replace_string_in_file(filename: str, search_pattern: str, replace_with: str) -> None:
    """
    Заменяет строки в файле по регулярному выражению.

    Args:
        filename: Путь к файлу, в котором нужно произвести замену.
        search_pattern: Регулярное выражение для поиска.
        replace_with: Строка, на которую будет произведена замена.

    Raises:
        OSError: Если произошла ошибка при чтении/записи файла.
        re.error: При ошибке компиляции регулярного выражения.
    """
    try:
        with open(filename, "r", encoding="utf-8") as source:
            lines = source.readlines()

        with open(filename, "w", encoding="utf-8") as destination:
            for line in lines:
                new_line = re.sub(search_pattern, replace_with, line)
                destination.write(new_line)
    except (OSError, re.error) as e:
        raise RuntimeError(f"Ошибка при замене строк в файле {filename}: {str(e)}") from e


def execute_scripts(installer, scripts: list, chroot: str = None, update_env: bool = False) -> None:
    """
    Выполняет список скриптов в chroot или текущем окружении.

    Args:
        installer: Объект установщика.
        scripts: Список путей к скриптам.
        chroot: Путь к корню chroot-окружения (или None).
        update_env: Обновлять ли переменные окружения при выполнении скрипта.

    Raises:
        Exception: Если скрипт не исполняемый или завершился с ошибкой.
    """
    for script_path in scripts:
        abs_path = script_path
        if chroot is not None:
            abs_path = os.path.join(chroot, script_path.lstrip("/"))

        if not os.access(abs_path, os.X_OK):
            raise Exception(f"Скрипт {script_path} не является исполняемым.")

        cmd = script_path
        if update_env:
            # Экспортировать все переменные окружения перед запуском
            cmd = ["/bin/bash", "-c", f"set -a && source {script_path}"]

        installer.logger.info(f"Выполнение скрипта: {script_path}")
        if chroot is None:
            retval = installer.cmd.run(cmd, update_env=update_env)
        else:
            retval = installer.cmd.run_in_chroot(chroot, cmd, update_env=update_env)

        if retval != 0:
            raise RuntimeError(f"Скрипт {script_path} завершился с ошибкой (код {retval})")


def make_script(directory: str, script_name: str, lines: list) -> None:
    """
    Создаёт исполняемый shell-скрипт из переданных строк.

    Args:
        directory: Каталог, в котором будет создан скрипт.
        script_name: Имя скрипта.
        lines: Список строк скрипта (тело команды).

    Raises:
        OSError: Если не удалось создать или записать файл.
    """
    script_path = os.path.join(directory, script_name)

    try:
        with open(script_path, "wt", encoding="utf-8") as f:
            for line in lines:
                f.write(f"{line}\n")

        os.chmod(script_path, stat.S_IRWXU)  # chmod 700
    except OSError as e:
        raise RuntimeError(f"Не удалось создать скрипт {script_path}: {str(e)}") from e
