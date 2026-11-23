---
paths:
  - "src/nvagik/**"
  - "pyproject.toml"
  - "tests/test_dependencies.py"
---

# Qt (PySide6)

- Qt comes from `pyside6-essentials`, not the full `pyside6`.
- A feature that needs an Addons module (Charts, Multimedia, WebSockets, ...) adds `pyside6-addons` with a docs/DECISIONS.md entry, and adds it to `ALLOWED_QT` in `tests/test_dependencies.py`.
- Qt's own translations are loaded as `qtbase_<lang>`, never `qt_<lang>`: that one needs an Addons file and fails silently. Details: `/i18n`.
