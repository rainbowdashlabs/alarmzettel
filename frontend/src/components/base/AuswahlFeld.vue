<script setup lang="ts">
import {computed, nextTick, ref, useId, watch} from 'vue'
import {t} from '../../i18n'

const props = defineProps<{
  label: string
  vorschlaege: string[]
  platzhalter?: string
  breit?: boolean
  /** The list already answers the typing — filtering it again here would only cut it down. */
  vorgefiltert?: boolean
}>()

const emit = defineEmits<{ change: [] }>()
const model = defineModel<string>({default: ''})
const id = useId()
const eingabe = ref<HTMLInputElement>()
const offen = ref(false)

/** Which entry the arrow keys are on, or -1 while the typing still stands on its own. */
const aktiv = ref(-1)

/**
 * Typing narrows the list, but a value taken from the list matches only itself — so a field that
 * already holds a catalogue entry would offer that one entry alone. Showing everything once the
 * text is an exact hit keeps the list usable for changing one's mind.
 */
const gefiltert = computed(() => {
  const suche = model.value.trim().toLowerCase()
  if (props.vorgefiltert || !suche) return props.vorschlaege
  if (props.vorschlaege.some(wert => wert.toLowerCase() === suche)) return props.vorschlaege
  return props.vorschlaege.filter(wert => wert.toLowerCase().includes(suche))
})

const sichtbar = computed(() => offen.value && gefiltert.value.length > 0)
const eintragId = (stelle: number) => `${id}-eintrag-${stelle}`

function waehlen(wert: string) {
  model.value = wert
  schliessen()
  emit('change')
}

function schliessen() {
  offen.value = false
  aktiv.value = -1
}

function umschalten() {
  offen.value = !offen.value
  aktiv.value = -1
  if (offen.value) eingabe.value?.focus()
}

/**
 * Wraps at both ends, so holding one arrow key walks the whole list either way. With nothing
 * highlighted yet, down starts at the top and up at the bottom — which is not the same as
 * counting from an imagined entry before the first one.
 */
async function bewegen(schritte: number) {
  const anzahl = gefiltert.value.length
  if (!anzahl) return
  offen.value = true
  aktiv.value = aktiv.value < 0
      ? (schritte > 0 ? 0 : anzahl - 1)
      : (aktiv.value + schritte + anzahl) % anzahl
  await nextTick()
  document.getElementById(eintragId(aktiv.value))?.scrollIntoView({block: 'nearest'})
}

/**
 * Enter takes the highlighted entry. With nothing highlighted it is left alone: the input fires
 * its own change event for what was typed, and picking that up here would run it twice.
 */
function bestaetigen(ereignis: KeyboardEvent) {
  if (!sichtbar.value) return
  ereignis.preventDefault()
  const gewaehlt = gefiltert.value[aktiv.value]
  if (gewaehlt !== undefined) waehlen(gewaehlt)
  else schliessen()
}

// Suggestions arrive while typing goes on, and an index into the old list means nothing in a new
// one — a stale one would take an entry the list no longer shows.
watch(gefiltert, () => (aktiv.value = -1))
</script>

<template>
  <div :class="breit ? 'col-span-2' : ''" class="auswahl">
    <label class="feld-label" :for="id">{{ label }}</label>
    <div class="auswahl-zeile">
      <input :id="id" ref="eingabe" v-model="model" type="text" class="field"
             :placeholder="platzhalter" autocomplete="off"
             role="combobox" aria-autocomplete="list" :aria-expanded="sichtbar"
             :aria-controls="`${id}-liste`"
             :aria-activedescendant="aktiv >= 0 ? eintragId(aktiv) : undefined"
             @focus="offen = true" @blur="schliessen" @change="$emit('change')"
             @keydown.down.prevent="bewegen(1)"
             @keydown.up.prevent="bewegen(-1)"
             @keydown.enter="bestaetigen"
             @keydown.tab="schliessen"
             @keydown.escape="schliessen"/>
      <button v-if="vorschlaege.length" type="button" class="auswahl-knopf" tabindex="-1"
              :title="t('feld.auswaehlen')" :aria-expanded="sichtbar"
              @mousedown.prevent="umschalten">
        <font-awesome-icon icon="fa-solid fa-angle-down"/>
      </button>
    </div>

    <ul v-if="sichtbar" :id="`${id}-liste`" class="auswahl-liste" role="listbox">
      <li v-for="(wert, stelle) in gefiltert" :id="eintragId(stelle)" :key="wert" role="option"
          :aria-selected="stelle === aktiv"
          :class="[stelle === aktiv ? 'ist-aktiv' : '', wert === model ? 'ist-gewaehlt' : '']"
          @mousedown.prevent="waehlen(wert)"
          @mousemove="aktiv = stelle">
        {{ wert }}
      </li>
    </ul>
  </div>
</template>
