interface ChatPanelProps {
  onMapUpdate: (markers: any[]) => void
  onCenterChange: (center: [number, number]) => void
}

export default function ChatPanel(_props: ChatPanelProps) {
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div style={{ padding: "16px", borderBottom: "1px solid #e0e0e0" }}>
        <h2>GeoAgent</h2>
      </div>
      <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: "#999" }}>
        Chat panel — coming in Step 5.4
      </div>
    </div>
  )
}
