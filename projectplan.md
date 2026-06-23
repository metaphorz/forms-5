# FORM S-6 — Interactive Grid + Windfields

## Goal
An interactive Leaflet web app over southern Florida that draws the official Form S-6
21×40 grid and runs selectable hurricane windfield models over it: **Powell** (PDE/slab),
**Holland**, and **Willoughby**. (An ERA5 4th option was considered and retired —
see Phase 4.) Supports the sensitivity/uncertainty analysis context of
Standard S-3 / Form S-6 in the ROA.

## Confirmed decisions (2026-06-18)
- **Scope:** Map + windfields first (phased). Loss-cost + SA/UA pipeline = later Phase 5.
- **Compute:** Hybrid. Powell (PDE) precomputed in Python → JSON. Holland +
  Willoughby computed live in the browser (analytic, instant interactivity).
- **ERA5:** Retired (2026-06-19). Originally planned as a 4th option; see Phase 4.

## Key facts (from ROA pp. 167–168, 182–191, 336–341 + Excel inputs)
- **Grid:** 21×40 = 840 vertices, ~3 statute-mile spacing.
  - E-W = 0,3,…,117 (40 columns); N-S = −15,−12,…,45 (21 rows).
  - Lat/lon for all 840 points are in the `Land-Water ID` sheet.
  - **682 land** (ID=1), 158 water (ID=0).
- **Track:** origin (0,0) = storm center at t=0, **9 mi east of landfall (25.8611 N,
  80.1196 W)**. Storm moves **due west** (0,0)→(117,0) over **12 hours**.
- **Inputs (`FormS6Input.xlsx`, 9 sheets):** CP, Rmax (st mi), VT (mph), WSP (shape),
  CF (conversion factor), FFP (mb), Quantile — 100 vectors × categories {1,3,5}.
  `FormS6InputQuantiles.xlsx` mirrors these as 0–1 quantiles. Sheet 1 = SA (all vars);
  sheets 2–8 = UA per variable; sheet 9 = Land-Water ID.
- **Pressure deficit:** dp = FFP − CP.
- **CF 3-zone radial rule (pp. 184–185):**
  - r < Rmax: CF·(r/Rmax)
  - Rmax < r < 3·Rmax: CF − [(r−Rmax)/(3Rmax−Rmax)]·0.1
  - r > 3·Rmax: CF − 0.1 (held constant)

## Reusable code
- `../storm-anim/hurricane_pde_marine.py` — implements all three models as functions:
  `pde_steady_marine` (Powell), `holland_asym_marine`, `willoughby_asym_marine`, with
  translation asymmetry + marine settings. Adapt to evaluate at the 840 grid points.
- `../era5tracks/web/` — Leaflet + canvas patterns, `start`/`stop` server scripts.

## Plan / Todo

### Phase 0 — Scaffold  ✅
- [x] Project venv + requirements (openpyxl, numpy)
- [x] Folder structure: `pipeline/`, `web/`, `outputs/web/`, `tests/auto/`
- [x] `start` / `stop` server scripts (port 8012)

### Phase 1 — Grid + map foundation  ✅
- [x] `pipeline/build_grid.py`: read `Land-Water ID` → `outputs/web/grid.json`
      (verified 840 pts, 682 land / 158 water, 40×21)
- [x] `web/index.html` + Leaflet: grid (land vs water), track (0,0)→(117,0),
      landfall marker, layer toggles, B-distribution UI control (default Uniform [1.0,2.5])

### Phase 2 — Windfield engine over the grid  (≈done)
- [x] `pipeline/read_inputs.py` → inputs.json (100×3 vectors, all variables)
- [x] `pipeline/windfield_grid.py`: Powell PDE → per-vertex 12-hr **peak** surface wind.
      Field computed once/vector (translation-invariant), sampled hourly t=0..12, CF
      3-zone conversion, dp=FFP−CP. ~2.4s/solve on MPS.
- [~] Precompute Powell all 100×3 → powell.json (running; cat1 done, peak 121 mph)
- [x] `web/windfield.js`: live Holland + Willoughby in JS — **validated** vs Python
      (Holland land-mean 76.3 mph == Powell marine 76.3 mph for cat1 v1).
- [x] **Surface roughness (rigorous)**: NLCD 2021 land cover (MRLC WCS, properly
      georeferenced) → modal class → published z0 table → **Vickery/ESDU gradient-tied
      log-law** marine→terrain ratio (`fetch_nlcd.sh` + `build_roughness.py`). Land-mean
      factor ≈0.67 (urban ~0.50, wetland ~0.70, water 1.0). Replaced the earlier
      heuristic+JPEG (whose georeferencing was wrong — sampling was spatially scrambled).
- [ ] **K&D land-effect selector**: replace roughness checkbox with 3-way
      None / Surface roughness / Kaplan–DeMaria decay (+Gulf recovery). (in progress)

### Phase 3 — Interactive viewer  ✅ (hour-animation deferred)
- [x] Controls: model, category {1,3,5}, input vector (1–100), B-distribution.
- [x] **"Color by" dropdown** (Max wind speed default; Land/Water option) + legend.
- [x] Hover vertex → tooltip: peak wind, (E-W,N-S) mi, lat/lon, land/water, **place name**
      (nearest area/county/state), input params.
- [x] **Display toggle: Points (default) / Filled contour** — banded filled contours on
      the 21×40 lattice (vendored d3-contour), matching ROA Figs 6–8.
- [x] **Light/Dark theme** toggle (dark default) — swaps basemap + sidebar.
- [x] **Place names**: `pipeline/add_place_names.py` (offline reverse_geocoder) → grid.json.
- [x] **Time-sampling fix**: peak envelope uses dt=0.1h (hourly aliased the fast westward
      storm → comb artifact in contours; fine sampling gives the true smooth peak).
