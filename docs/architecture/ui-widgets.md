# Qt Widget Baseline

Purpose: bind the current desktop models to the first concrete PySide6 widget layer.

Current baseline:
- A main window, dialogs, log dock, file preview pane, and embedded viewer exist
- Shell-level errors surface through the Qt shell
- The widget layer remains a thin adapter over the existing screen models
- The current tests run headlessly against the Qt baseline

Constraints:
- Keep widgets thin and state-driven
- Prefer one integrated shell workspace over many top-level windows
- Preserve the existing model boundaries when adding new UI

Next step:
- Add new widget surfaces only when the model layer is already stable
