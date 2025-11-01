import { MapPin, Hotel, Coffee, UtensilsCrossed, Camera, Mountain, Ship, Plane, ShoppingBag, Museum, TreePine, Waves } from 'lucide-react'

const ICON_OPTIONS = [
  { type: 'location', icon: MapPin, label: 'Location' },
  { type: 'hotel', icon: Hotel, label: 'Hotel' },
  { type: 'restaurant', icon: UtensilsCrossed, label: 'Restaurant' },
  { type: 'coffee', icon: Coffee, label: 'Café' },
  { type: 'camera', icon: Camera, label: 'Photo Spot' },
  { type: 'mountain', icon: Mountain, label: 'Mountain' },
  { type: 'beach', icon: Waves, label: 'Beach' },
  { type: 'ship', icon: Ship, label: 'Harbor' },
  { type: 'plane', icon: Plane, label: 'Airport' },
  { type: 'shopping', icon: ShoppingBag, label: 'Shopping' },
  { type: 'museum', icon: Museum, label: 'Museum' },
  { type: 'nature', icon: TreePine, label: 'Nature' },
]

export default function IconSelector({ value = 'location', onChange, label = 'Icon Type' }) {
  const handleIconChange = (iconType) => {
    if (onChange) {
      onChange(iconType)
    }
  }

  return (
    <div className="space-y-2">
      {label && <label className="block text-sm font-medium text-gray-700">{label}</label>}

      <div className="grid grid-cols-4 gap-2">
        {ICON_OPTIONS.map(({ type, icon: Icon, label: iconLabel }) => (
          <button
            key={type}
            type="button"
            onClick={() => handleIconChange(type)}
            className={`
              flex flex-col items-center gap-1 p-3 rounded-lg border-2 transition-all
              ${value === type
                ? 'border-indigo-500 bg-indigo-50 text-indigo-700'
                : 'border-gray-200 hover:border-gray-400 text-gray-600 hover:bg-gray-50'}
            `}
            title={iconLabel}
          >
            <Icon className="w-6 h-6" />
            <span className="text-xs font-medium">{iconLabel}</span>
          </button>
        ))}
      </div>
    </div>
  )
}
