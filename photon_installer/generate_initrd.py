#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
© 2025 ООО "НАЙС СОФТ ГРУПП" (ИНН 5024245440)
Контакты: <niceos@ncsgp.ru>
"""

import os
import stat
import shutil
import subprocess
import logging

from tdnf import Tdnf, create_repo_conf
from commandutils import CommandUtils


INITRD_FSTAB = """# Begin /etc/fstab for a bootable CD

# file system  mount-point  type   options         dump  fsck
#                                                        order
#/dev/EDITME     /            EDITME  defaults        1     1
#/dev/EDITME     swap         swap   pri=1           0     0
proc           /proc        proc   defaults        0     0
sysfs          /sys         sysfs  defaults        0     0
devpts         /dev/pts     devpts gid=4,mode=620  0     0
tmpfs          /dev/shm     tmpfs  defaults        0     0
tmpfs          /run         tmpfs  defaults        0     0
devtmpfs       /dev         devtmpfs mode=0755,nosuid 0   0
# End /etc/fstab
"""


class IsoInitrd:
    def __init__(self, **kwargs):
        """
        Инициализация класса для создания initrd-образа.

        Аргументы:
        - logger (logging.Logger, optional): Логгер для записи событий. Если None, логирование не выполняется.
        - working_dir (str): Рабочая директория для создания initrd.
        - initrd_pkgs (list): Список пакетов для установки в initrd.
        - rpms_path (str): Путь к RPM-пакетам.
        - niceos_release_version (str): Версия NiceOS Linux.
        - pkg_list_file (str): Путь к файлу со списком пакетов.
        - install_options_file (str): Путь к файлу с опциями установки.
        - ostree_iso (bool): Если True, используется OSTree ISO.
        - initrd_files (dict): Карта файлов для копирования в initrd.

        Выбрасывает:
        - KeyError: Если передан неизвестный аргумент.
        - ValueError: Если обязательные параметры отсутствуют или некорректны.
        """
        known_kw = [
            "logger",
            "working_dir",
            "initrd_pkgs",
            "rpms_path",
            "niceos_release_version",
            "pkg_list_file",
            "install_options_file",
            "ostree_iso",
            "initrd_files",
        ]
        if self.logger is not None:
            self.logger.debug(f"Инициализация IsoInitrd с параметрами: {kwargs}")

        # Проверка неизвестных аргументов
        for key in kwargs:
            if key not in known_kw:
                if self.logger is not None:
                    self.logger.error(f"Неизвестный аргумент: {key}")
                raise KeyError(f"{key} is not a known keyword")

        # Установка атрибутов
        for key in known_kw:
            setattr(self, key, kwargs.get(key, None))

        # Проверка обязательных параметров
        if not self.working_dir or not isinstance(self.working_dir, str):
            if self.logger is not None:
                self.logger.error(f"Недопустимая рабочая директория: {self.working_dir}")
            raise ValueError("working_dir должен быть непустой строкой")
        if not self.niceos_release_version or not isinstance(self.niceos_release_version, str):
            if self.logger is not None:
                self.logger.error(f"Недопустимая версия NiceOS: {self.niceos_release_version}")
            raise ValueError("niceos_release_version должен быть непустой строкой")
        if not self.initrd_pkgs or not isinstance(self.initrd_pkgs, list):
            if self.logger is not None:
                self.logger.error(f"Недопустимый список пакетов: {self.initrd_pkgs}")
            raise ValueError("initrd_pkgs должен быть непустым списком")

        self.cmd_util = CommandUtils(self.logger)
        self.initrd_path = os.path.join(self.working_dir, "niceos-chroot")
        self.license_text = f"NiceSOFT {self.niceos_release_version} ЛИЦЕНЗИОННОЕ СОГЛАШЕНИЕ"
        
        try:
            if CommandUtils.exists_in_file(
                "BETA LICENSE AGREEMENT", os.path.join(self.working_dir, "EULA.txt"), logger=self.logger
            ):
                self.license_text = f"NiceSOFT {self.niceos_release_version} BETA ЛИЦЕНЗИОННОЕ СОГЛАШЕНИЕ"
                if self.logger is not None:
                    self.logger.debug(f"Обнаружен BETA LICENSE, текст лицензии: {self.license_text}")
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка проверки EULA.txt: {str(e)}")
            raise

        self.tdnf = Tdnf(
            logger=self.logger,
            reposdir=self.working_dir,
            releasever=self.niceos_release_version,
            installroot=self.initrd_path,
            docker_image=f"niceos:{self.niceos_release_version}",
        )
        if self.logger is not None:
            self.logger.debug("Tdnf инициализирован")

    def create_installer_script(self):
        """
        Создание скрипта установщика для initrd.
        """
        if self.logger is not None:
            self.logger.debug("Создание скрипта установщика")

        install_options_file = os.path.basename(self.install_options_file)
        script_content = f"""#!/bin/bash
