import { useState } from 'react'
import { Check } from 'lucide-react'

const PRESET_COLORS = [
  '#6366F1', // Indigo (default)
  '#EF4444', // Red
  '#F59E0B', // Amber
  '#10B981', // Green
  '#3B82F6', // Blue
  '#8B5CF6', // Purple
  '#EC4899', // Pink
  '#14B8A6', // Teal
  '#F97316', // Orange
  '#06B6D4', // Cyan
  '#84CC16', // Lime
  '#A855F7', // Violet
]

export default function ColorPicker({ value = '#6366F1', onChange, label = 'Color' }) {
  const [showCustom, setShowCustom] = useState(false)

  const handleColorChange = (color) => {
    if (onChange) {
      onChange(color)
    }
  }

  return (
    <div className="space-y-2">
      {label && <label className="block text-sm font-medium text-gray-700">{label}</label>}

      {/* Preset Colors */}
      <div className="grid grid-cols-6 gap-2">
        {PRESET_COLORS.map((color) => (
          <button
            key={color}
            type="button"
            onClick={() => handleColorChange(color)}
            className={`
              w-10 h-10 rounded-lg border-2 transition-all
              ${value === color ? 'border-gray-900 scale-110' : 'border-gray-200 hover:border-gray-400'}
            `}
            style={{ backgroundColor: color }}
            title={color}
          >
            {value === color && (
              <Check className="w-5 h-5 text-white mx-auto drop-shadow" />
            )}
          </button>
        ))}
      </div>

      {/* Custom Color Input */}
      <div className="flex items-center gap-2 mt-3">
        <button
          type="button"
          onClick={() => setShowCustom(!showCustom)}
          className="text-sm text-indigo-600 hover:text-indigo-700 font-medium"
        >
          {showCustom ? 'Hide' : 'Choose'} custom color
        </button>
      </div>

      {showCustom && (
        <div className="flex items-center gap-2 mt-2">
          <input
            type="color"
            value={value}
            onChange={(e) => handleColorChange(e.target.value)}
            className="w-16 h-10 rounded border border-gray-300 cursor-pointer"
          />
          <input
            type="text"
            value={value}
            onChange={(e) => handleColorChange(e.target.value)}
            placeholder="#6366F1"
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm"
            maxLength={7}
          />
        </div>
      )}

      {/* Current Color Display */}
      <div className="flex items-center gap-2 text-sm text-gray-600 mt-2">
        <span>Selected:</span>
        <div
          className="w-6 h-6 rounded border border-gray-300"
          style={{ backgroundColor: value }}
        />
        <span className="font-mono">{value}</span>
      </div>
    </div>
  )
}
