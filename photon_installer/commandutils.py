#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
© 2025 ООО "НАЙС СОФТ ГРУПП" (ИНН 5024245440)
Контакты: <niceos@ncsgp.ru>
"""

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
        self.logger.debug("Инициализация CommandUtils с логгером")

    def run(self, cmd, update_env=False):
        """Запуск команды в оболочке или без нее с логированием и обновлением окружения."""
        self.logger.info(f"Запуск команды: {cmd}")
        self.logger.debug(f"Параметр update_env: {update_env}")
        use_shell = not isinstance(cmd, list)
        self.logger.debug(f"Используется shell: {use_shell}")
        try:
            process = subprocess.Popen(
                cmd, shell=use_shell, text=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            self.logger.debug(f"Процесс запущен с PID: {process.pid}")
            out, err = process.communicate()
            if out:
                self.logger.info(f"Вывод команды: {out}")
                if update_env:
                    self.logger.debug("Обновление окружения на основе вывода команды")
                    os.environ.clear()
                    env_update = dict(line.partition("=")[::2] for line in out.split("\0") if line)
                    self.logger.debug(f"Обновляемые переменные окружения: {env_update}")
                    os.environ.update(env_update)
            else:
                self.logger.debug("Команда не вернула вывода")
            if process.returncode != 0:
                self.logger.error(f"Команда завершилась с ошибкой: {cmd}")
                self.logger.error(f"Код ошибки: {process.returncode}")
                self.logger.error(f"Ошибка: {err}")
            else:
                self.logger.debug(f"Команда успешно выполнена с кодом: {process.returncode}")
            return process.returncode
        except Exception as e:
            self.logger.error(f"Ошибка при выполнении команды {cmd}: {str(e)}")
            return 1

    def run_in_chroot(self, chroot_path, cmd, update_env=False):
        """Запуск команды в chroot-окружении."""
        self.logger.info(f"Запуск команды в chroot: {cmd} в {chroot_path}")
        self.logger.debug(f"Параметр update_env: {update_env}")
        # Команда выполняется в chroot с использованием bash
        return self.run(["chroot", chroot_path, "/bin/bash", "-c", cmd], update_env)

    @staticmethod
    def is_vmware_virtualization(logger):
        """Проверка, выполняется ли код в виртуальной машине VMware."""
        logger.debug("Проверка виртуализации VMware")
        try:
            process = subprocess.Popen(["systemd-detect-virt"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = process.communicate()
            result = process.returncode == 0 and out.decode().strip() == "vmware"
            logger.debug(f"Результат проверки VMware: {result}, вывод: {out.decode().strip()}")
            return result
        except Exception as e:
            logger.error(f"Ошибка при проверке виртуализации: {str(e)}")
            return False

    @staticmethod
    def generate_password_hash(password, logger):
        """Генерация хэша для пароля."""
        logger.debug("Генерация хэша пароля")
        hash_value = sha512_crypt.hash(password)
        logger.debug(f"Хэш пароля успешно сгенерирован: {hash_value[:20]}... (обрезан для лога)")
        return hash_value

    @staticmethod
    def _requests_get(url, verify, logger):
        """Выполнение HTTP GET-запроса с проверкой сертификата."""
        logger.debug(f"Выполнение GET-запроса к {url}, verify={verify}")
        try:
            response = requests.get(url, verify=verify, stream=True, timeout=5.0)
            logger.debug(f"Ответ получен, статус: {response.status_code}")
            return response
        except requests.RequestException as e:
            logger.error(f"Ошибка HTTP-запроса к {url}: {str(e)}")
            return None

    @staticmethod
    def exists_in_file(target_string, file_path, logger):
        """
        Проверка наличия строки в файле.
        Возвращает False, если файл не существует.
        """
        logger.debug(f"Проверка наличия строки '{target_string}' в файле {file_path}")
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                result = any(target_string in line for line in file)
                logger.debug(f"Строка найдена: {result}")
                return result
        except FileNotFoundError:
            logger.info(f"Файл не найден: {file_path}")
            return False
        except Exception as e:
            logger.error(f"Ошибка при чтении файла {file_path}: {str(e)}")
            raise

    @staticmethod
    def is_url(url, logger):
        """Проверка, является ли строка URL."""
        logger.debug(f"Проверка, является ли {url} URL")
        try:
            result = urlparse(url)
            is_valid = all([result.scheme, result.netloc])
            logger.debug(f"Результат проверки URL: {is_valid}")
            return is_valid
        except ValueError as e:
            logger.error(f"Ошибка при проверке URL {url}: {str(e)}")
            return False

    @staticmethod
    def load_json(url, logger):
        """Чтение JSON из файла или URL."""
        logger.debug(f"Загрузка JSON из {url}")
        try:
            if CommandUtils.is_url(url, logger):
                with urlopen(url, timeout=5.0) as f:
                    data = json.load(f)
                    logger.debug(f"JSON успешно загружен из URL: {url}")
                    return data
            else:
                file_path = url[7:] if url.startswith("file://") else url
                logger.debug(f"Чтение JSON из файла: {file_path}")
                with open(file_path, "rt", encoding="utf-8") as f:
                    data = json.load(f)
                    logger.debug(f"JSON успешно загружен из файла: {file_path}")
                    return data
        except Exception as e:
            logger.error(f"Ошибка при загрузке JSON из {url}: {str(e)}")
            raise

    @staticmethod
    def wget(url, out, logger, enforce_https=True, ask_fn=None, fingerprint=None):
        """Загрузка файла по URL с проверкой HTTPS и сертификатов."""
        logger.debug(f"Загрузка файла из {url} в {out}, enforce_https={enforce_https}")
        try:
            u = urlparse(url)
            logger.debug(f"Разобранный URL: scheme={u.scheme}, netloc={u.netloc}")
            if not all([u.scheme, u.netloc]):
                logger.error("Недействительный URL")
                return False, "Недействительный URL"
            if enforce_https and u.scheme != "https":
                logger.error("URL не является HTTPS")
                return False, "URL должен быть защищенным (HTTPS)"

            r = CommandUtils._requests_get(url, verify=True, logger=logger)
            if r is None:
                logger.warning("Не удалось проверить сертификат, требуется дополнительная проверка")
                if fingerprint is None and ask_fn is None:
                    logger.error("Отсутствуют параметры для проверки сертификата")
                    return False, "Не удалось проверить сертификат сервера"
                port = u.port if u.port else 443
                logger.debug(f"Получение сертификата сервера для {u.netloc}:{port}")
                try:
                    pem = ssl.get_server_certificate((u.netloc, port))
                    cert = load_certificate(FILETYPE_PEM, pem)
                    fp = cert.digest("sha1").decode()
                    logger.debug(f"Получен отпечаток сертификата: {fp}")
                except Exception as e:
                    logger.error(f"Ошибка получения сертификата: {str(e)}")
                    return False, "Не удалось получить сертификат сервера"
                if ask_fn is not None and not ask_fn(fp):
                    logger.info("Операция прервана пользователем")
                    return False, "Операция прервана пользователем"
                if fingerprint is not None and fingerprint != fp:
                    logger.error(f"Отпечаток не совпадает, ожидался: {fingerprint}, получен: {fp}")
                    return False, f"Отпечаток сервера не совпадает. Получен: {fp}"
                logger.debug("Повторная попытка загрузки без проверки сертификата")
                r = CommandUtils._requests_get(url, verify=False, logger=logger)

            if r is None:
                logger.error("Не удалось загрузить файл")
                return False, "Не удалось загрузить файл"
            logger.debug("Декодирование содержимого ответа")
            r.raw.decode_content = True
            with open(out, "wb") as f:
                logger.debug(f"Запись файла в {out}")
                shutil.copyfileobj(r.raw, f)
            logger.info(f"Файл успешно загружен в {out}")
            return True, None
        except Exception as e:
            logger.error(f"Ошибка загрузки файла: {str(e)}")
            return False, f"Ошибка загрузки файла: {str(e)}"

    def checkIfHostRpmNotUsable(self):
        """Проверка, поддерживает ли хост rpm zstd и sqlite."""
        self.logger.debug(f"Проверка поддержки rpm, текущее значение hostRpmIsNotUsable: {self.hostRpmIsNotUsable}")
        if self.hostRpmIsNotUsable >= 0:
            self.logger.debug("Используется кэшированное значение проверки rpm")
            return self.hostRpmIsNotUsable

        cmds = [
            "rpm --showrc | grep -qw 'rpmlib(PayloadIsZstd)'",
            "rpm -E %{_db_backend} | grep -qw 'sqlite'",
        ]
        self.logger.debug(f"Команды для проверки rpm: {cmds}")

        for cmd in cmds:
            self.logger.debug(f"Выполнение команды проверки: {cmd}")
            if self.run(cmd):
                self.logger.info("Обнаружено отсутствие поддержки zstd или sqlite")
                self.hostRpmIsNotUsable = 1
                break
        else:
            self.logger.debug("Поддержка zstd и sqlite подтверждена")
            self.hostRpmIsNotUsable = 0

        self.logger.info(f"Результат проверки rpm: hostRpmIsNotUsable={self.hostRpmIsNotUsable}")
        return self.hostRpmIsNotUsable

    @staticmethod
    def jsonread(filename, logger):
        """Чтение JSON из файла."""
        logger.debug(f"Чтение JSON из файла: {filename}")
        try:
            with open(filename, "rt", encoding="utf-8") as f:
                data = json.load(f)
                logger.debug(f"JSON успешно прочитан из {filename}")
                return data
        except Exception as e:
            logger.error(f"Ошибка при чтении JSON из файла {filename}: {str(e)}")
            raise

    @staticmethod
    def _yaml_param(loader, node, logger):
        """Обработка параметра YAML с поддержкой значений по умолчанию."""
        logger.debug(f"Обработка YAML параметра: {node.value}")
        params = loader.app_params
        key = node.value
        assert isinstance(key, str), "Имя параметра должно быть строкой"
        logger.debug(f"Параметры приложения: {params}")

        if '=' in key:
            key, default = [t.strip() for t in key.split('=', maxsplit=1)]
            logger.debug(f"Ключ: {key}, значение по умолчанию: {default}")
            value = params.get(key, yaml.safe_load(default))
        else:
            assert key in params, f"Параметр '{key}' не задан и нет значения по умолчанию"
            value = params[key]
        logger.debug(f"Полученное значение параметра: {value}")
        return value

    @staticmethod
    def readConfig(stream, params=None, logger=None):
        """Чтение конфигурации из YAML-потока с параметрами."""
        logger.debug(f"Чтение конфигурации YAML, параметры: {params}")
        if params is None:
            params = {}
        try:
            yaml_loader = yaml.SafeLoader
            yaml_loader.app_params = params
            yaml.add_constructor("!param", lambda l, n: CommandUtils._yaml_param(l, n, logger), Loader=yaml_loader)
            config = yaml.load(stream, Loader=yaml_loader)
            logger.debug(f"Конфигурация успешно загружена: {config}")
            return config
        except Exception as e:
            logger.error(f"Ошибка при чтении конфигурации YAML: {str(e)}")
            raise

    def convertToBytes(self, size):
        """Конвертация размера в байты (поддержка k, m, g, t)."""
        self.logger.debug(f"Конвертация размера: {size}")
        if not isinstance(size, str):
            self.logger.debug(f"Размер не строка, возвращается как число: {int(size)}")
            return int(size)
        if not size[-1].isalpha():
            self.logger.debug(f"Размер без суффикса, возвращается как число: {int(size)}")
            return int(size)
        conv = {'k': 1024, 'm': 1024**2, 'g': 1024**3, 't': 1024**4}
        try:
            result = int(float(size[:-1]) * conv[size.lower()[-1]])
            self.logger.debug(f"Размер конвертирован в байты: {result}")
            return result
        except (ValueError, KeyError) as e:
            self.logger.error(f"Недопустимый формат размера: {size}, ошибка: {str(e)}")
            raise ValueError(f"Недопустимый формат размера: {size}")

    @staticmethod
    def get_disk_size_bytes(disk, logger):
        """Получение размера диска в байтах."""
        cmd = ["blockdev", "--getsize64", disk]
        logger.debug(f"Получение размера диска: {disk}, команда: {cmd}")
        try:
            process = subprocess.Popen(
                cmd, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            out, err = process.communicate()
            if process.returncode == 0:
                logger.debug(f"Размер диска успешно получен: {out.strip()}")
                return process.returncode, out.strip()
            logger.error(f"Ошибка при получении размера диска: {err.strip()}")
            return process.returncode, err.strip()
        except Exception as e:
            logger.error(f"Ошибка при выполнении команды blockdev: {str(e)}")
            return 1, f"Ошибка при получении размера диска: {str(e)}"

    def get_vgnames(self):
        """Получение списка групп томов (Volume Groups)."""
        vg_list = []
        cmd = ["vgdisplay", "-c"]
        self.logger.debug(f"Получение списка групп томов, команда: {cmd}")
        try:
            process = subprocess.Popen(
                cmd, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            out, err = process.communicate()
            if process.returncode == 0:
                vgdisplay_output = out.split("\n")
                self.logger.debug(f"Вывод vgdisplay: {vgdisplay_output}")
                for vg in vgdisplay_output:
                    if vg:
                        vg_name = vg.split(":")[0].strip()
                        vg_list.append(vg_name)
                        self.logger.debug(f"Добавлена группа томов: {vg_name}")
            else:
                self.logger.error(f"Ошибка выполнения vgdisplay: {err}")
            self.logger.info(f"Список групп томов: {vg_list}")
            return process.returncode, vg_list
        except Exception as e:
            self.logger.error(f"Ошибка при получении списка групп томов: {str(e)}")
            return 1, vg_list

    @staticmethod
    def write_pkg_list_file(file_path, packages_list, logger):
        """Запись списка пакетов в JSON-файл."""
        logger.debug(f"Запись списка пакетов в файл: {file_path}")
        try:
            with open(file_path, "w", encoding="utf-8") as json_file:
                json.dump(packages_list, json_file, indent=4)
                logger.debug(f"Список пакетов успешно записан: {packages_list}")
            return file_path
        except Exception as e:
            logger.error(f"Ошибка при записи JSON в файл {file_path}: {str(e)}")
            raise

    def replace_in_file(self, file_path, pattern, replacement):
        """Замена текста в файле с использованием регулярного выражения."""
        self.logger.debug(f"Замена в файле {file_path}: шаблон '{pattern}' на '{replacement}'")
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                file_contents = file.read()
                self.logger.debug(f"Содержимое файла прочитано, длина: {len(file_contents)}")
            modified_contents = re.sub(pattern, replacement, file_contents)
            with open(file_path, "w", encoding="utf-8") as file:
                file.write(modified_contents)
                self.logger.debug("Измененное содержимое записано в файл")
            self.logger.info(f"Замена выполнена в файле: {file_path}")
        except FileNotFoundError:
            self.logger.error(f"Файл не найден: {file_path}")
            raise
        except Exception as e:
            self.logger.error(f"Ошибка при замене в файле {file_path}: {str(e)}")
            raise

    def remove_files(self, file_list):
        """
        Удаление файлов или директорий по списку шаблонов.
        """
        self.logger.debug(f"Удаление файлов по шаблонам: {file_list}")
        for file_path in file_list:
            try:
                matched_files = glob.glob(file_path)
                self.logger.debug(f"Найдено файлов по шаблону {file_path}: {matched_files}")
                for file in matched_files:
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
                self.logger.error(f"Ошибка при удалении {file_path}: {str(e)}")
                raise

    def acquire_file_map(self, map, dest_dir):
        """
        Копирование или загрузка файлов по карте соответствия источников и назначений.
        """
        self.logger.debug(f"Обработка карты файлов: {map}, целевая директория: {dest_dir}")
        for src, dest in map.items():
            try:
                if dest.startswith("/"):
                    dest = dest[1:]
                    self.logger.debug(f"Удален начальный слэш из пути назначения: {dest}")
                if not os.path.basename(dest):
                    dest = os.path.join(os.path.dirname(dest), os.path.basename(src))
                    self.logger.debug(f"Сформирован путь назначения: {dest}")
                dest = os.path.join(dest_dir, dest)
                self.logger.debug(f"Полный путь назначения: {dest}")
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                self.logger.debug(f"Созданы директории для {dest}")

                if src.startswith("file://"):
                    src = src[7:]
                    self.logger.debug(f"Обработан file:// URL, новый путь: {src}")
                if CommandUtils.is_url(src, self.logger):
                    self.logger.info(f"Загрузка {src} в {dest}")
                    ret, err = CommandUtils.wget(src, dest, self.logger)
                    if not ret:
                        self.logger.error(f"Ошибка загрузки {src}: {err}")
                        raise Exception(f"Ошибка загрузки {src}: {err}")
                else:
                    self.logger.info(f"Копирование {src} в {dest}")
                    shutil.copyfile(src, dest)
                    self.logger.debug(f"Файл успешно скопирован из {src} в {dest}")
            except Exception as e:
                self.logger.error(f"Ошибка при обработке {src} -> {dest}: {str(e)}")
                raise
