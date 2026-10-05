/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        canvas: 'rgb(var(--bb-canvas) / <alpha-value>)',
        sidebar: 'rgb(var(--bb-sidebar) / <alpha-value>)',
        surface: 'rgb(var(--bb-surface) / <alpha-value>)',
        elevated: 'rgb(var(--bb-elevated) / <alpha-value>)',
        field: 'rgb(var(--bb-input) / <alpha-value>)',
        line: 'rgb(var(--bb-border) / <alpha-value>)',
        'line-strong': 'rgb(var(--bb-border-strong) / <alpha-value>)',
        ink: 'rgb(var(--bb-ink) / <alpha-value>)',
        secondary: 'rgb(var(--bb-secondary) / <alpha-value>)',
        muted: 'rgb(var(--bb-muted) / <alpha-value>)',
        accent: 'rgb(var(--bb-accent) / <alpha-value>)',
        action: 'rgb(var(--bb-action) / <alpha-value>)',
        'action-hover': 'rgb(var(--bb-action-hover) / <alpha-value>)',
        focus: 'rgb(var(--bb-focus) / <alpha-value>)',
        success: 'rgb(var(--bb-success) / <alpha-value>)',
        warning: 'rgb(var(--bb-warning) / <alpha-value>)',
        danger: 'rgb(var(--bb-danger) / <alpha-value>)',
        gold: 'rgb(var(--bb-gold) / <alpha-value>)',
      },
      fontSize: {
        'page-title': ['clamp(1.75rem, 1.5rem + .5vw, 2rem)', { lineHeight: '1.2', letterSpacing: '-.025em', fontWeight: '600' }],
        'section-title': ['1.125rem', { lineHeight: '1.5', letterSpacing: '-.01em', fontWeight: '600' }],
        'card-title': ['1rem', { lineHeight: '1.5', fontWeight: '600' }],
        body: ['.875rem', { lineHeight: '1.6' }],
        meta: ['.8125rem', { lineHeight: '1.5' }],
      },
      borderRadius: {
        control: 'var(--bb-radius-control)',
        card: 'var(--bb-radius-card)',
        panel: 'var(--bb-radius-panel)',
      },
      boxShadow: { card: 'var(--bb-shadow-card)', popover: 'var(--bb-shadow-popover)' },
      transitionDuration: { ui: 'var(--bb-duration)' },
    },
  },
  plugins: [],
}
