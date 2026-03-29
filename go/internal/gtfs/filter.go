package gtfs

import (
	"strings"
	"time"
)

var weekdays = []string{"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}

// FindBestWeekday scans the calendar for the weekday with the most trips.
// Returns the day name (lowercase) and a reference date for that day.
func FindBestWeekday(feed *Feed) (string, time.Time) {
	// Count trips per service
	tripCount := make(map[string]int)
	for _, t := range feed.Trips {
		tripCount[t.ServiceID]++
	}

	// For each day, sum trips from all services active that day
	bestDay := ""
	bestCount := 0
	for _, day := range weekdays {
		count := 0
		for _, cal := range feed.Calendar {
			if calendarDayActive(cal, day) {
				count += tripCount[cal.ServiceID]
			}
		}
		if count > bestCount {
			bestCount = count
			bestDay = day
		}
	}

	if bestDay == "" {
		bestDay = "monday"
	}

	// Find a reference date for this day. Use the first calendar entry's
	// start date and advance to the target weekday.
	refDate := findReferenceDate(feed, bestDay)

	return bestDay, refDate
}

// findReferenceDate returns a date within the calendar range that falls on
// the given weekday.
func findReferenceDate(feed *Feed, day string) time.Time {
	targetWd := dayToWeekday(day)

	if len(feed.Calendar) > 0 {
		start, err := time.Parse("20060102", feed.Calendar[0].StartDate)
		if err == nil {
			// Advance to the target weekday
			for i := 0; i < 7; i++ {
				d := start.AddDate(0, 0, i)
				if d.Weekday() == targetWd {
					return d
				}
			}
		}
	}
	// Fallback: use next occurrence from today
	now := time.Now()
	for i := 0; i < 7; i++ {
		d := now.AddDate(0, 0, i)
		if d.Weekday() == targetWd {
			return d
		}
	}
	return now
}

func dayToWeekday(day string) time.Weekday {
	switch strings.ToLower(day) {
	case "monday":
		return time.Monday
	case "tuesday":
		return time.Tuesday
	case "wednesday":
		return time.Wednesday
	case "thursday":
		return time.Thursday
	case "friday":
		return time.Friday
	case "saturday":
		return time.Saturday
	case "sunday":
		return time.Sunday
	}
	return time.Monday
}

// FilterFeed filters a feed to only the given routes and the target day's services.
func FilterFeed(feed *Feed, routes []string, targetDay string) (*Feed, error) {
	// Resolve active services for the target day
	activeServices := make(map[string]bool)
	for _, cal := range feed.Calendar {
		if calendarDayActive(cal, targetDay) {
			activeServices[cal.ServiceID] = true
		}
	}

	// TODO: handle calendar_dates exceptions if needed in the future

	// Filter routes by short name
	wantRoutes := make(map[string]bool)
	for _, r := range routes {
		wantRoutes[r] = true
	}

	var filteredRoutes []Route
	routeIDs := make(map[string]bool)
	for _, r := range feed.Routes {
		if wantRoutes[r.RouteShortName] {
			filteredRoutes = append(filteredRoutes, r)
			routeIDs[r.RouteID] = true
		}
	}

	// Filter trips by route + service
	var filteredTrips []Trip
	tripIDs := make(map[string]bool)
	for _, t := range feed.Trips {
		if routeIDs[t.RouteID] && activeServices[t.ServiceID] {
			filteredTrips = append(filteredTrips, t)
			tripIDs[t.TripID] = true
		}
	}

	// Filter stop_times by trip
	var filteredStopTimes []StopTime
	usedStopIDs := make(map[string]bool)
	for _, st := range feed.StopTimes {
		if tripIDs[st.TripID] {
			filteredStopTimes = append(filteredStopTimes, st)
			usedStopIDs[st.StopID] = true
		}
	}

	// Filter stops to only those used
	var filteredStops []Stop
	for _, s := range feed.Stops {
		if usedStopIDs[s.StopID] {
			filteredStops = append(filteredStops, s)
		}
	}

	return &Feed{
		Stops:         filteredStops,
		StopTimes:     filteredStopTimes,
		Trips:         filteredTrips,
		Routes:        filteredRoutes,
		Calendar:      feed.Calendar,
		CalendarDates: feed.CalendarDates,
		Shapes:        feed.Shapes,
	}, nil
}

// calendarDayActive checks if a calendar entry is active on the given day.
func calendarDayActive(cal Calendar, day string) bool {
	switch strings.ToLower(day) {
	case "monday":
		return cal.Monday
	case "tuesday":
		return cal.Tuesday
	case "wednesday":
		return cal.Wednesday
	case "thursday":
		return cal.Thursday
	case "friday":
		return cal.Friday
	case "saturday":
		return cal.Saturday
	case "sunday":
		return cal.Sunday
	}
	return false
}
