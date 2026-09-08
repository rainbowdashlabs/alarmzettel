<script setup lang="ts">
import {RouterLink, RouterView} from 'vue-router'
import {t} from './i18n'
import {activeTheme, toggleTheme} from './theme'
import {ref} from 'vue'
import {verbindung} from './store/sync'
import {neueSitzung, sitzung, sitzungVergessen, sitzungWechseln} from './store/sitzung'
import {arbeitsmappe} from './store/arbeitsmappe'

const wechsler = ref(false)
const arbeitet = ref(false)

/** Der Tag, an dem diese Sitzung verschwindet, wenn sie niemand öffnet. */
function laeuftAb(): string {
  return sitzung.laeuftAb ? new Date(sitzung.laeuftAb).toLocaleDateString('de-DE') : ''
}

async function tun(was: () => Promise<void>) {
  arbeitet.value = true
  try {
    await was()
    wechsler.value = false
  } finally {
    arbeitet.value = false
  }
}
</script>

<template>
  <div class="min-h-screen flex flex-col bg-page text-ink">
    <header class="bg-surface border-b border-rule">
      <div class="mx-auto w-full max-w-[1560px] px-4 md:px-6 py-2 md:h-15 flex flex-wrap items-center gap-x-6 gap-y-2">
        <RouterLink to="/" class="flex items-baseline gap-2 shrink-0 text-ink hover:text-ink">
          <span class="font-condensed font-bold text-xl tracking-wide uppercase">{{ t('app.name') }}</span>
          <span class="label hidden sm:inline">{{ t('app.untertitel') }}</span>
        </RouterLink>

        <nav class="flex flex-wrap gap-x-5 gap-y-1 grow">
          <RouterLink to="/" class="nav-link">{{ t('nav.alarme') }}</RouterLink>
          <RouterLink to="/kataloge" class="nav-link">{{ t('nav.kataloge') }}</RouterLink>
          <RouterLink v-if="arbeitsmappe.planung.aktiv" to="/planung" class="nav-link">
            {{ t('nav.planung') }}
          </RouterLink>
        </nav>

        <div class="flex items-center gap-2 shrink-0">
          <button type="button" class="knopf knopf-klein" :disabled="arbeitet"
                  :title="t('sitzung.neuTitel')" @click="tun(neueSitzung)">
            <font-awesome-icon icon="fa-solid fa-plus"/>
            <span class="hidden md:inline">{{ t('sitzung.neu') }}</span>
          </button>

          <div class="auswahl">
            <button type="button" class="knopf knopf-klein" :aria-expanded="wechsler"
                    @click="wechsler = !wechsler">
              <font-awesome-icon icon="fa-solid fa-rotate"/>
              <span class="hidden md:inline">{{ t('sitzung.wechseln') }}</span>
            </button>

            <ul v-if="wechsler" class="auswahl-liste sitzungsliste" role="listbox">
              <li v-if="!sitzung.bekannt.length" class="text-muted">{{ t('sitzung.keine') }}</li>
              <li v-for="eintrag in sitzung.bekannt" :key="eintrag.token"
                  :class="eintrag.token === sitzung.token ? 'ist-gewaehlt' : ''"
                  role="option" :aria-selected="eintrag.token === sitzung.token">
                <span class="grow" @click="tun(() => sitzungWechseln(eintrag.token))">
                  {{ eintrag.beschriftung }}
                </span>
                <button type="button" class="text-muted hover:text-signal shrink-0"
                        :title="t('sitzung.entfernen')"
                        @click.stop="sitzungVergessen(eintrag.token)">
                  <font-awesome-icon icon="fa-solid fa-xmark"/>
                </button>
              </li>
              <li v-if="sitzung.laeuftAb" class="text-muted text-[12px] pointer-events-none">
                {{ t('sitzung.laeuftAb', {datum: laeuftAb()}) }}
              </li>
            </ul>
          </div>

          <button type="button" class="icon-button" :title="t('theme.umschalten')" @click="toggleTheme">
            <font-awesome-icon :icon="activeTheme() === 'dark' ? 'fa-solid fa-sun' : 'fa-solid fa-moon'"/>
          </button>
        </div>
      </div>
      <div class="h-[3px] bg-signal"></div>

      <!-- Verbunden zu sein ist der Normalfall, seit jede Arbeitsmappe eine Sitzung ist. Nur
           wenn der Abgleich klemmt, gibt es etwas zu sagen. -->
      <div v-if="verbindung.fehler" class="mx-auto w-full max-w-[1560px] px-4 md:px-6 py-2">
        <span class="text-signal-ink text-[13px]">{{ t('freigabe.abgleichFehler') }}</span>
      </div>
    </header>

    <main class="grow mx-auto w-full max-w-[1560px] px-4 md:px-6 py-6">
      <RouterView/>
    </main>
  </div>
</template>

<style scoped>
.nav-link {
  color: var(--c-muted);
  font-size: 15px;
  padding-bottom: 3px;
  border-bottom: 2px solid transparent;
  transition: color 0.15s;
}

.nav-link:hover {
  color: var(--c-ink);
}

.nav-link.router-link-active {
  color: var(--c-ink);
  font-weight: 600;
  border-bottom-color: var(--c-signal);
}

.icon-button {
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: var(--radius-control);
  background: transparent;
  color: var(--c-muted);
  cursor: pointer;
}

.icon-button:hover {
  color: var(--c-ink);
  background: var(--c-raised);
}
</style>
