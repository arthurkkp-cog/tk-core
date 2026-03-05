# Copyright (c) 2023 Autodesk.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the ShotGrid Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the ShotGrid Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Autodesk.

from tank_test.tank_test_base import setUpModule  # noqa
from tank_test.tank_test_base import (
    TankTestBase,
    skip_if_pyside6,
)

from tank.util import pyside6_patcher


@skip_if_pyside6(found=False)
class PySide6PatcherTests(TankTestBase):
    """Tests PySide6 patcher functionality."""

    def setUp(self):
        super(PySide6PatcherTests, self).setUp()
        self.core, self.gui, _ = pyside6_patcher.PySide6Patcher.patch(None, None)

    def test_patch(self):
        """Test the PySide6Patcher patch method that patches PySide6 as PySide."""

        core = self.core
        gui = self.gui
        # Assert the core ang gui modules are created and returned
        assert core
        assert gui
        # Assert QtCore attributes
        assert core.Qt.MidButton == core.Qt.MiddleButton
        assert core.QRegExp == core.QRegularExpression
        # Assert QtGui attributes
        assert gui.QApplication.desktop
        assert gui.QAbstractButton.animateClick
        assert gui.QSortFilterProxyModel.filterRegExp == gui.QSortFilterProxyModel.filterRegularExpression
        assert gui.QSortFilterProxyModel.setFilterRegExp == gui.QSortFilterProxyModel.setFilterRegularExpression
        assert gui.QDesktopWidget == gui.QScreen
        assert gui.QFontMetrics.width == gui.QFontMetrics.horizontalAdvance
        assert gui.QFont.setWeight == gui.QFont.setLegacyWeight
        assert gui.QHeaderView.setResizeMode == gui.QHeaderView.setSectionResizeMode
        assert gui.QPainter.HighQualityAntialiasing == gui.QPainter.Antialiasing
        assert gui.QPalette.Background == gui.QPalette.Window

    def test_qregexp_indexin_and_cap(self):
        """Test that indexIn stores match state and cap/pos/matchedLength work."""

        QRegExp = self.core.QRegExp
        # Pattern with a capture group: match "hello" followed by a space and
        # capture the next word.
        rx = QRegExp(r"(hello)\s+(\w+)")
        subject = "say hello world!"

        idx = rx.indexIn(subject)
        # "hello world" starts at index 4
        self.assertEqual(idx, 4)
        # Full match is "hello world" -> length 11
        self.assertEqual(rx.matchedLength(), 11)
        # cap(0) is the full match
        self.assertEqual(rx.cap(0), "hello world")
        # cap(1) is first capture group
        self.assertEqual(rx.cap(1), "hello")
        # cap(2) is second capture group
        self.assertEqual(rx.cap(2), "world")
        # pos(0) is start of full match
        self.assertEqual(rx.pos(0), 4)
        # pos(1) is start of first capture group
        self.assertEqual(rx.pos(1), 4)
        # pos(2) is start of second capture group
        self.assertEqual(rx.pos(2), 10)

    def test_qregexp_no_match(self):
        """Test that dummy values are returned when there is no match."""

        QRegExp = self.core.QRegExp
        rx = QRegExp(r"notfound")
        subject = "hello world"

        idx = rx.indexIn(subject)
        self.assertEqual(idx, -1)
        self.assertEqual(rx.matchedLength(), -1)
        self.assertEqual(rx.cap(0), "")
        self.assertEqual(rx.pos(0), -1)

    def test_qregexp_pattern_syntax_wildcard(self):
        """Test that wildcard pattern syntax converts the pattern correctly."""

        QRegExp = self.core.QRegExp
        # QRegExp.Wildcard enum value is 1
        _Wildcard = 1
        rx = QRegExp("*.txt", syntax=_Wildcard)
        # The pattern should have been converted from a glob to a regex.
        # It should match a string ending with ".txt".
        idx = rx.indexIn("readme.txt")
        self.assertGreaterEqual(idx, 0)
        self.assertEqual(rx.cap(0), "readme.txt")

    def test_qregexp_pattern_syntax_fixed_string(self):
        """Test that fixed string syntax escapes the pattern."""

        QRegExp = self.core.QRegExp
        # QRegExp.FixedString enum value is 2
        _FixedString = 2
        # The dot and plus should be treated as literal characters.
        rx = QRegExp("a.b+c", syntax=_FixedString)
        # Should NOT match "aXbbbbc" (regex interpretation)
        idx = rx.indexIn("aXbbbbc")
        self.assertEqual(idx, -1)
        # Should match the literal string "a.b+c"
        idx = rx.indexIn("a.b+c")
        self.assertGreaterEqual(idx, 0)
        self.assertEqual(rx.cap(0), "a.b+c")
