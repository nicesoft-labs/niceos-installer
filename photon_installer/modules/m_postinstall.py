#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
© 2025 ООО "НАЙС СОФТ ГРУПП" (ИНН 5024245440)
Контакты: <niceos@ncsgp.ru>

Запрещается любое изменение, копирование или распространение данного программного обеспечения
без письменного разрешения ООО "НАЙС СОФТ ГРУПП".

Описание:
Модуль для выполнения пост-установочных скриптов в системе NiceOS.
Создает временную директорию, копирует и выполняет указанные скрипты,
а затем удаляет временные файлы.
"""

import os
import commons
import shutil

install_phase = commons.POST_INSTALL
enabled = True


def execute(installer):
    """
    Выполняет пост-установочные скрипты для системы NiceOS.

    Args:
        installer: Объект установщика NiceOS.

    Raises:
        OSError: Если произошла ошибка при работе с файловой системой.
        RuntimeError: Если выполнение скриптов завершилось с ошибкой.
    """
    try:
        # Проверка наличия конфигурации для пост-установки
        if (
            'postinstall' not in installer.install_config
            and 'postinstallscripts' not in installer.install_config
        ):
            installer.logger.debug("Конфигурация для пост-установки отсутствует, пропуск")
            return

        scripts = []

        # Создание временной директории
        tmpdir = os.path.join("/tmp", "post-install")
        tmpdir_abs = os.path.join(installer.niceos_root, tmpdir.lstrip("/"))
        installer.logger.debug(f"Создание временной директории: {tmpdir_abs}")
        os.makedirs(tmpdir_abs, exist_ok=True)

        # Обработка скрипта postinstall из конфигурации
        if 'postinstall' in installer.install_config:
            script_name = "postinstall-tmp.sh"
            installer.logger.debug(f"Создание скрипта {script_name}")
            commons.make_script(tmpdir_abs, script_name, installer.install_config['postinstall'])
            scripts.append(os.path.join(tmpdir, script_name))
            installer.logger.debug(f"Скрипт {script_name} добавлен в список")

        # Обработка дополнительных скриптов из postinstallscripts
        for script in installer.install_config.get('postinstallscripts', []):
            script_file = installer.getfile(script)
            installer.logger.debug(f"Копирование скрипта {script_file} в {tmpdir_abs}")
            shutil.copy(script_file, tmpdir_abs)
            scripts.append(os.path.join(tmpdir, os.path.basename(script_file)))
            installer.logger.debug(f"Скрипт {os.path.basename(script_file)} добавлен в список")

        # Выполнение скриптов
        installer.logger.info("Выполнение пост-установочных скриптов")
        commons.execute_scripts(installer, scripts, chroot=installer.niceos_root)
        installer.logger.info("Пост-установочные скрипты успешно выполнены")

        # Удаление временной директории
        installer.logger.debug(f"Удаление временной директории: {tmpdir_abs}")
        shutil.rmtree(tmpdir_abs, ignore_errors=True)
        installer.logger.debug("Временная директория удалена")

    except OSError as e:
        installer.logger.error(f"Ошибка при работе с файловой системой: {str(e)}")
        raise OSError(f"Не удалось выполнить операции с файлами: {str(e)}") from e
    except RuntimeError as e:
        installer.logger.error(f"Ошибка выполнения скриптов: {str(e)}")
        raise RuntimeError(f"Ошибка выполнения пост-установочных скриптов: {str(e)}") from e
