---
paths:
  - ".gitattributes"
  - ".gitignore"
  - "tests/test_gitattributes.py"
---

# Line endings and binary files

- `.gitattributes` keeps every text file in LF, on disk too (`* text=auto eol=lf`, overriding `core.autocrlf`). Only `*.bat` and `*.cmd` use CRLF.
- A new binary file type (audio, images, fonts, packages) is added there as `binary`. The guard then reads such files whole from the object database.
- `tests/test_gitattributes.py` checks the rules and that no file is stored with CRLF.
- `PRIVATE.md` stays in `.gitignore`.
