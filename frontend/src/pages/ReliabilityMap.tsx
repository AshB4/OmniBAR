import { useEffect, useRef, useState } from 'react';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useReliabilityMapData, type Node, type Link } from '@/hooks/useReliabilityMapData';

export default function ReliabilityMap() {
  const { data, loading, error } = useReliabilityMapData();
  const svgRef = useRef<SVGSVGElement>(null);
  const [positions, setPositions] = useState<Map<string, { x: number; y: number }>>(new Map());

  useEffect(() => {
    if (!data) return;

    const centerX = 400;
    const centerY = 300;
    const radius = 150;

    const newPositions = new Map<string, { x: number; y: number }>();
    newPositions.set('agent', { x: centerX, y: centerY });

    const surroundingNodes = data.nodes.filter(n => n.id !== 'agent');
    surroundingNodes.forEach((node, index) => {
      const angle = (index / surroundingNodes.length) * 2 * Math.PI;
      const x = centerX + radius * Math.cos(angle);
      const y = centerY + radius * Math.sin(angle);
      newPositions.set(node.id, { x, y });
    });

    setPositions(newPositions);
  }, [data]);

  if (loading) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-semibold tracking-tight">Reliability Map</h1>
        <p className="text-sm text-muted-foreground">Loading reliability network...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-semibold tracking-tight">Reliability Map</h1>
        <div className="rounded-md border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">{error}</div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-semibold tracking-tight">Reliability Map</h1>
        <p className="text-sm text-muted-foreground">No reliability data available.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">Reliability Map</h1>
        <p className="text-muted-foreground text-sm">
          System-level MRI showing reliability network evolution: center = active agent, nodes = suites/personas, edges = pulse intensity.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Reliability Network</CardTitle>
          <CardDescription>Force-directed graph with animated edges for reliability strength and drift.</CardDescription>
        </CardHeader>
        <CardContent>
          <svg ref={svgRef} width="800" height="600" className="border rounded">
            {data.links.map((link, index) => {
               const sourcePos = positions.get(link.source);
               const targetPos = positions.get(link.target);
               if (!sourcePos || !targetPos) return null;

               const sourceNode = data.nodes.find(n => n.id === link.source);
               const targetNode = data.nodes.find(n => n.id === link.target);
               const tooltip = `Connection: ${sourceNode?.label || link.source} → ${targetNode?.label || link.target}\nStrength: ${(link.strength * 100).toFixed(0)}%\nDrift: ${(link.drift * 100).toFixed(0)}%`;

               return (
                 <line
                   key={index}
                   x1={sourcePos.x}
                   y1={sourcePos.y}
                   x2={targetPos.x}
                   y2={targetPos.y}
                   stroke="hsl(var(--primary))"
                   strokeWidth={link.strength * 5}
                   opacity={1 - link.drift}
                   className="animate-pulse"
                 >
                   <title>{tooltip}</title>
                 </line>
               );
             })}
            {data.nodes.map((node) => {
              const pos = positions.get(node.id);
              if (!pos) return null;

              const size = node.type === 'agent' ? 20 : 15;
              const color = node.type === 'agent' ? 'hsl(var(--primary))' : node.type === 'suite' ? 'hsl(var(--secondary))' : 'hsl(var(--muted))';

               const tooltip = `Type: ${node.type}\nScore: ${node.score ? (node.score * 100).toFixed(0) + '%' : 'N/A'}\nLast Run: ${node.lastRun ? new Date(node.lastRun).toLocaleString() : 'N/A'}`;

               return (
                 <g key={node.id}>
                   <circle
                     cx={pos.x}
                     cy={pos.y}
                     r={size}
                     fill={color}
                     opacity={node.score || 0.8}
                     style={{ cursor: 'pointer' }}
                     onClick={() => console.log('Node clicked:', node)}
                   >
                     <title>{tooltip}</title>
                   </circle>
                   <text
                     x={pos.x}
                     y={pos.y + size + 15}
                     textAnchor="middle"
                     fontSize="12"
                     fill="hsl(var(--foreground))"
                   >
                     {node.label}
                   </text>
                   {node.score && (
                     <text
                       x={pos.x}
                       y={pos.y - size - 5}
                       textAnchor="middle"
                       fontSize="10"
                       fill="hsl(var(--muted-foreground))"
                     >
                       {(node.score * 100).toFixed(0)}%
                     </text>
                   )}
                 </g>
               );
            })}
          </svg>
        </CardContent>
      </Card>
    </div>
  );
}