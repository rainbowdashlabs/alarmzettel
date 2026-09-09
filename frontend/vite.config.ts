import {execSync} from 'node:child_process'
import {defineConfig} from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

/**
 * Woher die Fassung kommt, die im Fuß der Seite steht.
 *
 * Im Image reicht der Bau sie als Umgebungsvariable herein — dort gibt es kein `.git`. Wer
 * daheim baut, bekommt sie aus dem Arbeitsverzeichnis, und wer beides nicht hat, bekommt
 * `dev`: eine erfundene Nummer wäre schlimmer als keine.
 */
function commit(): string {
    if (process.env.ALARMPLANER_COMMIT) return process.env.ALARMPLANER_COMMIT
    try {
        return execSync('git rev-parse --short HEAD', {encoding: 'utf8'}).trim()
    } catch {
        return 'dev'
    }
}

export default defineConfig({
    define: {
        __COMMIT__: JSON.stringify(commit()),
        __GEBAUT__: JSON.stringify(process.env.ALARMPLANER_GEBAUT || new Date().toISOString()),
    },
    plugins: [vue(), tailwindcss()],
    server: {
        proxy: {
            '/api': {
                target: process.env.VITE_API_PROXY_TARGET || 'http://localhost:8000',
                changeOrigin: true,
            }
        }
    }
})
