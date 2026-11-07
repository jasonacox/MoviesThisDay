"""Tests for movie_db/correction_tool.py and the updates.jsonl file."""

import json
import os
import shutil

import pytest

from movie_db import correction_tool

UPDATES = os.path.join(os.path.dirname(__file__), "movie_db", "updates.jsonl")


def parse_lines(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def test_updates_file_is_valid_jsonl():
    for obj in parse_lines(UPDATES):
        assert obj.get("imdb_id", "").startswith("tt")


@pytest.mark.parametrize("trailing_newline", [True, False])
def test_append_keeps_every_line_parseable(tmp_path, monkeypatch, trailing_newline):
    path = tmp_path / "updates.jsonl"
    content = '{"imdb_id": "tt0000001", "release_year": "1999"}'
    path.write_text(content + ("\n" if trailing_newline else ""), encoding="utf-8")
    monkeypatch.setattr(correction_tool, "CORRECTIONS_PATH", str(path))

    correction_tool.append_correction(
        "tt0000002", {"release_date": "2000-01-02"}, {"title": "X"}
    )

    objs = parse_lines(path)
    assert [o["imdb_id"] for o in objs] == ["tt0000001", "tt0000002"]


def test_append_to_new_file(tmp_path, monkeypatch):
    path = tmp_path / "updates.jsonl"
    monkeypatch.setattr(correction_tool, "CORRECTIONS_PATH", str(path))
    correction_tool.append_correction("tt0000003", {"release_year": "2001"}, {})
    assert parse_lines(path) == [{"imdb_id": "tt0000003", "release_year": "2001"}]
