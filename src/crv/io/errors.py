"""
Custom exceptions for the crv.io module.

Purpose
- Provide IO-layer specific error types that map cleanly to responsibilities in crv.io.
- Keep crv.core as the source of truth for grammar/schema/versioning errors (see crv.core.errors).

Source of truth and boundaries
- crv.core.errors.GrammarError and crv.core.errors.SchemaError are raised by core validators/models.
- crv.io raises Io* errors for filesystem/writer/manifest concerns:
  - IoConfigError: invalid or unsupported configuration.
  - IoSchemaError: DataFrame failed validation against crv.core.tables descriptors.
  - IoWriteError: atomic write path failed (tmp write/fsync/rename).
  - IoManifestError: manifest load/write/rebuild errors.

Notes
- These exceptions do not perform any IO and are stdlib-only.
"""

from __future__ import annotations


class IoError(Exception):
    """
    Base class for IO-related errors in crv.io.

    Notes:
        Use this as a catch-all for IO-layer failures, distinct from crv.core errors.
    """


class IoConfigError(IoError):
    """
    Raised when IO configuration is invalid or unsupported.

    Examples:
        - Unsupported filesystem protocol
        - Invalid tick bucket size (< 1)
    """


class IoSchemaError(IoError):
    """
    Raised when a DataFrame fails schema validation against crv.core.tables descriptors.

    Notes:
        Validation aligns with descriptor dtypes and required/nullable columns.
        Scalar columns (i64, f64, str) may be safely cast prior to raising.
    """


class IoWriteError(IoError):
    """
    Raised when an append/write operation fails to complete atomically.

    Notes:
        The write path is tmp parquet → fsync → os.replace(tmp, final). Failures at any step
        should surface as IoWriteError (with best-effort cleanup of tmp files).
    """


class IoManifestError(IoError):
    """
    Raised when a table manifest is missing, corrupt, or inconsistent.

    Notes:
        Includes failures to load, write (atomic rename), or rebuild manifests.
    """
