# PySide2 to PySide6 Migration Spec for tk-core

## 1. Executive Summary

This document specifies the migration plan for `tk-core` (the Shotgun Pipeline Toolkit Core API) from **PySide2** (Qt5) to **PySide6** (Qt6) as the primary Qt binding. Today, tk-core ships with a compatibility layer that allows PySide6 to be used as a fallback when PySide2 is absent, but PySide2 remains the preferred binding. The goal of this migration is to **make PySide6 the default and eventually remove PySide2 support entirely**.

### Current State vs. Target State

```
 CURRENT STATE                               TARGET STATE
 +-----------------------------------------+ +-----------------------------------------+
 |          QtImporter._import_modules()    | |          QtImporter._import_modules()    |
 |                                          | |                                          |
 |  QT4 interface requested:               | |  QT4 interface requested:                |
 |    1. Try PySide2 (preferred)  <----+    | |    1. Try PySide6 (preferred)  <----+    |
 |    2. Fallback to PySide6      (new)|    | |    2. Fallback to PySide2 (legacy)  |    |
 |                                          | |       (behind env-var gate)          |    |
 |  QT5 interface requested:               | |                                          |
 |    1. Try PySide2 only                   | |  QT6 interface requested:                |
 |                                          | |    1. Try PySide6 only                   |
 |  QT6 interface requested:               | |                                          |
 |    1. Try PySide6 only                   | |  QT5 interface requested (deprecated):   |
 +-----------------------------------------+ |    1. Try PySide2 (if available)          |
                                              +-----------------------------------------+
```

---

## 2. Scope of PySide2 Usage in tk-core

### 2.1 File Inventory

The following files directly reference PySide2 or contain PySide2-specific logic:

| File | Role | Migration Impact |
|------|------|-----------------|
| `python/tank/util/qt_importer.py` | Central Qt import orchestrator | **HIGH** - Controls binding resolution order |
| `python/tank/util/pyside2_patcher.py` | Patches PySide2 to look like PySide (Qt4 API) | **HIGH** - Must be retained for backward compat or removed |
| `python/tank/util/pyside6_patcher.py` | Patches PySide6 to look like PySide (Qt4 API), inherits from PySide2Patcher | **HIGH** - Becomes the primary patcher |
| `python/tank/platform/engine.py` | Engine base class; initializes Qt, exposes `has_qt5`/`has_qt6` | **MEDIUM** - Imports & properties need updating |
| `python/tank/platform/qt/__init__.py` | Exposes `QtCore`, `QtGui` at engine init | LOW - Populated dynamically |
| `python/tank/platform/qt5/__init__.py` | Exposes PySide2 modules at engine init | LOW - Populated dynamically |
| `python/tank/platform/qt6/__init__.py` | Exposes PySide6 modules at engine init | LOW - Populated dynamically |
| `python/tank/authentication/ui/qt_abstraction.py` | Instantiates `QtImporter()` for auth UI | LOW - Uses importer abstraction |
| `python/tank/authentication/login_dialog.py` | Login dialog using Qt widgets | MEDIUM - Uses `exec_()`, `QMessageBox`, etc. |
| `python/tank/authentication/sso_saml2/core/sso_saml2_core.py` | SSO web login via QtWebEngine | MEDIUM - Comments reference PySide2 |
| `python/tank/authentication/sso_saml2/core/errors.py` | `SsoSaml2IncompletePySide2` exception class | LOW - Rename / generalize |
| `python/tank/authentication/sso_saml2/sso_saml2.py` | SSO wrapper (docstrings reference PySide2) | LOW - Docstring update |
| `python/tank/authentication/sso_saml2/sso_saml2_rv.py` | RV-specific SSO (docstrings reference PySide2) | LOW - Docstring update |
| `tests/util_tests/test_qt_importer.py` | Tests for QtImporter | MEDIUM - Test logic must flip |
| `tests/util_tests/test_pyside6_patcher.py` | Tests for PySide6Patcher | LOW |
| `tests/python/tank_test/tank_test_base.py` | Test helpers (`skip_if_pyside2`, `skip_if_pyside6`) | MEDIUM |
| `docs/environment_variables.rst` | Documents `SHOTGUN_SKIP_QTWEBENGINEWIDGETS_IMPORT` | LOW - Doc update |

### 2.2 Architecture Overview

