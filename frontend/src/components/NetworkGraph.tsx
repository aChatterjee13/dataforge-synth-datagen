import { useMemo, useState, useRef, useCallback, useEffect } from 'react';
import type { GraphVisualizationData } from '../types';

interface Props {
  data: GraphVisualizationData;
  width?: number;
  height?: number;
  nodeColor?: string;
  edgeColor?: string;
  label?: string;
}

interface Transform {
  x: number;
  y: number;
  scale: number;
}

const MIN_ZOOM = 0.2;
const MAX_ZOOM = 10;

export default function NetworkGraph({
  data,
  width = 500,
  height = 500,
  nodeColor = '#f59e0b',
  edgeColor = '#d1d5db',
  label,
}: Props) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [transform, setTransform] = useState<Transform>({ x: 0, y: 0, scale: 1 });
  const [isPanning, setIsPanning] = useState(false);
  const panStart = useRef<{ x: number; y: number; tx: number; ty: number }>({ x: 0, y: 0, tx: 0, ty: 0 });
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);

  const { scaledNodes, scaledLinks, maxDegree, nodeMap } = useMemo(() => {
    if (!data.nodes.length)
      return { scaledNodes: [], scaledLinks: [], maxDegree: 1, nodeMap: new Map() };

    const pad = 50;
    const xs = data.nodes.map((n) => n.x);
    const ys = data.nodes.map((n) => n.y);
    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const minY = Math.min(...ys);
    const maxY = Math.max(...ys);
    const rangeX = maxX - minX || 1;
    const rangeY = maxY - minY || 1;

    const maxDeg = Math.max(...data.nodes.map((n) => n.degree), 1);

    const nodeMap = new Map<string, { sx: number; sy: number; degree: number }>();
    const scaledNodes = data.nodes.map((n) => {
      const sx = pad + ((n.x - minX) / rangeX) * (width - 2 * pad);
      const sy = pad + ((n.y - minY) / rangeY) * (height - 2 * pad);
      nodeMap.set(n.id, { sx, sy, degree: n.degree });
      return { ...n, sx, sy };
    });

    const scaledLinks = data.links
      .map((l) => {
        const s = nodeMap.get(l.source);
        const t = nodeMap.get(l.target);
        if (!s || !t) return null;
        return { x1: s.sx, y1: s.sy, x2: t.sx, y2: t.sy, source: l.source, target: l.target };
      })
      .filter(Boolean) as { x1: number; y1: number; x2: number; y2: number; source: string; target: string }[];

    return { scaledNodes, scaledLinks, maxDegree: maxDeg, nodeMap };
  }, [data, width, height]);

  // Compute connected edges for hovered node
  const hoveredEdges = useMemo(() => {
    if (!hoveredNode) return new Set<number>();
    const s = new Set<number>();
    scaledLinks.forEach((l, i) => {
      if (l.source === hoveredNode || l.target === hoveredNode) s.add(i);
    });
    return s;
  }, [hoveredNode, scaledLinks]);

  const hoveredNeighbors = useMemo(() => {
    if (!hoveredNode) return new Set<string>();
    const s = new Set<string>();
    scaledLinks.forEach((l) => {
      if (l.source === hoveredNode) s.add(l.target);
      if (l.target === hoveredNode) s.add(l.source);
    });
    return s;
  }, [hoveredNode, scaledLinks]);

  // Reset transform when data changes
  useEffect(() => {
    setTransform({ x: 0, y: 0, scale: 1 });
  }, [data]);

  const handleWheel = useCallback(
    (e: React.WheelEvent<SVGSVGElement>) => {
      e.preventDefault();
      const svg = svgRef.current;
      if (!svg) return;

      const rect = svg.getBoundingClientRect();
      // Mouse position in SVG coordinates
      const mx = ((e.clientX - rect.left) / rect.width) * width;
      const my = ((e.clientY - rect.top) / rect.height) * height;

      const zoomFactor = e.deltaY < 0 ? 1.15 : 1 / 1.15;

      setTransform((prev) => {
        const newScale = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, prev.scale * zoomFactor));
        const ratio = newScale / prev.scale;
        // Zoom toward mouse position
        const nx = mx - (mx - prev.x) * ratio;
        const ny = my - (my - prev.y) * ratio;
        return { x: nx, y: ny, scale: newScale };
      });
    },
    [width, height],
  );

  const handlePointerDown = useCallback(
    (e: React.PointerEvent<SVGSVGElement>) => {
      // Only pan on primary button and when not clicking a node
      if (e.button !== 0) return;
      const target = e.target as SVGElement;
      if (target.tagName === 'circle') return;

      const svg = svgRef.current;
      if (!svg) return;
      svg.setPointerCapture(e.pointerId);

      setIsPanning(true);
      const rect = svg.getBoundingClientRect();
      panStart.current = {
        x: ((e.clientX - rect.left) / rect.width) * width,
        y: ((e.clientY - rect.top) / rect.height) * height,
        tx: transform.x,
        ty: transform.y,
      };
    },
    [transform, width, height],
  );

  const handlePointerMove = useCallback(
    (e: React.PointerEvent<SVGSVGElement>) => {
      if (!isPanning) return;
      const svg = svgRef.current;
      if (!svg) return;
      const rect = svg.getBoundingClientRect();
      const mx = ((e.clientX - rect.left) / rect.width) * width;
      const my = ((e.clientY - rect.top) / rect.height) * height;
      setTransform((prev) => ({
        ...prev,
        x: panStart.current.tx + (mx - panStart.current.x),
        y: panStart.current.ty + (my - panStart.current.y),
      }));
    },
    [isPanning, width, height],
  );

  const handlePointerUp = useCallback(() => {
    setIsPanning(false);
  }, []);

  const zoomIn = () =>
    setTransform((prev) => ({
      ...prev,
      scale: Math.min(MAX_ZOOM, prev.scale * 1.4),
    }));

  const zoomOut = () =>
    setTransform((prev) => ({
      ...prev,
      scale: Math.max(MIN_ZOOM, prev.scale / 1.4),
    }));

  const resetView = () => setTransform({ x: 0, y: 0, scale: 1 });

  if (!data.nodes.length) {
    return (
      <div
        className="w-full flex items-center justify-center bg-gray-50 rounded-lg border border-dashed border-gray-300"
        style={{ aspectRatio: `${width} / ${height}` }}
      >
        <p className="text-gray-400 text-sm">No graph data</p>
      </div>
    );
  }

  const nodeRadius = (degree: number) => {
    const min = 4;
    const max = 14;
    return min + (degree / maxDegree) * (max - min);
  };

  // Adaptive stroke based on node count
  const edgeStroke = data.nodes.length > 200 ? 0.6 : 1;
  const edgeOpacity = data.nodes.length > 200 ? 0.25 : 0.4;

  return (
    <div>
      {label && (
        <div className="text-center mb-2">
          <span className="text-sm font-semibold text-gray-700">{label}</span>
          <span className="text-xs text-gray-400 ml-2">
            {data.nodes.length} nodes, {data.links.length} edges
            {data.subsampled && (
              <span className="text-amber-600 ml-1">
                (showing subset of {data.total_nodes.toLocaleString()})
              </span>
            )}
          </span>
        </div>
      )}
      <div className="relative">
        <svg
          ref={svgRef}
          viewBox={`0 0 ${width} ${height}`}
          className="w-full bg-gray-50 rounded-lg border border-gray-200"
          style={{ aspectRatio: `${width} / ${height}`, cursor: isPanning ? 'grabbing' : 'grab' }}
          onWheel={handleWheel}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerLeave={handlePointerUp}
        >
          <g transform={`translate(${transform.x}, ${transform.y}) scale(${transform.scale})`}>
            {/* Edges */}
            <g>
              {scaledLinks.map((l, i) => {
                const highlighted = hoveredEdges.has(i);
                return (
                  <line
                    key={i}
                    x1={l.x1}
                    y1={l.y1}
                    x2={l.x2}
                    y2={l.y2}
                    stroke={highlighted ? nodeColor : edgeColor}
                    strokeWidth={highlighted ? edgeStroke * 2.5 : edgeStroke}
                    strokeOpacity={hoveredNode ? (highlighted ? 0.8 : 0.08) : edgeOpacity}
                  />
                );
              })}
            </g>
            {/* Nodes */}
            <g>
              {scaledNodes.map((n) => {
                const isHovered = n.id === hoveredNode;
                const isNeighbor = hoveredNeighbors.has(n.id);
                const dimmed = hoveredNode !== null && !isHovered && !isNeighbor;
                const r = nodeRadius(n.degree);
                return (
                  <circle
                    key={n.id}
                    cx={n.sx}
                    cy={n.sy}
                    r={isHovered ? r * 1.5 : r}
                    fill={nodeColor}
                    fillOpacity={dimmed ? 0.15 : isHovered ? 1 : 0.85}
                    stroke={isHovered ? '#fff' : isNeighbor ? '#fff' : 'rgba(255,255,255,0.6)'}
                    strokeWidth={isHovered ? 2 / transform.scale : 0.8 / transform.scale}
                    style={{ cursor: 'pointer', transition: 'r 0.15s, fill-opacity 0.15s' }}
                    onPointerEnter={() => setHoveredNode(n.id)}
                    onPointerLeave={() => setHoveredNode(null)}
                  />
                );
              })}
            </g>
          </g>

          {/* Hovered node tooltip rendered outside transform so it doesn't scale */}
          {hoveredNode && nodeMap.has(hoveredNode) && (() => {
            const nd = nodeMap.get(hoveredNode)!;
            const screenX = nd.sx * transform.scale + transform.x;
            const screenY = nd.sy * transform.scale + transform.y;
            const tooltipX = Math.min(Math.max(screenX, 60), width - 60);
            const tooltipY = Math.max(screenY - 18, 16);
            return (
              <g>
                <rect
                  x={tooltipX - 50}
                  y={tooltipY - 12}
                  width={100}
                  height={24}
                  rx={4}
                  fill="rgba(0,0,0,0.8)"
                />
                <text
                  x={tooltipX}
                  y={tooltipY + 3}
                  textAnchor="middle"
                  fill="white"
                  fontSize={10}
                  fontFamily="monospace"
                >
                  {String(hoveredNode).length > 12
                    ? String(hoveredNode).slice(0, 11) + '…'
                    : hoveredNode}
                  {' '}(d:{nd.degree})
                </text>
              </g>
            );
          })()}
        </svg>

        {/* Zoom controls */}
        <div className="absolute top-2 right-2 flex flex-col gap-1">
          <button
            onClick={zoomIn}
            className="w-7 h-7 bg-white border border-gray-300 rounded shadow-sm text-gray-600 hover:bg-gray-100 flex items-center justify-center text-sm font-bold"
            title="Zoom in"
          >
            +
          </button>
          <button
            onClick={zoomOut}
            className="w-7 h-7 bg-white border border-gray-300 rounded shadow-sm text-gray-600 hover:bg-gray-100 flex items-center justify-center text-sm font-bold"
            title="Zoom out"
          >
            −
          </button>
          <button
            onClick={resetView}
            className="w-7 h-7 bg-white border border-gray-300 rounded shadow-sm text-gray-600 hover:bg-gray-100 flex items-center justify-center text-xs"
            title="Reset view"
          >
            ⟲
          </button>
        </div>

        {/* Zoom level indicator */}
        {transform.scale !== 1 && (
          <div className="absolute bottom-2 left-2 px-2 py-0.5 bg-black/60 rounded text-white text-xs font-mono">
            {Math.round(transform.scale * 100)}%
          </div>
        )}
      </div>
    </div>
  );
}
