import { TileLayer } from 'react-leaflet'

// OpenStreetMap standard tiles need no API key. They're desaturated via the
// `basemap-muted` class in globals.css so data overlays stay prominent.
export default function BaseMap() {
  return (
    <TileLayer
      className="basemap-muted"
      attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
      url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
      maxZoom={19}
    />
  )
}