```
  DCC Application (Maya, Nuke, Houdini, ...)
       |
       v
  +--------------------+
  |   Engine.__init__   |
  |   (engine.py)       |
  +--------------------+
       |
       |  _define_qt_base() --> QtImporter(QT4)
       |  __define_qt5_base() --> QtImporter(QT5)
       |  __define_qt6_base() --> QtImporter(QT6)
       |
       v
  +--------------------+      +------------------------+
  |   QtImporter        |----->| _import_pyside2_as_    |
  |   (qt_importer.py)  |     |    _pyside()            |
  +--------------------+      | Uses PySide2Patcher     |
       |                       +------------------------+
       |
       +--------------------->+------------------------+
                              | _import_pyside6_as_    |
                              |    _pyside()            |
                              | Uses PySide6Patcher     |
                              +------------------------+
                                        |
                    Inherits from PySide2Patcher
                                        |
                                        v
                              +------------------------+
                              |   PySide2Patcher        |
                              | (pyside2_patcher.py)    |
                              |                         |
                              | Creates shim modules:   |
                              |  PySide.QtCore          |
                              |  PySide.QtGui           |
                              | (merges QtWidgets back  |
                              |  into QtGui for Qt4     |
                              |  compat)                |
                              +------------------------+

                              +------------------------+
                              |   PySide6Patcher        |
                              | (pyside6_patcher.py)    |
                              |                         |
                              | Additional patches:     |
                              |  - QDesktopWidget shim  |
                              |  - QRegExp -> QRegularExpression |
                              |  - exec_() alias        |
                              |  - QPixmap(None) fix    |
                              |  - QWheelEvent.delta()  |
                              |  - QFont.setWeight()    |
                              |  - etc.                 |
                              +------------------------+
```

---

## 3. Breaking Changes: PySide2 vs. PySide6

This section catalogs every breaking change relevant to tk-core, along with the current patching status.

### 3.1 Module Reorganization

| Change | PySide2 (Qt5) | PySide6 (Qt6) | Currently Patched? |
|--------|---------------|---------------|--------------------|
| `QtWidgets` split from `QtGui` | `QtWidgets` exists as separate module | Same | YES - merged back into `QtGui` shim |
| OpenGL classes moved to `QtOpenGL` | In `QtGui` | In `QtOpenGL` | YES - `_opengl_to_gui` set in PySide6Patcher |
| `QtWebEngineWidgets` split | `QWebEnginePage`/`QWebEngineProfile` in `QtWebEngineWidgets` | Moved to `QtWebEngineCore` | YES - patched in PySide6Patcher |
| `shiboken2` -> `shiboken6` | `import shiboken2` | `import shiboken6` | YES - abstracted as `shiboken` key |

### 3.2 Removed / Renamed Classes

| Removed/Renamed | Replacement in Qt6 | Currently Patched? |
|-----------------|--------------------|--------------------|
| `QDesktopWidget` | `QScreen` (via `QGuiApplication.screens()`) | YES - `_patch_QScreen` creates full shim |
| `QRegExp` | `QRegularExpression` | YES - `_patch_QRegularExpression` + alias |
| `QTextCodec` | Removed entirely | YES - stub class patched in |

### 3.3 Removed / Renamed Methods and Properties

| Old API (PySide2) | New API (PySide6) | Currently Patched? | Notes |
|-------------------|-------------------|--------------------|-------|
| `QApplication.exec_()` | `QApplication.exec()` | YES | `exec_` alias added in pyside6_patcher |
| `QDialog.exec_()` | `QDialog.exec()` | YES | `exec_` alias added in pyside6_patcher |
| `QWheelEvent.delta()` | `QWheelEvent.angleDelta().y()` | YES | `_patch_QWheelEvent` |
| `QModelIndex.child(row, col)` | `model().index(row, col, parent)` | YES | `_patch_QModelIndex` |
| `QFontMetrics.width()` | `QFontMetrics.horizontalAdvance()` | YES | Alias patched |
| `QFont.setWeight()` | `QFont.setLegacyWeight()` | YES | Alias patched |
| `QHeaderView.setResizeMode()` | `QHeaderView.setSectionResizeMode()` | YES | Alias patched |
| `QAbstractItemView.viewOptions()` | `QAbstractItemView.initViewItemOption()` | YES | `_patch_QAbstractItemView` |
| `QPixmap(None)` | `QPixmap()` (no args) | YES | `_patch_QPixmap` |
| `QPixmap.grabWindow()` | `QScreen.grabWindow()` | YES | Patched via static method |
| `QPainter.HighQualityAntialiasing` | `QPainter.Antialiasing` | YES | Alias patched |
| `QPalette.Background` | `QPalette.Window` | YES | Alias patched |
| `Qt.MidButton` | `Qt.MiddleButton` | YES | Alias patched |
| `QAbstractButton.animateClick(msec)` | `QAbstractButton.animateClick()` (no timeout param) | YES | Lambda wrapper patched |
| `QCoreApplication.flush()` | Removed | YES | No-op stub patched |
| `QOpenGLContext.versionFunctions()` | `QOpenGLVersionFunctionsFactory.get()` | YES | `_patch_QOpenGLContext` |
| `QSortFilterProxyModel.filterRegExp` | `filterRegularExpression` | YES | Alias patched |
| `QSortFilterProxyModel.setFilterRegExp` | `setFilterRegularExpression` | YES | Alias patched |

