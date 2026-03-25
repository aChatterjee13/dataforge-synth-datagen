"""
Graph / Network Data Synthesis Service - Analyze and synthesize graph data.
"""

import os
import json
import csv
import random
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

import networkx as nx

from app.utils.logger import get_logger

logger = get_logger(__name__)


class GraphAnalyzer:
    """Load, analyze, and synthesize graph data."""

    @staticmethod
    def load_graph(file_path: str) -> nx.Graph:
        """Load a graph from various file formats."""
        ext = os.path.splitext(file_path)[1].lower()

        if ext == '.graphml':
            return GraphAnalyzer._load_graphml(file_path)
        elif ext == '.json':
            return GraphAnalyzer._load_json_graph(file_path)
        elif ext == '.csv':
            return GraphAnalyzer._load_csv_edgelist(file_path)
        elif ext in ('.gexf',):
            return nx.read_gexf(file_path)
        else:
            # Try CSV first, then JSON
            try:
                return GraphAnalyzer._load_csv_edgelist(file_path)
            except Exception:
                return GraphAnalyzer._load_json_graph(file_path)

    @staticmethod
    def _load_graphml(file_path: str) -> nx.Graph:
        """Load GraphML, fixing non-standard namespaces if needed."""
        try:
            return nx.read_graphml(file_path)
        except Exception:
            pass

        # NetworkX expects namespace http://graphml.graphdrawing.org/xmlns
        # Fix files that use non-standard namespaces
        import re
        with open(file_path, 'r') as f:
            content = f.read()

        # Replace any graphml namespace with the correct one
        fixed = re.sub(
            r'http://graphml\.graphstruct\.org/graphml',
            'http://graphml.graphdrawing.org/xmlns',
            content,
        )

        if fixed != content:
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.graphml', delete=False) as tmp:
                tmp.write(fixed)
                tmp_path = tmp.name
            try:
                return nx.read_graphml(tmp_path)
            finally:
                os.remove(tmp_path)

        raise ValueError(f"Could not parse GraphML file: {file_path}")

    @staticmethod
    def _load_csv_edgelist(file_path: str) -> nx.Graph:
        """Load graph from CSV edge list (source,target[,weight])."""
        G = nx.Graph()

        with open(file_path, 'r') as f:
            reader = csv.reader(f)
            header = next(reader, None)

            # Detect if first row is header
            if header and not all(h.replace('.', '').replace('-', '').isdigit() for h in header[:2]):
                # It's a header row, skip it
                pass
            else:
                # First row is data
                if header and len(header) >= 2:
                    weight = float(header[2]) if len(header) > 2 and header[2].replace('.', '').isdigit() else 1.0
                    G.add_edge(header[0], header[1], weight=weight)

            for row in reader:
                if len(row) >= 2:
                    weight = float(row[2]) if len(row) > 2 else 1.0
                    try:
                        G.add_edge(row[0].strip(), row[1].strip(), weight=weight)
                    except Exception:
                        continue

        return G

    @staticmethod
    def _load_json_graph(file_path: str) -> nx.Graph:
        """Load graph from JSON adjacency format."""
        with open(file_path, 'r') as f:
            data = json.load(f)

        # Support node-link format (networkx default)
        if 'nodes' in data and ('links' in data or 'edges' in data):
            # NetworkX 3.x: edges key defaults to 'edges', multigraph defaults to True
            edges_key = 'links' if 'links' in data else 'edges'
            try:
                return nx.node_link_graph(data, edges=edges_key, multigraph=False)
            except TypeError:
                # Older NetworkX without edges/multigraph parameters
                if 'links' in data and 'edges' not in data:
                    data['edges'] = data.pop('links')
                return nx.node_link_graph(data)

        # Support adjacency format { "node1": ["node2", "node3"], ... }
        G = nx.Graph()
        if isinstance(data, dict):
            for node, neighbors in data.items():
                G.add_node(node)
                if isinstance(neighbors, list):
                    for neighbor in neighbors:
                        if isinstance(neighbor, dict):
                            G.add_edge(node, neighbor.get('id', neighbor.get('target', '')))
                        else:
                            G.add_edge(node, str(neighbor))

        return G

    @staticmethod
    def analyze_graph(G: nx.Graph) -> Dict[str, Any]:
        """Compute graph statistics for comparison and synthesis."""
        from collections import Counter

        n = G.number_of_nodes()
        m = G.number_of_edges()

        if n == 0:
            return {
                'nodes': 0, 'edges': 0, 'density': 0, 'avg_degree': 0,
                'clustering_coefficient': 0, 'connected_components': 0,
                'is_directed': G.is_directed(),
            }

        degrees = [d for _, d in G.degree()]

        stats = {
            'nodes': n,
            'edges': m,
            'density': round(nx.density(G), 6),
            'avg_degree': round(sum(degrees) / n, 2),
            'max_degree': max(degrees) if degrees else 0,
            'min_degree': min(degrees) if degrees else 0,
            'clustering_coefficient': round(nx.average_clustering(G), 4),
            'is_directed': G.is_directed(),
        }

        if G.is_directed():
            stats['connected_components'] = nx.number_weakly_connected_components(G)
        else:
            stats['connected_components'] = nx.number_connected_components(G)

        # Degree distribution summary (for charts)
        degree_dist = Counter(degrees)
        stats['degree_distribution'] = dict(sorted(degree_dist.items())[:20])

        # Full degree sequence (for synthesis — not sent to frontend)
        stats['_degree_sequence'] = sorted(degrees, reverse=True)

        return stats

    @staticmethod
    def _detect_power_law(degrees: List[int]) -> float:
        """Estimate how well the degree distribution fits a power law.
        Returns a score 0-1 (1 = perfect power-law fit)."""
        from collections import Counter
        import math

        if len(degrees) < 5:
            return 0.0

        counts = Counter(degrees)
        if len(counts) < 3:
            return 0.0

        # Simple log-log linearity test
        points = [(math.log(k), math.log(v))
                   for k, v in counts.items() if k > 0 and v > 0]
        if len(points) < 3:
            return 0.0

        n = len(points)
        sx = sum(p[0] for p in points)
        sy = sum(p[1] for p in points)
        sxx = sum(p[0] ** 2 for p in points)
        sxy = sum(p[0] * p[1] for p in points)

        denom = n * sxx - sx * sx
        if abs(denom) < 1e-12:
            return 0.0

        # R-squared of log-log linear fit
        syy = sum(p[1] ** 2 for p in points)
        r_num = n * sxy - sx * sy
        r_den_sq = (n * sxx - sx * sx) * (n * syy - sy * sy)
        if r_den_sq <= 0:
            return 0.0

        r_squared = (r_num ** 2) / r_den_sq
        return max(0.0, min(1.0, r_squared))

    @staticmethod
    def _detect_communities(G: nx.Graph) -> List[set]:
        """Detect communities using greedy modularity optimization."""
        try:
            U = G.to_undirected() if G.is_directed() else G
            communities = list(nx.community.greedy_modularity_communities(U))
            return communities
        except Exception:
            return [set(G.nodes())]

    @staticmethod
    def select_model(stats: Dict[str, Any]) -> str:
        """Auto-select the best graph model based on original graph properties.

        For small graphs (< 200 nodes) we prefer the configuration model since
        it faithfully reproduces the exact degree sequence.  For larger graphs
        we pick a generative model whose assumptions match the topology.
        """
        density = stats.get('density', 0)
        clustering = stats.get('clustering_coefficient', 0)
        nodes = stats.get('nodes', 0)

        if nodes == 0:
            return 'erdos_renyi'

        degrees = stats.get('_degree_sequence', [])
        power_law_score = GraphAnalyzer._detect_power_law(degrees) if degrees else 0.0

        # Small graphs: configuration model is the most faithful since it
        # directly matches the degree sequence and we can tune clustering
        # afterwards.  Only switch away for very strong structural signals.
        if nodes < 200:
            # Still use BA for very clear scale-free networks
            if power_law_score > 0.85:
                return 'barabasi_albert'
            return 'configuration'

        # Compute small-world sigma: high clustering relative to random graph
        clustering_ratio = clustering / max(density, 1e-6)

        # Scale-free: strong power-law degree distribution
        if power_law_score > 0.7:
            return 'barabasi_albert'

        # Small-world: clustering much higher than random, density not too high
        if clustering_ratio > 3.0 and density < 0.3:
            return 'watts_strogatz'

        # Community structure: moderate-to-high clustering
        if clustering > 0.15 and density < 0.5:
            return 'stochastic_block'

        # Default: configuration model (most general)
        return 'configuration'

    @staticmethod
    def generate_synthetic_graph(
        stats: Dict[str, Any],
        model: str,
        target_nodes: int,
        target_edges: Optional[int] = None,
        original_graph: Optional[nx.Graph] = None,
    ) -> nx.Graph:
        """Generate a synthetic graph preserving structural properties.

        Strategy per model:
        - configuration: Match degree sequence exactly (most faithful)
        - barabasi_albert: Preferential attachment, calibrated m parameter
        - erdos_renyi: Random graph with matched density
        - watts_strogatz: Small-world with estimated beta from clustering ratio
        - stochastic_block: Community-aware with detected block structure

        Post-processing always:
        1. Adjust edge count to match target (scaled from original)
        2. Tune clustering coefficient via edge rewiring
        3. Ensure connectivity if original was connected
        """
        # Seed for reproducibility across random + networkx generators
        random.seed(42)

        n = target_nodes
        is_directed = stats.get('is_directed', False)
        orig_n = stats.get('nodes', n)
        orig_m = stats.get('edges', 0)
        scale = n / max(orig_n, 1)

        # Always compute target edges: scale proportionally to node ratio
        # For undirected: edges scale ~ n^2 ratio.  For small same-size: just
        # use the original count directly.
        if target_edges is None:
            if n == orig_n:
                target_edges = orig_m
            else:
                # Scale edges proportionally (density-preserving)
                target_edges = max(n - 1, round(orig_m * (scale ** 2)))

        if model == 'configuration':
            G = GraphAnalyzer._gen_configuration(stats, n, is_directed)

        elif model == 'barabasi_albert':
            G = GraphAnalyzer._gen_barabasi_albert(stats, n, is_directed)

        elif model == 'erdos_renyi':
            G = GraphAnalyzer._gen_erdos_renyi(stats, n, is_directed)

        elif model == 'watts_strogatz':
            G = GraphAnalyzer._gen_watts_strogatz(stats, n)

        elif model == 'stochastic_block':
            G = GraphAnalyzer._gen_stochastic_block(stats, n, original_graph)

        else:
            G = GraphAnalyzer._gen_configuration(stats, n, is_directed)

        # 1. Adjust edge count to match target
        GraphAnalyzer._adjust_edge_count(G, target_edges)

        # 2. Tune clustering coefficient to match original
        target_cc = stats.get('clustering_coefficient', 0)
        if n > 2:
            GraphAnalyzer._tune_clustering(G, target_cc, target_edges)

        # 3. Ensure connectivity LAST (after all rewiring is done)
        if stats.get('connected_components', 1) == 1 and n > 1:
            GraphAnalyzer._ensure_connected(G)

        return G

    @staticmethod
    def _scale_degree_sequence(orig_seq: List[int], target_n: int) -> List[int]:
        """Scale the degree sequence to a new node count, preserving distribution shape."""
        orig_n = len(orig_seq)
        if orig_n == 0 or target_n == 0:
            return [1] * target_n

        if target_n == orig_n:
            seq = list(orig_seq)
        else:
            # Resample from original distribution
            seq = [orig_seq[int(i * orig_n / target_n) % orig_n] for i in range(target_n)]

        # Ensure even sum for undirected configuration model
        if sum(seq) % 2 != 0:
            seq[random.randint(0, len(seq) - 1)] += 1

        # Ensure no degree >= n
        seq = [min(d, target_n - 1) for d in seq]
        # Ensure minimum degree 1 for connectivity
        seq = [max(d, 1) for d in seq]

        if sum(seq) % 2 != 0:
            seq[0] += 1

        return seq

    @staticmethod
    def _gen_configuration(stats: Dict, n: int, directed: bool) -> nx.Graph:
        """Degree-sequence preserving model.

        Uses Chung-Lu (expected_degree_graph) for dense graphs since the
        configuration model creates multi-edges that get lost when converting
        to a simple graph. For sparse graphs, uses the configuration model
        which produces a more exact degree match.
        """
        orig_seq = stats.get('_degree_sequence', [])
        seq = GraphAnalyzer._scale_degree_sequence(orig_seq, n) if orig_seq else [2] * n
        density = stats.get('density', 0)

        # Dense graphs (density > 0.3): Chung-Lu handles multi-edges better
        # Sparse graphs: configuration model gives tighter degree match
        use_chung_lu = density > 0.3

        if use_chung_lu:
            try:
                G = nx.expected_degree_graph(seq, seed=42, selfloops=False)
                if directed:
                    G = G.to_directed()
                return G
            except Exception as e:
                logger.warning(f"Chung-Lu failed ({e}), falling back to configuration model")

        try:
            if directed:
                in_seq = [max(1, d // 2) for d in seq]
                out_seq = [max(1, d - d // 2) for d in seq]
                while sum(in_seq) != sum(out_seq):
                    if sum(in_seq) > sum(out_seq):
                        out_seq[random.randint(0, n - 1)] += 1
                    else:
                        in_seq[random.randint(0, n - 1)] += 1
                G = nx.directed_configuration_model(in_seq, out_seq, seed=42)
                G = nx.DiGraph(G)
            else:
                G = nx.configuration_model(seq, seed=42)
                G = nx.Graph(G)
            G.remove_edges_from(nx.selfloop_edges(G))
            return G
        except Exception as e:
            logger.warning(f"Configuration model failed ({e}), falling back to ER")
            return GraphAnalyzer._gen_erdos_renyi(stats, n, directed)

    @staticmethod
    def _gen_barabasi_albert(stats: Dict, n: int, directed: bool) -> nx.Graph:
        """Barabasi-Albert with calibrated m from actual degree sequence."""
        avg_deg = stats.get('avg_degree', 4)
        # In BA model, expected avg_degree ≈ 2m for large n
        m = max(1, min(round(avg_deg / 2), n - 1))
        G = nx.barabasi_albert_graph(n, m, seed=42)
        if directed:
            G = G.to_directed()
        return G

    @staticmethod
    def _gen_erdos_renyi(stats: Dict, n: int, directed: bool) -> nx.Graph:
        """Erdos-Renyi random graph with matched density."""
        p = stats.get('density', 0.05)
        if p <= 0:
            p = 0.05
        G = nx.erdos_renyi_graph(n, p, seed=42, directed=directed)
        return G

    @staticmethod
    def _gen_watts_strogatz(stats: Dict, n: int) -> nx.Graph:
        """Watts-Strogatz with beta estimated from clustering vs density ratio."""
        k = max(2, round(stats.get('avg_degree', 4)))
        if k % 2 != 0:
            k += 1
        k = min(k, n - 1)

        # Estimate beta from clustering:
        # WS with beta=0 has clustering ≈ 3(k-2) / (4(k-1))
        # WS with beta=1 has clustering ≈ k / n (like random)
        clustering = stats.get('clustering_coefficient', 0)
        lattice_cc = 3 * (k - 2) / (4 * (k - 1)) if k > 1 else 0
        if lattice_cc > 0 and clustering > 0:
            # beta ~ 1 - (observed_cc / lattice_cc)
            beta = max(0.01, min(0.99, 1.0 - clustering / lattice_cc))
        else:
            beta = 0.3

        G = nx.watts_strogatz_graph(n, k, beta, seed=42)
        return G

    @staticmethod
    def _gen_stochastic_block(stats: Dict, n: int, original_graph: Optional[nx.Graph] = None) -> nx.Graph:
        """SBM with communities detected from original graph."""
        density = stats.get('density', 0.1)

        # Detect real communities if we have the original graph
        if original_graph is not None and original_graph.number_of_nodes() > 0:
            communities = GraphAnalyzer._detect_communities(original_graph)
            num_communities = len(communities)
            orig_sizes = [len(c) for c in communities]

            # Compute actual intra/inter edge probabilities
            orig_n = sum(orig_sizes)
            intra_edges = 0
            inter_edges = 0
            node_to_comm = {}
            for i, comm in enumerate(communities):
                for node in comm:
                    node_to_comm[node] = i

            U = original_graph.to_undirected() if original_graph.is_directed() else original_graph
            for u, v in U.edges():
                if u in node_to_comm and v in node_to_comm:
                    if node_to_comm[u] == node_to_comm[v]:
                        intra_edges += 1
                    else:
                        inter_edges += 1

            # Compute probabilities
            intra_possible = sum(s * (s - 1) // 2 for s in orig_sizes)
            inter_possible = orig_n * (orig_n - 1) // 2 - intra_possible

            intra_p = intra_edges / max(intra_possible, 1)
            inter_p = inter_edges / max(inter_possible, 1)
        else:
            num_communities = max(2, min(5, n // 10))
            intra_p = min(density * 3, 0.8)
            inter_p = max(density * 0.2, 0.001)
            orig_sizes = None

        # Scale community sizes to target n
        if orig_sizes:
            total_orig = sum(orig_sizes)
            sizes = [max(1, round(s * n / total_orig)) for s in orig_sizes]
            # Fix rounding
            diff = n - sum(sizes)
            if diff > 0:
                sizes[-1] += diff
            elif diff < 0:
                for i in range(abs(diff)):
                    idx = sizes.index(max(sizes))
                    sizes[idx] -= 1
        else:
            sizes = [n // num_communities] * num_communities
            sizes[-1] += n - sum(sizes)

        # Clamp probabilities
        intra_p = max(0.001, min(intra_p, 0.95))
        inter_p = max(0.0001, min(inter_p, intra_p * 0.5))

        p_matrix = [
            [intra_p if i == j else inter_p for j in range(num_communities)]
            for i in range(num_communities)
        ]

        directed = stats.get('is_directed', False)

        # For directed graphs, halve probabilities since to_directed doubles edges
        if directed:
            p_matrix = [[p / 2 for p in row] for row in p_matrix]

        try:
            G = nx.stochastic_block_model(sizes, p_matrix, seed=42)
            if directed:
                G = G.to_directed()
            return G
        except Exception as e:
            logger.warning(f"SBM failed ({e}), falling back to configuration model")
            return GraphAnalyzer._gen_configuration(stats, n, stats.get('is_directed', False))

    @staticmethod
    def _adjust_edge_count(G: nx.Graph, target_edges: int):
        """Add or remove edges to match target count, preserving structure.

        When removing: prefer edges between high-degree nodes (less structural
        impact on low-degree nodes).  When adding: prefer connecting nodes whose
        degree is below average (preserves degree distribution shape).
        """
        current = G.number_of_edges()
        if current == target_edges:
            return

        if current > target_edges:
            to_remove_count = current - target_edges
            # Remove edges between highest-degree node pairs first
            edges_by_max_degree = sorted(
                G.edges(),
                key=lambda e: min(G.degree(e[0]), G.degree(e[1])),
            )
            # Don't disconnect nodes completely if possible — skip edges
            # where removal would leave a node with degree 0
            removed = 0
            for e in edges_by_max_degree:
                if removed >= to_remove_count:
                    break
                if G.degree(e[0]) > 1 and G.degree(e[1]) > 1:
                    G.remove_edge(*e)
                    removed += 1
            # If still need to remove more, remove remaining regardless
            if removed < to_remove_count:
                remaining = list(G.edges())
                random.shuffle(remaining)
                for e in remaining:
                    if removed >= to_remove_count:
                        break
                    G.remove_edge(*e)
                    removed += 1

        elif current < target_edges:
            to_add = target_edges - current
            nodes = list(G.nodes())
            n = len(nodes)
            if n < 2:
                return

            # Prefer connecting low-degree nodes to preserve distribution
            added = 0
            attempts = 0
            max_attempts = to_add * 10
            while added < to_add and attempts < max_attempts:
                # Bias towards low-degree nodes
                if random.random() < 0.7:
                    # Pick two nodes with below-average degree
                    avg_deg = sum(dict(G.degree()).values()) / n
                    low_deg = [v for v in nodes if G.degree(v) <= avg_deg]
                    if len(low_deg) >= 2:
                        u, v = random.sample(low_deg, 2)
                    else:
                        u, v = random.sample(nodes, 2)
                else:
                    u, v = random.sample(nodes, 2)

                if u != v and not G.has_edge(u, v):
                    G.add_edge(u, v)
                    added += 1
                attempts += 1

    @staticmethod
    def _ensure_connected(G: nx.Graph):
        """Connect disconnected components by adding bridge edges."""
        if G.is_directed():
            components = list(nx.weakly_connected_components(G))
        else:
            components = list(nx.connected_components(G))

        if len(components) <= 1:
            return

        # Connect each component to the largest one
        comp_lists = [list(c) for c in components]
        main = comp_lists[0]
        for comp in comp_lists[1:]:
            u = random.choice(main)
            v = random.choice(comp)
            G.add_edge(u, v)
            if G.is_directed():
                G.add_edge(v, u)
            main.extend(comp)

    @staticmethod
    def _tune_clustering(G: nx.Graph, target_cc: float, target_edges: int,
                         max_iterations: int = 800):
        """Rewire edges to bring clustering coefficient closer to the target.

        Uses a Markov-chain approach: propose a random edge swap, accept
        it if it moves clustering closer to the target, reject otherwise.
        Edge count stays constant throughout.
        """
        current_cc = nx.average_clustering(G)
        if abs(current_cc - target_cc) < 0.015:
            return  # Already close enough

        nodes = list(G.nodes())
        n = len(nodes)
        if n < 4:
            return

        best_diff = abs(current_cc - target_cc)
        stale_count = 0

        for iteration in range(max_iterations):
            if best_diff < 0.015:
                break
            # Stop if no progress for a while
            if stale_count > 80:
                break

            if current_cc < target_cc:
                # --- Clustering too low: create triangles ---
                node = random.choice(nodes)
                nbrs = list(G.neighbors(node))
                if len(nbrs) < 2:
                    continue

                u, v = random.sample(nbrs, 2)
                if G.has_edge(u, v):
                    continue

                # Find a non-triangle edge to remove (swap)
                edge_to_remove = None
                candidates = list(G.edges())
                random.shuffle(candidates)
                for e in candidates:
                    a, b = e
                    if a in (u, v, node) or b in (u, v, node):
                        continue
                    if G.degree(a) > 1 and G.degree(b) > 1:
                        common = set(G.neighbors(a)) & set(G.neighbors(b))
                        if len(common) == 0:
                            edge_to_remove = e
                            break

                if edge_to_remove is None:
                    stale_count += 1
                    continue

                # Try the swap
                G.remove_edge(*edge_to_remove)
                G.add_edge(u, v)

            else:
                # --- Clustering too high: break triangles ---
                # Find an actual triangle edge to remove
                triangle_edge = None
                candidates = list(G.edges())
                random.shuffle(candidates)
                for e in candidates:
                    a, b = e
                    common = set(G.neighbors(a)) & set(G.neighbors(b))
                    if len(common) > 0 and G.degree(a) > 1 and G.degree(b) > 1:
                        triangle_edge = e
                        break

                if triangle_edge is None:
                    stale_count += 1
                    continue

                a, b = triangle_edge

                # Find two unconnected nodes (not already forming a triangle)
                found_new = False
                for _ in range(20):
                    u, v = random.sample(nodes, 2)
                    if u != v and not G.has_edge(u, v):
                        # Prefer edges that won't create new triangles
                        common = set(G.neighbors(u)) & set(G.neighbors(v))
                        if len(common) == 0:
                            found_new = True
                            break

                if not found_new:
                    stale_count += 1
                    continue

                # Try the swap
                G.remove_edge(a, b)
                G.add_edge(u, v)

            # Evaluate
            new_cc = nx.average_clustering(G)
            new_diff = abs(new_cc - target_cc)

            if new_diff < best_diff:
                # Accept
                best_diff = new_diff
                current_cc = new_cc
                stale_count = 0
            else:
                # Reject — undo the last swap
                if current_cc < target_cc:
                    G.remove_edge(u, v)
                    G.add_edge(*edge_to_remove)
                else:
                    G.remove_edge(u, v)
                    G.add_edge(a, b)
                stale_count += 1

        # Final edge count correction (rewiring keeps count, but just in case)
        GraphAnalyzer._adjust_edge_count(G, target_edges)

    @staticmethod
    def extract_attribute_distributions(G: nx.Graph) -> Dict[str, Any]:
        """Catalog all node/edge attribute keys and their value lists for sampling."""
        node_attrs: Dict[str, list] = {}
        for _, data in G.nodes(data=True):
            for key, val in data.items():
                node_attrs.setdefault(key, []).append(val)

        edge_attrs: Dict[str, list] = {}
        for _, _, data in G.edges(data=True):
            for key, val in data.items():
                edge_attrs.setdefault(key, []).append(val)

        return {'node_attrs': node_attrs, 'edge_attrs': edge_attrs}

    @staticmethod
    def _generate_node_id(existing_ids: set, index: int) -> str:
        """Detect naming pattern (e.g. 'paper-1') and generate sequential IDs."""
        if not existing_ids:
            return str(index)

        # Try to detect a prefix-number pattern
        import re
        pattern = re.compile(r'^(.*?)(\d+)$')
        prefixes: Dict[str, int] = {}
        max_num = 0
        for nid in existing_ids:
            m = pattern.match(str(nid))
            if m:
                prefix = m.group(1)
                num = int(m.group(2))
                prefixes[prefix] = prefixes.get(prefix, 0) + 1
                max_num = max(max_num, num)

        if prefixes:
            # Use the most common prefix
            best_prefix = max(prefixes, key=prefixes.get)
            return f"{best_prefix}{max_num + 1 + index}"

        # Fallback: purely numeric IDs
        numeric_ids = []
        for nid in existing_ids:
            try:
                numeric_ids.append(int(nid))
            except (ValueError, TypeError):
                pass

        if numeric_ids:
            return str(max(numeric_ids) + 1 + index)

        return f"new_node_{index}"

    @staticmethod
    def augment_graph(
        G_original: nx.Graph,
        stats: Dict[str, Any],
        additional_nodes: int,
        additional_edges: int,
    ) -> nx.Graph:
        """Add new nodes and edges to an existing graph while preserving structural patterns.

        Strategy:
        1. Copy the original graph (all nodes, edges, attributes preserved)
        2. Detect communities for community-aware attachment
        3. Extract node/edge attribute distributions for sampling
        4. Add new nodes via preferential attachment biased toward home community
        5. Add extra edges via triadic closure to preserve clustering
        6. Sample attributes from original distributions for all new elements
        7. Handle directed graphs by splitting in/out edges
        """
        # 1. Copy original graph
        G = G_original.copy()

        if additional_nodes == 0 and additional_edges == 0:
            return G

        # 2. Detect communities
        communities = GraphAnalyzer._detect_communities(G_original)
        node_to_comm: Dict[Any, int] = {}
        for i, comm in enumerate(communities):
            for node in comm:
                node_to_comm[node] = i
        comm_sizes = [len(c) for c in communities]
        total_comm = sum(comm_sizes)

        # Compute p_intra from original graph
        U = G_original.to_undirected() if G_original.is_directed() else G_original
        intra_edges = 0
        total_edges_counted = 0
        for u, v in U.edges():
            if u in node_to_comm and v in node_to_comm:
                total_edges_counted += 1
                if node_to_comm[u] == node_to_comm[v]:
                    intra_edges += 1
        p_intra = intra_edges / max(total_edges_counted, 1)

        # 3. Extract attribute distributions
        attr_dists = GraphAnalyzer.extract_attribute_distributions(G_original)
        node_attr_keys = attr_dists['node_attrs']
        edge_attr_keys = attr_dists['edge_attrs']

        # Degree distribution for sampling
        degrees = [d for _, d in G_original.degree()]
        is_directed = G_original.is_directed()

        # For directed graphs, compute in/out degree ratio
        if is_directed:
            in_degrees = [d for _, d in G_original.in_degree()]
            out_degrees = [d for _, d in G_original.out_degree()]
            total_in = sum(in_degrees) or 1
            total_out = sum(out_degrees) or 1
            in_ratio = total_in / (total_in + total_out)
        else:
            in_ratio = 0.5

        existing_ids = set(G.nodes())
        existing_nodes = list(G.nodes())
        new_node_ids = []

        # 4. Add new nodes with preferential attachment
        for i in range(additional_nodes):
            new_id = GraphAnalyzer._generate_node_id(existing_ids, i)
            while new_id in existing_ids:
                new_id = f"{new_id}_"
            existing_ids.add(new_id)

            # Sample attributes from original distributions
            node_data = {}
            for attr_key, values in node_attr_keys.items():
                node_data[attr_key] = random.choice(values)
            G.add_node(new_id, **node_data)

            # Sample degree from original distribution
            target_degree = random.choice(degrees) if degrees else 1
            target_degree = max(1, min(target_degree, len(existing_nodes)))

            # Assign to a community proportionally
            home_comm = random.choices(
                range(len(communities)),
                weights=comm_sizes,
                k=1,
            )[0]
            home_nodes = [n for n in communities[home_comm] if n in G.nodes() and n != new_id]
            other_nodes = [n for n in existing_nodes if n != new_id and node_to_comm.get(n, -1) != home_comm]

            # Preferential attachment: bias toward home community
            connected = 0
            attempts = 0
            max_attempts = target_degree * 10
            while connected < target_degree and attempts < max_attempts:
                # Decide intra vs inter community
                if home_nodes and (random.random() < p_intra or not other_nodes):
                    # Pick from home community with preferential attachment (degree-biased)
                    candidates = home_nodes
                else:
                    candidates = other_nodes if other_nodes else existing_nodes

                if not candidates:
                    break

                # Preferential attachment: weight by degree
                weights = [G.degree(n) + 1 for n in candidates]
                target_node = random.choices(candidates, weights=weights, k=1)[0]

                if not G.has_edge(new_id, target_node) and target_node != new_id:
                    edge_data = {}
                    for attr_key, values in edge_attr_keys.items():
                        edge_data[attr_key] = random.choice(values)

                    if is_directed:
                        # Split in/out edges based on original ratio
                        if random.random() < in_ratio:
                            G.add_edge(target_node, new_id, **edge_data)
                        else:
                            G.add_edge(new_id, target_node, **edge_data)
                    else:
                        G.add_edge(new_id, target_node, **edge_data)
                    connected += 1
                attempts += 1

            new_node_ids.append(new_id)
            existing_nodes.append(new_id)
            # Add new node to its home community for future lookups
            node_to_comm[new_id] = home_comm

        # 5. Add extra edges between existing nodes using triadic closure
        added_edges = 0
        attempts = 0
        max_attempts = additional_edges * 20
        all_nodes = list(G.nodes())

        while added_edges < additional_edges and attempts < max_attempts:
            # Triadic closure: prefer pairs sharing common neighbors
            if random.random() < 0.7 and len(all_nodes) > 2:
                # Pick a random node, then two of its neighbors
                pivot = random.choice(all_nodes)
                nbrs = list(G.neighbors(pivot)) if not is_directed else (
                    list(G.successors(pivot)) + list(G.predecessors(pivot))
                )
                if len(nbrs) >= 2:
                    u, v = random.sample(nbrs, 2)
                    if u != v and not G.has_edge(u, v):
                        edge_data = {}
                        for attr_key, values in edge_attr_keys.items():
                            edge_data[attr_key] = random.choice(values)
                        G.add_edge(u, v, **edge_data)
                        added_edges += 1
                        attempts += 1
                        continue

            # Fallback: random edge with preferential attachment
            if len(all_nodes) >= 2:
                u, v = random.sample(all_nodes, 2)
                if u != v and not G.has_edge(u, v):
                    edge_data = {}
                    for attr_key, values in edge_attr_keys.items():
                        edge_data[attr_key] = random.choice(values)
                    G.add_edge(u, v, **edge_data)
                    added_edges += 1
            attempts += 1

        return G

    @staticmethod
    def save_graph(G: nx.Graph, path: str, fmt: str):
        """Save graph to file in the specified format."""
        if fmt == 'graphml':
            nx.write_graphml(G, path)
        elif fmt == 'gexf':
            nx.write_gexf(G, path)
        elif fmt == 'json':
            data = nx.node_link_data(G)
            with open(path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        else:  # csv
            with open(path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['source', 'target', 'weight'])
                for u, v, d in G.edges(data=True):
                    writer.writerow([u, v, d.get('weight', 1.0)])


    @staticmethod
    def extract_visualization_data(G: nx.Graph, max_nodes: int = 150) -> Dict[str, Any]:
        """Extract node positions and edges for frontend visualization.

        Uses spring layout to compute coordinates. Subsamples large graphs
        by taking the largest connected component (or a subgraph) to keep
        the browser responsive.
        """
        if G.number_of_nodes() == 0:
            return {'nodes': [], 'links': []}

        # Subsample large graphs
        H = G
        if G.number_of_nodes() > max_nodes:
            # Pick the largest connected component first
            if G.is_directed():
                components = sorted(nx.weakly_connected_components(G), key=len, reverse=True)
            else:
                components = sorted(nx.connected_components(G), key=len, reverse=True)

            largest = G.subgraph(components[0]).copy()
            if largest.number_of_nodes() > max_nodes:
                # Take a random subset of nodes from the largest component
                sampled_nodes = list(largest.nodes())[:max_nodes]
                H = largest.subgraph(sampled_nodes).copy()
            else:
                H = largest

        # Compute spring layout (force-directed positions)
        pos = nx.spring_layout(H, seed=42, k=1.5 / (H.number_of_nodes() ** 0.5) if H.number_of_nodes() > 1 else 1)

        # Compute degree for node sizing
        degrees = dict(H.degree())

        nodes = []
        for node_id in H.nodes():
            x, y = pos[node_id]
            nodes.append({
                'id': str(node_id),
                'x': round(float(x), 4),
                'y': round(float(y), 4),
                'degree': degrees.get(node_id, 0),
            })

        links = []
        for u, v in H.edges():
            links.append({'source': str(u), 'target': str(v)})

        return {
            'nodes': nodes,
            'links': links,
            'subsampled': G.number_of_nodes() > max_nodes,
            'total_nodes': G.number_of_nodes(),
            'total_edges': G.number_of_edges(),
        }


def generate_graph_background(job_id: str, original_path: str, config: dict):
    """Background task for graph synthesis."""
    from app.db.database import SessionLocal, Job, JobStatusEnum

    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return

        job.progress = 5
        job.message = "Loading graph..."
        db.commit()

        G_original = GraphAnalyzer.load_graph(original_path)

        job.progress = 15
        job.message = "Analyzing graph properties..."
        db.commit()

        original_stats = GraphAnalyzer.analyze_graph(G_original)

        graph_mode = config.get('graph_mode', 'generate')

        if graph_mode == 'augment':
            # ── Augment existing graph ──
            additional_nodes = config.get('graph_additional_nodes', 0)
            additional_edges = config.get('graph_additional_edges', 0)

            job.progress = 30
            job.message = f"Augmenting graph (+{additional_nodes} nodes, +{additional_edges} edges)..."
            db.commit()

            G_augmented = GraphAnalyzer.augment_graph(
                G_original, original_stats, additional_nodes, additional_edges,
            )

            job.progress = 70
            job.message = "Analyzing augmented graph..."
            db.commit()

            augmented_stats = GraphAnalyzer.analyze_graph(G_augmented)

            job.progress = 80
            job.message = "Saving output..."
            db.commit()

            output_dir = os.path.join("outputs", job_id)
            os.makedirs(output_dir, exist_ok=True)

            fmt = config.get('graph_output_format', 'csv')
            ext_map = {'csv': '.csv', 'json': '.json', 'graphml': '.graphml', 'gexf': '.gexf'}
            ext = ext_map.get(fmt, '.csv')
            output_path = os.path.join(output_dir, f"augmented_graph{ext}")

            GraphAnalyzer.save_graph(G_augmented, output_path, fmt)

            # Compute structural preservation score (density, clustering, avg_degree only)
            comparison = {}
            structural_keys = ['density', 'avg_degree', 'clustering_coefficient']
            for key in ['nodes', 'edges'] + structural_keys:
                orig = original_stats.get(key, 0)
                aug = augmented_stats.get(key, 0)
                if isinstance(orig, (int, float)) and isinstance(aug, (int, float)):
                    if orig > 0:
                        comparison[key] = {
                            'original': orig,
                            'synthetic': aug,
                            'ratio': round(aug / orig, 3) if orig != 0 else 0,
                            'match_score': round(1 - abs(aug - orig) / max(orig, aug, 1), 3),
                        }
                    else:
                        comparison[key] = {'original': orig, 'synthetic': aug, 'ratio': 0, 'match_score': 1.0}

            # Overall score uses only structural metrics (not nodes/edges which are intentionally different)
            structural_scores = [
                comparison[k].get('match_score', 0)
                for k in structural_keys if k in comparison
            ]
            overall_match = sum(structural_scores) / max(len(structural_scores), 1)

            nodes_added = augmented_stats.get('nodes', 0) - original_stats.get('nodes', 0)
            edges_added = augmented_stats.get('edges', 0) - original_stats.get('edges', 0)

            # Extract graph data for visualization
            job.progress = 85
            job.message = "Computing graph layouts for visualization..."
            db.commit()

            original_viz = GraphAnalyzer.extract_visualization_data(G_original)
            augmented_viz = GraphAnalyzer.extract_visualization_data(G_augmented)

            results = {
                'summary': {
                    'mode': 'augment',
                    'model_used': 'augment',
                    'original_nodes': original_stats.get('nodes', 0),
                    'original_edges': original_stats.get('edges', 0),
                    'synthetic_nodes': augmented_stats.get('nodes', 0),
                    'synthetic_edges': augmented_stats.get('edges', 0),
                    'nodes_added': nodes_added,
                    'edges_added': edges_added,
                    'overall_match_score': round(overall_match, 3),
                    'output_format': fmt,
                },
                'original_stats': {k: v for k, v in original_stats.items() if not k.startswith('_')},
                'synthetic_stats': {k: v for k, v in augmented_stats.items() if not k.startswith('_')},
                'comparison': comparison,
                'graph_data': {
                    'original': original_viz,
                    'synthetic': augmented_viz,
                },
            }

            results_path = os.path.join(output_dir, "results.json")
            with open(results_path, 'w') as f:
                json.dump(results, f, indent=2, default=str)

            job.progress = 100
            job.status = JobStatusEnum.COMPLETED
            job.message = f"Augmented graph: +{nodes_added} nodes, +{edges_added} edges (total: {augmented_stats['nodes']} nodes, {augmented_stats['edges']} edges)"
            job.rows_generated = augmented_stats['nodes']
            job.completed_at = datetime.utcnow()
            db.commit()

        else:
            # ── Generate new synthetic graph ──
            job.progress = 30
            job.message = "Selecting synthesis model..."
            db.commit()

            model = config.get('graph_model', 'auto')
            if model == 'auto':
                model = GraphAnalyzer.select_model(original_stats)

            target_nodes = config.get('graph_target_nodes', original_stats.get('nodes', 100))
            # Default target_edges: scale proportionally from original
            user_target_edges = config.get('graph_target_edges')
            if user_target_edges is not None:
                target_edges = user_target_edges
            else:
                orig_n = original_stats.get('nodes', 1)
                orig_m = original_stats.get('edges', 0)
                scale = target_nodes / max(orig_n, 1)
                target_edges = orig_m if target_nodes == orig_n else max(
                    target_nodes - 1, round(orig_m * (scale ** 2))
                )

            job.progress = 40
            job.message = f"Generating synthetic graph ({model})..."
            db.commit()

            G_synthetic = GraphAnalyzer.generate_synthetic_graph(
                original_stats, model, target_nodes, target_edges,
                original_graph=G_original,
            )

            job.progress = 70
            job.message = "Analyzing synthetic graph..."
            db.commit()

            synthetic_stats = GraphAnalyzer.analyze_graph(G_synthetic)

            job.progress = 80
            job.message = "Saving output..."
            db.commit()

            output_dir = os.path.join("outputs", job_id)
            os.makedirs(output_dir, exist_ok=True)

            fmt = config.get('graph_output_format', 'csv')
            ext_map = {'csv': '.csv', 'json': '.json', 'graphml': '.graphml', 'gexf': '.gexf'}
            ext = ext_map.get(fmt, '.csv')
            output_path = os.path.join(output_dir, f"synthetic_graph{ext}")

            GraphAnalyzer.save_graph(G_synthetic, output_path, fmt)

            # Compute comparison
            comparison = {}
            for key in ['nodes', 'edges', 'density', 'avg_degree', 'clustering_coefficient']:
                orig = original_stats.get(key, 0)
                synth = synthetic_stats.get(key, 0)
                if isinstance(orig, (int, float)) and isinstance(synth, (int, float)):
                    if orig > 0:
                        comparison[key] = {
                            'original': orig,
                            'synthetic': synth,
                            'ratio': round(synth / orig, 3) if orig != 0 else 0,
                            'match_score': round(1 - abs(synth - orig) / max(orig, synth, 1), 3),
                        }
                    else:
                        comparison[key] = {'original': orig, 'synthetic': synth, 'ratio': 0, 'match_score': 1.0}

            overall_match = sum(v.get('match_score', 0) for v in comparison.values()) / max(len(comparison), 1)

            # Extract graph data for visualization (subsampled for large graphs)
            job.progress = 85
            job.message = "Computing graph layouts for visualization..."
            db.commit()

            original_viz = GraphAnalyzer.extract_visualization_data(G_original)
            synthetic_viz = GraphAnalyzer.extract_visualization_data(G_synthetic)

            results = {
                'summary': {
                    'mode': 'generate',
                    'model_used': model,
                    'original_nodes': original_stats.get('nodes', 0),
                    'original_edges': original_stats.get('edges', 0),
                    'synthetic_nodes': synthetic_stats.get('nodes', 0),
                    'synthetic_edges': synthetic_stats.get('edges', 0),
                    'overall_match_score': round(overall_match, 3),
                    'output_format': fmt,
                },
                'original_stats': {k: v for k, v in original_stats.items() if not k.startswith('_')},
                'synthetic_stats': {k: v for k, v in synthetic_stats.items() if not k.startswith('_')},
                'comparison': comparison,
                'graph_data': {
                    'original': original_viz,
                    'synthetic': synthetic_viz,
                },
            }

            results_path = os.path.join(output_dir, "results.json")
            with open(results_path, 'w') as f:
                json.dump(results, f, indent=2, default=str)

            job.progress = 100
            job.status = JobStatusEnum.COMPLETED
            job.message = f"Generated synthetic graph: {synthetic_stats['nodes']} nodes, {synthetic_stats['edges']} edges ({model})"
            job.rows_generated = synthetic_stats['nodes']
            job.completed_at = datetime.utcnow()
            db.commit()

    except Exception as e:
        logger.error(f"Graph synthesis failed: {e}")
        if job:
            job.status = JobStatusEnum.FAILED
            job.error = str(e)[:500]
            job.message = f"Failed: {str(e)[:200]}"
            db.commit()
    finally:
        db.close()
