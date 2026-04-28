import { useState } from "react"
import ChatPanel from "./components/ChatPanel"
import MapPanel from "./components/MapPanel"
import type { MapMarker, TradeArea, TradeCircle } from "./components/MapPanel"
import "./App.css"

function App() {
  const [markers, setMarkers] = useState<MapMarker[]>([])
  const [center, setCenter] = useState<[number, number]>([43.45, -80.49])
  const [circle, setCircle] = useState<TradeCircle | null>(null)
  const [tradeAreas, setTradeAreas] = useState<TradeArea[]>([])

  return (
    <div className="app">
      <div className="chat-panel">
        <ChatPanel
          onMapUpdate={setMarkers}
          onCenterChange={setCenter}
          onCircleUpdate={setCircle}
          onTradeAreasUpdate={setTradeAreas}
        />
      </div>
      <div className="map-panel">
        <MapPanel
          markers={markers}
          center={center}
          circle={circle}
          tradeAreas={tradeAreas}
        />
      </div>
    </div>
  )
}

export default App
