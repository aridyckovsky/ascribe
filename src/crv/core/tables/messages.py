"""
Canonical descriptor for the 'messages' table.

Purpose:
- Communication events emitted by agents (e.g., chat/announcements) with channel/visibility metadata.

Schema:
- columns:
    bucket i64, tick i64, sender_agent_id str, channel_name str, visibility_scope str,
    audience struct, speech_act str, topic_label str, stance_label str, claims struct, style struct
- required:
    ["bucket","tick","sender_agent_id","channel_name","visibility_scope","audience",
     "speech_act","topic_label","claims","style"]
- nullable:
    ["stance_label"]
- partitioning: ["bucket"]
- version: pinned to crv.core.versioning.SCHEMA_V

Notes:
- Core is zero-IO; IO layers (crv.io) materialize and validate row schemas.
- See src/crv/core/README.md (Table Catalog) for details and downstream usage.
"""

from __future__ import annotations

from ..grammar import TableDescriptor, TableName
from ..versioning import SCHEMA_V

MESSAGES_DESC = TableDescriptor(
    name=TableName.MESSAGES,
    columns={
        "bucket": "i64",
        "tick": "i64",
        "sender_agent_id": "str",
        "channel_name": "str",
        "visibility_scope": "str",
        "audience": "struct",
        "speech_act": "str",
        "topic_label": "str",
        "stance_label": "str",
        "claims": "struct",
        "style": "struct",
    },
    partitioning=["bucket"],
    required=[
        "bucket",
        "tick",
        "sender_agent_id",
        "channel_name",
        "visibility_scope",
        "audience",
        "speech_act",
        "topic_label",
        "claims",
        "style",
    ],
    nullable=[
        "stance_label",
    ],
    version=SCHEMA_V,
)
