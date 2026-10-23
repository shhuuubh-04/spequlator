import shutil
from pathlib import Path

import pytest

from spequlator.datasets import codocbench as cdb

FIXTURE = Path(__file__).parent / "fixtures" / "codocbench_mini.jsonl"
FIXTURE_IDS = {
    "8e8e00c86a25",
    "b0759e4b9cdb",
    "21bbad6b09d7",
    "dc8baf45e2f6",
    "46d6cf9be0f2",
    "fc412c0a787b",
}


@pytest.fixture
def records():
    return list(cdb.iter_jsonl(FIXTURE, "train"))


def test_fixture_loads_with_stable_ids(records):
    assert {r.record_id for r in records} == FIXTURE_IDS
    lr = next(r for r in records if r.record_id == "8e8e00c86a25")
    assert lr.function == "observe_lr"
    assert lr.project_key == "chainer/chainer"
    assert "optimizer_name" in lr.new_code and "optimizer_name" not in lr.old_code
    assert lr.old_commit != lr.new_commit


def test_to_input_old_and_new(records):
    lr = next(r for r in records if r.function == "observe_lr")
    old = cdb.to_input(lr, "old")
    new = cdb.to_input(lr, "new")
    assert old.mode == new.mode == "change"
    assert old.documentation == lr.old_doc and new.documentation == lr.new_doc
    assert old.source.doc_version == "old" and old.source.record_id == lr.record_id
    with pytest.raises(ValueError):
        cdb.to_input(lr, "latest")  # type: ignore[arg-type]


def test_malformed_line_reports_line_number(tmp_path):
    bad = tmp_path / "train.jsonl"
    lines = FIXTURE.read_text(encoding="utf-8").splitlines()
    bad.write_text(lines[0] + "\n{not json\n", encoding="utf-8")
    with pytest.raises(cdb.DataIntegrityError, match="line 2"):
        list(cdb.iter_jsonl(bad, "train"))


def test_missing_field_is_rejected(tmp_path):
    bad = tmp_path / "train.jsonl"
    bad.write_text('{"owner": "a", "project": "b"}\n', encoding="utf-8")
    with pytest.raises(cdb.DataIntegrityError, match="missing field"):
        list(cdb.iter_jsonl(bad, "train"))


def test_missing_file_points_to_setup_guide(tmp_path):
    with pytest.raises(cdb.DataIntegrityError, match="START_HERE"):
        cdb.load_split("train", tmp_path)


def test_checksum_mismatch_raises(tmp_path):
    shutil.copy(FIXTURE, tmp_path / "train.jsonl")
    with pytest.raises(cdb.DataIntegrityError, match="does not match"):
        cdb.verify_checksums(tmp_path, names=("train.jsonl",))


def test_get_record_and_not_found(tmp_path):
    shutil.copy(FIXTURE, tmp_path / "train.jsonl")
    (tmp_path / "test.jsonl").write_text("", encoding="utf-8")
    assert cdb.get_record("8e8e00c86a25", directory=tmp_path).function == "observe_lr"
    with pytest.raises(cdb.RecordNotFound):
        cdb.get_record("000000000000", directory=tmp_path)


def test_invalid_split_name():
    with pytest.raises(ValueError):
        cdb.load_split("dev")  # type: ignore[arg-type]


_REAL = cdb.data_dir() / "train.jsonl"


@pytest.mark.skipif(not _REAL.exists(), reason="CoDocBench not downloaded (START_HERE step 3.3)")
def test_real_dataset_pins_counts_and_project_disjointness():
    cdb.verify_checksums()
    train, test = cdb.load_split("train"), cdb.load_split("test")
    assert (len(train), len(test)) == (2300, 2273)
    assert len({r.record_id for r in train + test}) == 4573
    # Repo *names* overlap (Python, manim) but owner/project keys must not (D-010).
    assert not ({r.project_key for r in train} & {r.project_key for r in test})
