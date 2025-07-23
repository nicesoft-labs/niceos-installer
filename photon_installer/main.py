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
from colorama import init, Fore, Style
from commandutils import CommandUtils


def initialize_colors():
    """Initialize colorama for colored console output."""
    init(autoreset=True)


def parse_key_value_params(params_list):
    """Parse key=value parameters into a dictionary."""
    params = {}
    for param in params_list:
        try:
            key, value = param.split('=', 1)
            params[key] = yaml.safe_load(value)
        except ValueError:
            raise ValueError(
                f"{Fore.RED}Ошибка: Неверный формат параметра '{param}'. Ожидается формат 'ключ=значение'{Style.RESET_ALL}"
            )
    return params


def validate_arguments(options):
    """Validate input arguments."""
    if not options.photon_release_version:
        raise ValueError(f"{Fore.RED}Ошибка: Не указана версия Photon OS (--photon-release-version){Style.RESET_ALL}")
    if options.image_type not in ['iso', 'ova', 'ami']:
        raise ValueError(
            f"{Fore.RED}Ошибка: Неподдерживаемый тип образа '{options.image_type}'. "
            f"Доступные типы: iso, ova, ami{Style.RESET_ALL}"
        )
    if not options.working_directory:
        raise ValueError(f"{Fore.RED}Ошибка: Не указана рабочая директория (--working-directory){Style.RESET_ALL}")
    if not os.path.exists(options.working_directory):
        raise ValueError(
            f"{Fore.RED}Ошибка: Рабочая директория '{options.working_directory}' не существует{Style.RESET_ALL}"
        )
    if options.install_config_file and not os.path.isfile(options.install_config_file):
        raise ValueError(
            f"{Fore.RED}Ошибка: Файл конфигурации '{options.install_config_file}' не найден{Style.RESET_ALL}"
        )


def setup_argument_parser():
    """Set up the argument parser with a human-readable help message in Russian."""
    parser = ArgumentParser(
        description="Скрипт для создания установочных образов Photon OS",
        formatter_class=RawTextHelpFormatter,
        prog="photon-installer",
        epilog=(
            "Примеры использования:\n"
            "  photon-installer --image-type iso --photon-release-version 5.0 --working-directory /tmp/workdir\n"
            "  photon-installer --image-type ova --photon-release-version 5.0 --install-config ks.cfg "
            "--working-directory /tmp/workdir --repo-paths /repo1,/repo2"
        )
    )

    parser.add_argument(
        "-i", "--image-type",
        dest="image_type",
        help=(
            "Тип создаваемого образа:\n"
            "  iso - ISO-образ для установки\n"
            "  ova - Виртуальный образ OVA\n"
            "  ami - Образ для Amazon Machine Image"
        )
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
        help=(
            "Список путей к локальным RPM-репозиториям, разделённых запятыми\n"
            "Пример: /path/to/repo1,/path/to/repo2"
        )
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
        help="Каталог для хранения логов установки (по умолчанию: /var/log)"
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
        help=(
            "Дополнительные параметры в формате ключ=значение\n"
            "Можно указать несколько раз\n"
            "Пример: --param debug=true --param timeout=300"
        )
    )

    return parser


def main():
    """Main function to execute the installer."""
    initialize_colors()
    parser = setup_argument_parser()
    try:
        options = parser.parse_args()
    except SystemExit:
        # Перехватываем ошибку парсинга аргументов для кастомизации сообщения
        print(f"{Fore.RED}Ошибка: Не указана версия Photon OS. Пожалуйста, используйте флаг --photon-release-version{Style.RESET_ALL}")
        sys.exit(1)

    params = parse_key_value_params(options.params)

    try:
        validate_arguments(options)

        if options.image_type == 'iso':
            from isoInstaller import IsoInstaller
            installer = IsoInstaller(options, params=params)
            installer.execute()
        else:
            from installer import Installer
            if not options.install_config_file:
                raise ValueError(
                    f"{Fore.RED}Ошибка: Не указан файл конфигурации установки (--install-config){Style.RESET_ALL}"
                )

            with open(options.install_config_file) as f:
                install_config = CommandUtils.readConfig(f, params=params)

            if options.repo_paths is None and "repos" not in install_config:
                raise ValueError(
                    f"{Fore.RED}Ошибка: Не указаны репозитории! Используйте --repo-paths или настройте 'repos' "
                    f"в конфигурации{Style.RESET_ALL}"
                )

            installer = Installer(
                working_directory=options.working_directory,
                repo_paths=options.repo_paths,
                log_path=options.log_path,
                photon_release_version=options.photon_release_version
            )
            installer.configure(install_config)
            installer.execute()

    except Exception as err:
        print(f"{Fore.RED}Ошибка: {str(err)}{Style.RESET_ALL}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
