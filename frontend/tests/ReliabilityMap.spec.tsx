import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import ReliabilityMap from '../src/pages/ReliabilityMap';
import { useReliabilityMapData } from '../src/hooks/useReliabilityMapData';

// Mock the hook
vi.mock('../src/hooks/useReliabilityMapData', () => ({
  useReliabilityMapData: () => ({
    data: {
      nodes: [
        { id: 'agent', label: 'Active Agent', type: 'agent', score: 0.85 },
        { id: 'output', label: 'Calculator Demo Suite', type: 'suite', score: 0.8 },
      ],
      links: [
        { source: 'agent', target: 'output', strength: 0.8, drift: 0.1 },
      ],
    },
    loading: false,
    error: null,
  }),
}));

describe('ReliabilityMap', () => {
  it('renders the reliability map with nodes and edges', () => {
    render(<ReliabilityMap />);

    expect(screen.getByText('Reliability Map')).toBeInTheDocument();
    expect(screen.getByText('Reliability Network')).toBeInTheDocument();
    // Check for SVG elements (nodes/links)
    const svg = document.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('shows loading state', () => {
    vi.mocked(useReliabilityMapData).mockReturnValue({
      data: null,
      loading: true,
      error: null,
    });

    render(<ReliabilityMap />);
    expect(screen.getByText('Loading reliability network...')).toBeInTheDocument();
  });

  it('shows error state', () => {
    vi.mocked(useReliabilityMapData).mockReturnValue({
      data: null,
      loading: false,
      error: 'Test error',
    });

    render(<ReliabilityMap />);
    expect(screen.getByText('Test error')).toBeInTheDocument();
  });
});