### 3.4 Behavioral Changes

| Behavior | PySide2 | PySide6 | Impact |
|----------|---------|---------|--------|
| Enum scoping | Unscoped (`Qt.AlignLeft`) | Scoped enums (`Qt.AlignmentFlag.AlignLeft`), but backward-compat aliases still work | LOW risk - monitor for edge cases |
| Signal/slot `emit()` | `signal.emit(args)` | Same, but `QVariant` removed | Possible breakage in custom signals |
| `QLabel.setPixmap(None)` | Accepted | Raises TypeError | YES - patched |
| `QIcon.pixmap()` returns native `QPixmap` | Returns PySide2 QPixmap | Returns PySide6 QPixmap (not patched subclass) | YES - `_patch_QIcon` wraps result |
| Cookie persistence (WebEngine) | `QWebEngineProfile.ForcePersistentCookies` | Same constant, but import path changed | YES - handled through shim |

### 3.5 Partially Patched / Known Limitations

The following `QRegExp`-to-`QRegularExpression` adaptations **cannot be fully patched** because `QRegularExpression` is stateless (returns match objects instead of storing state):

```
  PySide2 QRegExp (stateful)               PySide6 QRegularExpression (stateless)
  +----------------------------+            +-----------------------------------+
  | re = QRegExp("pattern")    |            | re = QRegularExpression("pattern")|
  | re.indexIn(text)           |            | match = re.match(text)            |
  | pos = re.pos(0)  <-- state|            | pos = match.capturedStart(0)      |
  | len = re.matchedLength()   |            | len = match.capturedLength(0)     |
  | cap = re.cap(0)            |            | cap = match.captured(0)           |
  +----------------------------+            +-----------------------------------+

  The patcher's matchedLength(), pos(), and cap() methods return
  dummy values (-1, -1, "") because the regex object has no internal
  match state. Code relying on these WILL BREAK.
```

---

## 4. Migration Plan

### Phase 1: Preparation (No user-facing changes)

1. **Audit all downstream engines and apps** for direct `from PySide2 import ...` usage. These must go through `tank.platform.qt` or `tank.platform.qt5` instead.

2. **Add deprecation warnings** to `_import_pyside2()` and `_import_pyside2_as_pyside()` in `qt_importer.py`:
   ```python
   import warnings
   warnings.warn(
       "PySide2 support is deprecated and will be removed in a future release. "
       "Please migrate to PySide6.",
       DeprecationWarning,
       stacklevel=2,
   )
   ```

3. **Rename `SsoSaml2IncompletePySide2`** to `SsoSaml2IncompleteQtBinding` (keep old name as alias for backward compat).

4. **Update all docstrings/comments** that say "PySide2" when they mean "the current Qt binding" (e.g., in `sso_saml2.py`, `sso_saml2_rv.py`, `sso_saml2_core.py`).

### Phase 2: Flip the Default

5. **Change `_import_modules()` resolution order** in `qt_importer.py`:

   **Before (current):**
   ```
   QT4 interface:
     1. Try PySide2  <-- first
     2. Try PySide6  <-- fallback
   ```

   **After:**
   ```
   QT4 interface:
     1. Try PySide6  <-- first (new default)
     2. Try PySide2  <-- fallback (deprecated)
   ```

   The relevant code block is in `_import_modules()` (lines 372-388 of `qt_importer.py`).

6. **Add an environment variable** `SGTK_FORCE_PYSIDE2` that forces the old PySide2-first behavior for studios that need a transition period:
   ```python
   if os.environ.get("SGTK_FORCE_PYSIDE2"):
       # Legacy order: PySide2 first
       try_order = [self._import_pyside2_as_pyside, self._import_pyside6_as_pyside]
   else:
       # New default: PySide6 first
       try_order = [self._import_pyside6_as_pyside, self._import_pyside2_as_pyside]
   ```

7. **Update `__define_qt5_base()`** to also try PySide6 modules when PySide2 is not available, since many Qt5 modules are available in PySide6.

### Phase 3: Harden PySide6 Patcher

