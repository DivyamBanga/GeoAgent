import { MapContainer, TileLayer, Marker, Popup, Circle, CircleMarker } from "react-leaflet"
import L from "leaflet"
import "leaflet/dist/leaflet.css"

// Fix Leaflet's default marker icon paths (broken by bundlers)
import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png"
import markerIcon from "leaflet/dist/images/marker-icon.png"
import markerShadow from "leaflet/dist/images/marker-shadow.png"

L.Icon.Default.mergeOptions({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
})

export interface MapMarker {
  lat: number
  lng: number
  label: string
  type: "target" | "competitor" | "complementary"
}

export interface TradeCircle {
  lat: number
  lng: number
  radiusKm: number
}

export interface TradeArea {
  lat: number
  lng: number
  population: number
  median_income: number
}

interface MapPanelProps {
  markers: MapMarker[]
  center: [number, number]
  circle: TradeCircle | null
  tradeAreas: TradeArea[]
}

function getIncomeColor(income: number): string {
  if (income >= 90000) return "#1a237e"   // dark blue — high income
  if (income >= 70000) return "#1565c0"
  if (income >= 50000) return "#42a5f5"
  if (income >= 30000) return "#90caf9"
  return "#e3f2fd"                         // light blue — low income
}

function getPopulationRadius(population: number): number {
  if (population >= 1000) return 12
  if (population >= 500) return 9
  if (population >= 200) return 6
  return 4
}

export default function MapPanel({ markers, center, circle, tradeAreas }: MapPanelProps) {
  return (
    <MapContainer center={center} zoom={14} style={{ height: "100%", width: "100%" }}>
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {/* Trade area circle — search radius overlay */}
      {circle && (
        <Circle
          center={[circle.lat, circle.lng]}
          radius={circle.radiusKm * 1000}
          pathOptions={{
            color: "#1976d2",
            fillColor: "#1976d2",
            fillOpacity: 0.08,
            weight: 2,
            dashArray: "6 4",
          }}
        />
      )}

      {/* Census area markers — colored by income, sized by population */}
      {tradeAreas.map((area, i) => (
        <CircleMarker
          key={`area-${i}`}
          center={[area.lat, area.lng]}
          radius={getPopulationRadius(area.population)}
          pathOptions={{
            color: getIncomeColor(area.median_income),
            fillColor: getIncomeColor(area.median_income),
            fillOpacity: 0.6,
            weight: 1,
          }}
        >
          <Popup>
            Pop: {area.population.toLocaleString()}<br />
            Income: ${area.median_income.toLocaleString()}
          </Popup>
        </CircleMarker>
      ))}

      {/* Business markers — competitors, etc. */}
      {markers.map((m, i) => (
        <Marker key={`marker-${i}`} position={[m.lat, m.lng]}>
          <Popup>{m.label} ({m.type})</Popup>
        </Marker>
      ))}
    </MapContainer>
  )
}
