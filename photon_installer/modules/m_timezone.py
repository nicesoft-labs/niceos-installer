#/*
# * Copyright © 2024 VMware, Inc.
# * SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only
# */

import os
import commons

install_phase = commons.POST_INSTALL
enabled = True


def execute(installer):
    timezone = installer.install_config.get('timezone', 'Europe/Moscow')
    installer.logger.info(f"Set timezone to {timezone}")
    target_localtime = os.path.join(installer.photon_root, 'etc/localtime')
    target_timezone = os.path.join(installer.photon_root, 'etc/timezone')

    if os.path.islink(target_localtime) or os.path.exists(target_localtime):
        os.remove(target_localtime)
    tz_path = os.path.join('/usr/share/zoneinfo', timezone)
    if not os.path.exists(tz_path):
        installer.logger.warning(f"Timezone {timezone} not found, falling back to UTC")
        timezone = 'UTC'
        tz_path = os.path.join('/usr/share/zoneinfo', timezone)
    os.symlink(tz_path, target_localtime)
    with open(target_timezone, 'w') as f:
        f.write(timezone + '\n')
