#/*
# * Copyright © 2020-2023 VMware, Inc.
# * SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only
# */
from os.path import dirname, join
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
import sys
import traceback
from commandutils import CommandUtils
import yaml

class RussianArgumentParser(ArgumentParser):
    """Класс парсера аргументов, выводящий сообщения об ошибках на русском."""

    def error(self, message):
        sys.stderr.write(f"Ошибка: {message}\n\n")
        self.print_help()
        sys.exit(2)

def main():
    parser = RussianArgumentParser(
        description=(
            "Установщик NiceOS. Позволяет создавать ISO-образ или выполнить "
            "установку из локального репозитория."
        ),
        epilog=(
            "Пример:\n"
            "  python3 main.py -c sample_ks.cfg -r /path/to/repo -w /mnt/niceos-root -v 5.2"
        ),
        formatter_class=ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "-i",
        "--image-type",
        dest="image_type",
        help="Тип создаваемого образа (например, iso)",
    )
    parser.add_argument(
        "-c",
        "--install-config",
        dest="install_config_file",
        help="Путь к файлу конфигурации установки (kickstart)",
    )
    parser.add_argument(
        "-u",
        "--ui-config",
        dest="ui_config_file",
        help="Файл настроек графического интерфейса установщика",
    )
    # comma separated paths to rpms
    parser.add_argument(
        "-r",
        "--repo-paths",
        dest="repo_paths",
        default=None,
        help="Список путей к каталогам с RPM-пакетами, разделённый запятыми",
    )
    parser.add_argument(
        "-o",
        "--options-file",
        dest="options_file",
        help="JSON-файл с дополнительными опциями",
    )
    parser.add_argument(
        "-w",
        "--working-directory",
        dest="working_directory",
        help="Рабочая директория для установки системы",
    )
    parser.add_argument(
        "-l",
        "--log-path",
        dest="log_path",
        default="/var/log",
        help="Каталог для размещения лог-файлов",
    )
    parser.add_argument(
        "-e",
        "--eula-file",
        dest="eula_file_path",
        default=None,
        help="Путь к файлу лицензионного соглашения (EULA)",
    )
    parser.add_argument(
        "-t",
        "--license-title",
        dest="license_display_title",
        default=None,
        help="Заголовок окна отображения лицензии",
    )
    parser.add_argument(
        "-v",
        "--niceos-release-version",
        dest="niceos_release_version",
        required=True,
        help="Версия релиза NiceOS (обязательный аргумент)",
    )
    parser.add_argument(
        "-p",
        "--param",
        dest="params",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help=(
            "Дополнительный параметр в формате ключ=значение. "
            "Может быть указан несколько раз"
        ),
    )

    options = parser.parse_args()

    params = {}
    for p in options.params:
        k,v = p.split('=', maxsplit=1)
        params[k] = yaml.safe_load(v)

    try:
        if options.image_type == 'iso':
            from isoInstaller import IsoInstaller
            IsoInstaller(options, params=params)
        else:
            from installer import Installer
            import json
            install_config = None
            if options.install_config_file:
                with open(options.install_config_file) as f:
                    install_config = CommandUtils.readConfig(f, params=params)
            else:
                raise Exception('install config file not provided')
            if options.repo_paths is None and "repos" not in install_config:
                raise Exception('No repo available! Specify repo via "--repo-paths" or "repos" in install_config')
            if not options.working_directory:
                raise Exception('Please provide "--working-directory"')

            installer = Installer(working_directory=options.working_directory, repo_paths=options.repo_paths,
                                log_path=options.log_path, niceos_release_version=options.niceos_release_version)
            installer.configure(install_config)
            installer.execute()
    except Exception as err:
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

