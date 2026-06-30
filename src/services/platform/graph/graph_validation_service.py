from typing import Iterator

from api.errors import ConflictError
from database.models.main.agent_node_edge import AgentNodeEdge
from services.platform.graph.platform_cache_manager import PlatformCacheManager
from setup.translator import trans


# DFS coloring states for cycle detection.
_WHITE = 0  # unvisited
_GRAY = 1   # on current DFS stack
_BLACK = 2  # fully explored


class GraphValidationService:
    @staticmethod
    def validate_no_cycle_from(parent_id: int, child_id: int) -> None:
        """Reject self-loops and any edge whose addition would close a cycle.

        Uses iterative DFS from `child_id` to detect whether `parent_id`
        is reachable; if so, adding the edge `parent_id -> child_id` would
        create a cycle.
        """
        if parent_id == child_id:
            raise ConflictError(trans("errors.platform.graph.self_reference"))

        visited: set[int] = set()
        stack: list[int] = [child_id]
        while stack:
            node_id = stack.pop()
            if node_id in visited:
                continue
            visited.add(node_id)
            if node_id == parent_id:
                raise ConflictError(trans("errors.platform.graph.edge_would_create_cycle"))
            for edge in PlatformCacheManager.get_children_edges(node_id):
                if edge.child_node_id not in visited:
                    stack.append(edge.child_node_id)

    @staticmethod
    def validate_existing_graph() -> None:
        """Iterative three-color DFS over every node in the current snapshot.

        Replaces the previous recursive implementation so that arbitrarily
        deep graphs (or accidental cycles) cannot blow the Python recursion
        limit on the hot `PlatformRunService.run/stream` path.
        """
        color: dict[int, int] = {}
        for start in list(PlatformCacheManager.nodes_by_id):
            if color.get(start, _WHITE) != _WHITE:
                continue
            color[start] = _GRAY
            stack: list[tuple[int, Iterator[AgentNodeEdge]]] = [
                (start, iter(PlatformCacheManager.get_children_edges(start)))
            ]
            while stack:
                nid, it = stack[-1]
                next_edge = next(it, None)
                if next_edge is None:
                    color[nid] = _BLACK
                    stack.pop()
                    continue
                child = next_edge.child_node_id
                c = color.get(child, _WHITE)
                if c == _GRAY:
                    raise ConflictError(trans("errors.platform.graph.cycle_detected_at_node", node_id=child))
                if c == _BLACK:
                    continue
                color[child] = _GRAY
                stack.append(
                    (child, iter(PlatformCacheManager.get_children_edges(child)))
                )
