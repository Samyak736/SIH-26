import fs from 'fs'
import path from 'path'

export default function handler(req, res) {
  try {
    // Read the dataset placed inside the frontend app so Next.js can access it at runtime
    const p = path.join(process.cwd(), 'data', 'dashboard_data.json')
    const raw = fs.readFileSync(p, 'utf8')
    const data = JSON.parse(raw)
    res.status(200).json(data)
  } catch (err) {
    res.status(500).json({ error: String(err) })
  }
}
