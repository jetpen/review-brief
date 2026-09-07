from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Node:
    id: str
    label: str
    shape: str = "box"
    role: str | None = None
    container_id: str | None = None


@dataclass(frozen=True)
class Edge:
    id: str
    source: str
    target: str
    label: str | None = None
    role: str = "relates_to"
    directed: bool = True
    style: str = "solid"
    sequence_index: int | None = None
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Container:
    id: str
    label: str
    role: str = "boundary"
    parent_id: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class DiagramIR:
    family: str
    direction: str
    nodes: tuple[Node, ...]
    edges: tuple[Edge, ...]
    containers: tuple[Container, ...] = field(default_factory=tuple)
    schema_version: str = "1"

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "family": self.family,
            "direction": self.direction,
            "containers": [
                {"id": c.id, "label": c.label, "role": c.role, "parent_id": c.parent_id, "metadata": c.metadata}
                for c in self.containers
            ],
            "nodes": [
                {
                    "id": n.id,
                    "label": n.label,
                    "shape": n.shape,
                    **({"role": n.role} if n.role else {}),
                    **({"container_id": n.container_id} if n.container_id else {}),
                }
                for n in self.nodes
            ],
            "edges": [
                {
                    "id": e.id,
                    "source": e.source,
                    "target": e.target,
                    **({"label": e.label} if e.label is not None else {}),
                    "role": e.role,
                    "directed": e.directed,
                    "style": e.style,
                    **({"sequence_index": e.sequence_index} if e.sequence_index is not None else {}),
                    **({"metadata": e.metadata} if e.metadata else {}),
                }
                for e in self.edges
            ],
        }


@dataclass(frozen=True)
class ArtifactBundle:
    path: Path
    artifacts: tuple[Path, ...] = field(default_factory=tuple)
