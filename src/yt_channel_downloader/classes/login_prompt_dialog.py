from ..ui.ui_login_prompt import Ui_LoginPromptDialog
from .settings_manager import SettingsManager

from PyQt6.QtWidgets import QDialog


class LoginPromptDialog(QDialog):
    def __init__(self, parent=None):
        super(LoginPromptDialog, self).__init__(parent)
        self.settings_manager = SettingsManager()
        self.ui = Ui_LoginPromptDialog()
        self.ui.setupUi(self)

        self.ui.checkBox.stateChanged.connect(self.toggle_show_again)
        self.ui.buttonBox.accepted.connect(self.accept)
        self.ui.buttonBox.rejected.connect(self.reject)

    def toggle_show_again(self, state):
        is_checked = bool(state)
        settings = self.settings_manager.settings
        settings['dont_show_login_prompt'] = is_checked
        self.settings_manager.save_settings_to_file(settings)
