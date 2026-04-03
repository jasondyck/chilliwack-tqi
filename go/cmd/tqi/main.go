// Package main provides the CLI entrypoint for the TQI tool.
package main

import (
	"encoding/json"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strings"

	"github.com/spf13/cobra"

	"github.com/jasondyck/chwk-tqi/internal/api"
	"github.com/jasondyck/chwk-tqi/internal/config"
	"github.com/jasondyck/chwk-tqi/internal/equity"
	"github.com/jasondyck/chwk-tqi/internal/grid"
	"github.com/jasondyck/chwk-tqi/internal/gtfs"
	"github.com/jasondyck/chwk-tqi/internal/isochrone"
	"github.com/jasondyck/chwk-tqi/internal/neighbourhood"
	"github.com/jasondyck/chwk-tqi/internal/raptor"
	"github.com/jasondyck/chwk-tqi/internal/scoring"
	"github.com/jasondyck/chwk-tqi/web"
)

func main() {
	rootCmd := &cobra.Command{
		Use:   "tqi",
		Short: "Transit Quality Index — measure how well transit connects a city",
	}

	rootCmd.AddCommand(
		newServeCmd(),
		newRunCmd(),
		newDownloadCmd(),
		newCompareCmd(),
	)

	if err := rootCmd.Execute(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

// ── serve ──

func newServeCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "serve",
		Short: "Start the TQI API server",
		RunE: func(cmd *cobra.Command, args []string) error {
			port, _ := cmd.Flags().GetInt("port")
			noDownload, _ := cmd.Flags().GetBool("no-download")
			noCache, _ := cmd.Flags().GetBool("no-cache")
			workers, _ := cmd.Flags().GetInt("workers")
			skipRun, _ := cmd.Flags().GetBool("skip-run")

			srv := api.NewServer(port)
			srv.WebFS = web.DistFS()

			if !skipRun {
				fmt.Println("Running analysis pipeline before starting server...")
				results, err := runPipeline(pipelineOpts{
					gtfsURL:      config.GTFSURL,
					dataDir:      "data",
					bboxSW:       config.BBoxSW,
					bboxNE:       config.BBoxNE,
					routes:       config.ChilliwackRoutes,
					boundaryPath: config.BoundaryGeoJSON,
					noDownload:   noDownload,
					noCache:      noCache,
					workers:      workers,
					outputDir:    "output",
					cityName:     "chilliwack",
				})
				if err != nil {
					return fmt.Errorf("pipeline failed: %w", err)
				}
				srv.SetResults(results)
				fmt.Printf("\nAnalysis complete — TQI: %.1f / 100\n\n", results.TQI.TQI)
			}

			fmt.Printf("Starting TQI server on http://localhost:%d\n", port)
			return srv.Start()
		},
	}
	cmd.Flags().Int("port", 8080, "Port to listen on")
	cmd.Flags().Bool("no-download", false, "Skip GTFS download")
	cmd.Flags().Bool("no-cache", false, "Ignore cached matrix")
	cmd.Flags().Int("workers", 0, "Number of parallel workers (0 = auto)")
	cmd.Flags().Bool("skip-run", false, "Start server without running pipeline (no results until POST /api/run)")
	return cmd
}

// ── run ──

func newRunCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "run",
		Short: "Run the full TQI analysis pipeline",
		RunE: func(cmd *cobra.Command, args []string) error {
			noDownload, _ := cmd.Flags().GetBool("no-download")
			noCache, _ := cmd.Flags().GetBool("no-cache")
			workers, _ := cmd.Flags().GetInt("workers")
			outputDir, _ := cmd.Flags().GetString("output-dir")

			_, err := runPipeline(pipelineOpts{
				gtfsURL:      config.GTFSURL,
				dataDir:      "data",
				bboxSW:       config.BBoxSW,
				bboxNE:       config.BBoxNE,
				routes:       config.ChilliwackRoutes,
				boundaryPath: config.BoundaryGeoJSON,
				noDownload:   noDownload,
				noCache:      noCache,
				workers:      workers,
				outputDir:    outputDir,
				cityName:     "chilliwack",
			})
			return err
		},
	}
	cmd.Flags().Bool("no-download", false, "Skip GTFS download")
	cmd.Flags().Bool("no-cache", false, "Ignore cached matrix")
	cmd.Flags().Int("workers", 0, "Number of parallel workers (0 = auto)")
	cmd.Flags().Bool("equity", false, "Include census equity overlay")
	cmd.Flags().String("output-dir", "output", "Output directory")
	return cmd
}

