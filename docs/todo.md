# Task Board

## Completed
- ✅ TXT/GPKG import + domain model (`FractureNetwork`, `FractureLine`), unit tests.
- ✅ Project persistence (JSON) with layer order/visibility/style and project metadata.
- ✅ Canvas orientation fix (Y axis up) with pan/zoom controls (mouse + shortcuts).
- ✅ Enhanced export workflow (PNG/JPEG/SVG, custom size, DPI, background, title, legend).

## In Progress / Near Term
- [x] Style presets (colour/width themes) and live legend panel in GUI.
- [x] Persist user preferences (recent files, last export path, axis toggle, zoom level).
- [x] Scale bar and coordinate grid overlays with configurable appearance.
- [x] Axis orientation handled automatically (consistent with QGIS).

## Data Acquisition & Management
- [ ] Validation pipeline: coordinate parity checks, CRS assignment, error reporting in GUI.
- [ ] Export pipelines: GPKG/TXT writers with metadata + CRS support; bulk export dialog.
- [ ] Additional format backlog: GeoJSON, shapefile, CSV (WKT), raster (GeoTIFF) readers/writers.
- [ ] Session persistence: store analysis outputs, map state, legend, measurement overlays.

## Digitising Toolkit (`networkgt/digitising`)
- [x] Raster skeletonisation (`Fracture_Network`): scikit-image skeleton + vectorisation.
- [ ] Simplify network (Douglas–Peucker with topology checks).
- [x] Thresholding (binary raster generation) with histogram preview.
- [ ] Node operations: SnapNodes, SnapYNodes, Repair, Extend_Trim.
- [ ] Network cleanup utilities: Fracture_Number, short isolated branches removal.
- [ ] Digitising control panel with parameters, dependency checks, progress feedback.

## Geometry Toolkit (`networkgt/geometry`)
- [ ] Orientation histograms & rose diagrams (matplotlib/plotly embed).
- [ ] Set classification (`Sets.py`) with interactive bin editor.
- [ ] Tortuosity metrics, fracture length distributions, line frequency calculations.
- [ ] Distribution analysis visualisations + export of summary tables.

## Topology Toolkit (`networkgt/topology`)
- [ ] Branch/node classification visual overlays (Branches_Nodes).
- [ ] Topology parameters (TP, TB, BI, Relationships) with result tables.
- [ ] Shortest pathway analysis with highlight + metrics.
- [ ] Cluster detection (BI) with statistics + optional colour coding.

## Sampling & Grid Toolkit (`networkgt/sampling`)
- [ ] Grid creation tools (Simple Grid / Simple Line Grid) with interactive extent control.
- [ ] Grid statistics/calculators; heatmap/plot outputs for sampling results.
- [ ] Grid plot utilities integrated with export dialogue.

## Flow Toolkit (`networkgt/flow`)
- [ ] Flow simulations (Flow1D/2D, flow.py wrapper) with UI forms and result plots.
- [ ] Aperture, percolation, permTensor computations; contour/arrow visualisation.
- [ ] Mesh generation pipeline (meshio + gmsh) including config UI and dependency checks.
- [ ] Tracer modelling, time-step charts, exportable tables.

## GUI Enhancements
- [ ] Parameter panels for each toolkit with validation and binding to algorithms.
- [ ] Result viewers: tabular views (QTableView), embedded charts, downloadable reports.
- [ ] Measurement tools (distances, angles) and selection/highlight interactions on canvas.
- [ ] Job manager (QThreadPool) for long-running tasks, with cancellable progress dialogs.
- [ ] Logging/notifications pane (success, warnings, dependency hints) with persistence.

## Core & Services
- [ ] Core helpers: CRS management (`pyproj`), units conversion, geometry caching/memoisation.
- [ ] Services/orchestration layer for analysis jobs, dependency management, messaging.
- [ ] CLI entry points for batch processing and scripted analysis pipelines.
- [ ] Packaging/distribution: build scripts (`pyinstaller`/`briefcase`), dependency locking, installer UX.

## Testing & Quality
- [ ] Extend unit tests to cover IO edge cases, geometry/topology calculations.
- [ ] GUI smoke/integration tests (pytest-qt or Qt Test) for critical workflows.
- [ ] Performance benchmarks (< 200 ms redraw) and regression monitoring for large networks.
- [ ] Documentation: user guide (import→analysis→export), developer setup, API reference.

## Risks / Open Questions
- [ ] Validate behaviour parity against original QGIS plugin (edge cases, defaults).
- [ ] Define CRS strategy for TXT inputs lacking metadata (user prompts, defaults).
- [ ] Evaluate licensing for bundling external binaries (gmsh, etc.).
- [ ] Confirm long-term scope (2D only vs potential 3D support) and update roadmap accordingly.

