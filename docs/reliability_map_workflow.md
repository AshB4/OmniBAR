## Overview

- **Purpose**: Visualize agent reliability across benchmark suites and personas, showing relationships and temporal changes.
- **Key Features**: Radial node graph with animated edges, pulse intensity for reliability strength, opacity for drift/decay, dark mode support.
- **Difference from Quality Radar**: Quality Radar shows static 4-axis scores per iteration; Reliability Map shows dynamic network evolution.

## Quick Start

### Reliability Map (Agent MRI)

The Reliability Map provides a system-level view of agent reliability as an interactive network graph:

- **Center Node**: Active agent with overall reliability score
- **Surrounding Nodes**: Benchmark suites (e.g., Calculator Demo, Crisis Command) and personas (e.g., Rhema, Tutor)
- **Animated Edges**: Pulse intensity shows live reliability strength; opacity indicates drift/decay over time
- **Tooltips**: Display scores, last run timestamps, and drift factors

**Demo Script:**
1. Navigate to "Reliability Map" in the sidebar
2. Observe the radial network with pulsing edges
3. Hover nodes for details (e.g., suite scores, persona states)
4. Watch animations reflect temporal reliability changes

## Overview

- **Purpose**: Visualize agent reliability across benchmark suites and personas, showing relationships and temporal changes.
- **Key Features**: Radial node graph with animated edges, pulse intensity for reliability strength, opacity for drift/decay, dark mode support.
- **Difference from Quality Radar**: Quality Radar shows static 4-axis scores per iteration; Reliability Map shows dynamic network evolution.

## Workflow Steps

### 1. Access the Reliability Map
- Navigate to "Reliability Map" in the sidebar of the OmniBAR frontend.
- The page loads reliability data from `/reliability_map` (requires authentication; uses mock data for demo).

### 2. Interpret the Network Graph
- **Center Node**: Active agent (e.g., "Active Agent") with overall reliability score.
- **Suite Nodes**: Benchmark suites (e.g., "Calculator Demo Suite") connected to the center.
- **Persona Nodes**: Agent personas (e.g., "Rhema", "Tutor") for different modes.
- **Edges**: Lines connecting nodes with animations:
  - **Pulse Width**: Based on `strength` (reliability score, 0-1).
  - **Opacity**: Based on `drift` (decay factor, lower = more faded).

### 3. Interact with the Visualization
- **Hover Nodes**: Tooltips show score, last run timestamp, type, and connection details.
- **Observe Animations**: Edges pulse to indicate live reliability; fading shows temporal decay.
- **Node Details**: Click nodes to view details in console (basic implementation); future enhancement for drill-down views.
- **Theme Toggle**: Switch between light and dark modes using the toggle in the header for better visibility in different environments.

### 4. Monitor Reliability Evolution
- **Strength Changes**: Watch pulse intensity for reliability trends.
- **Drift Indicators**: Lower opacity signals degrading performance over time.
- **Network Patterns**: Identify clusters of high/low reliability suites/personas.

### 5. Integration with Other Features
- **Link to Runs**: From node tooltips, jump to regression traces in the Runs page.
- **Compare Iterations**: Use alongside Quality Radar for per-iteration vs. system-level views.
- **Persona Selection**: Select personas to filter the map (future enhancement).

## Technical Implementation

### Backend
- **Endpoint**: `GET /reliability_map` (requires X-API-Key authentication)
- **Data Structure**:
  ```json
  {
    "nodes": [
      {"id": "agent", "label": "Active Agent", "type": "agent", "score": 0.85, "lastRun": "2025-10-31T..."},
      {"id": "output", "label": "Calculator Demo Suite", "type": "suite", "score": 0.8, "lastRun": "..."}
    ],
    "links": [
      {"source": "agent", "target": "output", "strength": 0.8, "drift": 0.1}
    ]
  }
  ```
- **Mock Logic**: Derives from `SUITE_TEMPLATES` and adds personas with random scores/drift.

### Frontend
- **Hook**: `useReliabilityMapData` fetches and normalizes data.
- **Component**: `ReliabilityMap` renders SVG graph with radial positioning and animations.
- **Styling**: Uses Tailwind classes with CSS variables for theme support; animations via CSS `animate-pulse`; supports light and dark modes.

### Testing
- **Spec**: `frontend/tests/ReliabilityMap.spec.ts` mocks hook and verifies rendering.
- **Coverage**: Nodes, edges, loading/error states.

## Demo Script

1. Start backend: `uvicorn backend.app:app --reload --port 8000`
2. Start frontend: `cd frontend && npm run dev`
3. Navigate to Reliability Map.
4. Observe radial layout: center agent, surrounding suites/personas.
5. Watch edge pulses (reliability strength) and fading (drift).
6. Hover nodes for tooltips (scores, timestamps).
7. Simulate changes by refreshing or modifying mock data.

## Future Enhancements

- **Force-Directed Layout**: Replace radial with d3-force for dynamic positioning.
- **Real-Time Updates**: WebSocket integration for live reliability feeds.
- **Interactive Filtering**: Select personas/suites to filter the graph.
- **Drill-Down**: Click nodes to open detailed views (e.g., suite benchmarks).
- **Export**: Save graph as image or data for reports.

## Related Features

- **Quality Radar**: Per-iteration quality dimensions (complements system-level view).
- **Runs Page**: Historical suite executions (link from map tooltips).
- **Benchmarks Page**: Suite configurations (reference for map nodes).