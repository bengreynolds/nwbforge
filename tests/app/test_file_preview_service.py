from __future__ import annotations

from pathlib import Path

from nwbforge.app.services.file_preview import FilePreviewKind, LocalFilePreviewService


def test_file_preview_service_builds_text_preview(tmp_path: Path) -> None:
    path = tmp_path / "notes.txt"
    path.write_text("line one\nline two\n", encoding="utf-8")

    preview = LocalFilePreviewService().build_preview(path)

    assert preview.kind is FilePreviewKind.TEXT
    assert preview.path == path
    assert preview.text_content is not None
    assert "line one" in preview.text_content
    assert "Text preview loaded" in preview.summary


def test_file_preview_service_builds_table_preview(tmp_path: Path) -> None:
    path = tmp_path / "table.csv"
    path.write_text("name,value\nalpha,1\nbeta,2\n", encoding="utf-8")

    preview = LocalFilePreviewService().build_preview(path)

    assert preview.kind is FilePreviewKind.TABLE
    assert preview.table is not None
    assert preview.table.headers == ("name", "value")
    assert preview.table.rows == (("alpha", "1"), ("beta", "2"))


def test_file_preview_service_builds_directory_preview(tmp_path: Path) -> None:
    folder = tmp_path / "bundle"
    folder.mkdir()
    (folder / "a.txt").write_text("a", encoding="utf-8")
    (folder / "b.txt").write_text("b", encoding="utf-8")

    preview = LocalFilePreviewService().build_preview(folder)

    assert preview.kind is FilePreviewKind.DIRECTORY
    assert preview.text_content is not None
    assert "[file] a.txt" in preview.text_content
    assert "Directory preview" in preview.summary


def test_file_preview_service_marks_nwb_for_specialized_viewing(tmp_path: Path) -> None:
    path = tmp_path / "result.nwb"
    path.write_bytes(b"NWB")

    preview = LocalFilePreviewService().build_preview(path)

    assert preview.kind is FilePreviewKind.NWB
    assert "integrated NWB viewer" in preview.summary