8. **Fix incomplete `QRegularExpression` patches**: For `matchedLength()`, `pos()`, and `cap()`, log a `DeprecationWarning` instead of silently returning dummy values:
   ```python
   @staticmethod
   def matchedLength(re):
       warnings.warn(
           "QRegExp.matchedLength() is not supported under PySide6. "
           "Please use QRegularExpressionMatch.capturedLength() instead.",
           DeprecationWarning,
           stacklevel=2,
       )
       return -1
   ```

9. **Decouple `PySide6Patcher` from `PySide2Patcher` inheritance**: Currently `PySide6Patcher(PySide2Patcher)`. This coupling means PySide2Patcher cannot be removed without refactoring PySide6Patcher. Extract shared logic into a `_BaseQtPatcher`:

   ```
   CURRENT                          TARGET
   +------------------+             +------------------+
   | PySide2Patcher   |             | _BaseQtPatcher   |
   +------------------+             +------------------+
          ^                                ^        ^
          |                                |        |
   +------------------+             +------+--+ +---+----------+
   | PySide6Patcher   |             |PySide2  | | PySide6      |
   +------------------+             |Patcher  | | Patcher      |
                                    +---------+ +--------------+
   ```

10. **Handle scoped enums**: While Qt6 maintains backward-compatible unscoped enum access in most cases, add a runtime check in the patcher for any known enum breakages discovered during testing.

### Phase 4: Test Suite Updates

11. **Update `test_qt_importer.py`**:
    - Adjust `test_qt_importer_with_pyside6_interface_qt4` to no longer require `@skip_if_pyside2(found=True)` (since PySide6 will be preferred even when PySide2 is present).
    - Add a new test: `test_qt_importer_force_pyside2_env_var` to verify the `SGTK_FORCE_PYSIDE2` override.
    - Add a test that verifies deprecation warnings are emitted when PySide2 is loaded.

12. **Update `tank_test_base.py`**: Add `skip_if_no_qt` decorator for tests that require any Qt binding.

13. **Add integration tests** that import every patched class/method and verify they work under PySide6 (expand `test_pyside6_patcher.py` beyond the current single test).

### Phase 5: Remove PySide2 Support (Future)

14. **Remove `pyside2_patcher.py`** (after extracting shared logic to `_BaseQtPatcher`).

15. **Remove `_import_pyside2()` and `_import_pyside2_as_pyside()`** from `qt_importer.py`.

16. **Remove `SGTK_FORCE_PYSIDE2` env var** and related fallback code.

17. **Remove `skip_if_pyside2` test decorators** and PySide2-specific tests.

18. **Remove `shiboken2` references** from all code paths.

19. **Clean up `pyside6_patcher.py`**: Remove patches that only exist for PySide2 backward compat (e.g., `exec_()` alias can be removed once all downstream code uses `exec()`).

---

## 5. Affected Downstream Components

Engines and apps that import Qt through `tank.platform.qt` will automatically pick up the new binding. However, the following patterns in downstream code must be audited:

| Pattern | Risk | Action |
|---------|------|--------|
| `from PySide2 import ...` (direct import) | HIGH | Must change to `from sgtk.platform.qt import ...` |
| `import shiboken2` | HIGH | Must change to `from sgtk.platform.qt import shiboken` |
| Use of `exec_()` | LOW | Already aliased, but should migrate to `exec()` |
| Use of `QDesktopWidget` | LOW | Already shimmed, but should migrate to `QScreen` |
| Use of `QRegExp` with stateful methods | MEDIUM | Must migrate to `QRegularExpression` + match objects |
| Use of `QPixmap(None)` | LOW | Already patched |
| Use of `QFontMetrics.width()` | LOW | Already aliased |
| Custom `QWebEnginePage` subclasses | MEDIUM | Import paths changed between Qt5 and Qt6 |

---

## 6. Environment Variables (New and Modified)

| Variable | Status | Description |
|----------|--------|-------------|
| `SGTK_FORCE_PYSIDE2` | **NEW** | Forces PySide2-first resolution order (escape hatch during migration) |
| `SHOTGUN_SKIP_QTWEBENGINEWIDGETS_IMPORT` | Existing | Prevents importing QtWebEngine modules (unchanged) |
| `SGTK_FORCE_STANDARD_LOGIN_DIALOG` | Existing | Forces legacy login dialog (unchanged) |

---

