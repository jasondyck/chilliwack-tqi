package gtfs

// Feed holds all parsed GTFS data.
type Feed struct {
	Stops         []Stop
	StopTimes     []StopTime
	Trips         []Trip
	Routes        []Route
	Calendar      []Calendar
	CalendarDates []CalendarDate
	Shapes        []Shape
}

// Stop represents a GTFS stop.
type Stop struct {
	StopID   string
	StopName string
	StopLat  float64
	StopLon  float64
}

// StopTime represents a scheduled stop within a trip.
type StopTime struct {
	TripID       string
	StopID       string
	ArrivalMin   int
	DepartureMin int
	StopSequence int
}

// Trip represents a GTFS trip.
type Trip struct {
	TripID      string
	RouteID     string
	ServiceID   string
	ShapeID     string
	DirectionID string
}

// Route represents a GTFS route.
type Route struct {
	RouteID        string
	RouteShortName string
	RouteLongName  string
}

// Calendar represents a GTFS calendar entry.
type Calendar struct {
	ServiceID string
	Monday    bool
	Tuesday   bool
	Wednesday bool
	Thursday  bool
	Friday    bool
	Saturday  bool
	Sunday    bool
	StartDate string
	EndDate   string
}

// CalendarDate represents a GTFS calendar date exception.
type CalendarDate struct {
	ServiceID     string
	Date          string
	ExceptionType int
}

// Shape represents a single point in a GTFS shape.
type Shape struct {
	ShapeID    string
	ShapePtLat float64
	ShapePtLon float64
	ShapePtSeq int
}
