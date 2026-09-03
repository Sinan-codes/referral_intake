import { Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { NotFoundPage } from './pages/NotFoundPage'
import { QueuePage } from './pages/QueuePage'
import { ReferralDetailPage } from './pages/ReferralDetailPage'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<QueuePage />} />
        <Route path="/referrals/:id" element={<ReferralDetailPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </Layout>
  )
}

export default App