- [x] `pipeline/build_all.sh` — one-command reproducible rebuild (dependency order).
- [ ] Hour slider / animate (t=0..12) — deferred (peak-wind is the agreed metric).

### Phase 4 — ERA5 4th option  ❌ RETIRED (2026-06-19)
- [x] Removed the inert "ERA5 (coming soon)" dropdown entry.
- **Rationale:** ERA5 is a *reanalysis* (fixed, already-observed field), not a
  *parametric* model. It cannot be a peer to Powell/Holland/Willoughby:
  - **Paradigm mismatch:** the 3 models are generated from tunable inputs
    (CP, Rmax, VT, WSP, CF, FFP); ERA5 has no such knobs, so category {1,3,5},
    input-vector 1–100, and the B-distribution controls would all be inert.
  - **SA/UA undefined:** SRC/EPR require perturbing the 6 inputs; a single fixed
    reanalysis field has nothing to vary.
  - **Resolution:** ERA5 ~0.25° (~28 km) under-resolves the TC inner core and
    systematically damps peak winds — the exact quantity (peak wind → loss) the
    app reports — and yields only ~8–12 cells over the southern-FL domain vs. 840
    grid vertices.
- **If revisited later**, the only coherent roles are (A) a clearly-labeled,
  per-historical-storm *validation overlay* (storm/date picker; coarse), or
  (B) using ERA5's well-resolved large scales (CP, track, translation speed) to
  *estimate* the input vector fed into the existing parametric models — a
  separate feature, not a dropdown entry.

### Phase 4.5 — Sensitivity & Uncertainty Analysis  ✅ (v1)
- [x] **SA → SRC**: standardized regression of output on the 6 inputs (CP, Rmax, VT,
      WSP, CF, FFP) over the 100 "SA all Variables" vectors, per category. (`analysis.js`)
- [x] **UA → EPR**: EPR_i = SRC_i²·100% (Option 2 variance-share approximation; valid for
      ~independent inputs). Uniform for all 3 models in v1.
- [x] Output metric: **mean peak wind over 682 land vertices** (wind proxy; → loss in P5).
- [x] UI: **Analysis** buttons (Sensitivity / Uncertainty) → SVG line chart x=cat {1,3,5},
      one line per variable + legend + R² (lightweight SVG, no new dep). ROA Figs 9/10 analog.
- [x] SRC + EPR open as **independent floating windows** — both viewable at once,
      **draggable** (title bar) and **resizable** (corner handle); bring-to-front on click.
- [x] **Validated**: SRC signs/ranking match ROA Fig 9 (WSP dominant cat1, CP negative,
      CF/FFP/Rmax positive).
- [ ] Option 1 (faithful Powell EPR via 1800-solve UA-sheet precompute) — optional, later.
- [ ] ASCII/PDF export of SA/UA (XXX25SA, XXX25UA) — Phase 5.

### Phase 5 — Full Form S-6 analysis (later)
- [ ] Loss costs at 682 land points; 300-row + 2,046-row ASCII/PDF outputs;
      CDF (Fig 5), contour (Figs 6–8), SRC (Fig 9), EPR (Fig 10).

## Resolved (2026-06-18)
- **Output metric:** per-vertex **peak (12-hr max) surface wind speed** is sufficient for
  now. Loss costs deferred to Phase 5.
- **Powell precompute:** all 100 vectors × 3 categories (300 PDE solves).
- **WSP → B (shape parameter):** WSP is a quantile p∈[0,1]; convert via inverse-CDF of a
  user-chosen distribution for Holland's B (shared shape knob across all 3 models).
  **UI control** lets the user pick the family + parameters:
    - Uniform: [Bmin, Bmax]  — **default Uniform [1.0, 2.5]**  → B = Bmin + p·(Bmax−Bmin)
    - Triangular: [Bmin, Bmode, Bmax]
    - Normal: [mean, std] (clamped to a sane range)
  Powell precompute uses the default; Holland/Willoughby recompute live in JS when the
  user changes the distribution.

## Conventions
- **Selenium** is used to (a) analyze/verify the web interface during development and
  (b) generate all figures when `docs/` is built later (as in other ~/code projects).

## Open questions for later
- (ERA5 4th-option resolved — retired; see Phase 4.)

## Mean / CSV buttons (2026-06-23) — DONE
Two buttons below the Input-vector slider.

Decisions confirmed with user:
- **CSV scope:** all 3 categories (300 rows + header). `Category` column is the bare
  number (1/3/5), per follow-up request.
- **Mean mode:** persistent toggle that overrides the slider (slider greyed while active);
  mean is over all 100 input vectors.

Done:
- [x] `index.html`: `<div class="vec-actions">` with `#btnMean` + `#btnCsv` under the slider.
- [x] `style.css`: `.vec-actions` / `.vec-btn` (+ `.active` green) styles; greyed disabled slider.
- [x] `viewer.js`: `state.meanMode`; `computeMeanWind(model,cat)` averages per-point wind
      over all 100 vectors (respects current model/category/land-effect/B); `computeWind()`
      returns the mean field when `meanMode`.
- [x] `viewer.js`: wired `#btnMean` (toggle, disable slider, deferred "Computing…" status)
      and `#btnCsv` (`downloadInputsCsv()` builds CP,Rmax,VT,WSP,CF,FFP for all 3 cats).
- [x] `viewer.js`: `pointInfoHTML` + info `tag` read "mean (100 vectors)" in mean mode.
- [x] Selenium test `tests/auto/test_mean_csv_buttons.py` — Powell + Holland mean, toggle,
      slider-disable, and 300-row CSV download. **ALL CHECKS PASSED.**

## Review
_(to be filled in as work proceeds)_
