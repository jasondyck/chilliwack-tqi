package gtfs

import (
	"encoding/csv"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
)

// ParseTime converts "HH:MM:SS" to minutes since midnight.
// Handles hours >= 24 (common in GTFS for trips past midnight).
func ParseTime(s string) int {
	parts := strings.Split(s, ":")
	if len(parts) != 3 {
		return 0
	}
	h, _ := strconv.Atoi(parts[0])
	m, _ := strconv.Atoi(parts[1])
	return h*60 + m
}

// LoadGTFS reads all CSV files from a GTFS directory and returns a Feed.
func LoadGTFS(dir string) (*Feed, error) {
	feed := &Feed{}

	// Required files
	stops, err := readCSV(filepath.Join(dir, "stops.txt"))
	if err != nil {
		return nil, fmt.Errorf("reading stops.txt: %w", err)
	}
	feed.Stops = parseStops(stops)

	routes, err := readCSV(filepath.Join(dir, "routes.txt"))
	if err != nil {
		return nil, fmt.Errorf("reading routes.txt: %w", err)
	}
	feed.Routes = parseRoutes(routes)

	trips, err := readCSV(filepath.Join(dir, "trips.txt"))
	if err != nil {
		return nil, fmt.Errorf("reading trips.txt: %w", err)
	}
	feed.Trips = parseTrips(trips)

	stopTimes, err := readCSV(filepath.Join(dir, "stop_times.txt"))
	if err != nil {
		return nil, fmt.Errorf("reading stop_times.txt: %w", err)
	}
	feed.StopTimes = parseStopTimes(stopTimes)

	// Optional files
	calRows, err := readCSV(filepath.Join(dir, "calendar.txt"))
	if err == nil {
		feed.Calendar = parseCalendar(calRows)
	} else if !errors.Is(err, os.ErrNotExist) {
		return nil, fmt.Errorf("reading calendar.txt: %w", err)
	}

	calDateRows, err := readCSV(filepath.Join(dir, "calendar_dates.txt"))
	if err == nil {
		feed.CalendarDates = parseCalendarDates(calDateRows)
	} else if !errors.Is(err, os.ErrNotExist) {
		return nil, fmt.Errorf("reading calendar_dates.txt: %w", err)
	}

	shapeRows, err := readCSV(filepath.Join(dir, "shapes.txt"))
	if err == nil {
		feed.Shapes = parseShapes(shapeRows)
	} else if !errors.Is(err, os.ErrNotExist) {
		return nil, fmt.Errorf("reading shapes.txt: %w", err)
	}

	return feed, nil
}

// readCSV reads a CSV file and returns rows as maps keyed by header names.
func readCSV(path string) ([]map[string]string, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	r := csv.NewReader(f)
	r.TrimLeadingSpace = true

	records, err := r.ReadAll()
	if err != nil {
		return nil, err
	}
	if len(records) < 1 {
		return nil, nil
	}

	headers := records[0]
	// Strip BOM from first header if present
	if len(headers) > 0 {
		headers[0] = strings.TrimPrefix(headers[0], "\xef\xbb\xbf")
	}

	var rows []map[string]string
	for _, record := range records[1:] {
		row := make(map[string]string, len(headers))
		for i, h := range headers {
			if i < len(record) {
				row[h] = record[i]
			}
		}
		rows = append(rows, row)
	}
	return rows, nil
}

func parseStops(rows []map[string]string) []Stop {
	stops := make([]Stop, 0, len(rows))
	for _, r := range rows {
		lat, _ := strconv.ParseFloat(r["stop_lat"], 64)
		lon, _ := strconv.ParseFloat(r["stop_lon"], 64)
		stops = append(stops, Stop{
			StopID:   r["stop_id"],
			StopName: r["stop_name"],
			StopLat:  lat,
			StopLon:  lon,
		})
	}
	return stops
}

func parseRoutes(rows []map[string]string) []Route {
	routes := make([]Route, 0, len(rows))
	for _, r := range rows {
		routes = append(routes, Route{
			RouteID:        r["route_id"],
			RouteShortName: r["route_short_name"],
			RouteLongName:  r["route_long_name"],
		})
	}
	return routes
}

func parseTrips(rows []map[string]string) []Trip {
	trips := make([]Trip, 0, len(rows))
	for _, r := range rows {
		trips = append(trips, Trip{
			TripID:      r["trip_id"],
			RouteID:     r["route_id"],
			ServiceID:   r["service_id"],
			ShapeID:     r["shape_id"],
			DirectionID: r["direction_id"],
		})
	}
	return trips
}

func parseStopTimes(rows []map[string]string) []StopTime {
	stopTimes := make([]StopTime, 0, len(rows))
	for _, r := range rows {
		seq, _ := strconv.Atoi(r["stop_sequence"])
		stopTimes = append(stopTimes, StopTime{
			TripID:       r["trip_id"],
			StopID:       r["stop_id"],
			ArrivalMin:   ParseTime(r["arrival_time"]),
			DepartureMin: ParseTime(r["departure_time"]),
			StopSequence: seq,
		})
	}
	return stopTimes
}

func parseCalendar(rows []map[string]string) []Calendar {
	cals := make([]Calendar, 0, len(rows))
	for _, r := range rows {
		cals = append(cals, Calendar{
			ServiceID: r["service_id"],
			Monday:    r["monday"] == "1",
			Tuesday:   r["tuesday"] == "1",
			Wednesday: r["wednesday"] == "1",
			Thursday:  r["thursday"] == "1",
			Friday:    r["friday"] == "1",
			Saturday:  r["saturday"] == "1",
			Sunday:    r["sunday"] == "1",
			StartDate: r["start_date"],
			EndDate:   r["end_date"],
		})
	}
	return cals
}

func parseCalendarDates(rows []map[string]string) []CalendarDate {
	dates := make([]CalendarDate, 0, len(rows))
	for _, r := range rows {
		et, _ := strconv.Atoi(r["exception_type"])
		dates = append(dates, CalendarDate{
			ServiceID:     r["service_id"],
			Date:          r["date"],
			ExceptionType: et,
		})
	}
	return dates
}

func parseShapes(rows []map[string]string) []Shape {
	shapes := make([]Shape, 0, len(rows))
	for _, r := range rows {
		lat, _ := strconv.ParseFloat(r["shape_pt_lat"], 64)
		lon, _ := strconv.ParseFloat(r["shape_pt_lon"], 64)
		seq, _ := strconv.Atoi(r["shape_pt_sequence"])
		shapes = append(shapes, Shape{
			ShapeID:    r["shape_id"],
			ShapePtLat: lat,
			ShapePtLon: lon,
			ShapePtSeq: seq,
		})
	}
	return shapes
}
