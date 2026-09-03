import { Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { QueuePage } from './pages/QueuePage'
import { ReferralDetailPage } from './pages/ReferralDetailPage'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<QueuePage />} />
        <Route path="/referrals/:id" element={<ReferralDetailPage />} />
      </Routes>
    </Layout>
  )
}

export default App
