<script setup lang="ts">
import {t} from '../../i18n'

const QUELLE = 'https://github.com/rainbowdashlabs/alarmzettel'
const commit = __COMMIT__

/** Die Bauzeit steht als ISO-Wert im Bündel; gelesen wird sie in der Zeitzone des Lesers. */
function gebaut(): string {
  const zeitpunkt = new Date(__GEBAUT__)
  return Number.isNaN(zeitpunkt.getTime())
      ? ''
      : zeitpunkt.toLocaleString('de-DE', {dateStyle: 'medium', timeStyle: 'short'})
}
</script>

<template>
  <footer class="border-t border-rule mt-auto">
    <div class="mx-auto w-full max-w-[1560px] px-4 md:px-6 py-5
                flex flex-col items-center gap-1 text-[13px] text-muted text-center">
      <a :href="QUELLE" target="_blank" rel="noreferrer noopener"
         class="flex items-center gap-2 text-ink hover:underline">
        <font-awesome-icon :icon="['fab', 'github']"/>
        GitHub
      </a>
      <span>{{ t('fuss.urheber') }}</span>
      <span>{{ t('fuss.gemacht') }}</span>
      <span>{{ t('fuss.lizenz') }}</span>
      <span class="tabular">{{ t('fuss.fassung', {commit, gebaut: gebaut()}) }}</span>
    </div>
  </footer>
</template>
