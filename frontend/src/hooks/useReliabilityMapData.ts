import { useEffect, useState } from 'react';

export type Node = {
  id: string;
  label: string;
  type: 'agent' | 'suite' | 'persona' | 'memory';
  x?: number;
  y?: number;
  score?: number;
  lastRun?: string;
};

export type Link = {
  source: string;
  target: string;
  strength: number; // 0-1, for pulse intensity
  drift: number; // decay factor
};

export type ReliabilityMapData = {
  nodes: Node[];
  links: Link[];
};

export function useReliabilityMapData() {
  const [data, setData] = useState<ReliabilityMapData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch('/api/reliability_map');
        if (!response.ok) {
          throw new Error('Failed to fetch reliability map data');
        }
        const result: ReliabilityMapData = await response.json();
        setData(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  return { data, loading, error };
}