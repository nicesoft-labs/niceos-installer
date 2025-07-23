#!/usr/bin/env python3
#/*
# * Copyright © 2020-2025 VMware, Inc.
# * SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only
# */
import os
from os.path import dirname, join
from argparse import ArgumentParser, RawTextHelpFormatter
import sys
import traceback
import yaml
from commandutils import CommandUtils


def parse_key_value_params(params_list):
    """Парсит параметры в формате ключ=значение в словарь."""
    params = {}
    for param in params_list:
        try:
            key, value = param.split('=', 1)
            params[key] = yaml.safe_load(value)
        except ValueError:
            raise ValueError(f"Неверный формат параметра: {param}. Ожидается формат 'ключ=значение'")
    return params


def validate_arguments(options):
    """Проверяет входные аргументы на корректность."""
    if not options.photon_release_version:
        raise ValueError("Не указана версия Photon OS (--photon-release-version)")
    if options.image_type not in ['iso', 'ova', 'ami']:
        raise ValueError(f"Неподдерживаемый тип образа: {options.image_type}. Доступные типы: iso, ova, ami")
    if not options.working_directory:
        raise ValueError("Не указана рабочая директория (--working-directory)")
    if not os.path.exists(options.working_directory):
        raise ValueError(f"Рабочая директория {options.working_directory} не существует")
    if options.install_config_file and not os.path.isfile(options.install_config_file):
        raise ValueError(f"Файл конфигурации {options.install_config_file} не найден")


def setup_argument_parser():
    """Настраивает парсер аргументов с человекопонятной справкой."""
    parser = ArgumentParser(
        description="Скрипт для создания установочных образов Photon OS",
        formatter_class=RawTextHelpFormatter
    )

    parser.add_argument(
        "-i", "--image-type",
        dest="image_type",
        help="Тип создаваемого образа:\n"
             "  iso - ISO-образ для установки\n"
             "  ova - Виртуальный образ OVA\n"
             "  ami - Образ для Amazon Machine Image"
    )
    parser.add_argument(
        "-c", "--install-config",
        dest="install_config_file",
        help="Путь к файлу конфигурации установки (например, kickstart-файл)"
    )
    parser.add_argument(
        "-u", "--ui-config",
        dest="ui_config_file",
        help="Путь к файлу конфигурации пользовательского интерфейса"
    )
    parser.add_argument(
        "-r", "--repo-paths",
        dest="repo_paths",
        default=None,
        help="Список путей к локальным RPM-репозиториям, разделённых запятыми\n"
             "Пример: /path/to/repo1,/path/to/repo2"
    )
    parser.add_argument(
        "-o", "--options-file",
        dest="options_file",
        help="Путь к файлу с дополнительными параметрами установки"
    )
    parser.add_argument(
        "-w", "--working-directory",
        dest="working_directory",
        help="Рабочая директория для хранения временных файлов"
    )
    parser.add_argument(
        "-l", "--log-path",
        dest="log_path",
        default="/var/log",
        help="Каталог для хранения логов установки\n"
             "По умолчанию: /var/log"
    )
    parser.add_argument(
        "-t", "--license-title",
        dest="license_display_title",
        default=None,
        help="Заголовок окна лицензионного соглашения"
    )
    parser.add_argument(
        "-v", "--photon-release-version",
        dest="photon_release_version",
        required=True,
        help="Версия Photon OS (например, 5.0)"
    )
    parser.add_argument(
        "-p", "--param",
        dest="params",
        action="append",
        default=[],
        help="Дополнительные параметры в формате ключ=значение\n"
             "Можно указать несколько раз\n"
             "Пример: --param debug=true --param timeout=300"
    )

    return parser


def main():
    """Основная функция скрипта."""
    parser = setup_argument_parser()
    options = parser.parse_args()

    try:
        # Парсинг дополнительных параметров
        params = parse_key_value_params(options.params)

        # Валидация аргументов
        validate_arguments(options)

        if options.image_type == 'iso':
            from isoInstaller import IsoInstaller
            installer = IsoInstaller(options, params=params)
            installer.execute()
        else:
            from installer import Installer
            if not options.install_config_file:
                raise ValueError("Не указан файл конфигурации установки (--install-config)")
            
            # Чтение конфигурации
            with open(options.install_config_file) as f:
                install_config = CommandUtils.readConfig(f, params=params)
            
            if options.repo_paths is None and "repos" not in install_config:
                raise ValueError("Не указаны репозитории! Используйте --repo-paths или настройте 'repos' в конфигурации")

            # Инициализация и выполнение установки
            installer = Installer(
                working_directory=options.working_directory,
                repo_paths=options.repo_paths,
                log_path=options.log_path,
                photon_release_version=options.photon_release_version
            )
            installer.configure(install_config)
            installer.execute()

    except Exception as err:
        print(f"Ошибка: {str(err)}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