// ── download ──

func newDownloadCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "download",
		Short: "Download GTFS data from BC Transit",
		RunE: func(cmd *cobra.Command, args []string) error {
			destDir := filepath.Join("data", "gtfs")
			fmt.Printf("Downloading GTFS from %s to %s\n", config.GTFSURL, destDir)
			hash, err := gtfs.DownloadGTFS(config.GTFSURL, destDir)
			if err != nil {
				return err
			}
			fmt.Printf("Download complete. Feed hash: %s\n", hash)
			return nil
		},
	}
	return cmd
}

// ── compare ──

func newCompareCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "compare",
		Short: "Compare TQI across multiple BC Transit cities",
		RunE: func(cmd *cobra.Command, args []string) error {
			citiesStr, _ := cmd.Flags().GetString("cities")
			workers, _ := cmd.Flags().GetInt("workers")
			outputDir, _ := cmd.Flags().GetString("output-dir")

			cityNames := strings.Split(citiesStr, ",")
			for i := range cityNames {
				cityNames[i] = strings.TrimSpace(cityNames[i])
			}

			for _, name := range cityNames {
				cc, ok := config.CityConfigs[name]
				if !ok {
					fmt.Fprintf(os.Stderr, "Warning: unknown city %q, skipping\n", name)
					continue
				}

				fmt.Printf("\n══════ %s ══════\n", strings.ToUpper(name))
				_, err := runPipeline(pipelineOpts{
					gtfsURL:      cc.URL,
					dataDir:      filepath.Join("data", name),
					bboxSW:       cc.BBoxSW,
					bboxNE:       cc.BBoxNE,
					routes:       cc.Routes,
					boundaryPath: "", // no boundary filter for non-Chilliwack cities
					noDownload:   false,
					noCache:      false,
					workers:      workers,
					outputDir:    filepath.Join(outputDir, name),
					cityName:     name,
				})
				if err != nil {
					fmt.Fprintf(os.Stderr, "Error running pipeline for %s: %v\n", name, err)
				}
			}
			return nil
		},
	}
	cmd.Flags().String("cities", "chilliwack,victoria,kelowna", "Comma-separated list of cities to compare")
	cmd.Flags().Int("workers", 0, "Number of parallel workers (0 = auto)")
	cmd.Flags().String("output-dir", "output", "Output directory")
	return cmd
}

// ── pipeline ──

type pipelineOpts struct {
	gtfsURL      string
	dataDir      string
	bboxSW       [2]float64
	bboxNE       [2]float64
	routes       []string
	boundaryPath string
	noDownload   bool
	noCache      bool
	workers      int
	outputDir    string
	cityName     string
}

