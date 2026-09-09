"""Shared read-only file preview pane for desktop review surfaces."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from nwbforge.app.services.file_preview import FilePreviewKind, FilePreviewResult, LocalFilePreviewService

try:
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
    from PySide6.QtMultimediaWidgets import QVideoWidget
except Exception:  # pragma: no cover - optional runtime support
    QAudioOutput = None
    QMediaPlayer = None
    QVideoWidget = None


class FilePreviewPane(QWidget):
    """Render bounded read-only previews for selected local files."""

    def __init__(
        self,
        parent=None,
        *,
        preview_service: LocalFilePreviewService | None = None,
        empty_message: str = "Select a file to preview it here.",
    ) -> None:
        super().__init__(parent)
        self._preview_service = preview_service or LocalFilePreviewService()
        self._empty_message = empty_message
        self._current_path: Path | None = None

        self._title_label = QLabel("No file selected", self)
        self._title_label.setProperty("role", "sectionTitle")
        self._summary_label = QLabel(empty_message, self)
        self._summary_label.setWordWrap(True)
        self._summary_label.setProperty("role", "muted")
        self._metadata_label = QLabel("", self)
        self._metadata_label.setWordWrap(True)
        self._metadata_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self._stack = QStackedWidget(self)

        self._message_label = QLabel(empty_message, self)
        self._message_label.setWordWrap(True)
        self._message_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        message_page = QWidget(self)
        message_layout = QVBoxLayout(message_page)
        message_layout.setContentsMargins(0, 0, 0, 0)
        message_layout.addWidget(self._message_label)
        message_layout.addStretch(1)

        self._text_preview = QPlainTextEdit(self)
        self._text_preview.setReadOnly(True)

        self._table_preview = QTableWidget(self)
        self._table_preview.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table_preview.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._table_preview.setAlternatingRowColors(True)
        self._table_preview.verticalHeader().setVisible(False)
        self._table_preview.setWordWrap(False)

        self._image_label = QLabel(self)
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setMinimumHeight(220)
        self._image_label.setText("Image preview unavailable.")
        self._image_label.setWordWrap(True)
        image_scroll = QScrollArea(self)
        image_scroll.setWidgetResizable(True)
        image_scroll.setWidget(self._image_label)

        self._media_hint_label = QLabel("Media preview unavailable.", self)
        self._media_hint_label.setWordWrap(True)
        self._media_play_button = QPushButton("Play", self)
        self._media_pause_button = QPushButton("Pause", self)
        self._media_stop_button = QPushButton("Stop", self)
        self._media_play_button.setProperty("secondary", True)
        self._media_pause_button.setProperty("secondary", True)
        self._media_stop_button.setProperty("secondary", True)
        media_controls = QHBoxLayout()
        media_controls.addWidget(self._media_play_button)
        media_controls.addWidget(self._media_pause_button)
        media_controls.addWidget(self._media_stop_button)
        media_controls.addStretch(1)
        media_page = QWidget(self)
        media_layout = QVBoxLayout(media_page)
        media_layout.setContentsMargins(0, 0, 0, 0)
        media_layout.addWidget(self._media_hint_label)
        media_layout.addLayout(media_controls)
        if QVideoWidget is not None:
            self._video_widget = QVideoWidget(media_page)
            self._video_widget.setMinimumHeight(220)
            media_layout.addWidget(self._video_widget, 1)
        else:  # pragma: no cover - depends on runtime multimedia support
            self._video_widget = None
        media_layout.addStretch(1)

        self._stack.addWidget(message_page)
        self._stack.addWidget(self._text_preview)
        self._stack.addWidget(self._table_preview)
        self._stack.addWidget(image_scroll)
        self._stack.addWidget(media_page)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self._title_label)
        layout.addWidget(self._summary_label)
        layout.addWidget(self._metadata_label)
        layout.addWidget(self._stack, 1)

        if QMediaPlayer is not None and QAudioOutput is not None:
            self._audio_output = QAudioOutput(self)
            self._media_player = QMediaPlayer(self)
            self._media_player.setAudioOutput(self._audio_output)
            if self._video_widget is not None:
                self._media_player.setVideoOutput(self._video_widget)
        else:  # pragma: no cover - depends on runtime multimedia support
            self._audio_output = None
            self._media_player = None
        self._media_play_button.clicked.connect(self._play_media)
        self._media_pause_button.clicked.connect(self._pause_media)
        self._media_stop_button.clicked.connect(self._stop_media)
        self.set_preview_path(None)

    def set_preview_path(self, path: Path | None) -> None:
        """Load preview content for the given path."""

        self._current_path = path.resolve() if path is not None else None
        preview = self._preview_service.build_preview(path)
        self._apply_preview(preview)

    @property
    def current_path(self) -> Path | None:
        return self._current_path

    def _apply_preview(self, preview: FilePreviewResult) -> None:
        self._title_label.setText(preview.title)
        self._summary_label.setText(preview.summary)
        self._metadata_label.setText("\n".join(preview.metadata_lines))
        self._stop_media()
        self._image_label.setPixmap(QPixmap())
        self._image_label.setText("Image preview unavailable.")
        if preview.kind in {FilePreviewKind.EMPTY, FilePreviewKind.MISSING, FilePreviewKind.ERROR, FilePreviewKind.NWB, FilePreviewKind.BINARY}:
            self._message_label.setText(preview.summary)
            self._stack.setCurrentIndex(0)
            return
        if preview.kind in {FilePreviewKind.TEXT, FilePreviewKind.DIRECTORY}:
            self._text_preview.setPlainText(preview.text_content or "")
            self._stack.setCurrentIndex(1)
            return
        if preview.kind is FilePreviewKind.TABLE and preview.table is not None:
            self._populate_table(preview)
            self._stack.setCurrentIndex(2)
            return
        if preview.kind is FilePreviewKind.IMAGE and preview.media_path is not None:
            self._populate_image(preview.media_path)
            self._stack.setCurrentIndex(3)
            return
        if preview.kind in {FilePreviewKind.VIDEO, FilePreviewKind.AUDIO}:
            if preview.media_path is not None and self._media_player is not None:
                self._populate_media(preview)
                self._stack.setCurrentIndex(4)
                return
            self._message_label.setText(preview.summary)
            self._stack.setCurrentIndex(0)
            return
        self._message_label.setText(preview.summary)
        self._stack.setCurrentIndex(0)

    def _populate_table(self, preview: FilePreviewResult) -> None:
        table = preview.table
        if table is None:
            self._table_preview.clear()
            self._table_preview.setRowCount(0)
            self._table_preview.setColumnCount(0)
            return
        headers = table.headers
        rows = table.rows
        column_count = max(len(headers), max((len(row) for row in rows), default=0))
        self._table_preview.clear()
        self._table_preview.setColumnCount(column_count)
        self._table_preview.setRowCount(len(rows))
        if headers:
            self._table_preview.setHorizontalHeaderLabels(list(headers))
        elif column_count > 0:
            self._table_preview.setHorizontalHeaderLabels(
                [f"Column {index + 1}" for index in range(column_count)]
            )
        for row_index, row in enumerate(rows):
            for column_index in range(column_count):
                value = row[column_index] if column_index < len(row) else ""
                item = QTableWidgetItem(value)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                self._table_preview.setItem(row_index, column_index, item)
        self._table_preview.resizeColumnsToContents()

    def _populate_image(self, path: Path) -> None:
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            self._image_label.setText("Image preview could not be loaded.")
            self._image_label.setPixmap(QPixmap())
            return
        scaled = pixmap.scaled(
            720,
            420,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._image_label.setPixmap(scaled)
        self._image_label.setText("")

    def _populate_media(self, preview: FilePreviewResult) -> None:
        if self._media_player is None or preview.media_path is None:
            self._media_hint_label.setText(preview.summary)
            return
        media_kind = "video" if preview.kind is FilePreviewKind.VIDEO else "audio"
        self._media_hint_label.setText(
            f"Loaded {media_kind} preview for {preview.media_path.name}. Use the playback controls to inspect it."
        )
        if self._video_widget is not None:
            self._video_widget.setVisible(preview.kind is FilePreviewKind.VIDEO)
        self._media_player.setSource(QUrl.fromLocalFile(str(preview.media_path)))

    def _play_media(self) -> None:
        if self._media_player is not None:
            self._media_player.play()

    def _pause_media(self) -> None:
        if self._media_player is not None:
            self._media_player.pause()

    def _stop_media(self) -> None:
        if self._media_player is not None:
            self._media_player.stop()
