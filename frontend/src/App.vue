<script setup lang="ts">
import {RouterLink, RouterView} from 'vue-router'
import {t} from './i18n'
import {activeTheme, toggleTheme} from './theme'
import {verbindung, verlassen} from './store/sync'
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
        </nav>

        <button type="button" class="icon-button" :title="t('theme.umschalten')" @click="toggleTheme">
          <font-awesome-icon :icon="activeTheme() === 'dark' ? 'fa-solid fa-sun' : 'fa-solid fa-moon'"/>
        </button>
      </div>
      <div class="h-[3px] bg-signal"></div>

      <div v-if="verbindung.laeuft"
           class="mx-auto w-full max-w-[1560px] px-4 md:px-6 py-2 flex items-center gap-3 flex-wrap">
        <span class="label">
          <font-awesome-icon icon="fa-solid fa-users" class="mr-1"/>
          {{ t('freigabe.verbunden', {wer: verbindung.wer}) }}
        </span>
        <span v-if="verbindung.fehler" class="text-signal-ink text-[13px]">
          {{ t('freigabe.abgleichFehler') }}
        </span>
        <button type="button" class="knopf knopf-klein" @click="verlassen">
          {{ t('freigabe.verlassen') }}
        </button>
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
