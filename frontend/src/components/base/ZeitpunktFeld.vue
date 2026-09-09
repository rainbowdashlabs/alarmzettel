<script setup lang="ts">
import {computed, useId} from 'vue'

/**
 * Ein Zeitpunkt in einem Feld, obwohl der Zettel zwei druckt.
 *
 * Auf dem Blatt stehen Datum und Uhrzeit getrennt und in deutscher Schreibweise — daran ändert
 * sich nichts. Eingegeben werden sie hier wie überall sonst im Werkzeug: mit dem Auswahlfeld des
 * Browsers, das Kalender und Uhr mitbringt.
 */
const datum = defineModel<string>('datum', {default: ''})
const zeit = defineModel<string>('zeit', {default: ''})
const {label, gesperrt} = defineProps<{ label: string, gesperrt?: boolean }>()
/** Erst wenn beide Felder stehen — wer daran hängt, soll nicht die halbe Änderung sehen. */
const meldet = defineEmits<{ change: [] }>()

const id = useId()

/** „19.9.2026“ und „08:00“ werden zu dem, was ein `datetime-local` versteht — oder zu nichts. */
const zeitpunkt = computed(() => {
  const teile = /^(\d{1,2})\.(\d{1,2})\.(\d{4})$/.exec(datum.value.trim())
  const uhr = /^(\d{1,2}):(\d{2})/.exec(zeit.value.trim())
  if (!teile) return ''
  const tag = `${teile[3]}-${teile[2]!.padStart(2, '0')}-${teile[1]!.padStart(2, '0')}`
  return uhr ? `${tag}T${uhr[1]!.padStart(2, '0')}:${uhr[2]}` : `${tag}T00:00`
})

/** Zurück in die Schreibweise des Zettels; ein geleertes Feld leert beide. */
function gesetzt(wert: string) {
  const teile = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(wert)
  if (!teile) {
    datum.value = ''
    zeit.value = ''
  } else {
    datum.value = `${teile[3]}.${teile[2]}.${teile[1]}`
    zeit.value = `${teile[4]}:${teile[5]}`
  }
  meldet('change')
}
</script>

<template>
  <div>
    <label class="feld-label" :for="id">{{ label }}</label>
    <input :id="id" :value="zeitpunkt" type="datetime-local" step="60" class="field"
           :disabled="gesperrt"
           @change="gesetzt(($event.target as HTMLInputElement).value)"/>
  </div>
</template>
