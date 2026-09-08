import {ref} from 'vue'

export type Theme = 'light' | 'dark'

const STORAGE_KEY = 'alarmzettel_theme'

/** The theme the viewer chose, or null while the browser preference still decides. */
const stored = ref<Theme | null>(readStored())

function readStored(): Theme | null {
    try {
        const value = localStorage.getItem(STORAGE_KEY)
        return value === 'light' || value === 'dark' ? value : null
    } catch {
        return null
    }
}

function systemTheme(): Theme {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

export function activeTheme(): Theme {
    return stored.value ?? systemTheme()
}

function apply() {
    const root = document.documentElement
    if (stored.value) {
        root.setAttribute('data-theme', stored.value)
    } else {
        root.removeAttribute('data-theme')
    }
}

export function toggleTheme() {
    stored.value = activeTheme() === 'dark' ? 'light' : 'dark'
    try {
        localStorage.setItem(STORAGE_KEY, stored.value)
    } catch { /* a viewer with storage blocked keeps the browser preference */ }
    apply()
}

export function initTheme() {
    apply()
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
        if (!stored.value) apply()
    })
}
