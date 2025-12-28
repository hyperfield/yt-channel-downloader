from yt_channel_downloader.classes import support_prompt as sp


class FakeMessageBox:
    class Icon:
        Information = object()

    class ButtonRole:
        AcceptRole = object()
        DestructiveRole = object()
        RejectRole = object()

    desired_label = None

    def __init__(self, parent=None):
        self.parent = parent
        self._clicked = None

    def setIcon(self, icon):
        self.icon = icon

    def setWindowTitle(self, title):
        self.window_title = title

    def setText(self, text):
        self.text = text

    def setInformativeText(self, text):
        self.info_text = text

    def addButton(self, label, role):
        btn = {"label": label, "role": role}
        if label == self.desired_label:
            self._clicked = btn
        return btn

    def exec(self):
        return None

    def clickedButton(self):
        return self._clicked


def _build_prompt(monkeypatch, desired_label):
    FakeMessageBox.desired_label = desired_label
    monkeypatch.setattr(sp, "QMessageBox", FakeMessageBox)
    monkeypatch.setattr(sp, "QUrl", lambda value: value)
    opened = []

    def fake_open(url):
        opened.append(url)
        return True

    monkeypatch.setattr(sp.QDesktopServices, "openUrl", fake_open)
    prompt = sp.SupportPrompt(
        parent=None,
        settings_manager=None,
        short_snooze=5,
        medium_snooze=10,
        long_snooze=20,
    )
    return prompt, opened


def test_should_prompt_threshold():
    prompt = sp.SupportPrompt(parent=None, settings_manager=None)
    assert prompt.should_prompt(10, 10) is True
    assert prompt.should_prompt(11, 10) is True
    assert prompt.should_prompt(9, 10) is False


def test_support_choice_opens_url_and_uses_long_snooze(monkeypatch):
    prompt, opened = _build_prompt(monkeypatch, "Support")
    next_threshold = prompt.show_and_get_next_threshold(100)
    assert next_threshold == 120
    assert opened == [sp.SUPPORT_URL]


def test_cannot_donate_choice_uses_medium_snooze(monkeypatch):
    prompt, opened = _build_prompt(monkeypatch, "I cannot donate")
    next_threshold = prompt.show_and_get_next_threshold(50)
    assert next_threshold == 60
    assert opened == []


def test_not_sure_choice_uses_short_snooze(monkeypatch):
    prompt, opened = _build_prompt(monkeypatch, "I'm not yet sure")
    next_threshold = prompt.show_and_get_next_threshold(25)
    assert next_threshold == 30
    assert opened == []