## 7. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| DCC ships only PySide2 (no PySide6) | HIGH (Maya <2025, Nuke <15) | Toolkit breaks in those DCCs | Keep PySide2 fallback with `SGTK_FORCE_PYSIDE2` env var |
| `QRegExp` stateful API used in apps | MEDIUM | Silent incorrect behavior | Add deprecation warnings; audit app codebase |
| Scoped enum changes break app code | LOW | Runtime AttributeError | Qt6 still supports unscoped access for most enums |
| `PySide6Patcher` misses a patch | MEDIUM | Runtime errors in specific DCCs | Expand integration test coverage |
| SSO/WebEngine behavior differences | LOW | Login failures | QtWebEngine API largely stable; test SSO flow |
| Third-party plugins using PySide2 directly | MEDIUM | Import conflicts | Document migration path; provide deprecation timeline |

---

## 8. Testing Strategy

### Unit Tests
- All existing tests in `tests/util_tests/test_qt_importer.py` and `test_pyside6_patcher.py` updated
- New tests for `SGTK_FORCE_PYSIDE2` env var
- New tests for deprecation warnings

### Integration Tests
- Test `QtImporter` with both PySide2 and PySide6 installed simultaneously
- Test login dialog renders and functions under PySide6
- Test SSO flow under PySide6
- Test dark theme initialization under PySide6

### DCC Smoke Tests
Each DCC engine should be tested:
- **Maya** (2024+): PySide6 available since Maya 2025
- **Nuke** (14+): PySide6 available since Nuke 15
- **Houdini** (19.5+): PySide6 available since Houdini 20
- **Unreal Engine**: Ships its own Qt; verify compatibility

---

## 9. Migration Timeline (Suggested)

| Milestone | Target | Description |
|-----------|--------|-------------|
| Phase 1 | Sprint 1 | Deprecation warnings, docstring updates, error class rename |
| Phase 2 | Sprint 2 | Flip default to PySide6, add `SGTK_FORCE_PYSIDE2` |
| Phase 3 | Sprint 2-3 | Harden PySide6Patcher, decouple from PySide2Patcher |
| Phase 4 | Sprint 3 | Test suite overhaul |
| Phase 5 | Sprint 6+ | Remove PySide2 support (after one major release cycle) |

---

## 10. Appendix: Full List of Patched APIs in PySide6Patcher

The `PySide6Patcher.patch()` method (in `pyside6_patcher.py`) applies the following transformations:

### Inherited from PySide2Patcher
- `_move_attributes()` - Merges `QtWidgets` + `QtGui` -> `QtGui` shim
- `_patch_QCoreApplication()` - Adds `translate()` compat
- `_patch_QApplication()` - Adds `qApp` attribute, `desktop()` method
- `_patch_QStandardItemModel()` - Wraps `dataChanged` signal
- `_patch_QMessageBox()` - Fixes button union handling (only for PySide < 5.x)
- `_patch_QDesktopServices()` - Adds `openUrl()` fallback
- `_patch_QTextCodec()` - Stub class (overridden by PySide6Patcher)

### PySide6-Specific Patches
- `_patch_QAbstractItemView()` - `viewOptions()` -> `initViewItemOption()`
- `_patch_QPixmap()` - Handles `QPixmap(None)` constructor
- `_patch_QIcon()` - Wraps `pixmap()` to return patched `QPixmap`
- `_patch_QLabel()` - Handles `setPixmap(None)`
- `_patch_QScreen()` - Full `QDesktopWidget` shim with signals
- `_patch_QOpenGLContext()` - `versionFunctions()` redirect
- `_patch_QWheelEvent()` - `delta()` -> `angleDelta().y()`
- `_patch_QModelIndex()` - `child()` method restoration
- `_patch_QRegularExpression()` - `QRegExp` API emulation
- `_patch_QCoreApplication_flush()` - No-op stub

### Direct Attribute Aliases
- `Qt.MidButton` = `Qt.MiddleButton`
- `QRegExp` = `QRegularExpression`
- `QApplication.exec_` = `QApplication.exec`
- `QDialog.exec_` = `QDialog.exec`
- `QDesktopWidget` = `QScreen`
- `QFontMetrics.width` = `QFontMetrics.horizontalAdvance`
- `QFont.setWeight` = `QFont.setLegacyWeight`
- `QHeaderView.setResizeMode` = `QHeaderView.setSectionResizeMode`
- `QPainter.HighQualityAntialiasing` = `QPainter.Antialiasing`
- `QPalette.Background` = `QPalette.Window`
- `QSortFilterProxyModel.filterRegExp` = `filterRegularExpression`
- `QSortFilterProxyModel.setFilterRegExp` = `setFilterRegularExpression`
- `QAbstractButton.animateClick(msec)` = `animateClick()` (timeout ignored)
- `QWebEnginePage` / `QWebEngineProfile` -> pulled from `QtWebEngineCore`
