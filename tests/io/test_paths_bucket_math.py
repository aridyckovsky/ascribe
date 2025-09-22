import os

import pytest

from crv.io.config import IoSettings
from crv.io.paths import (
    bucket_dir,
    bucket_id_for_tick,
    format_bucket_dir,
    manifest_path,
    run_root,
    table_dir,
    tables_root,
)


def test_bucket_id_for_tick_basic():
    assert bucket_id_for_tick(0, 100) == 0
    assert bucket_id_for_tick(99, 100) == 0
    assert bucket_id_for_tick(100, 100) == 1
    assert bucket_id_for_tick(101, 100) == 1
    assert bucket_id_for_tick(199, 100) == 1
    assert bucket_id_for_tick(200, 100) == 2


def test_bucket_id_for_tick_invalid():
    with pytest.raises(ValueError):
        bucket_id_for_tick(-1, 100)
    with pytest.raises(ValueError):
        bucket_id_for_tick(0, 0)


def test_format_bucket_dir():
    assert format_bucket_dir(0) == "bucket=000000"
    assert format_bucket_dir(1) == "bucket=000001"
    assert format_bucket_dir(123) == "bucket=000123"
    with pytest.raises(ValueError):
        format_bucket_dir(-1)


def test_path_layout_helpers(tmp_path):
    settings = IoSettings(root_dir=str(tmp_path))
    run_id = "20250101-000000"
    tname = "identity_edges"

    rroot = run_root(settings, run_id)
    assert rroot == os.path.join(str(tmp_path), "runs", run_id)

    troot = tables_root(settings, run_id)
    assert troot == os.path.join(rroot, "tables")

    tdir = table_dir(settings, run_id, tname)
    assert tdir == os.path.join(troot, tname)

    mpath = manifest_path(settings, run_id, tname)
    assert mpath == os.path.join(tdir, "manifest.json")

    bdir = bucket_dir(settings, run_id, tname, 123)
    assert bdir == os.path.join(tdir, "bucket=000123")
