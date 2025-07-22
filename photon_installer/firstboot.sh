#!/bin/bash
#
# script installed by niceos-installer
#

SCRIPT_DIR=/etc/firstboot.d

[ -d ${SCRIPT_DIR} ] || exit 0

for script in ${SCRIPT_DIR}/*.sh ; do
    if [ -x ${script} ] ; then
        echo "running ${script}"
        ${script} || echo "${script} failed with $?"
    fi
done

exit 0
