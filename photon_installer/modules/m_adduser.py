# /*
#  * Copyright © 2024 VMware, Inc.
#  * SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only
#  */

import os
import commons

install_phase = commons.POST_INSTALL
enabled = True


def execute(installer):
    username = installer.install_config.get('user_name')
    shadow_password = installer.install_config.get('user_shadow_password')
    if not username or not shadow_password:
        return

    installer.logger.info(f"Create user {username}")

    installer.cmd.run_in_chroot(installer.photon_root, f"/usr/sbin/useradd -m {username}")

    passwd_filename = os.path.join(installer.photon_root, 'etc/passwd')
    shadow_filename = os.path.join(installer.photon_root, 'etc/shadow')

    if os.path.isfile(shadow_filename):
        commons.replace_string_in_file(shadow_filename,
            fr'{username}:[^:]*:', f'{username}:{shadow_password}:')
    else:
        with open(shadow_filename, 'a') as dest:
            dest.write(f"{username}:{shadow_password}:")

    installer.cmd.run_in_chroot(installer.photon_root, "/usr/sbin/pwconv")
    installer.cmd.run_in_chroot(installer.photon_root, "/usr/sbin/grpconv")

    if installer.install_config.get('user_wheel'):
        installer.cmd.run_in_chroot(installer.photon_root, f"/usr/sbin/usermod -a -G wheel {username}")
