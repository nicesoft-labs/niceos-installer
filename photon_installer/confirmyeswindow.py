#/*
# * Copyright © 2020 VMware, Inc.
# * SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-only
# */
#
#    Based on ConfirmWindow, this window asks the user to type "yes" to confirm.

from windowstringreader import WindowStringReader
from actionresult import ActionResult

class ConfirmYesWindow(object):
    """Window that asks the user to type 'yes' before proceeding."""

    def __init__(self, height, width, maxy, maxx, message):
        self._config = {}
        self._reader = WindowStringReader(
            maxy,
            maxx,
            height,
            width,
            'confirm',
            None,
            None,
            None,
            self._validate_yes,
            None,
            'Confirm',
            message + "\nType 'yes' to continue:",
            2,
            self._config,
            '',
            False,
        )

    def _validate_yes(self, text):
        if text.strip() != 'yes':
            return False, "Please type 'yes' to confirm"
        return True, None

    def do_action(self):
        result = self._reader.get_user_string(None)
        if not result.success:
            return result
        yes = self._config.get('confirm', '').strip() == 'yes'
        return ActionResult(yes, {'yes': yes})
