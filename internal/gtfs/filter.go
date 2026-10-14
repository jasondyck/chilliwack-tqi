package gtfs

import (
	"fmt"
	"sort"
	"strings"
	"time"
)

const dateLayout = "20060102"

// maxCalendarSpanDays bounds how far a single calendar.txt range is expanded
// when enumerating service dates.
const maxCalendarSpanDays = 400

// ActiveServices returns the service IDs running on date, applying
// calendar.txt weekday patterns and calendar_dates.txt exceptions.
func ActiveServices(feed *Feed, date time.Time) map[string]bool {
	ds := date.Format(dateLayout)
	active := make(map[string]bool)
	for _, cal := range feed.Calendar {
		if !calendarDayActive(cal, date.Weekday()) {
			continue
		}
		if cal.StartDate != "" && ds < cal.StartDate {
			continue
		}
		if cal.EndDate != "" && ds > cal.EndDate {
			continue
		}
		active[cal.ServiceID] = true
	}
	for _, cd := range feed.CalendarDates {
		if cd.Date != ds {
			continue
		}
		switch cd.ExceptionType {
		case 1:
			active[cd.ServiceID] = true
		case 2:
			delete(active, cd.ServiceID)
		}
	}
	return active
}

// SelectServiceDate picks a representative weekday to analyse.
//
// Every Monday–Friday covered by the feed (on or after from, when any exist)
// is grouped by its exact set of active services. The largest group is the
// "typical weekday" pattern, which naturally excludes statutory holidays and
// one-off service changes. Ties go to the pattern with more trips on routes.
// The earliest date in the winning group is returned.
func SelectServiceDate(feed *Feed, routes []string, from time.Time) (time.Time, error) {
	routeIDs := routeIDsFor(feed, routes)
	tripsPerService := make(map[string]int)
	for _, t := range feed.Trips {
		if routeIDs[t.RouteID] {
			tripsPerService[t.ServiceID]++
		}
	}

	from = truncateDay(from)
	dates := serviceDates(feed)
	var upcoming []time.Time
	for _, d := range dates {
		if !d.Before(from) {
			upcoming = append(upcoming, d)
		}
	}
	if len(upcoming) > 0 {
		dates = upcoming
	}

	type group struct {
		first time.Time
		n     int
		trips int
	}
	groups := make(map[string]*group)
	for _, d := range dates {
		if wd := d.Weekday(); wd == time.Saturday || wd == time.Sunday {
			continue
		}
		active := ActiveServices(feed, d)
		trips := 0
		ids := make([]string, 0, len(active))
		for id := range active {
			trips += tripsPerService[id]
			ids = append(ids, id)
		}
		if trips == 0 {
			continue
		}
		sort.Strings(ids)
		key := strings.Join(ids, "\x00")
		g, ok := groups[key]
		if !ok {
			g = &group{first: d, trips: trips}
			groups[key] = g
		}
		g.n++
	}

	var best *group
	for _, g := range groups {
		if best == nil || g.n > best.n ||
			(g.n == best.n && g.trips > best.trips) ||
			(g.n == best.n && g.trips == best.trips && g.first.Before(best.first)) {
			best = g
		}
	}
	if best == nil {
		return time.Time{}, fmt.Errorf("no weekday service found for routes %v", routes)
	}
	return best.first, nil
}

// serviceDates returns every distinct date the feed's calendars cover, sorted.
func serviceDates(feed *Feed) []time.Time {
	seen := make(map[string]time.Time)
	add := func(d time.Time) { seen[d.Format(dateLayout)] = d }
	for _, cal := range feed.Calendar {
		start, err1 := time.Parse(dateLayout, cal.StartDate)
		end, err2 := time.Parse(dateLayout, cal.EndDate)
		if err1 != nil || err2 != nil {
			continue
		}
		for i := 0; i <= maxCalendarSpanDays && !start.AddDate(0, 0, i).After(end); i++ {
			add(start.AddDate(0, 0, i))
		}
	}
	for _, cd := range feed.CalendarDates {
		if cd.ExceptionType != 1 {
			continue
		}
		if d, err := time.Parse(dateLayout, cd.Date); err == nil {
			add(d)
		}
	}
	out := make([]time.Time, 0, len(seen))
	for _, d := range seen {
		out = append(out, d)
	}
	sort.Slice(out, func(i, j int) bool { return out[i].Before(out[j]) })
	return out
}

func truncateDay(t time.Time) time.Time {
	y, m, d := t.Date()
	return time.Date(y, m, d, 0, 0, 0, 0, time.UTC)
}

func routeIDsFor(feed *Feed, routes []string) map[string]bool {
	want := make(map[string]bool, len(routes))
	for _, r := range routes {
		want[r] = true
	}
	ids := make(map[string]bool)
	for _, r := range feed.Routes {
		if want[r.RouteShortName] {
			ids[r.RouteID] = true
		}
	}
	return ids
}

// FilterFeed filters a feed to the given routes and the services running on date.
func FilterFeed(feed *Feed, routes []string, date time.Time) (*Feed, error) {
	activeServices := ActiveServices(feed, date)

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

// calendarDayActive reports whether a calendar entry runs on the given weekday.
func calendarDayActive(cal Calendar, wd time.Weekday) bool {
	return [...]bool{
		time.Sunday:    cal.Sunday,
		time.Monday:    cal.Monday,
		time.Tuesday:   cal.Tuesday,
		time.Wednesday: cal.Wednesday,
		time.Thursday:  cal.Thursday,
		time.Friday:    cal.Friday,
		time.Saturday:  cal.Saturday,
	}[wd]
}
