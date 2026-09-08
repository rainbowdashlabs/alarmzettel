<script setup lang="ts">
import {t} from '../../i18n'

/**
 * An in-page confirmation. The browser's own `confirm` blocks the whole renderer while it is
 * open, which in a workspace that syncs every few seconds means the exchange stops too.
 */
defineProps<{ frage: string, bestaetigung?: string }>()
const emit = defineEmits<{ ja: [], nein: [] }>()
</script>

<template>
  <div class="fixed inset-0 z-50 bg-black/55 flex items-center justify-center p-4"
       @click.self="emit('nein')">
    <div class="abschnitt max-w-md w-full grid gap-4">
      <p>{{ frage }}</p>
      <div class="flex gap-2 justify-end">
        <button type="button" class="knopf" @click="emit('nein')">{{ t('aktion.abbrechen') }}</button>
        <button type="button" class="knopf knopf-primaer" @click="emit('ja')">
          {{ bestaetigung ?? t('aktion.weiter') }}
        </button>
      </div>
    </div>
  </div>
</template>
