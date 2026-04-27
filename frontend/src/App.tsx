import { useState } from "react"
import ChatPanel from "./components/ChatPanel"
import MapPanel from "./components/MapPanel"
import "./App.css"

function App() {
  const [markers, setMarkers] = useState<any[]>([])
  const [center, setCenter] = useState<[number, number]>([43.45, -80.49]) // Kitchener

  return (
    <div className="app">
      <div className="chat-panel">
        <ChatPanel onMapUpdate={setMarkers} onCenterChange={setCenter} />
      </div>
      <div className="map-panel">
        <MapPanel markers={markers} center={center} />
      </div>
    </div>
  )
}

export default App
