"""
LangGraph State Definition
===========================
Typed state that flows through every node in the intelligence pipeline graph.
LangGraph merges state using the Annotated reducers — list fields append,
scalar fields overwrite.
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional, Annotated
from typing_extensions import TypedDict
import operator


def _merge_dicts(a: dict, b: dict) -> dict:
    """Merge two dicts, b wins on key conflicts."""
    return {**a, **b}


class PipelineState(TypedDict, total=False):
    # Input
    session_id:     str
    company:        str

    # Evidence collection
    raw_chunks:     Annotated[List[dict], operator.add]   # appends across parallel nodes
    chunks_stored:  int

    # Agent outputs (each agent writes its own key)
    research:       dict
    discovery:      dict
    risk:           dict
    competitor_analysis: dict
    verification:   dict
    report:         dict

    # Pipeline control
    status:         str
    errors:         Annotated[List[str], operator.add]
    completed_nodes: Annotated[List[str], operator.add]

    # Discovered competitor names (passed research→analysis)
    competitor_names: List[str]
