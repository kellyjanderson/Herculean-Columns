from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar


@dataclass(frozen=True, order=True)
class ConcernId:
    value: int


@dataclass(frozen=True, order=True)
class NodeId:
    value: int


@dataclass(frozen=True, order=True)
class EdgeId:
    value: int


Identity = ConcernId | NodeId | EdgeId
I = TypeVar("I", ConcernId, NodeId, EdgeId)


class MonotonicIdAllocator(Generic[I]):
    """Allocate identities independently of collection size or pruning."""

    def __init__(self, identity_type: type[I], start: int = 0) -> None:
        if start < 0:
            raise ValueError("identity allocator start must be non-negative")
        self._identity_type: type[I] = identity_type
        self._next = start

    def allocate(self) -> I:
        identity = self._identity_type(self._next)
        self._next += 1
        return identity

    @property
    def next_value(self) -> int:
        return self._next
