"""
Octree Spatial Index for efficient point cloud tiling.
Partitions 3D point clouds into an octree structure to support
Level-of-Detail (LOD) 3D Tiles generation.
"""

from __future__ import annotations
import numpy as np
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class OctreeNode:
    """A single node in the octree."""

    def __init__(
        self,
        min_x: float, max_x: float,
        min_y: float, max_y: float,
        min_z: float, max_z: float,
        depth: int = 0,
    ):
        self.min_x = min_x; self.max_x = max_x
        self.min_y = min_y; self.max_y = max_y
        self.min_z = min_z; self.max_z = max_z
        self.depth = depth
        self.indices: Optional[np.ndarray] = None
        self.children: list = []
        self.is_leaf = True
        self.node_id: str = ""

    @property
    def center_x(self) -> float:
        return (self.min_x + self.max_x) / 2.0

    @property
    def center_y(self) -> float:
        return (self.min_y + self.max_y) / 2.0

    @property
    def center_z(self) -> float:
        return (self.min_z + self.max_z) / 2.0

    @property
    def diagonal(self) -> float:
        dx = self.max_x - self.min_x
        dy = self.max_y - self.min_y
        dz = self.max_z - self.min_z
        return float(np.sqrt(dx * dx + dy * dy + dz * dz))


class OctreeIndex:
    """
    Octree spatial index for a point cloud.

    Args:
        max_depth:        Maximum tree depth (deeper = more tiles).
        max_points_leaf:  Split a node when it exceeds this many points.
    """

    def __init__(self, max_depth: int = 5, max_points_leaf: int = 10000):
        self.max_depth = max_depth
        self.max_points_leaf = max_points_leaf
        self.root: Optional[OctreeNode] = None
        self._x: Optional[np.ndarray] = None
        self._y: Optional[np.ndarray] = None
        self._z: Optional[np.ndarray] = None

    def build(self, x: np.ndarray, y: np.ndarray, z: np.ndarray) -> OctreeNode:
        """Build the octree from XYZ numpy arrays."""
        self._x = x
        self._y = y
        self._z = z

        min_x, max_x = float(x.min()), float(x.max())
        min_y, max_y = float(y.min()), float(y.max())
        min_z, max_z = float(z.min()), float(z.max())

        pad_x = max((max_x - min_x) * 0.001, 0.01)
        pad_y = max((max_y - min_y) * 0.001, 0.01)
        pad_z = max((max_z - min_z) * 0.001, 0.01)

        root = OctreeNode(
            min_x - pad_x, max_x + pad_x,
            min_y - pad_y, max_y + pad_y,
            min_z - pad_z, max_z + pad_z,
            depth=0,
        )
        root.indices = np.arange(len(x), dtype=np.int64)
        root.node_id = "r"
        self.root = root
        self._split(root)
        leaf_count = len(self.leaf_nodes())
        logger.info(f"Octree built: {len(x):,} points, {leaf_count} leaves, depth<={self.max_depth}")
        return root

    def _split(self, node: OctreeNode) -> None:
        if node.indices is None or len(node.indices) <= self.max_points_leaf:
            return
        if node.depth >= self.max_depth:
            return

        cx, cy, cz = node.center_x, node.center_y, node.center_z
        x = self._x[node.indices]
        y = self._y[node.indices]
        z = self._z[node.indices]

        node.is_leaf = False
        node.children = []
        child_idx = 0

        for xi in range(2):
            for yi in range(2):
                for zi in range(2):
                    c_min_x = node.min_x if xi == 0 else cx
                    c_max_x = cx if xi == 0 else node.max_x
                    c_min_y = node.min_y if yi == 0 else cy
                    c_max_y = cy if yi == 0 else node.max_y
                    c_min_z = node.min_z if zi == 0 else cz
                    c_max_z = cz if zi == 0 else node.max_z

                    mask = (
                        (x >= c_min_x) & (x < c_max_x) &
                        (y >= c_min_y) & (y < c_max_y) &
                        (z >= c_min_z) & (z < c_max_z)
                    )
                    child_global_indices = node.indices[mask]

                    if len(child_global_indices) == 0:
                        node.children.append(None)
                        child_idx += 1
                        continue

                    child = OctreeNode(c_min_x, c_max_x, c_min_y, c_max_y, c_min_z, c_max_z, depth=node.depth + 1)
                    child.indices = child_global_indices
                    child.node_id = f"{node.node_id}_{child_idx}"
                    self._split(child)
                    node.children.append(child)
                    child_idx += 1

    def all_nodes(self) -> list:
        result = []
        if not self.root:
            return result
        queue = [self.root]
        while queue:
            node = queue.pop(0)
            result.append(node)
            for child in node.children:
                if child is not None:
                    queue.append(child)
        return result

    def leaf_nodes(self) -> list:
        return [n for n in self.all_nodes() if n.is_leaf]
