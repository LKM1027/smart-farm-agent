/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        /* ── Soft Eco Light palette ── */
        'eco': {
          'bg':       '#fafaf9',   /* stone-50  — 전체 배경 */
          'surface':  '#ffffff',   /* white     — 카드 */
          'border':   '#d1fae5',   /* emerald-100 */
          'muted':    '#e7f5ef',   /* emerald-50/80 */
          'text':     '#1e293b',   /* slate-800 — 기본 텍스트 */
          'dim':      '#64748b',   /* slate-500 — 보조 텍스트 */
          'hint':     '#94a3b8',   /* slate-400 — 힌트/placeholder */
          'primary':  '#059669',   /* emerald-600 — 브랜딩 컬러 */
          'primary-l':'#d1fae5',   /* emerald-100 */
          'primary-d':'#047857',   /* emerald-700 */
          'accent':   '#10b981',   /* emerald-500 */
          'warn':     '#d97706',   /* amber-600 */
          'warn-l':   '#fef3c7',   /* amber-100 */
          'danger':   '#dc2626',   /* red-600 */
          'danger-l': '#fee2e2',   /* red-100 */
          'info':     '#0284c7',   /* sky-600 */
          'info-l':   '#e0f2fe',   /* sky-100 */
          'forest':   '#064e3b',   /* emerald-900 — 테이블 헤더 */
          'forest-t': '#ecfdf5',   /* emerald-50  — 테이블 헤더 텍스트 */
        }
      },
      boxShadow: {
        'eco-card':  '0 4px 25px rgba(16,185,129,0.05)',
        'eco-active':'0 0 0 2px #10b981, 0 0 15px rgba(16,185,129,0.3)',
        'eco-btn':   '0 4px 14px rgba(5,150,105,0.25)',
        'eco-btn-hover': '0 6px 20px rgba(5,150,105,0.4)',
      },
      animation: {
        'scan':       'scan 2s linear infinite',
        'pulse-eco':  'pulseEco 2s ease-in-out infinite',
        'glow-eco':   'glowEco 1.5s ease-in-out infinite alternate',
        'float':      'float 6s ease-in-out infinite',
        'spin-slow':  'spin 3s linear infinite',
        'fade-in':    'fadeIn 0.5s ease-out forwards',
        'slide-up':   'slideUp 0.4s ease-out forwards',
        'leaf-sway':  'leafSway 4s ease-in-out infinite',
      },
      keyframes: {
        scan: {
          '0%':   { top: '0%' },
          '100%': { top: '100%' },
        },
        pulseEco: {
          '0%, 100%': { boxShadow: '0 0 0 0 rgba(16,185,129,0.4)' },
          '50%':      { boxShadow: '0 0 0 6px rgba(16,185,129,0)' },
        },
        glowEco: {
          '0%':   { boxShadow: '0 0 0 2px #10b981, 0 0 8px rgba(16,185,129,0.2)' },
          '100%': { boxShadow: '0 0 0 2px #10b981, 0 0 20px rgba(16,185,129,0.45)' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%':      { transform: 'translateY(-8px)' },
        },
        fadeIn: {
          from: { opacity: '0', transform: 'translateY(8px)' },
          to:   { opacity: '1', transform: 'translateY(0)' },
        },
        slideUp: {
          from: { opacity: '0', transform: 'translateY(16px)' },
          to:   { opacity: '1', transform: 'translateY(0)' },
        },
        leafSway: {
          '0%, 100%': { transform: 'rotate(-4deg)' },
          '50%':      { transform: 'rotate(4deg)' },
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
}
