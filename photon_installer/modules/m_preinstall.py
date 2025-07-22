#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
© 2025 ООО "НАЙС СОФТ ГРУПП" (ИНН 5024245440)
Контакты: <niceos@ncsgp.ru>

Описание:
Модуль для выполнения предустановочных скриптов в системе NiceOS.
Создает временную директорию, копирует и выполняет указанные скрипты с обновлением переменных окружения,
а затем удаляет временные файлы.
"""

import os
import commons
import shutil

install_phase = commons.PRE_INSTALL
enabled = True


def execute(installer):
    """
    Выполняет предустановочные скрипты для системы NiceOS.

    Args:
        installer: Объект установщика NiceOS.

    Raises:
        OSError: Если произошла ошибка при работе с файловой системой.
        RuntimeError: Если выполнение скриптов завершилось с ошибкой.
    """
    try:
        # Проверка наличия конфигурации для предустановки
        if (
            'preinstall' not in installer.install_config
            and 'preinstallscripts' not in installer.install_config
        ):
            installer.logger.debug("Конфигурация для предустановки отсутствует, пропуск")
            return

        scripts = []

        # Создание временной директории
        tmpdir = os.path.join("/tmp", "pre-install")
        installer.logger.debug(f"Создание временной директории: {tmpdir}")
        os.makedirs(tmpdir, exist_ok=True)

        # Обработка скрипта preinstall из конфигурации
        if 'preinstall' in installer.install_config:
            script_name = "preinstall-tmp.sh"
            installer.logger.debug(f"Создание скрипта {script_name}")
            commons.make_script(tmpdir, script_name, installer.install_config['preinstall'])
            scripts.append(os.path.join(tmpdir, script_name))
            installer.logger.debug(f"Скрипт {script_name} добавлен в список")

        # Обработка дополнительных скриптов из preinstallscripts
        for script in installer.install_config.get('preinstallscripts', []):
            script_file = installer.getfile(script)
            installer.logger.debug(f"Копирование скрипта {script_file} в {tmpdir}")
            shutil.copy(script_file, tmpdir)
            scripts.append(os.path.join(tmpdir, os.path.basename(script_file)))
            installer.logger.debug(f"Скрипт {os.path.basename(script_file)} добавлен в список")

        # Выполнение скриптов с обновлением переменных окружения
        installer.logger.info("Выполнение предустановочных скриптов")
        commons.execute_scripts(installer, scripts, update_env=True)
        installer.logger.info("Предустановочные скрипты успешно выполнены")

        # Удаление временной директории
        installer.logger.debug(f"Удаление временной директории: {tmpdir}")
        shutil.rmtree(tmpdir, ignore_errors=True)
        installer.logger.debug("Временная директория удалена")

    except OSError as e:
        installer.logger.error(f"Ошибка при работе с файловой системой: {str(e)}")
        raise OSError(f"Не удалось выполнить операции с файлами: {str(e)}") from e
    except RuntimeError as e:
        installer.logger.error(f"Ошибка выполнения скриптов: {str(e)}")
        raise RuntimeError(f"Ошибка выполнения предустановочных скриптов: {str(e)}") from e
