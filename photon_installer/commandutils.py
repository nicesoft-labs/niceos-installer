# /*
# * Copyright © 2020 VMware, Inc.
# * SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only
# */
# pylint: disable=invalid-name,missing-docstring
import subprocess
import os
import re
import glob
from passlib.hash import sha512_crypt
import shutil
import ssl
import requests
import copy
import json
from urllib.parse import urlparse
from urllib.request import urlopen
from OpenSSL.crypto import load_certificate, FILETYPE_PEM
import yaml


class CommandUtils(object):
    def __init__(self, logger):
        self.logger = logger
        self.hostRpmIsNotUsable = -1

    def run(self, cmd, update_env=False):
        """Запуск команды в оболочке или без нее с логированием и обновлением окружения."""
        self.logger.info(f"Запуск команды: {cmd}")
        use_shell = not isinstance(cmd, list)
        try:
            process = subprocess.Popen(
                cmd, shell=use_shell, text=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            out, err = process.communicate()
            if out != "":
                self.logger.info(f"Вывод команды: {out}")
                if update_env:
                    os.environ.clear()
                    os.environ.update(
                        dict(
                            line.partition("=")[::2]
                            for line in out.split("\0")
                            if line
                        )
                    )
            if process.returncode != 0:
                self.logger.error(f"Команда завершилась с ошибкой: {cmd}")
                self.logger.error(f"Код ошибки: {process.returncode}")
                self.logger.error(f"Ошибка: {err}")
            return process.returncode
        except Exception as e:
            self.logger.error(f"Ошибка при выполнении команды {cmd}: {str(e)}")
            return 1

    def run_in_chroot(self, chroot_path, cmd, update_env=False):
        """Запуск команды в chroot-окружении."""
        # Команда выполняется в chroot с использованием bash
        return self.run(["chroot", chroot_path, "/bin/bash", "-c", cmd], update_env)

    @staticmethod
    def is_vmware_virtualization():
        """Проверка, выполняется ли код в виртуальной машине VMware."""
        try:
            process = subprocess.Popen(["systemd-detect-virt"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = process.communicate()
            return process.returncode == 0 and out.decode().strip() == "vmware"
        except Exception:
            return False

    @staticmethod
    def generate_password_hash(password):
        """Генерация хэша для пароля."""
        return sha512_crypt.hash(password)

    @staticmethod
    def _requests_get(url, verify):
        """Выполнение HTTP GET-запроса с проверкой сертификата."""
        try:
            return requests.get(url, verify=verify, stream=True, timeout=5.0)
        except requests.RequestException:
            return None

    @staticmethod
    def exists_in_file(target_string, file_path):
        """
        Проверка наличия строки в файле.
        Возвращает False, если файл не существует.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                return any(target_string in line for line in file)
        except FileNotFoundError:
            return False
        except Exception as e:
            raise Exception(f"Ошибка при чтении файла {file_path}: {str(e)}")

    @staticmethod
    def is_url(url):
        """Проверка, является ли строка URL."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except ValueError:
            return False

    @staticmethod
    def load_json(url):
        """Чтение JSON из файла или URL."""
        try:
            if CommandUtils.is_url(url):
                with urlopen(url, timeout=5.0) as f:
                    return json.load(f)
            else:
                file_path = url[7:] if url.startswith("file://") else url
                with open(file_path, "rt", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            raise Exception(f"Ошибка при загрузке JSON из {url}: {str(e)}")

    @staticmethod
    def wget(url, out, enforce_https=True, ask_fn=None, fingerprint=None):
        """Загрузка файла по URL с проверкой HTTPS и сертификатов."""
        try:
            u = urlparse(url)
            if not all([u.scheme, u.netloc]):
                return False, "Недействительный URL"
            if enforce_https and u.scheme != "https":
                return False, "URL должен быть защищенным (HTTPS)"

            r = CommandUtils._requests_get(url, verify=True)
            if r is None:
                if fingerprint is None and ask_fn is None:
                    return False, "Не удалось проверить сертификат сервера"
                port = u.port if u.port else 443
                try:
                    pem = ssl.get_server_certificate((u.netloc, port))
                    cert = load_certificate(FILETYPE_PEM, pem)
                    fp = cert.digest("sha1").decode()
                except Exception:
                    return False, "Не удалось получить сертификат сервера"
                if ask_fn is not None and not ask_fn(fp):
                    return False, "Операция прервана пользователем"
                if fingerprint is not None and fingerprint != fp:
                    return False, f"Отпечаток сервера не совпадает. Получен: {fp}"
                r = CommandUtils._requests_get(url, verify=False)

            if r is None:
                return False, "Не удалось загрузить файл"
            r.raw.decode_content = True
            with open(out, "wb") as f:
                shutil.copyfileobj(r.raw, f)
            return True, None
        except Exception as e:
            return False, f"Ошибка загрузки файла: {str(e)}"

    def checkIfHostRpmNotUsable(self):
        """Проверка, поддерживает ли хост rpm zstd и sqlite."""
        if self.hostRpmIsNotUsable >= 0:
            return self.hostRpmIsNotUsable

        cmds = [
            "rpm --showrc | grep -qw 'rpmlib(PayloadIsZstd)'",
            "rpm -E %{_db_backend} | grep -qw 'sqlite'",
        ]

        for cmd in cmds:
            if self.run(cmd):
                self.hostRpmIsNotUsable = 1
                break
        else:
            self.hostRpmIsNotUsable = 0

        return self.hostRpmIsNotUsable

    @staticmethod
    def jsonread(filename):
        """Чтение JSON из файла."""
        try:
            with open(filename, "rt", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            raise Exception(f"Ошибка при чтении JSON из файла {filename}: {str(e)}")

    @staticmethod
    def _yaml_param(loader, node):
        """Обработка параметра YAML с поддержкой значений по умолчанию."""
        params = loader.app_params
        key = node.value
        assert isinstance(key, str), "Имя параметра должно быть строкой"

        if '=' in key:
            key, default = [t.strip() for t in key.split('=', maxsplit=1)]
            value = params.get(key, yaml.safe_load(default))
        else:
            assert key in params, f"Параметр '{key}' не задан и нет значения по умолчанию"
            value = params[key]

        return value

    @staticmethod
    def readConfig(stream, params=None):
        """Чтение конфигурации из YAML-потока с параметрами."""
        if params is None:
            params = {}
        try:
            yaml_loader = yaml.SafeLoader
            yaml_loader.app_params = params
            yaml.add_constructor("!param", CommandUtils._yaml_param, Loader=yaml_loader)
            return yaml.load(stream, Loader=yaml_loader)
        except Exception as e:
            raise Exception(f"Ошибка при чтении конфигурации YAML: {str(e)}")

    def convertToBytes(self, size):
        """Конвертация размера в байты (поддержка k, m, g, t)."""
        if not isinstance(size, str):
            return int(size)
        if not size[-1].isalpha():
            return int(size)
        conv = {'k': 1024, 'm': 1024**2, 'g': 1024**3, 't': 1024**4}
        try:
            return int(float(size[:-1]) * conv[size.lower()[-1]])
        except (ValueError, KeyError) as e:
            raise ValueError(f"Недопустимый формат размера: {size}")

    @staticmethod
    def get_disk_size_bytes(disk):
        """Получение размера диска в байтах."""
        cmd = ["blockdev", "--getsize64", disk]
        try:
            process = subprocess.Popen(
                cmd, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            out, err = process.communicate()
            if process.returncode == 0:
                return process.returncode, out.strip()
            return process.returncode, err.strip()
        except Exception as e:
            return 1, f"Ошибка при получении размера диска: {str(e)}"

    def get_vgnames(self):
        """Получение списка групп томов (Volume Groups)."""
        vg_list = []
        cmd = ["vgdisplay", "-c"]
        try:
            process = subprocess.Popen(
                cmd, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            out, err = process.communicate()
            if process.returncode == 0:
                vgdisplay_output = out.split("\n")
                for vg in vgdisplay_output:
                    if vg:
                        vg_list.append(vg.split(":")[0].strip())
            self.logger.info(f"Список групп томов: {vg_list}")
            return process.returncode, vg_list
        except Exception as e:
            self.logger.error(f"Ошибка при получении списка групп томов: {str(e)}")
            return 1, vg_list

    @staticmethod
    def write_pkg_list_file(file_path, packages_list):
        """Запись списка пакетов в JSON-файл."""
        try:
            with open(file_path, "w", encoding="utf-8") as json_file:
                json.dump(packages_list, json_file, indent=4)
            return file_path
        except Exception as e:
            raise Exception(f"Ошибка при записи JSON в файл {file_path}: {str(e)}")

    def replace_in_file(self, file_path, pattern, replacement):
        """Замена текста в файле с использованием регулярного выражения."""
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                file_contents = file.read()
            modified_contents = re.sub(pattern, replacement, file_contents)
            with open(file_path, "w", encoding="utf-8") as file:
                file.write(modified_contents)
            self.logger.info(f"Замена выполнена в файле: {file_path}")
        except FileNotFoundError:
            self.logger.error(f"Файл не найден: {file_path}")
            raise
        except Exception as e:
            raise Exception(f"Ошибка при замене в файле {file_path}: {str(e)}")

    def remove_files(self, file_list):
        """
        Удаление файлов или директорий по списку шаблонов.
        """
        for file_path in file_list:
            try:
                for file in glob.glob(file_path):
                    if os.path.isfile(file):
                        os.remove(file)
                        self.logger.info(f"Удален файл: {file}")
                    elif os.path.islink(file):
                        os.unlink(file)
                        self.logger.info(f"Удалена ссылка: {file}")
                    elif os.path.isdir(file):
                        shutil.rmtree(file)
                        self.logger.info(f"Удалена директория: {file}")
                    else:
                        self.logger.warning(f"Неизвестный тип файла: {file}")
            except FileNotFoundError:
                self.logger.info(f"Файл или путь не найден: {file_path}")
            except Exception as e:
                raise Exception(f"Ошибка при удалении {file_path}: {str(e)}")

    def acquire_file_map(self, map, dest_dir):
        """
        Копирование или загрузка файлов по карте соответствия источников и назначений.
        """
        for src, dest in map.items():
            try:
                if dest.startswith("/"):
                    dest = dest[1:]
                if not os.path.basename(dest):
                    dest = os.path.join(os.path.dirname(dest), os.path.basename(src))
                dest = os.path.join(dest_dir, dest)
                os.makedirs(os.path.dirname(dest), exist_ok=True)

                if src.startswith("file://"):
                    src = src[7:]
                if CommandUtils.is_url(src):
                    self.logger.info(f"Загрузка {src} в {dest}")
                    ret, err = CommandUtils.wget(src, dest)
                    if not ret:
                        raise Exception(f"Ошибка загрузки {src}: {err}")
                else:
                    self.logger.info(f"Копирование {src} в {dest}")
                    shutil.copyfile(src, dest)
            except Exception as e:
                raise Exception(f"Ошибка при обработке {src} -> {dest}: {str(e)}")
