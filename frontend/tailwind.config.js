export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        'bg-base': '#0C0E12',
        'bg-surface': '#13161C',
        'bg-raised': '#1A1E27',
        'bg-hover': '#1F2430',
        'bg-active': '#252A38',

        border: '#252A38',
        'border-strong': '#2E3447',

        'text-primary': '#E8EAF0',
        'text-secondary': '#7C8399',
        'text-muted': '#4A5168',

        'accent-cyan': '#22D3EE',
        'accent-cyan-dim': '#164E63',
        'accent-cyan-text': '#67E8F9',

        'status-success': '#10B981',
        'status-success-bg': '#052E16',
        'status-warning': '#F59E0B',
        'status-warning-bg': '#2D1B00',
        'status-error': '#EF4444',
        'status-error-bg': '#2D0A0A',

        'confidence-high': '#10B981',
        'confidence-medium': '#F59E0B',
        'confidence-low': '#EF4444',
      },
      fontFamily: {
        sans: ['"IBM Plex Sans"', 'system-ui', 'sans-serif'],
        mono: ['"DM Mono"', 'ui-monospace', 'monospace'],
      },
      spacing: {
        4: '4px',
        8: '8px',
        12: '12px',
        16: '16px',
        20: '20px',
        24: '24px',
        32: '32px',
        40: '40px',
        48: '48px',
      },
    },
  },
  plugins: [],
}
