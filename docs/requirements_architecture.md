# PyNetworkGT Standalone Application Specification

## 1. Vision & Scope
- Deliver a cross-platform Python desktop application that reproduces (and eventually extends) the analytical capabilities of the original NetworkGT QGIS plugin without requiring QGIS.
- Support geoscientists analysing fracture networks through an integrated workflow: data import, visual inspection, algorithm execution, and result export.

## 2. Primary Objectives
- Provide a deterministic import layer for the bespoke TXT fracture format and GeoPackage (`.gpkg`) vector layers.
- Re-implement the NetworkGT processing tools (Digitising, Geometry, Topology, Sampling, Flow) using Python libraries that do not depend on QGIS.
- Offer an interactive GUI with layer management, map rendering, parameter forms, and results visualisation.
- Maintain compatibility with the scientific dependencies used by the original plugin (e.g. `numpy`, `scipy`, `scikit-image`, `networkx`) while exposing a clear Python API for automation.

## 3. Supported Data & Formats
- **Custom TXT format**: each line contains an even number of tab-separated values interpreted as `x1\ty1\tx2\ty2...`; every line maps to a `LineString` geometry.
- **GeoPackage (`.gpkg`)**: primary GIS interchange format for both import and export; multiple layers per file are permitted.
- **Future extensions (optional)**: GeoJSON, shapefile, CSV with WKT, raster formats (GeoTIFF) when required by algorithms.

## 4. Domain Model
- **Geometry primitives**: leverage `shapely` (or `pygeos`) `LineString`/`MultiLineString` as the canonical representation of fractures and networks.
- **Attributes**: store metadata (length, orientation, set id, topology metrics, flow parameters) in accompanying pandas DataFrames or geopandas GeoDataFrames.
- **Layer abstraction**: define a `Layer` class encapsulating name, visibility, drawing order, symbology (colour, width, opacity), and a reference to the underlying geometry/attribute container.

## 5. Functional Requirements
### 5.1 Data Acquisition & Management
- Import TXT/GPKG files into the internal layer model with validation of coordinate parity and optional CRS assignment.
- Export processed layers back to GPKG or TXT (for fracture-only datasets).
- Maintain project/session state (open layers, order, visibility, symbology, analysis results) in a portable file (e.g. JSON).

### 5.2 Digitising Toolkit Migration
Replicate the behaviour of QGIS-based tools under `networkgt/digitising`:
- `Fracture_Network`: skeletonise binary rasters, convert to vector networks, simplify geometries, remove short isolated fractures.
- `SimplifyNetwork`: apply line simplification with tolerance control while preserving topology.
- `Thresholding`: generate binary rasters from greyscale imagery using configurable thresholds.
- `SnapNodes`, `SnapYNodes`, `Repair`, `Extend_Trim`, `Fracture_Number`: implement node snapping, network cleaning, extension/trimming operations, and fracture counting utilities.

### 5.3 Geometry Analysis Toolkit
Recreate algorithms found in `networkgt/geometry`:
- Orientation histograms, rose diagrams, set classification (`Sets.py`), tortuosity metrics, fracture length distributions, line frequency calculations, etc.
- Produce both tabular outputs and optional plots (Matplotlib/Plotly) embedded in the GUI.

### 5.4 Topology Toolkit
- Implement cluster detection, branch/node classification, topological parameters (`Topology_Parameters`, `Branches_Nodes`, `TB`, `BI`, `Relationships`, `ShortestPathway`).
- Ensure compatibility with `networkx` for graph-based operations.

### 5.5 Sampling & Grid Toolkit
- Port grid creation utilities (`Simple_Grid`, `Simple_Line_Grid`), grid calculators/statistics, and plotting helpers.
- Allow users to define sampling grids interactively or via parameter inputs.

### 5.6 Flow Toolkit
- Re-implement fracture flow simulations (`Flow1D`, `Flow2D`, `flow`, `aperture`, `percolation`, `permTensor`, `tracer`) with CLI-equivalent interfaces.
- Support mesh generation (via `meshio`, `gmsh` CLI integration when available) and result visualisation.

### 5.7 User Interface Requirements
- Desktop GUI built with Qt (`PySide6` preferred):
  - Central map canvas with pan/zoom, selection, measurement tools.
  - Dockable layer tree with checkboxes for visibility, drag-and-drop reordering, and context menus for styling or analysis.
  - Support simultaneous display of multiple layers obeying tree order (top item drawn last).
  - Parameter panels to configure and run analyses; progress feedback and error reporting.
  - Result viewers: attribute tables, charts, export options.
- Keyboard shortcuts and menus for file operations, analysis workflows, and layout management.

## 6. Non-Functional Requirements
- **Cross-platform**: Windows, macOS, Linux with Python ≥ 3.10.
- **Performance**: render networks with tens of thousands of segments interactively (< 200 ms redraw) via geometry caching and level-of-detail strategies.
- **Reliability**: deterministic outputs for given inputs; log all processing steps and errors.
- **Extensibility**: modular architecture enabling new tools to be added without touching core components.
- **Testing**: automated unit/integration tests for parsers, algorithms, and GUI controllers (Qt Test, pytest + Qt bot).

## 7. Technology Stack & Dependencies (initial proposal)
- **Core**: Python 3.11, `numpy`, `scipy`, `pandas`.
- **Geometry/GIS**: `shapely`, `pyproj`, `geopandas`, `fiona`, `rasterio`, `scikit-image`.
- **Graphs & analysis**: `networkx`, `meshio`, `gmsh` (optional external binary), `sympy` if required by legacy code.
- **Visualisation**: `matplotlib`, `plotly` (for interactive plots), optional `pyqtgraph`.
- **GUI**: `PySide6` (or `PyQt6`), `QtGraphicalEffects` equivalents.
- **Packaging**: `poetry` or `pip`-based virtualenv with `pyinstaller` build target for distribution.

## 8. Architecture Overview
```
├── core            # domain models, helpers (geometry, units, CRS)
├── io              # readers/writers for TXT, GPKG, future formats
├── algorithms      # digitising, geometry, topology, sampling, flow
│   ├── digitising
│   ├── geometry
│   ├── topology
│   ├── sampling
│   └── flow
├── gui             # Qt application, widgets, layer tree, map canvas
├── services        # orchestration, job management, logging
└── tests           # pytest suites
```
- Map canvas built atop reusable rendering service that converts shapely geometries into Qt `QPainterPath` or Matplotlib artists.
- Algorithms operate on plain Python objects (`Layer`, `GeoDataFrame`), not GUI classes.
- Job manager to execute long-running analyses in worker threads (`QThreadPool`) with progress callbacks.

## 9. Project Roadmap (Milestones)
1. **Foundations**: parser implementations (TXT, GPKG), core data model, unit tests.
2. **Viewer MVP**: Qt shell with map canvas, layer tree, basic styling, file open/save.
3. **Geometry & Topology Core**: port key analytical tools (Sets, tortuosity, topology parameters) and integrate with GUI panels.
4. **Digitising & Sampling Enhancements**: raster handling, skeletonisation workflows, grid utilities, plotting.
5. **Flow Module & Advanced Outputs**: integrate flow simulations, mesh export, advanced charts; polish UX and packaging.

## 10. Open Questions & Risks
- Confirm detailed behaviour of each legacy tool (edge cases, parameter defaults) through targeted code review and tests.
- Determine handling of coordinate reference systems when TXT inputs lack CRS metadata.
- Decide on 2D vs 3D support (legacy plugin appears 2D-only; maintain assumption unless new requirements arise).
- Evaluate licensing implications of bundling `gmsh` or other external binaries.

