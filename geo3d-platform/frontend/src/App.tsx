import React, { useEffect, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import './index.css'
import { useAppStore } from './stores'

import Navbar from './components/layout/Navbar'
import AIAssistantChat from './components/panels/AIAssistantChat'

import ProjectsCatalogPage from './pages/ProjectsCatalogPage'
import PhotogrammetryPage from './pages/PhotogrammetryPage'
import CesiumViewerPage from './pages/CesiumViewerPage'
import PotreeViewerPage from './pages/PotreeViewerPage'
import DualViewerPage from './pages/DualViewerPage'
import AnalysisPage from './pages/AnalysisPage'

export default function App() {
  const { loadProjects, checkBackend } = useAppStore()

  useEffect(() => {
    checkBackend()
    loadProjects()
  }, [])

  return (
    <BrowserRouter>
      <div
        style={{
          width: '100vw',
          height: '100vh',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          background: '#090d16',
        }}
      >
        {/* Sleek Top Navigation Header */}
        <Navbar />

        {/* Dedicated Route Body */}
        <main style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
          <Suspense
            fallback={
              <div
                style={{
                  height: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: '#090d16',
                  color: '#38bdf8',
                  fontSize: 14,
                }}
              >
                Initializing 3D Geospatial Engine…
              </div>
            }
          >
            <Routes>
              <Route path="/" element={<ProjectsCatalogPage />} />
              <Route path="/projects" element={<ProjectsCatalogPage />} />
              <Route path="/photogrammetry" element={<PhotogrammetryPage />} />
              <Route path="/viewer" element={<CesiumViewerPage />} />
              <Route path="/globe" element={<CesiumViewerPage />} />
              <Route path="/potree" element={<PotreeViewerPage />} />
              <Route path="/dual" element={<DualViewerPage />} />
              <Route path="/analysis" element={<AnalysisPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
        </main>

        {/* Global AI Copilot Assistant Drawer */}
        <AIAssistantChat />
      </div>
    </BrowserRouter>
  )
}
