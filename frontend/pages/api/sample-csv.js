import fs from 'fs'
import path from 'path'

export default function handler(req, res) {
  try {
    const samplePath = path.join(process.cwd(), '..', 'sample_reports.csv')
    const csv = fs.readFileSync(samplePath, 'utf8')
    res.status(200).setHeader('Content-Type', 'text/csv; charset=utf-8').send(csv)
  } catch (error) {
    res.status(500).json({ error: String(error) })
  }
}