cd /installer
ACTIVE_CONSOLE="$(< /sys/devices/virtual/tty/console/active)"
install() {{
    LANG=ru_RU.UTF-8 niceos-installer -i iso -o {install_options_file} -e EULA.txt -t "{self.license_text}" -v {self.niceos_release_version} && shutdown -r now
}}
try_run_installer() {{
    if [ "$ACTIVE_CONSOLE" == "tty0" ]; then
        [ "$(tty)" == '/dev/tty1' ] && install
    else
        [ "$(tty)" == "/dev/$ACTIVE_CONSOLE" ] && install
    fi
}}
try_run_installer || exec /bin/bash
"""
        try:
            script_path = f"{self.initrd_path}/bin/bootniceosinstaller"
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(script_content)
            os.chmod(script_path, 0o755)
            if self.logger is not None:
                self.logger.info(f"Скрипт установщика создан: {script_path}")
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при создании скрипта установщика: {str(e)}")
            raise

    def create_init_script(self):
        """
        Создание init-скрипта для initrd.
        """
        if self.logger is not None:
            self.logger.debug("Создание init-скрипта")

        try:
            script_path = f"{self.initrd_path}/init"
            with open(script_path, "w", encoding="utf-8") as init_script:
                init_script.writelines(["mount -t proc proc /proc\n", "/lib/systemd/systemd"])
            os.chmod(script_path, 0o755)
            if self.logger is not None:
                self.logger.info(f"Init-скрипт создан: {script_path}")
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при создании init-скрипта: {str(e)}")
            raise

    def strip_if_needed(self, file_path):
        """
        Удаление отладочной информации из ELF-файлов, если необходимо.

        Аргументы:
        - file_path (str): Путь к файлу для проверки.
        """
        if self.logger is not None:
            self.logger.debug(f"Проверка файла на необходимость strip: {file_path}")

        try:
            output = subprocess.check_output(["file", file_path], text=True)
            stripped_files = [
                line.split(":")[0]
                for line in output.splitlines()
                if "ELF" in line and "not stripped" in line
            ]
            for stripped_file in stripped_files:
                self.cmd_util.run(["strip", stripped_file])
                if self.logger is not None:
                    self.logger.debug(f"Файл обработан strip: {stripped_file}")
        except subprocess.CalledProcessError as err:
            if self.logger is not None:
                self.logger.error(f"Ошибка обработки файла {file_path}: {str(err)}")
            raise Exception(f"Failed to strip {file_path} with err: {err}")
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при strip файла {file_path}: {str(e)}")
            raise

    def process_files(self):
        """
        Обработка файлов в директории usr/lib для удаления отладочной информации.
        """
        if self.logger is not None:
            self.logger.debug("Обработка файлов в usr/lib")

        lib_directory = os.path.join(self.initrd_path, "usr/lib")
        try:
            for file in os.listdir(lib_directory):
                file_path = os.path.join(lib_directory, file)
                if os.path.isfile(file_path):
                    self.strip_if_needed(file_path)
            if self.logger is not None:
                self.logger.info("Обработка файлов в usr/lib завершена")
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при обработке файлов в {lib_directory}: {str(e)}")
            raise

    def clean_up(self):
        """
        Очистка ненужных файлов и директорий в initrd.
        """
        if self.logger is not None:
            self.logger.debug("Запуск очистки ненужных файлов")

        exclusions = ["terminfo", "cracklib", "grub", "factory", "dbus-1", "ansible", "consolefonts", "consoletrans", "keymaps", "unimaps"]
        dir_to_list = ["usr/share", "usr/sbin"]
        listed_contents = []
        files_to_remove = [
            "/home/*",
            "/var/cache",
            "/var/lib/rpm*",
            "/var/lib/.rpm*",
            "/usr/lib/sysimage/rpm*",
            "/usr/lib/sysimage/.rpm",
            "/usr/lib/sysimage/tdnf",
            "/boot",
            "/usr/include",
            "/usr/sbin/sln",
            "/usr/bin/iconv",
            "/usr/bin/oldfind",
            "/usr/bin/localedef",
            "/usr/bin/sqlite3",
            "/usr/bin/grub2-*",
            "/usr/bin/bsdcpio",
            "/usr/bin/bsdtar",
            "/usr/bin/networkctl",
            "/usr/bin/machinectl",
            "/usr/bin/pkg-config",
            "/usr/bin/openssl",
            "/usr/bin/timedatectl",
            "/usr/bin/localectl",
            "/usr/bin/systemd-cgls",
            "/usr/bin/systemd-analyze",
            "/usr/bin/systemd-nspawn",
            "/usr/bin/systemd-inhibit",
            "/usr/bin/systemd-studio-bridge",
            "/usr/lib/python*/lib2to3",
            "/usr/lib/python*/lib-tk",
            "/usr/lib/python*/ensurepip",
            "/usr/lib/python*/distutils",
            "/usr/lib/python*/pydoc_data",
            "/usr/lib/python*/idlelib",
            "/usr/lib/python*/unittest",
            "/usr/lib/librpmbuild.so*",
            "/usr/lib/libdb_cxx*",
            "/usr/lib/libnss_compat*",
            "/usr/lib/grub/i386-pc/*.module",
            "/usr/lib/grub/x86_64-efi/*.module",
            "/usr/lib/grub/arm64-efi/*.module",
            "/usr/lib/libmvec*",
            "/usr/lib/gconv",
        ]

        try:
            for directory in dir_to_list:
                dir_path = os.path.join(self.initrd_path, directory)
                if os.path.exists(dir_path):
                    contents = os.listdir(dir_path)
                    listed_contents.extend([os.path.join(directory, c) for c in contents])
                    if self.logger is not None:
                        self.logger.debug(f"Сканирование директории {dir_path}: найдено {len(contents)} элементов")
            
            for file_name in listed_contents:
                if os.path.basename(file_name) not in exclusions:
                    files_to_remove.append(file_name)
                if file_name.startswith("usr/sbin/grub2") and file_name != "usr/sbin/grub2-install":
                    files_to_remove.append(file_name)
            
            files_to_remove = [os.path.join(self.initrd_path, f.lstrip("/")) for f in files_to_remove]
            self.cmd_util.remove_files(files_to_remove)
            if self.logger is not None:
                self.logger.info(f"Очистка завершена, удалено {len(files_to_remove)} файлов")
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при очистке: {str(e)}")
            raise

    def install_initrd_packages(self):
        """
        Установка пакетов в initrd с помощью tdnf.
        """
        if self.logger is not None:
            self.logger.debug(f"Установка пакетов initrd: {self.initrd_pkgs}")

        if isinstance(self.initrd_pkgs, str):
            tdnf_args = ["--rpmverbosity", "10", "install"] + self.initrd_pkgs.split()
        else:
            tdnf_args = ["--rpmverbosity", "10", "install"] + self.initrd_pkgs

        mount_dirs = []
        if self.ostree_iso:
            self.tdnf.config_file = None
            self.tdnf.reposdir = None
            if self.logger is not None:
                self.logger.debug("OSTree ISO: отключены config_file и reposdir")
        else:
            mount_dirs = [self.rpms_path, self.working_dir]
            if self.logger is not None:
                self.logger.debug(f"Подключение директорий для tdnf: {mount_dirs}")

        try:
            self.tdnf.run(tdnf_args, directories=mount_dirs)
            if self.logger is not None:
                self.logger.info("Пакеты initrd успешно установлены")
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка установки пакетов initrd: {str(e)}")
            raise

    def prepare_installer_dir(self):
        """
        Подготовка директории установщика.
        """
        if self.logger is not None:
            self.logger.debug("Подготовка директории установщика")

        installer_dir = os.path.join(self.initrd_path, "installer")
        try:
            if not os.path.exists(installer_dir):
                os.mkdir(installer_dir)
                if self.logger is not None:
                    self.logger.debug(f"Создана директория: {installer_dir}")
            
            shutil.copy(self.install_options_file, installer_dir)
            if self.logger is not None:
                self.logger.debug(f"Скопирован файл опций: {self.install_options_file}")
            
            if self.pkg_list_file:
                shutil.copy(self.pkg_list_file, installer_dir)
                if self.logger is not None:
                    self.logger.debug(f"Скопирован файл списка пакетов: {self.pkg_list_file}")
            
            self.cmd_util.acquire_file_map(self.initrd_files, self.initrd_path)
            if self.logger is not None:
                self.logger.info("Директория установщика подготовлена")
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при подготовке директории установщика: {str(e)}")
            raise

    def build_initrd(self):
        """
        Сборка initrd-образа.
        """
        if self.logger is not None:
            self.logger.debug("Запуск сборки initrd-образа")

        try:
            os.makedirs(self.initrd_path, exist_ok=True)
            os.chmod(self.initrd_path, 0o755)
            if self.logger is not None:
                self.logger.debug(f"Создана директория initrd: {self.initrd_path}")

            if not self.ostree_iso:
                create_repo_conf(
                    {
                        "niceos-local": {
                            "name": "NiceSOFT NiceOS Linux (x86_64)",
                            "baseurl": f"file://{self.rpms_path}",
                            "gpgcheck": 0,
                            "enabled": 1,
                            "skip_if_unavailable": True,
                        }
                    },
                    reposdir=self.working_dir,
                )
                if self.logger is not None:
                    self.logger.debug("Создан локальный репозиторий niceos-local")

            self.install_initrd_packages()

            with open(f"{self.initrd_path}/etc/locale.conf", "w", encoding="utf-8") as locale_conf:
                locale_conf.write("LANG=ru_RU.UTF-8")
                if self.logger is not None:
                    self.logger.debug("Создан файл locale.conf")

            with open(f"{self.initrd_path}/etc/hostname", "w", encoding="utf-8") as hostname:
                hostname.write("niceos-installer\n")
                if self.logger is not None:
                    self.logger.debug("Создан файл hostname")

            self.cmd_util.remove_files([f"{self.initrd_path}/var/cache/tdnf"])
            shutil.move(f"{self.initrd_path}/boot", self.working_dir)
            if self.logger is not None:
                self.logger.debug(f"Перемещена директория boot в {self.working_dir}")

            self.prepare_installer_dir()

            retval = self.cmd_util.run_in_chroot(self.initrd_path, "/bin/systemd-machine-id-setup")
            if self.logger is not None:
                self.logger.debug(f"Результат systemd-machine-id-setup: {retval}")

            if retval:
                alt_cmd = f"chroot {self.initrd_path} date -Ins | md5sum | cut -f1 -d' '"
                hash_value = subprocess.check_output(
                    alt_cmd, shell=True, stderr=subprocess.STDOUT, text=True
                ).strip()
                with open(f"{self.initrd_path}/etc/machine-id", "w", encoding="utf-8") as machine_id:
                    machine_id.write(hash_value)
                if self.logger is not None:
                    self.logger.debug(f"Создан machine-id: {hash_value}")

            self.cmd_util.run_in_chroot(self.initrd_path, "/usr/sbin/pwconv")
            self.cmd_util.run_in_chroot(self.initrd_path, "/usr/sbin/grpconv")
            if self.logger is not None:
                self.logger.debug("Выполнены pwconv и grpconv")

            os.mkfifo(f"{self.initrd_path}/dev/initctl")
            for idx in range(0, 4):
                os.mknod(
                    f"{self.initrd_path}/dev/ram{idx}",
                    mode=stat.S_IFBLK | 0o660,
                    device=os.makedev(1, idx),
                )
            os.mknod(
                f"{self.initrd_path}/dev/sda",
                mode=stat.S_IFBLK | 0o660,
                device=os.makedev(8, 0),
            )
            if self.logger is not None:
                self.logger.debug("Созданы необходимые устройства в /dev")

            if not os.path.exists(f"{self.initrd_path}/etc/systemd/scripts"):
                os.makedirs(f"{self.initrd_path}/etc/systemd/scripts")
                if self.logger is not None:
                    self.logger.debug("Создана директория /etc/systemd/scripts")

            create_repo_conf(
                {
                    "niceos-iso": {
                        "name": "NiceSOFT NiceOS Linux (x86_64)",
                        "baseurl": "file:///mnt/media/RPMS",
                        "gpgkey": "file:///etc/pki/rpm-gpg/RPM-GPG-KEY-NICEOS",
                        "gpgcheck": 1,
                        "enabled": 1,
                        "skip_if_unavailable": True,
                    }
                },
                reposdir=f"{self.initrd_path}/etc/yum.repos.d",
            )
            if self.logger is not None:
                self.logger.debug("Создан репозиторий niceos-iso")

            self.create_installer_script()
            self.create_init_script()

            with open(f"{self.initrd_path}/etc/fstab", "w", encoding="utf-8") as fstab:
                fstab.write(INITRD_FSTAB)
                if self.logger is not None:
                    self.logger.debug("Создан файл fstab")

            self.cmd_util.replace_in_file(
                f"{self.initrd_path}/lib/systemd/system/getty@.service",
                "ExecStart.*",
                "ExecStart=-/sbin/agetty --autologin root --noclear %I linux",
            )
            self.cmd_util.replace_in_file(
                f"{self.initrd_path}/lib/systemd/system/serial-getty@.service",
                "ExecStart.*",
                "ExecStart=-/sbin/agetty --autologin root --keep-baud 115200,38400,9600 %I screen",
            )
            self.cmd_util.replace_in_file(
                f"{self.initrd_path}/etc/passwd",
                "root:.*",
                "root:x:0:0:root:/root:/bin/bootniceosinstaller",
            )
            if self.logger is not None:
                self.logger.debug("Обновлены файлы getty и passwd")

            os.symlink("/dev/null", f"{self.initrd_path}/etc/systemd/system/vmtoolsd.service")
            os.symlink("/dev/null", f"{self.initrd_path}/etc/systemd/system/vgauthd.service")
            if self.logger is not None:
                self.logger.debug("Созданы символьные ссылки для vmtoolsd и vgauthd")

            os.makedirs(f"{self.initrd_path}/mnt/niceos-root/niceos-chroot", exist_ok=True)
            if self.logger is not None:
                self.logger.debug("Создана директория /mnt/niceos-root/niceos-chroot")

            self.process_files()
            self.clean_up()

            self.cmd_util.run_in_chroot(self.initrd_path, "chage -M 99999 root")
            if self.logger is not None:
                self.logger.debug("Установлен срок действия пароля root")

            if self.logger is not None:
                self.logger.info(f"Генерация initrd-образа: {self.working_dir}/initrd.img")
            
            cur_dir = os.getcwd()
            os.chdir(self.initrd_path)
            self.cmd_util.run(
                f"(find . | cpio -o -H newc --quiet | gzip -9) > {self.working_dir}/initrd.img"
            )
            os.chdir(cur_dir)
            if self.logger is not None:
                self.logger.info(f"Initrd-образ создан: {self.working_dir}/initrd.img")

            if self.logger is not None:
                self.logger.info("Очистка директории initrd и JSON-файла")
            self.cmd_util.remove_files(
                [self.initrd_path, f"{self.working_dir}/packages_installer_initrd.json"]
            )
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при сборке initrd-образа: {str(e)}")
            raise
