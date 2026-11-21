"""The headless Qt test setup (NVG-7): an example of how widget tests are written."""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontInfo, QFontMetrics
from PySide6.QtWidgets import QComboBox, QLineEdit, QMainWindow, QMenu, QPushButton


def test_qapp_uses_the_offscreen_platform(qapp):
    assert qapp.platformName() == "offscreen"


@pytest.mark.parametrize("text", ["Nvagik", "Нвагик", "Նվագիկ"])
def test_offscreen_text_uses_real_system_fonts(qapp, text):
    # Without QT_QPA_FONTDIR (tests/conftest.py) the offscreen platform has no
    # fonts on Windows: the family is empty, no glyph is found and every one of
    # these strings measures 78 px instead of about 45 px.
    font = QFont("Segoe UI", 10)
    assert QFontInfo(font).family() == "Segoe UI"
    assert QFontMetrics(font).inFontUcs4(ord(text[0]))
    assert 0 < QFontMetrics(font).horizontalAdvance(text) < 60


def test_button_click_emits_clicked(qtbot):
    button = QPushButton()
    qtbot.addWidget(button)  # pytest-qt closes and deletes it after the test

    with qtbot.waitSignal(button.clicked, timeout=1000):
        qtbot.mouseClick(button, Qt.MouseButton.LeftButton)


def test_typing_into_a_line_edit(qtbot):
    edit = QLineEdit()
    qtbot.addWidget(edit)
    edit.show()  # offscreen windows can be shown; nothing appears on screen
    qtbot.waitExposed(edit)

    qtbot.keyClicks(edit, "Nvagik")

    assert edit.text() == "Nvagik"


def test_offscreen_plugin_limitations_are_not_failures(qtbot):
    # Qt warnings fail tests (qt_log_level_fail), but the offscreen plugin warns
    # "This plugin does not support ..." for resizing shown windows, raising
    # popups and grabbing the keyboard. Those are not app bugs (qt_log_ignore).
    window = QMainWindow()
    qtbot.addWidget(window)
    window.menuBar().addMenu("File")
    window.show()
    qtbot.waitExposed(window)
    window.setMinimumSize(400, 300)

    combo = QComboBox(window)
    combo.addItems(["A", "B"])
    combo.showPopup()
    combo.hidePopup()

    menu = QMenu(window)
    menu.addAction("Item")
    menu.popup(window.mapToGlobal(window.rect().center()))
    menu.close()


def test_real_qt_warnings_fail_and_offscreen_limits_do_not(pytester, pytestconfig):
    # Runs two tests with this project's own Qt log settings from pyproject.toml.
    ignore = "".join(f"\n    {pattern}" for pattern in pytestconfig.getini("qt_log_ignore"))
    pytester.makeini(
        "[pytest]\n"
        f"qt_api = {pytestconfig.getini('qt_api')}\n"
        f"qt_log_level_fail = {pytestconfig.getini('qt_log_level_fail')}\n"
        f"qt_log_ignore ={ignore}\n"
    )
    pytester.makepyfile(
        "from PySide6.QtCore import qWarning\n"
        "def test_real_warning(qapp):\n"
        "    qWarning('QObject::connect: No such signal')\n"
        "def test_offscreen_limit(qapp):\n"
        "    qWarning('This plugin does not support raise()')\n"
    )
    result = pytester.runpytest()
    result.assert_outcomes(passed=1, failed=1)
    result.stdout.fnmatch_lines(["FAILED *test_real_warning*"])
