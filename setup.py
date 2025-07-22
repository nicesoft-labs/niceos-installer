#
# Copyright © 2020-2023 VMware, Inc.
# SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only
#

import os
from version import get_installer_version
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, "requirements.txt")) as requirements_txt:
    REQUIRES = requirements_txt.read().splitlines()

setup(
    name='niceos-installer',
    description='Installer code for niceos',
    packages=find_packages(include=['niceos_installer', 'niceos_installer.modules']),
    install_requires=REQUIRES,
    include_package_data=True,
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'niceos-installer = niceos_installer.main:main',
            'niceos-iso-builder = niceos_installer.isoBuilder:main'
        ]
    },
    version=get_installer_version(),
    author_email='gpiyush@vmware.com'
)
