interface MapMarker {
  lat: number
  lng: number
  label: string
  type: "target" | "competitor" | "complementary"
}

interface MapPanelProps {
  markers: MapMarker[]
  center: [number, number]
}

export default function MapPanel(_props: MapPanelProps) {
  return (
    <div style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center", background: "#f0f0f0", color: "#999" }}>
      Map panel — coming in Step 5.3
    </div>
  )
}
