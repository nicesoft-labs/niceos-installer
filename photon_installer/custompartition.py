#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
© 2025 ООО "НАЙС СОФТ ГРУПП" (ИНН 5024245440)
Контакты: <niceos@ncsgp.ru>
"""

from typing import Optional, Tuple, List, Dict
from window import Window
from windowstringreader import WindowStringReader
from partitionpane import PartitionPane
from readmultext import ReadMulText
from confirmwindow import ConfirmWindow
from actionresult import ActionResult
from device import Device
from installer import BIOSSIZE, ESPSIZE
from filesystemselector import FilesystemSelector


class CustomPartition:
    """Класс для настройки пользовательских разделов диска."""

    def __init__(self, maxy: int, maxx: int, install_config: Dict, logger=None):
        self.maxx = maxx
        self.maxy = maxy
        self.win_width = maxx - 4
        self.win_height = maxy - 4
        self.install_config = install_config
        self.path_checker: List[str] = []
        self.logger = logger

        self.win_starty = (self.maxy - self.win_height) // 2
        self.win_startx = (self.maxx - self.win_width) // 2
        self.text_starty = self.win_starty + 4
        self.text_height = self.win_height - 6
        self.text_width = self.win_width - 6
        self.cp_config: Dict = {'partitionsnumber': 0}
        self.devices: Optional[List[Device]] = None
        self.has_slash = False
        self.has_remain = False
        self.has_empty = False
        self.disk_size: List[Tuple[str, int]] = []
        self.disk_to_index: Dict[str, int] = {}

        self.window = Window(
            self.win_height,
            self.win_width,
            self.maxy,
            self.maxx,
            'Разметка дисков НАЙС.ОС',
            False,
            can_go_next=False,
            help_text=(
                "Здесь вы можете вручную создать или удалить разделы на выбранном диске.\n\n"
                "- Нажмите «<Создать новый>», чтобы добавить новый раздел.\n"
                "- Необходимо создать хотя бы один раздел с точкой монтирования `/` (основной раздел).\n"
                "- Можно создать раздел swap для подкачки, а также другие — например, `/home`, `/var` и т.д.\n"
                "- Обязательно следите за доступным размером диска — он указан в МБ.\n"
                "- Для завершения нажмите «<Далее>». Без раздела `/` установка не продолжится.\n"
                "- Чтобы очистить текущую схему разделов, нажмите «<Удалить все>».\n"
                "- Используйте «<Назад>» для возврата к предыдущему этапу настройки."
            ),
            help_url="https://niceos.ru/manual/installer-partitioning"

        )
        Device.refresh_devices()

    def initialize_devices(self) -> None:
        """Инициализация устройств и расчет размеров дисков."""
        self.devices = Device.refresh_devices(bytes=True)
        for index, device in enumerate(self.devices):
            try:
                size_bytes = int(device.size)  # Convert string to integer
                size_mb = size_bytes // 1048576 - (BIOSSIZE + ESPSIZE + 2)
                self.disk_size.append((device.path, size_mb))
                self.disk_to_index[device.path] = index
            except ValueError as e:
                if self.logger:
                    self.logger.error(f"Недействительный размер устройства {device.path}: {device.size}")
                raise ValueError(f"Не удалось преобразовать размер устройства {device.path} в число: {device.size}")

    def display(self) -> ActionResult:
        """Отображение интерфейса настройки разделов."""
        self.initialize_devices()

        if self.install_config.get('autopartition', False):
            return ActionResult(True, None)

        self.device_index = self.disk_to_index[self.install_config['disk']]
        self.disk_buttom_items = [
            ('<Далее>', self._next),
            ('<Создать новый>', self._create_function),
            ('<Удалить все>', self._delete_function),
            ('<Назад>', self._go_back)
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

        info = (
            f"Неразмеченное пространство: {self.disk_size[self.device_index][1]} МБ, "
            f"Общий размер: {int(self.devices[self.device_index].size) // 1048576} МБ"
        )

        self.partition_pane = PartitionPane(
            self.text_starty, self.maxx, self.text_width, self.text_height,
            self.disk_buttom_items, config=self.cp_config, text_items=self.text_items,
            table_space=self.table_space, info=info,
            size_left=str(self.disk_size[self.device_index][1])
        )
        self.window.set_action_panel(self.partition_pane)
        return self.window.do_action()

    def validate_partition(self, pstr: List[str]) -> Tuple[bool, Optional[str]]:
        """Валидация параметров раздела."""
        if not pstr:
            return False, None

        sizedata, typedata, mtdata = pstr[0], pstr[1], pstr[2]
        devicedata = self.devices[self.device_index].path

        # Проверка на пустые поля (кроме swap)
        if typedata == 'swap' and (mtdata or not typedata or not devicedata):
            return False, "Недействительные данные для swap"

        if typedata != 'swap' and (not sizedata or not mtdata or not typedata or not devicedata):
            if not self.has_empty and mtdata and typedata and devicedata:
                self.has_empty = True
            else:
                return False, "Поля не могут быть пустыми"

        if typedata not in ['swap', 'ext3', 'ext4', 'xfs', 'btrfs']:
            return False, "Недопустимый тип файловой системы"

        if mtdata and mtdata[0] != '/':
            return False, "Недопустимый путь монтирования"

        if mtdata in self.path_checker:
            return False, "Путь уже существует"

        if mtdata == "/":
            self.has_slash = True

        if sizedata:
            try:
                size = int(sizedata)
                curr_size = self.disk_size[self.device_index][1]
                if curr_size - size < 0:
                    return False, "Недостаточно места на диске"
                self.disk_size[self.device_index] = (self.disk_size[self.device_index][0], curr_size - size)
            except ValueError:
                return False, "Недействительный размер раздела"

        self.path_checker.append(mtdata)
        return True, None

    def _create_function(self) -> ActionResult:
        """Создание нового раздела."""
        self.window.hide_window()
        self.cp_config['partition_disk'] = self.devices[self.device_index].path
        tmp_config = {}
        partition_idx = str(self.cp_config['partitionsnumber'])

        input_items = [
            f'Размер в МБ: {self.disk_size[self.device_index][1]} доступно',
            'Точка монтирования:'
        ]

        create_win = ReadMulText(
            self.maxy, self.maxx, 0, tmp_config, 'partition_tmp', input_items,
            None, None, None, None, None, True
        )
        result = create_win.do_action()
        if not result.success:
            return self.display()

        size = tmp_config.get('partition_tmp0', '')
        mountpoint = tmp_config.get('partition_tmp1', '')

        fs_selector = FilesystemSelector(self.maxy, self.maxx)
        fs_result = fs_selector.display()
        if not fs_result.success:
            return self.display()

        fstype = fs_selector.selected_fs
        fs_options = None
        if fstype == 'btrfs':
            from btrfscompressionselector import BtrfsCompressionSelector
            comp_sel = BtrfsCompressionSelector(self.maxy, self.maxx)
            comp_res = comp_sel.display()
            if not comp_res.success:
                return self.display()
            fs_options = f"compress={comp_sel.selected}"

        valid, err = self.validate_partition([size, fstype, mountpoint])
        if not valid:
            window_height, window_width = 9, 50
            window_starty = (self.maxy - window_height) // 2 + 5
            confirm_window = ConfirmWindow(
                window_height, window_width, self.maxy, self.maxx, window_starty,
                err or "Ошибка при создании раздела", info=True
            )
            confirm_window.do_action()
            return self.display()

        self.cp_config[f'{partition_idx}partition_info0'] = size
        self.cp_config[f'{partition_idx}partition_info1'] = fstype
        self.cp_config[f'{partition_idx}partition_info2'] = mountpoint
        if fs_options:
            self.cp_config[f'{partition_idx}fs_options'] = fs_options
        self.cp_config['partitionsnumber'] += 1
        return self.display()

    def _delete_function(self) -> ActionResult:
        """Удаление всех разделов."""
        self._delete()
        return self.display()

    def _go_back(self) -> ActionResult:
        """Возврат к предыдущему экрану."""
        self._delete()
        self.window.hide_window()
        self.partition_pane.hide()
        return ActionResult(False, {'goBack': True})

    def _next(self) -> ActionResult:
        """Переход к следующему шагу."""
        if self.cp_config['partitionsnumber'] == 0:
            window_height, window_width = 9, 40
            window_starty = (self.maxy - window_height) // 2 + 5
            confirm_window = ConfirmWindow(
                window_height, window_width, self.maxy, self.maxx, window_starty,
                'Информация о разделах не может быть пустой', info=True
            )
            confirm_window.do_action()
            return self.display()

        if not self.has_slash:
            window_height, window_width = 9, 40
            window_starty = (self.maxy - window_height) // 2 + 5
            confirm_window = ConfirmWindow(
                window_height, window_width, self.maxy, self.maxx, window_starty,
                'Отсутствует корневая точка монтирования /', info=True
            )
            confirm_window.do_action()
            return self.display()

        self.window.hide_window()
        self.partition_pane.hide()

        partitions = []
        for i in range(self.cp_config['partitionsnumber']):
            sizedata = int(self.cp_config.get(f'{i}partition_info0', 0) or 0)
            mtdata = self.cp_config[f'{i}partition_info2']
            typedata = self.cp_config[f'{i}partition_info1']
            fs_opts = self.cp_config.get(f'{i}fs_options')
            part = {"mountpoint": mtdata, "size": sizedata, "filesystem": typedata}
            if fs_opts:
                part['fs_options'] = fs_opts
            partitions.append(part)
        self.install_config['partitions'] = partitions

        return ActionResult(True, {'goNext': True})

    def _delete(self) -> None:
        """Сброс конфигурации разделов."""
        for i in range(self.cp_config['partitionsnumber']):
            for j in range(4):
                self.cp_config[f'{i}partition_info{j}'] = ''
            if f'{i}fs_options' in self.cp_config:
                del self.cp_config[f'{i}fs_options']
        self.disk_size.clear()
        for index, device in enumerate(self.devices):
            try:
                size_bytes = int(device.size)
                size_mb = size_bytes // 1048576 - (BIOSSIZE + ESPSIZE + 2)
                self.disk_size.append((device.path, size_mb))
            except ValueError as e:
                if self.logger:
                    self.logger.error(f"Недействительный размер устройства {device.path}: {device.size}")
                raise ValueError(f"Не удалось преобразовать размер устройства {device.path} в число: {device.size}")
        self.path_checker.clear()
        self.has_slash = False
        self.has_remain = False
        self.has_empty = False
        self.cp_config['partitionsnumber'] = 0