func runPipeline(opts pipelineOpts) (*api.PipelineResults, error) {
	gtfsDir := filepath.Join(opts.dataDir, "gtfs")

	// 1. Optionally download GTFS.
	if !opts.noDownload {
		fmt.Println("Downloading GTFS data...")
		hash, err := gtfs.DownloadGTFS(opts.gtfsURL, gtfsDir)
		if err != nil {
			return nil, fmt.Errorf("download GTFS: %w", err)
		}
		fmt.Printf("Feed hash: %s\n", hash)
	}

	// 2. Get feed hash.
	feedHash := gtfs.GetFeedHash(gtfsDir)
	if feedHash == "" {
		fmt.Println("Warning: no feed hash found; caching will be disabled")
	}

	// 3. Parse GTFS.
	fmt.Println("Parsing GTFS feed...")
	feed, err := gtfs.LoadGTFS(gtfsDir)
	if err != nil {
		return nil, fmt.Errorf("parse GTFS: %w", err)
	}
	fmt.Printf("Loaded %d stops, %d trips, %d routes\n", len(feed.Stops), len(feed.Trips), len(feed.Routes))

	// 4. Filter feed.
	fmt.Println("Filtering feed...")
	filtered, err := gtfs.FilterFeed(feed, opts.routes, "")
	if err != nil {
		return nil, fmt.Errorf("filter feed: %w", err)
	}
	fmt.Printf("After filtering: %d stops, %d trips\n", len(filtered.Stops), len(filtered.Trips))

	// 5. Build timetable.
	fmt.Println("Building RAPTOR timetable...")
	tt := raptor.BuildTimetable(filtered)
	fmt.Printf("Timetable: %d stops, %d patterns\n", tt.NStops, tt.NPatterns)

	// 6. Generate grid.
	fmt.Println("Generating grid points...")
	points := grid.Generate(opts.bboxSW, opts.bboxNE, config.GridSpacingM, opts.boundaryPath)
	fmt.Printf("Grid: %d points\n", len(points))

	// 7. Extract stop coordinates from feed using timetable.StopIDs.
	stopLats := make([]float64, tt.NStops)
	stopLons := make([]float64, tt.NStops)
	stopMap := make(map[string]*gtfs.Stop, len(filtered.Stops))
	for i := range filtered.Stops {
		stopMap[filtered.Stops[i].StopID] = &filtered.Stops[i]
	}
	for i, sid := range tt.StopIDs {
		if s, ok := stopMap[sid]; ok {
			stopLats[i] = s.StopLat
			stopLons[i] = s.StopLon
		}
	}

	// 8. Compute OD matrix (check cache first).
	var metrics *scoring.ODMetrics
	cacheDir := opts.outputDir

	if !opts.noCache && feedHash != "" {
		fmt.Println("Checking matrix cache...")
		cached, err := raptor.LoadCache(cacheDir, feedHash, len(points))
		if err == nil && cached != nil {
			fmt.Println("Using cached OD metrics.")
			metrics = cached
		}
	}

	if metrics == nil {
		fmt.Println("Computing OD matrix...")
		progressFn := func(completed, total int) {
			if total > 0 {
				pct := float64(completed) / float64(total) * 100
				fmt.Printf("\r  Progress: %d/%d (%.1f%%)", completed, total, pct)
			}
		}
		metrics = raptor.ComputeMatrix(tt, points, stopLats, stopLons, config.DepartureTimes(), opts.workers, progressFn)
		fmt.Println() // newline after progress

		// Save to cache.
		if feedHash != "" {
			if err := os.MkdirAll(cacheDir, 0755); err == nil {
				if err := raptor.SaveCache(cacheDir, feedHash, len(points), metrics); err != nil {
					fmt.Fprintf(os.Stderr, "Warning: could not save cache: %v\n", err)
				} else {
					fmt.Println("Matrix cached.")
				}
			}
		}
	}

	// 9. Compute route LOS.
	fmt.Println("Computing route LOS (TCQSM)...")
	routeLOS := scoring.ComputeRouteLOS(filtered)
	systemLOS := scoring.ComputeSystemLOSSummary(routeLOS)
	fmt.Printf("System LOS: %d routes, median headway %.1f min, best grade %s\n",
		systemLOS.NRoutes, systemLOS.MedianSystemHeadway, systemLOS.BestGrade)

	// 10. Compute PTAL.
	fmt.Println("Computing PTAL...")
	ptal := scoring.ComputePTAL(points, filtered)
	if len(ptal.Grades) > 0 {
		fmt.Printf("PTAL grades range: %s to %s\n", ptal.Grades[0], ptal.Grades[len(ptal.Grades)-1])
	}

	// 11. Compute TQI.
	fmt.Println("Computing TQI...")
	tqi := scoring.ComputeTQI(metrics)

	// 11b. Compute detailed analysis for frontend dashboard.
	fmt.Println("Computing detailed analysis...")
	detailed := scoring.ComputeDetailedAnalysis(points, metrics, tqi, ptal, stopLats, stopLons)

	// 12. Print results to stdout.
	fmt.Println()
	fmt.Println("════════════════════════════════════")
	fmt.Printf("  City:            %s\n", opts.cityName)
	fmt.Printf("  TQI Score:       %.2f / 100\n", tqi.TQI)
	fmt.Printf("  Coverage Score:  %.2f\n", tqi.CoverageScore)
	fmt.Printf("  Speed Score:     %.2f\n", tqi.SpeedScore)
	fmt.Printf("  Reliability CV:  %.4f\n", tqi.ReliabilityCV)
	fmt.Printf("  Category:        %s\n", config.WalkScoreCategory(tqi.TQI))
	fmt.Printf("  Grid Points:     %d\n", len(points))
	fmt.Printf("  Stops:           %d\n", tt.NStops)
	fmt.Println("════════════════════════════════════")
	fmt.Println()

	for _, r := range routeLOS {
		fmt.Printf("  Route %-6s  LOS %s  (median headway %.0f min)\n",
			r.RouteName, r.LOSGrade, r.MedianHeadway)
	}

	// 12b. Compute isochrones from stop centroid.
	fmt.Println("Computing isochrones...")
	var isoResults []isochrone.Result
	centroidLat, centroidLon := 0.0, 0.0
	for _, s := range filtered.Stops {
		centroidLat += s.StopLat
		centroidLon += s.StopLon
	}
	if len(filtered.Stops) > 0 {
		centroidLat /= float64(len(filtered.Stops))
		centroidLon /= float64(len(filtered.Stops))
	}
	for _, depMin := range []int{480, 720} { // 08:00 and 12:00
		iso, err := isochrone.Compute(tt, centroidLat, centroidLon, depMin, points, stopLats, stopLons, float64(config.GridSpacingM))
		if err != nil {
			fmt.Fprintf(os.Stderr, "Warning: isochrone at %d min: %v\n", depMin, err)
			continue
		}
		isoResults = append(isoResults, *iso)
	}
	fmt.Printf("Computed %d isochrones\n", len(isoResults))

	// 13. Write JSON results to output-dir/tqi_results.json.
	if err := os.MkdirAll(opts.outputDir, 0755); err != nil {
		return nil, fmt.Errorf("create output dir: %w", err)
	}

	// Compute per-origin grid scores (mean reachability * 100 for each origin).
	gridScores := make([]api.GridScorePoint, len(points))
	for i, pt := range points {
		var reachSum float64
		var reachCount int
		if i < len(metrics.Reachability) {
			for j := 0; j < len(metrics.Reachability[i]); j++ {
				if i == j {
					continue
				}
				reachSum += metrics.Reachability[i][j]
				reachCount++
			}
		}
		var score float64
		if reachCount > 0 {
			score = (reachSum / float64(reachCount)) * 100.0
		}
		gridScores[i] = api.GridScorePoint{
			Lat:   pt.Lat,
			Lon:   pt.Lon,
			Score: score,
		}
	}

	// 12c. Equity overlay (conditional — requires census data files).
	var eqResult *equity.Result
	boundaryPath := filepath.Join("data", "census", "da_boundaries.geojson")
	incomePath := filepath.Join("data", "census", "da_income.json")
	if _, err := os.Stat(boundaryPath); err == nil {
		if _, err := os.Stat(incomePath); err == nil {
			fmt.Println("Computing equity overlay...")
			gridScoreValues := make([]float64, len(gridScores))
			for i, gs := range gridScores {
				gridScoreValues[i] = gs.Score
			}
			eqResult, err = equity.Compute(boundaryPath, incomePath, points, gridScoreValues)
			if err != nil {
				log.Printf("equity computation: %v", err)
				eqResult = nil
			} else {
				fmt.Printf("Equity overlay: correlation r=%.3f\n", eqResult.Correlation)
			}
		}
	}

	// Neighbourhood-level scoring with population weighting.
	nbPath := filepath.Join("data", "neighbourhoods.geojson")
	var nbScores []neighbourhood.Score
	var nbBoundaries json.RawMessage
	if _, err := os.Stat(nbPath); err == nil {
		fmt.Println("Computing neighbourhood scores...")
		nbs, rawGeoJSON, err := neighbourhood.LoadBoundaries(nbPath)
		if err != nil {
			log.Printf("neighbourhood boundaries: %v", err)
		} else {
			nbBoundaries = rawGeoJSON
			assignments := neighbourhood.AssignPoints(nbs, points)

			// Compute per-origin coverage, speed, and TQI using the real formula.
			n := len(points)
			gridTQIVals := make([]float64, n)
			gridCov := make([]float64, n)
			gridSpd := make([]float64, n)
			for i := 0; i < n; i++ {
				if i >= len(metrics.Reachability) {
					continue
				}
				var reachSum float64
				var reachCount int
				var tsrSum float64
				var tsrCount int
				for j := 0; j < len(metrics.Reachability[i]); j++ {
					if i == j {
						continue
					}
					if !scoring.IsValidPair(metrics.DistancesKM[i][j]) {
						continue
					}
					reachSum += metrics.Reachability[i][j]
					reachCount++
					tsr := scoring.ComputeTSR(metrics.DistancesKM[i][j], metrics.MeanTravelTime[i][j])
					if tsr > 0 {
						tsrSum += tsr
						tsrCount++
					}
				}
				if reachCount > 0 {
					gridCov[i] = (reachSum / float64(reachCount)) * 100.0
				}
				if tsrCount > 0 {
					meanTSR := tsrSum / float64(tsrCount)
					gridSpd[i] = (meanTSR - config.TSRWalk) / (config.TSRCar - config.TSRWalk) * 100.0
					if gridSpd[i] < 0 {
						gridSpd[i] = 0
					}
					if gridSpd[i] > 100 {
						gridSpd[i] = 100
					}
				}
				gridTQIVals[i] = 0.5*gridCov[i] + 0.5*gridSpd[i]
			}

			var wTQI, wCov, wSpd float64
			nbScores, wTQI, wCov, wSpd = neighbourhood.ComputeScores(nbs, assignments, gridTQIVals, gridCov, gridSpd)

			// Replace uniform scores with population-weighted scores
			tqi.TQI = wTQI
			tqi.CoverageScore = wCov
			tqi.SpeedScore = wSpd
			fmt.Printf("Population-weighted TQI: %.2f (from %d neighbourhoods)\n", wTQI, len(nbScores))
		}
	}

	// Generate narrative analysis text.
	wsCategory := config.WalkScoreCategory(tqi.TQI)
	wsDesc := config.WalkScoreDescription(tqi.TQI)

	narrative := generateNarrative(opts.cityName, tqi, systemLOS, len(points), tt.NStops, wsCategory)

	results := api.PipelineResults{
		TQI:               tqi,
		Metrics:            metrics,
		RouteLOS:           routeLOS,
		SystemLOS:          systemLOS,
		PTAL:               ptal,
		GridPoints:         len(points),
		NStops:             tt.NStops,
		GridScores:         gridScores,
		Narrative:          narrative,
		WalkScoreCategory:  wsCategory,
		WalkScoreDesc:      wsDesc,
		DetailedAnalysis:   detailed,
		Isochrones:              isoResults,
		NeighbourhoodScores:     nbScores,
		NeighbourhoodBoundaries: nbBoundaries,
	}

	if eqResult != nil {
		results.Equity = eqResult
	}

	outPath := filepath.Join(opts.outputDir, "tqi_results.json")
	f, err := os.Create(outPath)
	if err != nil {
		return nil, fmt.Errorf("create results file: %w", err)
	}
	defer f.Close()

	enc := json.NewEncoder(f)
	enc.SetIndent("", "  ")
	if err := enc.Encode(results); err != nil {
		return nil, fmt.Errorf("write results JSON: %w", err)
	}
	fmt.Printf("Results written to %s\n", outPath)

	return &results, nil
}

