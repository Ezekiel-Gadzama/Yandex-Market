import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Products from './pages/Products'
import Orders from './pages/Orders'
import ActivationTemplates from './pages/ActivationTemplates'
import Clients from './pages/Clients'
import MarketingEmails from './pages/MarketingEmails'
import Documentations from './pages/Documentations'
import Settings from './pages/Settings'
import Reviews from './pages/Reviews'

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/products" element={<Products />} />
          <Route path="/orders" element={<Orders />} />
          <Route path="/activation-templates" element={<ActivationTemplates />} />
          <Route path="/clients" element={<Clients />} />
          <Route path="/marketing-emails" element={<MarketingEmails />} />
          <Route path="/documentations" element={<Documentations />} />
          <Route path="/reviews" element={<Reviews />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </Layout>
    </Router>
  )
}

export default App
