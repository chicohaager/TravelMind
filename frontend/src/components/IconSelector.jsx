import {
  MapPin,
  Hotel,
  Coffee,
  UtensilsCrossed,
  Camera,
  Mountain,
  Ship,
  Plane,
  ShoppingBag,
  // `Museum` gibt es in lucide-react 0.309 NICHT. Bis 2026-08-25 stand es
  // hier trotzdem: der Import ergab `undefined`, React warf beim Rendern
  // "Element type is invalid" — die Komponente war nicht darstellbar.
  // Aufgefallen ist es erst, als die Barrierefreiheits-Suite sie mountete;
  // benutzt wird sie (noch) nirgends. `Landmark` ist das Säulenportal.
  Landmark,
  TreePine,
  Waves,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'

// Nur Typ und Symbol; die Beschriftung kommt aus `places:iconTypes.<typ>`.
// Bis 2026-08-25 standen hier feste englische Woerter.
const ICON_OPTIONS = [
  { type: 'location', icon: MapPin },
  { type: 'hotel', icon: Hotel },
  { type: 'restaurant', icon: UtensilsCrossed },
  { type: 'coffee', icon: Coffee },
  { type: 'camera', icon: Camera },
  { type: 'mountain', icon: Mountain },
  { type: 'beach', icon: Waves },
  { type: 'ship', icon: Ship },
  { type: 'plane', icon: Plane },
  { type: 'shopping', icon: ShoppingBag },
  { type: 'museum', icon: Landmark },
  { type: 'nature', icon: TreePine },
]

export default function IconSelector({ value = 'location', onChange, label }) {
  const { t } = useTranslation()
  const beschriftung = label ?? t('places:iconType')
  const handleIconChange = (iconType) => {
    if (onChange) {
      onChange(iconType)
    }
  }

  return (
    <div className="space-y-2">
      {beschriftung && (
        <label className="block text-sm font-medium text-gray-700">{beschriftung}</label>
      )}

      <div className="grid grid-cols-4 gap-2">
        {ICON_OPTIONS.map(({ type, icon: Icon }) => (
          <button
            key={type}
            type="button"
            onClick={() => handleIconChange(type)}
            className={`
              flex flex-col items-center gap-1 p-3 rounded-lg border-2 transition-all
              ${
                value === type
                  ? 'border-primary-500 bg-primary-50 text-primary-700'
                  : 'border-gray-200 hover:border-gray-400 text-gray-600 hover:bg-gray-50'
              }
            `}
            title={t(`places:iconTypes.${type}`)}
          >
            <Icon className="w-6 h-6" />
            <span className="text-xs font-medium">{t(`places:iconTypes.${type}`)}</span>
          </button>
        ))}
      </div>
    </div>
  )
}
