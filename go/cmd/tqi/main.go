// Package main provides the CLI entrypoint for the TQI tool.
package main

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"
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
			fmt.Printf("Starting TQI API server on port %d (not yet implemented)\n", port)
			return nil
		},
	}
	cmd.Flags().Int("port", 8080, "Port to listen on")
	return cmd
}

// ── run ──

func newRunCmd() *cobra.Command {
	cmd := &cobra.Command{
		Use:   "run",
		Short: "Run the full TQI analysis pipeline",
		RunE: func(cmd *cobra.Command, args []string) error {
			fmt.Println("Running TQI analysis pipeline (not yet implemented)")
			return nil
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
			fmt.Println("Downloading GTFS data (not yet implemented)")
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
			cities, _ := cmd.Flags().GetString("cities")
			fmt.Printf("Comparing cities: %s (not yet implemented)\n", cities)
			return nil
		},
	}
	cmd.Flags().String("cities", "chilliwack,victoria,kelowna", "Comma-separated list of cities to compare")
	cmd.Flags().Int("workers", 0, "Number of parallel workers (0 = auto)")
	return cmd
}
