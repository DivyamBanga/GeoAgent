export interface Scores {
  [key: string]: number
}

interface ScoreCardProps {
  scores: Scores
}

const LABEL_MAP: Record<string, string> = {
  get_population: "demographics",
  find_competitors: "competition",
  get_median_income: "income",
  overall: "overall",
}

function getColor(score: number): string {
  if (score >= 70) return "#4caf50"
  if (score >= 40) return "#ff9800"
  return "#f44336"
}

export default function ScoreCard({ scores }: ScoreCardProps) {
  return (
    <div style={{ display: "flex", gap: "12px", padding: "12px 0", flexWrap: "wrap" }}>
      {Object.entries(scores).map(([key, value]) => (
        <div key={key} style={{
          textAlign: "center",
          padding: "8px 16px",
          borderRadius: "8px",
          border: `2px solid ${getColor(value)}`,
          minWidth: "80px",
        }}>
          <div style={{ fontSize: "1.5em", fontWeight: "bold", color: getColor(value) }}>
            {value}
          </div>
          <div style={{ fontSize: "0.8em", textTransform: "capitalize", color: "#666" }}>
            {LABEL_MAP[key] || key}
          </div>
        </div>
      ))}
    </div>
  )
}
