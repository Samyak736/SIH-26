import dynamic from 'next/dynamic'

// Use the local frontend component that fetches `/api/data`.
const SIFDashboard = dynamic(() => import('../components/SIFDashboardFixed'), { ssr: false })

export default function Home() {
  return (
    <main style={{ padding: 24 }}>
      <SIFDashboard />
    </main>
  )
}
