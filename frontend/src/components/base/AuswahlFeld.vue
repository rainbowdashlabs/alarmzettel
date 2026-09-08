<script setup lang="ts">
import {computed, ref, useId} from 'vue'
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

function waehlen(wert: string) {
  model.value = wert
  offen.value = false
  emit('change')
}

function umschalten() {
  offen.value = !offen.value
  if (offen.value) eingabe.value?.focus()
}
</script>

<template>
  <div :class="breit ? 'col-span-2' : ''" class="auswahl">
    <label class="feld-label" :for="id">{{ label }}</label>
    <div class="auswahl-zeile">
      <input :id="id" ref="eingabe" v-model="model" type="text" class="field"
             :placeholder="platzhalter" autocomplete="off"
             @focus="offen = true" @blur="offen = false" @change="$emit('change')"
             @keydown.escape="offen = false"/>
      <button v-if="vorschlaege.length" type="button" class="auswahl-knopf"
              :title="t('feld.auswaehlen')" :aria-expanded="offen"
              @mousedown.prevent="umschalten">
        <font-awesome-icon icon="fa-solid fa-angle-down"/>
      </button>
    </div>

    <ul v-if="offen && gefiltert.length" class="auswahl-liste">
      <li v-for="wert in gefiltert" :key="wert">
        <button type="button" :class="wert === model ? 'ist-gewaehlt' : ''"
                @mousedown.prevent="waehlen(wert)">
          {{ wert }}
        </button>
      </li>
    </ul>
  </div>
</template>
