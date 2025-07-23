#/*
# * Copyright © 2020 VMware, Inc.
# * SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only
# */
from window import Window
from windowstringreader import WindowStringReader
from partitionpane import PartitionPane
from readmultext import ReadMulText
from confirmwindow import ConfirmWindow
from actionresult import ActionResult
from device import Device
from installer import BIOSSIZE,ESPSIZE
from filesystemselector import FilesystemSelector


class CustomPartition(object):
    def __init__(self, maxy, maxx, install_config, logger=None):
        self.maxx = maxx
        self.maxy = maxy
        self.win_width = maxx - 4
        self.win_height = maxy - 4
        self.install_config = install_config
        self.path_checker = []

        self.win_starty = (self.maxy - self.win_height) // 2
        self.win_startx = (self.maxx - self.win_width) // 2

        self.text_starty = self.win_starty + 4
        self.text_height = self.win_height - 6
        self.text_width = self.win_width - 6
        self.cp_config = {}
        self.cp_config['partitionsnumber'] = 0
        self.devices = None
        self.has_slash = False
        self.has_remain = False
        self.has_empty = False

        self.disk_size = []
        self.disk_to_index = {}

        self.window = Window(
            self.win_height,
            self.win_width,
            self.maxy,
            self.maxx,
            'Welcome to the Photon installer',
            False,
            can_go_next=False,
            help_text='Создавайте или удаляйте разделы. Используйте меню внизу для действий.',
        )
        Device.refresh_devices()

    def initialize_devices(self):
        self.devices = Device.refresh_devices(bytes=True)

        # Subtract BIOS&ESP SIZE from the disk_size since this much is hardcoded for bios
        # and efi partition in installer.py
        for index, device in enumerate(self.devices):
            self.disk_size.append((device.path, int(device.size) / 1048576 - (BIOSSIZE + ESPSIZE + 2)))
            self.disk_to_index[device.path] = index

    def display(self):
        self.initialize_devices()

        if 'autopartition' in self.install_config and self.install_config['autopartition'] == True:
            return ActionResult(True, None)

        self.device_index = self.disk_to_index[self.install_config['disk']]

        self.disk_buttom_items = []
        self.disk_buttom_items.append(('<Next>', self.next))
        self.disk_buttom_items.append(('<Create New>', self.create_function))
        self.disk_buttom_items.append(('<Delete All>', self.delete_function))
        self.disk_buttom_items.append(('<Go Back>', self.go_back))

        self.text_items = []
        self.text_items.append(('Disk', 20))
        self.text_items.append(('Size', 5))
        self.text_items.append(('Type', 5))
        self.text_items.append(('Mountpoint', 20))
        self.table_space = 5

        title = 'Current partitions:\n'
        self.window.addstr(0, (self.win_width - len(title)) // 2, title)

        info = ("Unpartitioned space: " +
                str(self.disk_size[self.device_index][1])+
                " MB, Total size: "+
                str(int(self.devices[self.device_index].size)/ 1048576) + " MB")

        self.partition_pane = PartitionPane(self.text_starty, self.maxx, self.text_width,
                                  self.text_height, self.disk_buttom_items,
                                  config=self.cp_config,
                                  text_items=self.text_items, table_space=self.table_space,
                                  info=info,
                                  size_left=str(self.disk_size[self.device_index][1]))

        self.window.set_action_panel(self.partition_pane)

        return self.window.do_action()

    def validate_partition(self, pstr):
        if not pstr:
            return ActionResult(False, None)
        sizedata = pstr[0]
        mtdata = pstr[2]
        typedata = pstr[1]
        devicedata = self.devices[self.device_index].path

        #no empty fields unless swap
        if (typedata == 'swap' and
                (len(mtdata) != 0 or len(typedata) == 0 or len(devicedata) == 0)):
            return False, "invalid swap data "

        if (typedata != 'swap' and
                (len(sizedata) == 0 or
                 len(mtdata) == 0 or
                 len(typedata) == 0 or
                 len(devicedata) == 0)):
            if not self.has_empty and mtdata and typedata and devicedata:
                self.has_empty = True
            else:
                return False, "Input cannot be empty"

        if typedata not in ['swap', 'ext3', 'ext4', 'xfs', 'btrfs']:
            return False, "Invalid type"

        if len(mtdata) != 0 and mtdata[0] != '/':
            return False, "Invalid path"

        if mtdata in self.path_checker:
            return False, "Path already existed"
        #validate disk: must be one of the existing disks
        i = self.device_index

        #valid size: must not exceed memory limit
        curr_size = self.disk_size[i][1]
        if len(sizedata) != 0:
            try:
                int(sizedata)
            except ValueError:
                return False, "invalid device size"

            if int(curr_size) - int(sizedata) < 0:
                return False, "invalid device size"
            #if valid, update the size and return true
            new_size = (self.disk_size[i][0], int(curr_size)- int(sizedata))
            self.disk_size[i] = new_size

        if mtdata == "/":
            self.has_slash = True

        self.path_checker.append(mtdata)
        return True, None

    def create_function(self):
        self.window.hide_window()

        self.cp_config['partition_disk'] = self.devices[self.device_index].path
        tmp_config = {}
        partition_idx = str(self.cp_config['partitionsnumber'])

        input_items = [
            ('Size in MB: ' + str(self.disk_size[self.device_index][1]) + ' available'),
            ('Mountpoint:')
        ]

        create_win = ReadMulText(
            self.maxy, self.maxx, 0,
            tmp_config,
            'partition_tmp',
            input_items,
            None,
            None,
            None,
            None,
            None,
            True,
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
            window_height = 9
            window_width = 50
            window_starty = (self.maxy - window_height) // 2 + 5
            confirm_window = ConfirmWindow(window_height, window_width, self.maxy,
                                           self.maxx, window_starty, err, info=True)
            confirm_window.do_action()
            return self.display()

        self.cp_config[partition_idx + 'partition_info0'] = size
        self.cp_config[partition_idx + 'partition_info1'] = fstype
        self.cp_config[partition_idx + 'partition_info2'] = mountpoint
        if fs_options:
            self.cp_config[partition_idx + 'fs_options'] = fs_options
        self.cp_config['partitionsnumber'] = self.cp_config['partitionsnumber'] + 1
        return self.display()

    def delete_function(self):
        self.delete()
        return self.display()

    def go_back(self):
        self.delete()
        self.window.hide_window()
        self.partition_pane.hide()
        return ActionResult(False, {'goBack':True})

    def next(self):
        if self.cp_config['partitionsnumber'] == 0:
            window_height = 9
            window_width = 40
            window_starty = (self.maxy-window_height) // 2 + 5
            confirm_window = ConfirmWindow(window_height, window_width, self.maxy,
                                           self.maxx, window_starty,
                                           'Partition information cannot be empty',
                                           info=True)
            confirm_window.do_action()
            return self.display()
        #must have /
        if not self.has_slash:
            window_height = 9
            window_width = 40
            window_starty = (self.maxy - window_height) // 2 + 5
            confirm_window = ConfirmWindow(window_height, window_width, self.maxy,
                                           self.maxx, window_starty, 'Missing /',
                                           info=True)
            confirm_window.do_action()
            return self.display()

        self.window.hide_window()
        self.partition_pane.hide()

        partitions = []
        for i in range(int(self.cp_config['partitionsnumber'])):
            if len(self.cp_config[str(i)+'partition_info'+str(0)]) == 0:
                sizedata = 0
            else:
                sizedata = int(self.cp_config[str(i) + 'partition_info' + str(0)])
            mtdata = self.cp_config[str(i) + 'partition_info' + str(2)]
            typedata = self.cp_config[str(i) + 'partition_info'+str(1)]

            fs_opts = self.cp_config.get(str(i) + 'fs_options')
            part = {"mountpoint": mtdata,
                    "size": sizedata,
                    "filesystem": typedata}
            if fs_opts:
                part['fs_options'] = fs_opts
            partitions = partitions + [part]
        self.install_config['partitions'] = partitions

        return ActionResult(True, {'goNext':True})

    def delete(self):
        for i in range(int(self.cp_config['partitionsnumber'])):
            self.cp_config[str(i)+'partition_info'+str(0)] = ''
            self.cp_config[str(i)+'partition_info'+str(1)] = ''
            self.cp_config[str(i)+'partition_info'+str(2)] = ''
            self.cp_config[str(i)+'partition_info'+str(3)] = ''
            if str(i)+'fs_options' in self.cp_config:
                del self.cp_config[str(i)+'fs_options']
        del self.disk_size[:]
        for index, device in enumerate(self.devices):
            self.disk_size.append((device.path, int(device.size) / 1048576 - (BIOSSIZE + ESPSIZE + 2)))
        del self.path_checker[:]
        self.has_slash = False
        self.has_remain = False
        self.has_empty = False
        self.cp_config['partitionsnumber'] = 0
