#/*
# * Copyright © 2020-2023 VMware, Inc.
# * SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only
# */
import os

class Defaults():
    WORKING_DIRECTORY = "/mnt/niceos-root"
    MOUNT_PATH = "/mnt/media"
    REPO_PATHS = MOUNT_PATH + "/RPMS"
    LOG_PATH = "/var/log"
    INSECURE_INSTALLATION = False
    NICEOS_RELEASE_VERSION = "5.2"
