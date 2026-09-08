import dynamic from 'next/dynamic'
const SIFDashboard = dynamic(() => import('../components/SIFDashboard'), { ssr: false })

export default function Home() {
  return (
    <main style={{ padding: 24 }}>
      <SIFDashboard />
    </main>
  )
}
