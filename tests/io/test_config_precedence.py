from __future__ import annotations

from pathlib import Path

from crv.io.config import IoSettings


def _write_crv_toml(tmp: Path, content: str) -> Path:
    p = tmp / "crv.toml"
    p.write_text(content)
    return p


def test_io_settings_precedence_env_over_toml(tmp_path: Path, monkeypatch) -> None:
    # Arrange TOML
    _write_crv_toml(
        tmp_path,
        """
        [io]
        root_dir = "tmp_out_toml"
        tick_bucket_size = 256
        compression = "lz4"
        """.strip(),
    )
    # Ensure cwd for IoSettings.from_toml() search
    monkeypatch.chdir(tmp_path)
    # Arrange ENV that should override TOML
    monkeypatch.setenv("CRV_IO_ROOT_DIR", "tmp_out_env")
    monkeypatch.setenv("CRV_IO_TICK_BUCKET_SIZE", "512")
    monkeypatch.setenv("CRV_IO_COMPRESSION", "zstd")

    # Act
    s = IoSettings.load()

    # Assert precedence: env > TOML
    assert s.root_dir == "tmp_out_env"
    assert s.tick_bucket_size == 512  # env override
    assert s.compression == "zstd"  # env override


def test_io_settings_from_toml_when_no_env(tmp_path: Path, monkeypatch) -> None:
    # Arrange TOML only
    _write_crv_toml(
        tmp_path,
        """
        [io]
        root_dir = "tmp_out_toml"
        tick_bucket_size = 128
        compression = "snappy"
        strict_schema = true
        """.strip(),
    )
    monkeypatch.chdir(tmp_path)
    # Ensure env not set
    for key in [
        "CRV_IO_ROOT_DIR",
        "CRV_IO_TICK_BUCKET_SIZE",
        "CRV_IO_COMPRESSION",
        "CRV_IO_STRICT_SCHEMA",
    ]:
        monkeypatch.delenv(key, raising=False)

    # Act
    s = IoSettings.load()

    # Assert TOML applied
    assert s.root_dir == "tmp_out_toml"
    assert s.tick_bucket_size == 128
    assert s.compression == "snappy"
    assert s.strict_schema is True


def test_io_settings_defaults_when_no_config(tmp_path: Path, monkeypatch) -> None:
    # No TOML, no env
    monkeypatch.chdir(tmp_path)
    for key in [
        "CRV_IO_ROOT_DIR",
        "CRV_IO_TICK_BUCKET_SIZE",
        "CRV_IO_COMPRESSION",
        "CRV_IO_STRICT_SCHEMA",
    ]:
        monkeypatch.delenv(key, raising=False)

    s = IoSettings.load()

    # Defaults from IoSettings / crv.core.constants
    assert s.root_dir == "out"
    assert s.partitioning == "tick_buckets"
    assert isinstance(s.tick_bucket_size, int)
    assert s.compression in {"zstd", "lz4", "snappy"}