// generateNarrative produces human-readable analysis paragraphs.
func generateNarrative(city string, tqi *scoring.TQIResult, sys *scoring.SystemLOSSummary, gridPts, nStops int, category string) []string {
	paras := []string{
		fmt.Sprintf("The Transit Quality Index for %s is %.1f out of 100, placing it in the \"%s\" category on the Walk Score transit scale.",
			strings.Title(city), tqi.TQI, category),
		fmt.Sprintf("Coverage scored %.1f — this measures what percentage of the city can be reached by transit from any given point. Speed scored %.1f — this captures how competitive transit travel times are compared to driving.",
			tqi.CoverageScore, tqi.SpeedScore),
		fmt.Sprintf("The analysis evaluated %d grid points across the city with access to %d transit stops. Reliability (coefficient of variation) was %.4f, indicating %s in travel times across different departure windows.",
			gridPts, nStops, tqi.ReliabilityCV, reliabilityDesc(tqi.ReliabilityCV)),
	}
	if sys != nil {
		paras = append(paras, fmt.Sprintf("Across %d routes, the median system headway is %.0f minutes. The best route-level grade is %s and the worst is %s. %.0f%% of routes scored LOS D or worse.",
			sys.NRoutes, sys.MedianSystemHeadway, sys.BestGrade, sys.WorstGrade, sys.PctLOSDOrWorse))
	}
	return paras
}

func reliabilityDesc(cv float64) string {
	switch {
	case cv < 0.1:
		return "very consistent service"
	case cv < 0.2:
		return "moderate consistency"
	case cv < 0.3:
		return "some variability"
	default:
		return "significant variability"
	}
}
