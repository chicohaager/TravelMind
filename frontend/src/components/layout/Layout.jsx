import { Outlet } from 'react-router-dom'
import Navbar from './Navbar'
import Sidebar from './Sidebar'
import { useState } from 'react'

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Navbar onMenuClick={() => setSidebarOpen(!sidebarOpen)} />

      <div className="flex">
        <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />

        <main className="flex-1 p-3 sm:p-4 md:p-6 lg:ml-64 mt-16 w-full overflow-x-hidden">
          {/*
            Bis 2026-08-25 hart auf max-w-7xl (1280 px). Auf einem breiten Schirm
            (3440 px, 80 % Zoom = 4217 CSS-Pixel) benutzte die App damit
            30 % der Breite — der Rest war leer. Ab 2xl darf die Spalte
            mitwachsen; die Karten fliessen dann in mehr Spalten, statt
            dass Text laenger wird.
          */}
          <div className="max-w-7xl 2xl:max-w-[1800px] mx-auto">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
