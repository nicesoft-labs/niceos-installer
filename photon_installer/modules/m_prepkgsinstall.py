#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
© 2025 ООО "НАЙС СОФТ ГРУПП" (ИНН 5024245440)
Контакты: <niceos@ncsgp.ru>

Описание:
Модуль для выполнения скриптов перед установкой пакетов в системе NiceOS.
Создает временную директорию, копирует и выполняет указанные скрипты,
а затем удаляет временные файлы.
"""

import os
import commons
import shutil

install_phase = commons.PRE_PKGS_INSTALL
enabled = True


def execute(installer):
    """
    Выполняет скрипты перед установкой пакетов для системы NiceOS.

    Args:
        installer: Объект установщика NiceOS.

    Raises:
        OSError: Если произошла ошибка при работе с файловой системой.
        RuntimeError: Если выполнение скриптов завершилось с ошибкой.
    """
    try:
        # Проверка наличия конфигурации для скриптов перед установкой пакетов
        if (
            'prepkgsinstall' not in installer.install_config
            and 'prepkgsinstallscripts' not in installer.install_config
        ):
            installer.logger.debug("Конфигурация для скриптов перед установкой пакетов отсутствует, пропуск")
            return

        # Установка переменной окружения POI_ROOT
        installer.logger.debug(f"Установка переменной окружения POI_ROOT={installer.niceos_root}")
        os.environ['POI_ROOT'] = installer.niceos_root

        scripts = []

        # Создание временной директории
        tmpdir = os.path.join("/tmp", "prepkgs-install")
        installer.logger.debug(f"Создание временной директории: {tmpdir}")
        os.makedirs(tmpdir, exist_ok=True)

        # Обработка скрипта prepkgsinstall из конфигурации
        if 'prepkgsinstall' in installer.install_config:
            script_name = "prepkgsinstall-tmp.sh"
            installer.logger.debug(f"Создание скрипта {script_name}")
            commons.make_script(tmpdir, script_name, installer.install_config['prepkgsinstall'])
            scripts.append(os.path.join(tmpdir, script_name))
            installer.logger.debug(f"Скрипт {script_name} добавлен в список")

        # Обработка дополнительных скриптов из prepkgsinstallscripts
        for script in installer.install_config.get('prepkgsinstallscripts', []):
            script_file = installer.getfile(script)
            installer.logger.debug(f"Копирование скрипта {script_file} в {tmpdir}")
            shutil.copy(script_file, tmpdir)
            scripts.append(os.path.join(tmpdir, os.path.basename(script_file)))
            installer.logger.debug(f"Скрипт {os.path.basename(script_file)} добавлен в список")

        # Выполнение скриптов
        installer.logger.info("Выполнение скриптов перед установкой пакетов")
        commons.execute_scripts(installer, scripts)
        installer.logger.info("Скрипты перед установкой пакетов успешно выполнены")

        # Удаление временной директории
        installer.logger.debug(f"Удаление временной директории: {tmpdir}")
        shutil.rmtree(tmpdir, ignore_errors=True)
        installer.logger.debug("Временная директория удалена")

    except OSError as e:
        installer.logger.error(f"Ошибка при работе с файловой системой: {str(e)}")
        raise OSError(f"Не удалось выполнить операции с файлами: {str(e)}") from e
    except RuntimeError as e:
        installer.logger.error(f"Ошибка выполнения скриптов: {str(e)}")
        raise RuntimeError(f"Ошибка выполнения скриптов перед установкой пакетов: {str(e)}") from e
