import { Link, useLocation } from 'react-router-dom'
import { Home, Map, Sparkles, BookOpen, X, DollarSign, ChevronDown, ChevronRight, Mic } from 'lucide-react'
import { clsx } from 'clsx'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

export default function Sidebar({ open, onClose }) {
  const location = useLocation()
  const { t } = useTranslation()
  const [openMenus, setOpenMenus] = useState({})

  const navigation = [
    { name: t('nav:home'), href: '/', icon: Home },
    {
      name: t('nav:trips'),
      icon: Map,
      children: [
        { name: t('trips:title'), href: '/trips' },
        { name: t('nav:ai'), href: '/ai', icon: Sparkles },
      ]
    },
    { name: t('budget:title'), href: '/budget', icon: DollarSign },
    { name: t('nav:diary'), href: '/diary', icon: BookOpen },
    { name: 'Transcription', href: '/transcribe', icon: Mic },
  ]

  const toggleMenu = (itemName) => {
    setOpenMenus(prev => ({
      ...prev,
      [itemName]: !prev[itemName]
    }))
  }

  const isItemActive = (item) => {
    if (item.href) {
      return location.pathname === item.href
    }
    if (item.children) {
      return item.children.some(child => location.pathname === child.href)
    }
    return false
  }

  return (
    <>
      {/* Mobile overlay */}
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <aside
        className={clsx(
          'fixed top-16 left-0 z-40 w-64 h-[calc(100vh-4rem)] bg-white dark:bg-gray-800 shadow-lg transition-transform duration-300 overflow-y-auto',
          'lg:translate-x-0',
          open ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        {/* Close button (mobile) */}
        <div className="lg:hidden absolute top-4 right-4">
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="p-4 space-y-1 mt-12 lg:mt-4">
          {navigation.map((item) => {
            const Icon = item.icon
            const hasChildren = item.children && item.children.length > 0
            const isMenuOpen = openMenus[item.name]
            const isActive = isItemActive(item)

            if (hasChildren) {
              return (
                <div key={item.name}>
                  {/* Parent menu item */}
                  <button
                    onClick={() => toggleMenu(item.name)}
                    className={clsx(
                      'w-full flex items-center justify-between gap-3 px-4 py-3 rounded-lg transition-all duration-200',
                      isActive
                        ? 'bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-400'
                        : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                    )}
                  >
                    <div className="flex items-center gap-3">
                      <Icon className="w-5 h-5" />
                      <span className="font-medium">{item.name}</span>
                    </div>
                    {isMenuOpen ? (
                      <ChevronDown className="w-4 h-4" />
                    ) : (
                      <ChevronRight className="w-4 h-4" />
                    )}
                  </button>

                  {/* Submenu */}
                  {isMenuOpen && (
                    <div className="ml-4 mt-1 space-y-1 border-l-2 border-gray-200 dark:border-gray-700">
                      {item.children.map((child) => {
                        const childIsActive = location.pathname === child.href
                        const ChildIcon = child.icon

                        return (
                          <Link
                            key={child.name}
                            to={child.href}
                            onClick={onClose}
                            className={clsx(
                              'flex items-center gap-3 px-4 py-2 rounded-lg transition-all duration-200 ml-2',
                              childIsActive
                                ? 'bg-primary-500 text-white shadow-md'
                                : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
                            )}
                          >
                            {ChildIcon && <ChildIcon className="w-4 h-4" />}
                            <span className="text-sm font-medium">{child.name}</span>
                          </Link>
                        )
                      })}
                    </div>
                  )}
                </div>
              )
            }

            // Regular menu item without children
            return (
              <Link
                key={item.name}
                to={item.href}
                onClick={onClose}
                className={clsx(
                  'flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200',
                  isActive
                    ? 'bg-primary-500 text-white shadow-md'
                    : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                )}
              >
                <Icon className="w-5 h-5" />
                <span className="font-medium">{item.name}</span>
              </Link>
            )
          })}
        </nav>

        {/* Footer Info */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-200 dark:border-gray-700">
          <div className="text-sm text-gray-500 dark:text-gray-400 text-center">
            <p className="font-medium">TravelMind v1.0</p>
          </div>
        </div>
      </aside>
    </>
  )
}
