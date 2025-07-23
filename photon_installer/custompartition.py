#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
© 2025 ООО "НАЙС СОФТ ГРУПП" (ИНН 5024245440)
Контакты: <niceos@ncsgp.ru>
"""

import logging
from window import Window
from windowstringreader import WindowStringReader
from partitionpane import PartitionPane
from readmultext import ReadMulText
from confirmwindow import ConfirmWindow
from actionresult import ActionResult
from device import Device
from installer import BIOSSIZE, ESPSIZE
from filesystemselector import FilesystemSelector


class CustomPartition(object):
    def __init__(self, maxy, maxx, install_config, logger=None):
        """
        Инициализация селектора пользовательской разметки диска.

        Аргументы:
        - maxy (int): Максимальная координата Y экрана.
        - maxx (int): Максимальная координата X экрана.
        - install_config (dict): Конфигурация установки.
        - logger (logging.Logger, optional): Логгер для записи событий. Если None, логирование не выполняется.
        """
        self.logger = logger
        if self.logger is not None:
            self.logger.debug(f"Инициализация CustomPartition: maxy={maxy}, maxx={maxx}, install_config={install_config}")

        # Проверка входных параметров
        if not isinstance(maxy, int) or not isinstance(maxx, int) or maxy <= 0 or maxx <= 0:
            if self.logger is not None:
                self.logger.error(f"Недопустимые размеры экрана: maxy={maxy}, maxx={maxx}")
            raise ValueError("maxy и maxx должны быть положительными целыми числами")
        if not isinstance(install_config, dict):
            if self.logger is not None:
                self.logger.error(f"Недопустимая конфигурация: {install_config}")
            raise ValueError("install_config должен быть словарем")

        self.maxx = maxx
        self.maxy = maxy
        self.win_width = min(maxx - 4, 70)  # Ограничение ширины окна
        self.win_height = min(maxy - 4, 20)  # Ограничение высоты окна
        self.install_config = install_config
        self.path_checker = []
        self.win_starty = (self.maxy - self.win_height) // 2
        self.win_startx = (self.maxx - self.win_width) // 2
        self.text_starty = self.win_starty + 4
        self.text_height = self.win_height - 6
        self.text_width = self.win_width - 6
        self.cp_config = {'partitionsnumber': 0}
        self.devices = None
        self.has_slash = False
        self.has_remain = False
        self.has_empty = False
        self.disk_size = []
        self.disk_to_index = {}

        try:
            self.window = Window(self.win_height, self.win_width, self.maxy, self.maxx,
                                'Добро пожаловать в установщик NiceOS', False, can_go_next=False,
                                logger=self.logger)
            Device.refresh_devices()
            if self.logger is not None:
                self.logger.debug("Окно инициализировано")
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при создании окна: {str(e)}")
            raise

    def initialize_devices(self):
        """
        Инициализация списка устройств.
        """
        if self.logger is not None:
            self.logger.debug("Инициализация устройств")
        try:
            self.devices = Device.refresh_devices(bytes=True)
            self.disk_size = []
            self.disk_to_index = {}
            for index, device in enumerate(self.devices):
                size_mb = int(device.size / 1048576) - (BIOSSIZE + ESPSIZE + 2)
                self.disk_size.append((device.path, size_mb))
                self.disk_to_index[device.path] = index
            if self.logger is not None:
                self.logger.debug(f"Обнаружено устройств: {len(self.devices)}, размеры: {self.disk_size}")
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при инициализации устройств: {str(e)}")
            raise

    def display(self):
        """
        Отображение окна пользовательской разметки.

        Возвращает:
        - ActionResult: Результат действия.
        """
        if self.logger is not None:
            self.logger.debug("Запуск отображения окна разметки")

        try:
            self.initialize_devices()
            if 'autopartition' in self.install_config and self.install_config['autopartition']:
                if self.logger is not None:
                    self.logger.info("Автоматическая разметка включена, пропуск пользовательской разметки")
                return ActionResult(True, None)

            if 'disk' not in self.install_config or self.install_config['disk'] not in self.disk_to_index:
                if self.logger is not None:
                    self.logger.error("Диск не выбран или не найден в disk_to_index")
                return ActionResult(False, {"error": "Диск не выбран"})

            self.device_index = self.disk_to_index[self.install_config['disk']]
            self.disk_buttom_items = [
                ('<Далее>', self.next),
                ('<Создать новый>', self.create_function),
                ('<Удалить все>', self.delete_function),
                ('<Назад>', self.go_back)
            ]

            self.text_items = [
                ('Диск', 20),
                ('Размер', 5),
                ('Тип', 5),
                ('Точка монтирования', 20)
            ]
            self.table_space = 5
            title = 'Текущие разделы:\n'
            self.window.addstr(0, (self.win_width - len(title)) // 2, title)

            info = (f"Неразмеченное пространство: {self.disk_size[self.device_index][1]} МБ, "
                    f"Общий размер: {int(self.devices[self.device_index].size / 1048576)} МБ")

            self.partition_pane = PartitionPane(self.text_starty, self.maxx, self.text_width,
                                              self.text_height, self.disk_buttom_items,
                                              config=self.cp_config, text_items=self.text_items,
                                              table_space=self.table_space, info=info,
                                              size_left=str(self.disk_size[self.device_index][1]),
                                              logger=self.logger)
            self.window.set_action_panel(self.partition_pane)
            result = self.window.do_action()
            if self.logger is not None:
                self.logger.info(f"Результат разметки: {result}")
            return result
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при отображении окна: {str(e)}")
            return ActionResult(False, {"error": str(e)})

    def validate_partition(self, pstr):
        """
        Валидация данных раздела.

        Аргументы:
        - pstr (list): Список с данными раздела [размер, тип, точка монтирования].

        Возвращает:
        - tuple: (bool, str/None) - результат валидации и сообщение об ошибке (если есть).
        """
        if self.logger is not None:
            self.logger.debug(f"Валидация раздела: {pstr}")

        try:
            if not pstr or len(pstr) < 3:
                if self.logger is not None:
                    self.logger.warning("Недостаточно данных для раздела")
                return False, "Недостаточно данных для раздела"

            sizedata, typedata, mtdata = pstr[0], pstr[1], pstr[2]
            devicedata = self.devices[self.device_index].path

            # Проверка пустых полей
            if typedata == 'swap' and (mtdata or not typedata or not devicedata):
                if self.logger is not None:
                    self.logger.warning("Недопустимые данные для swap")
                return False, "Недопустимые данные для swap"

            if typedata != 'swap' and (not sizedata or not mtdata or not typedata or not devicedata):
                if not self.has_empty and mtdata and typedata and devicedata:
                    self.has_empty = True
                else:
                    if self.logger is not None:
                        self.logger.warning("Поля не могут быть пустыми")
                    return False, "Поля не могут быть пустыми"

            # Проверка типа файловой системы
            if typedata not in ['swap', 'ext3', 'ext4', 'xfs', 'btrfs']:
                if self.logger is not None:
                    self.logger.warning(f"Недопустимый тип файловой системы: {typedata}")
                return False, "Недопустимый тип файловой системы"

            # Проверка точки монтирования
            if mtdata and mtdata[0] != '/':
                if self.logger is not None:
                    self.logger.warning("Точка монтирования должна начинаться с /")
                return False, "Точка монтирования должна начинаться с /"

            if mtdata and mtdata.lower() in (p.lower() for p in self.path_checker):
                if self.logger is not None:
                    self.logger.warning(f"Точка монтирования уже существует: {mtdata}")
                return False, "Точка монтирования уже существует"

            # Проверка размера
            curr_size = self.disk_size[self.device_index][1]
            if sizedata:
                try:
                    size_mb = int(sizedata)
                    if size_mb < 1:
                        if self.logger is not None:
                            self.logger.warning("Размер раздела должен быть не менее 1 МБ")
                        return False, "Размер раздела должен быть не менее 1 МБ"
                    if size_mb > curr_size:
                        if self.logger is not None:
                            self.logger.warning(f"Размер раздела превышает доступное пространство: {size_mb} > {curr_size}")
                        return False, f"Размер раздела превышает доступное пространство ({curr_size} МБ)"
                except ValueError:
                    if self.logger is not None:
                        self.logger.warning(f"Недопустимый размер раздела: {sizedata}")
                    return False, "Недопустимый размер раздела"
                self.disk_size[self.device_index] = (devicedata, curr_size - size_mb)

            if mtdata == "/":
                self.has_slash = True

            self.path_checker.append(mtdata)
            if self.logger is not None:
                self.logger.debug(f"Раздел валиден: размер={sizedata}, тип={typedata}, точка монтирования={mtdata}")
            return True, None
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при валидации раздела: {str(e)}")
            return False, f"Ошибка валидации: {str(e)}"

    def create_function(self):
        """
        Создание нового раздела.

        Возвращает:
        - ActionResult: Результат действия.
        """
        if self.logger is not None:
            self.logger.debug("Создание нового раздела")
        try:
            self.window.hide_window()
            self.cp_config['partition_disk'] = self.devices[self.device_index].path

            tmp_config = {}
            partition_idx = str(self.cp_config['partitionsnumber'])
            input_items = [
                (f'Размер в МБ: {self.disk_size[self.device_index][1]} доступно'),
                ('Точка монтирования:')
            ]

            create_win = ReadMulText(
                self.maxy, self.maxx, 0, tmp_config, 'partition_tmp',
                input_items, None, None, None, None, None, True, logger=self.logger)
            result = create_win.do_action()
            if not result.success:
                if self.logger is not None:
                    self.logger.info("Отмена создания раздела")
                return self.display()

            size = tmp_config.get('partition_tmp0', '')
            mountpoint = tmp_config.get('partition_tmp1', '')

            fs_selector = FilesystemSelector(self.maxy, self.maxx, logger=self.logger)
            fs_result = fs_selector.display()
            if not fs_result.success:
                if self.logger is not None:
                    self.logger.info("Отмена выбора файловой системы")
                return self.display()

            fstype = fs_selector.selected_fs
            fs_options = None
            if fstype == 'btrfs':
                from btrfscompressionselector import BtrfsCompressionSelector
                comp_sel = BtrfsCompressionSelector(self.maxy, self.maxx, logger=self.logger)
                comp_res = comp_sel.display()
                if not comp_res.success:
                    if self.logger is not None:
                        self.logger.info("Отмена выбора сжатия для btrfs")
                    return self.display()
                fs_options = f"compress={comp_sel.selected}"

            valid, err = self.validate_partition([size, fstype, mountpoint])
            if not valid:
                window_height = 9
                window_width = 50
                window_starty = (self.maxy - window_height) // 2 + 5
                confirm_window = ConfirmWindow(window_height, window_width, self.maxy,
                                             self.maxx, window_starty, err, info=True,
                                             logger=self.logger)
                confirm_window.do_action()
                if self.logger is not None:
                    self.logger.warning(f"Ошибка валидации раздела: {err}")
                return self.display()

            self.cp_config[partition_idx + 'partition_info0'] = size
            self.cp_config[partition_idx + 'partition_info1'] = fstype
            self.cp_config[partition_idx + 'partition_info2'] = mountpoint
            if fs_options:
                self.cp_config[partition_idx + 'fs_options'] = fs_options
            self.cp_config['partitionsnumber'] += 1
            if self.logger is not None:
                self.logger.info(f"Создан раздел: размер={size}, тип={fstype}, точка монтирования={mountpoint}")

            return self.display()
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при создании раздела: {str(e)}")
            return ActionResult(False, {"error": str(e)})

    def delete_function(self):
        """
        Удаление всех разделов.

        Возвращает:
        - ActionResult: Результат действия.
        """
        if self.logger is not None:
            self.logger.debug("Удаление всех разделов")
        try:
            self.delete()
            return self.display()
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при удалении разделов: {str(e)}")
            return ActionResult(False, {"error": str(e)})

    def go_back(self):
        """
        Возврат назад с очисткой конфигурации.

        Возвращает:
        - ActionResult: Результат действия.
        """
        if self.logger is not None:
            self.logger.debug("Возврат назад")
        try:
            self.delete()
            self.window.hide_window()
            self.partition_pane.hide()
            if self.logger is not None:
                self.logger.info("Возврат назад с очисткой конфигурации")
            return ActionResult(False, {'goBack': True})
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при возврате назад: {str(e)}")
            return ActionResult(False, {"error": str(e)})

    def next(self):
        """
        Переход к следующему шагу с сохранением конфигурации разделов.

        Возвращает:
        - ActionResult: Результат действия.
        """
        if self.logger is not None:
            self.logger.debug("Переход к следующему шагу")

        try:
            if self.cp_config['partitionsnumber'] == 0:
                window_height = 9
                window_width = 40
                window_starty = (self.maxy - window_height) // 2 + 5
                confirm_window = ConfirmWindow(window_height, window_width, self.maxy,
                                             self.maxx, window_starty,
                                             'Информация о разделах не может быть пустой',
                                             info=True, logger=self.logger)
                confirm_window.do_action()
                if self.logger is not None:
                    self.logger.warning("Информация о разделах отсутствует")
                return self.display()

            if not self.has_slash:
                window_height = 9
                window_width = 40
                window_starty = (self.maxy - window_height) // 2 + 5
                confirm_window = ConfirmWindow(window_height, window_width, self.maxy,
                                             self.maxx, window_starty, 'Отсутствует точка монтирования /',
                                             info=True, logger=self.logger)
                confirm_window.do_action()
                if self.logger is not None:
                    self.logger.warning("Отсутствует корневая точка монтирования")
                return self.display()

            self.window.hide_window()
            self.partition_pane.hide()
            partitions = []
            for i in range(self.cp_config['partitionsnumber']):
                sizedata = int(self.cp_config.get(f"{i}partition_info0", 0) or 0)
                mtdata = self.cp_config.get(f"{i}partition_info2", "")
                typedata = self.cp_config.get(f"{i}partition_info1", "")
                fs_opts = self.cp_config.get(f"{i}fs_options")
                part = {"mountpoint": mtdata, "size": sizedata, "filesystem": typedata}
                if fs_opts:
                    part['fs_options'] = fs_opts
                partitions.append(part)
            self.install_config['partitions'] = partitions
            if self.logger is not None:
                self.logger.info(f"Сохранено разделов: {len(partitions)}")
            return ActionResult(True, {'goNext': True})
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при переходе вперед: {str(e)}")
            return ActionResult(False, {"error": str(e)})

    def delete(self):
        """
        Очистка конфигурации разделов.
        """
        if self.logger is not None:
            self.logger.debug("Очистка конфигурации разделов")
        try:
            self.cp_config = {'partitionsnumber': 0}
            self.disk_size = [(device.path, int(device.size / 1048576) - (BIOSSIZE + ESPSIZE + 2))
                              for device in self.devices]
            self.path_checker = []
            self.has_slash = False
            self.has_remain = False
            self.has_empty = False
            if self.logger is not None:
                self.logger.debug("Конфигурация разделов очищена")
        except Exception as e:
            if self.logger is not None:
                self.logger.error(f"Ошибка при очистке конфигурации: {str(e)}")
            raise
