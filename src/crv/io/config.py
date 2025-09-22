"""
Configuration for the crv.io module.

Defines IoSettings, a frozen dataclass carrying runtime configuration for IO behavior.
Defaults are sourced from crv.core.constants (the single source of truth) and align with
a local file-based layout and tick-bucket partitioning.

Source of truth
- crv.core.constants.TICK_BUCKET_SIZE, ROW_GROUP_SIZE, COMPRESSION
- Partitioning semantics and table descriptors come from crv.core.tables
- Canonical table names from crv.core.grammar.TableName

Import DAG discipline
- Depends only on stdlib and crv.core.constants.
- Does not import higher layers (world, mind, lab, viz, app).

Notes
- Partitioning baseline: "tick_buckets" with bucket = tick // tick_bucket_size.
- Compression applies to Parquet writes via pyarrow in crv.io.write.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Literal

try:  # Python 3.11+ stdlib TOML parser
    import tomllib  # type: ignore
except Exception:  # pragma: no cover - environments without tomllib
    tomllib = None  # type: ignore[assignment]

from crv.core.constants import COMPRESSION as CORE_COMPRESSION
from crv.core.constants import ROW_GROUP_SIZE as CORE_ROW_GROUP_SIZE
from crv.core.constants import TICK_BUCKET_SIZE as CORE_TICK_BUCKET_SIZE

# TODO: This should be in core
Partitioning = Literal["tick_buckets"]
Compression = Literal["zstd", "lz4", "snappy"]


@dataclass(frozen=True)
class IoSettings:
    """
    Runtime settings for the crv.io layer.

    Attributes:
        root_dir (str): Root under which run data is stored (e.g., "out" or "runs").
        partitioning (Literal["tick_buckets"]): Partitioning strategy (currently only "tick_buckets").
        tick_bucket_size (int): Number of ticks per bucket (default from crv.core.constants).
        row_group_size (int): Parquet row group size used for writes (default from crv.core.constants).
        compression (Literal["zstd","lz4","snappy"]): Parquet compression codec used for writes
            (default from crv.core.constants).
        fs_protocol (str): Filesystem protocol (baseline "file"; future: "s3", "gcs", etc.).
        fs_options (dict[str, Any]): Options for the filesystem (future use; ignored for "file").
        strict_schema (bool): If True, enforce strict schema validation vs crv.core.tables descriptors.
        write_manifest_every_n (int): Frequency to persist manifest updates (>=1).

    Notes:
        - crv.core is the source of truth for table descriptors (columns/dtypes/required/nullable),
          canonical table names, and versioning (SCHEMA_V).
        - crv.io.write computes bucket = tick // tick_bucket_size and writes per-bucket parts
          with atomic tmp→ready rename.
        - Changing defaults should be done in crv.core.constants; this class simply consumes them.

    Examples:
        Configure a dataset rooted at "out" with 100-tick buckets:

        >>> from crv.io import IoSettings
        >>> IoSettings(root_dir="out", tick_bucket_size=100)  # doctest: +ELLIPSIS
        IoSettings(...)
    """

    root_dir: str = "out"
    partitioning: Partitioning = "tick_buckets"
    tick_bucket_size: int = CORE_TICK_BUCKET_SIZE
    row_group_size: int = CORE_ROW_GROUP_SIZE  # 128k
    compression: Compression = CORE_COMPRESSION
    fs_protocol: str = "file"
    fs_options: dict[str, Any] = field(default_factory=dict)
    strict_schema: bool = True
    write_manifest_every_n: int = 1

    # Configuration loaders (env/TOML) with precedence: env > TOML > defaults.

    @classmethod
    def _apply_mapping(cls, base: IoSettings, cfg: dict[str, Any] | None) -> IoSettings:
        """Apply a loose config mapping onto IoSettings, returning a new instance."""
        if not isinstance(cfg, dict):
            return base

        s = base

        def _bool(v: Any) -> bool:
            if isinstance(v, bool):
                return v
            if isinstance(v, (int, float)):
                return bool(v)
            if isinstance(v, str):
                return v.strip().lower() in {"1", "true", "t", "yes", "y", "on"}
            return False

        # root_dir
        if "root_dir" in cfg and isinstance(cfg["root_dir"], str):
            s = replace(s, root_dir=cfg["root_dir"])

        # partitioning (currently only "tick_buckets")
        if "partitioning" in cfg and isinstance(cfg["partitioning"], str):
            part = cfg["partitioning"]
            if part == "tick_buckets":
                s = replace(s, partitioning="tick_buckets")

        # tick_bucket_size
        if "tick_bucket_size" in cfg:
            try:
                s = replace(s, tick_bucket_size=int(cfg["tick_bucket_size"]))
            except Exception:
                pass

        # row_group_size
        if "row_group_size" in cfg:
            try:
                s = replace(s, row_group_size=int(cfg["row_group_size"]))
            except Exception:
                pass

        # compression
        if "compression" in cfg and isinstance(cfg["compression"], str):
            comp = cfg["compression"].strip().lower()
            if comp in ("zstd", "lz4", "snappy"):
                # type: ignore[arg-type]
                s = replace(s, compression=comp)  # type: ignore[arg-type]

        # fs_protocol / fs_options
        if "fs_protocol" in cfg and isinstance(cfg["fs_protocol"], str):
            s = replace(s, fs_protocol=cfg["fs_protocol"])
        if "fs_options" in cfg and isinstance(cfg["fs_options"], dict):
            s = replace(s, fs_options=dict(cfg["fs_options"]))

        # strict_schema
        if "strict_schema" in cfg:
            try:
                s = replace(s, strict_schema=_bool(cfg["strict_schema"]))
            except Exception:
                pass

        # write_manifest_every_n
        if "write_manifest_every_n" in cfg:
            try:
                s = replace(s, write_manifest_every_n=int(cfg["write_manifest_every_n"]))
            except Exception:
                pass

        return s

    @classmethod
    def from_env(cls, base: IoSettings | None = None, prefix: str = "CRV_IO_") -> IoSettings:
        """
        Build IoSettings from environment variables. Precedence is env > base (if provided) > defaults.

        Recognized variables:
            - CRV_IO_ROOT_DIR
            - CRV_IO_PARTITIONING (currently only "tick_buckets")
            - CRV_IO_TICK_BUCKET_SIZE
            - CRV_IO_ROW_GROUP_SIZE
            - CRV_IO_COMPRESSION ("zstd" | "lz4" | "snappy")
            - CRV_IO_FS_PROTOCOL
            - CRV_IO_FS_OPTIONS (JSON-like not supported; ignored - provide via TOML)
            - CRV_IO_STRICT_SCHEMA (1/0/true/false/yes/no/on/off)
            - CRV_IO_WRITE_MANIFEST_EVERY_N
        """
        s = base or cls()

        def get(name: str) -> str | None:
            return os.getenv(prefix + name)

        mapping: dict[str, Any] = {}
        v = get("ROOT_DIR")
        if v:
            mapping["root_dir"] = v
        v = get("PARTITIONING")
        if v:
            mapping["partitioning"] = v
        v = get("TICK_BUCKET_SIZE")
        if v:
            try:
                mapping["tick_bucket_size"] = int(v)
            except Exception:
                pass
        v = get("ROW_GROUP_SIZE")
        if v:
            try:
                mapping["row_group_size"] = int(v)
            except Exception:
                pass
        v = get("COMPRESSION")
        if v:
            mapping["compression"] = v
        v = get("FS_PROTOCOL")
        if v:
            mapping["fs_protocol"] = v
        # FS_OPTIONS via env is intentionally skipped to avoid parsing complexity
        v = get("STRICT_SCHEMA")
        if v:
            mapping["strict_schema"] = v
        v = get("WRITE_MANIFEST_EVERY_N")
        if v:
            try:
                mapping["write_manifest_every_n"] = int(v)
            except Exception:
                pass

        return cls._apply_mapping(s, mapping)

    @classmethod
    def from_toml(cls, path: str | os.PathLike[str] | None = None) -> IoSettings:
        """
        Build IoSettings from a TOML file.

        Search order when `path` is None:
            1) ./crv.toml (with either top-level [io] or direct keys)
            2) ./pyproject.toml under [tool.crv.io]

        Returns defaults if no file present or tomllib is unavailable.
        """
        s = cls()
        if tomllib is None:
            return s

        def _load_toml(p: Path) -> dict[str, Any] | None:
            try:
                with p.open("rb") as fh:
                    return tomllib.load(fh)  # type: ignore[arg-type]
            except Exception:
                return None

        cfg: dict[str, Any] | None = None

        cand: list[Path] = []
        if path is not None:
            cand.append(Path(path))
        else:
            cand.append(Path.cwd() / "crv.toml")
            cand.append(Path.cwd() / "pyproject.toml")

        for p in cand:
            if not p.exists():
                continue
            data = _load_toml(p)
            if not isinstance(data, dict):
                continue
            if p.name == "pyproject.toml":
                # Expect [tool.crv.io]
                cfg = (
                    data.get("tool", {}).get("crv", {}).get("io", {})  # type: ignore[assignment]
                    if isinstance(data.get("tool", {}), dict)
                    else None
                )
            else:
                # crv.toml - accept either [io] table or top-level keys
                top = data
                if "io" in top and isinstance(top["io"], dict):
                    cfg = top["io"]  # type: ignore[assignment]
                else:
                    cfg = top  # type: ignore[assignment]
            if cfg:
                break

        return cls._apply_mapping(s, cfg)

    @classmethod
    def load(cls, path: str | os.PathLike[str] | None = None) -> IoSettings:
        """
        Load IoSettings applying precedence: environment > TOML > defaults.

        Args:
            path: Optional explicit TOML path. If None, search defaults (crv.toml, pyproject.toml).

        Returns:
            IoSettings
        """
        s = cls.from_toml(path)
        s = cls.from_env(base=s)
        return s
