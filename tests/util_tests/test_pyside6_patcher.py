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

    def test_patch(self):
        """Test the PySide6Patcher patch method that patches PySide6 as PySide."""

        core, gui, _ = pyside6_patcher.PySide6Patcher.patch(None, None)
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


@skip_if_pyside6(found=False)
class QRegExpCompatTests(TankTestBase):
    """Tests for QRegExp compatibility patches on QRegularExpression."""

    def setUp(self):
        super(QRegExpCompatTests, self).setUp()
        core, _, _ = pyside6_patcher.PySide6Patcher.patch(None, None)
        self.QRegExp = core.QRegExp

    # ------------------------------------------------------------------ #
    # indexIn stores state, matchedLength / pos / cap use it
    # ------------------------------------------------------------------ #

    def test_indexIn_and_matchedLength(self):
        """indexIn should store state so matchedLength returns the correct length."""
        rx = self.QRegExp(r"(\d+)")
        result = rx.indexIn("abc 1234 xyz")
        self.assertEqual(result, 4)
        self.assertEqual(rx.matchedLength(), 4)

    def test_indexIn_and_pos(self):
        """pos(n) should return the start position of capture group n."""
        rx = self.QRegExp(r"(\d+)-(\w+)")
        result = rx.indexIn("foo 42-bar end")
        self.assertEqual(result, 4)
        # group 0 = whole match
        self.assertEqual(rx.pos(0), 4)
        # group 1 = "42"
        self.assertEqual(rx.pos(1), 4)
        # group 2 = "bar"
        self.assertEqual(rx.pos(2), 7)

    def test_indexIn_and_cap(self):
        """cap(n) should return the captured text for group n."""
        rx = self.QRegExp(r"(\d+)-(\w+)")
        rx.indexIn("foo 42-bar end")
        self.assertEqual(rx.cap(0), "42-bar")
        self.assertEqual(rx.cap(1), "42")
        self.assertEqual(rx.cap(2), "bar")

    # ------------------------------------------------------------------ #
    # Default / dummy values before any indexIn call
    # ------------------------------------------------------------------ #

    def test_matchedLength_before_indexIn(self):
        """matchedLength should return -1 when indexIn has not been called."""
        rx = self.QRegExp(r"\d+")
        self.assertEqual(rx.matchedLength(), -1)

    def test_pos_before_indexIn(self):
        """pos should return -1 when indexIn has not been called."""
        rx = self.QRegExp(r"\d+")
        self.assertEqual(rx.pos(0), -1)

    def test_cap_before_indexIn(self):
        """cap should return empty string when indexIn has not been called."""
        rx = self.QRegExp(r"\d+")
        self.assertEqual(rx.cap(0), "")

    # ------------------------------------------------------------------ #
    # Negative offset
    # ------------------------------------------------------------------ #

    def test_indexIn_negative_offset(self):
        """indexIn with negative offset should return -1 and not crash state methods."""
        rx = self.QRegExp(r"\d+")
        result = rx.indexIn("abc 123", offset=-1)
        self.assertEqual(result, -1)
        # State methods should still return safe defaults
        self.assertEqual(rx.matchedLength(), -1)
        self.assertEqual(rx.pos(0), -1)
        self.assertEqual(rx.cap(0), "")

    # ------------------------------------------------------------------ #
    # No match
    # ------------------------------------------------------------------ #

    def test_indexIn_no_match(self):
        """When pattern does not match, state methods return defaults."""
        rx = self.QRegExp(r"\d+")
        result = rx.indexIn("no digits here")
        self.assertEqual(result, -1)
        self.assertEqual(rx.matchedLength(), -1)
        self.assertEqual(rx.pos(0), -1)
        self.assertEqual(rx.cap(0), "")

    # ------------------------------------------------------------------ #
    # Pattern syntax conversion
    # ------------------------------------------------------------------ #

    def test_fixed_string_pattern_syntax(self):
        """FixedString syntax (2) should escape the pattern for literal matching."""
        # "a.b" with FixedString should match the literal "a.b", not "a<any>b"
        rx = self.QRegExp("a.b", syntax=2)
        # Should match literal "a.b"
        self.assertNotEqual(rx.indexIn("a.b"), -1)
        # Should NOT match "axb" because the dot is escaped
        self.assertEqual(rx.indexIn("axb"), -1)

    def test_wildcard_pattern_syntax(self):
        """Wildcard syntax (1) should convert glob to regex."""
        rx = self.QRegExp("*.txt", syntax=1)
        self.assertNotEqual(rx.indexIn("readme.txt"), -1)

    def test_regexp_pattern_syntax_passthrough(self):
        """RegExp syntax (0) should pass through the pattern unchanged."""
        rx = self.QRegExp(r"\d+", syntax=0)
        result = rx.indexIn("abc 42 xyz")
        self.assertEqual(result, 4)
        self.assertEqual(rx.cap(0), "42")
