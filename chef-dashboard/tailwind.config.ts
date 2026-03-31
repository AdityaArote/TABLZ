import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0D0D12",
        primary: "#C9A84C",
        "primary-container": "#A68A3D",
        surface: {
          lowest: "#0A0A0E",
          low: "#15151A",
          DEFAULT: "#1A1A22",
          high: "#22222D",
          highest: "#2A2A35",
        },
        on: {
          background: "#FAF8F5",
          surface: "#FAF8F5",
          "surface-variant": "#D0C5B2",
          primary: "#0A0A0E",
        },
        outline: {
          DEFAULT: "#3A3A45",
          variant: "rgba(250, 248, 245, 0.08)",
        },
        // Kitchen specific status colors
        status: {
          pending: "#C9A84C", // primary gold
          preparing: "#7B61FF", // plasma 
          ready: "#34D399", // emerald
        }
      },
      fontFamily: {
        sans: ["var(--font-inter)", "sans-serif"],
        display: ["var(--font-playfair)", "serif"],
        mono: ["var(--font-jetbrains-mono)", "monospace"],
      },
      borderRadius: {
        "2xl": "1.5rem",
        "3xl": "2rem",
      },
      boxShadow: {
        'glass': '0 10px 40px -10px rgba(0,0,0,0.5)',
      },
      animation: {
        'fade-up': 'fadeUp 0.8s cubic-bezier(0.25, 0.46, 0.45, 0.94) forwards',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        fadeUp: {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        }
      }
    },
  },
  plugins: [],
};
export default config;
