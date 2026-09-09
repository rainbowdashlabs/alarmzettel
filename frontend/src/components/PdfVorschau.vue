<script setup lang="ts">
import {computed, onBeforeUnmount, reactive, ref, watch} from 'vue'
import {t} from '../i18n'
import {fehlertext} from '../api/render'

const props = defineProps<{ rendern: () => Promise<Blob>, ausloeser: unknown }>()

/**
 * Zwei Rahmen übereinander. Der sichtbare bleibt stehen, während der andere die neue Fassung
 * lädt; erst wenn die fertig ist, wird umgeblendet. Ein einzelner Rahmen, dessen Quelle sich
 * ändert, reißt den PDF-Betrachter jedes Mal ab — das ist das Flackern beim Tippen.
 */
type Rahmen = 'a' | 'b'

const RAHMEN: readonly Rahmen[] = ['a', 'b']
/** Wenn ein Rahmen nicht meldet, dass er fertig ist, wird nach dieser Zeit trotzdem getauscht. */
const GEDULD = 2000

const quellen = reactive<Record<Rahmen, string | null>>({a: null, b: null})
const aktiv = ref<Rahmen>('a')
const wartet = ref<Rahmen | null>(null)
const laedt = ref(false)
const fehler = ref<string | null>(null)
const zeigtEtwas = computed(() => Boolean(quellen.a || quellen.b))

let timer: number | undefined
let geduld: number | undefined
let lauf = 0

/** Die Werkzeugleiste und die Seitenleiste des Betrachters nehmen dem Blatt nur Platz weg. */
function anzeige(rahmen: Rahmen): string | undefined {
  const quelle = quellen[rahmen]
  return quelle ? `${quelle}#toolbar=0&navpanes=0&view=FitH` : undefined
}

function tauschen(rahmen: Rahmen) {
  window.clearTimeout(geduld)
  aktiv.value = rahmen
  wartet.value = null
  laedt.value = false
}

/** Der Rahmen meldet sich, sobald er die neue Fassung stehen hat. */
function geladen(rahmen: Rahmen) {
  if (wartet.value === rahmen) tauschen(rahmen)
}

/**
 * Die Vorschau ist derselbe Typst-Lauf wie der Download, kann dem Ausdruck also nicht
 * widersprechen. Getippt wird schneller, als gerendert werden kann: der Aufruf wird verzögert,
 * und ein überholter Lauf wird verworfen statt gezeigt.
 */
async function erzeugen() {
  const meine = ++lauf
  laedt.value = true
  try {
    const blob = await props.rendern()
    if (meine !== lauf) return
    const ziel: Rahmen = aktiv.value === 'a' ? 'b' : 'a'
    const alte = quellen[ziel]
    quellen[ziel] = URL.createObjectURL(blob)
    if (alte) URL.revokeObjectURL(alte)
    fehler.value = null
    wartet.value = ziel
    window.clearTimeout(geduld)
    geduld = window.setTimeout(() => {
      if (wartet.value === ziel) tauschen(ziel)
    }, GEDULD)
  } catch (error) {
    if (meine !== lauf) return
    fehler.value = await fehlertext(error)
    laedt.value = false
  }
}

watch(() => props.ausloeser, () => {
  window.clearTimeout(timer)
  timer = window.setTimeout(erzeugen, 400)
}, {deep: true, immediate: true})

onBeforeUnmount(() => {
  window.clearTimeout(timer)
  window.clearTimeout(geduld)
  for (const rahmen of RAHMEN) {
    const quelle = quellen[rahmen]
    if (quelle) URL.revokeObjectURL(quelle)
  }
})
</script>

<template>
  <div class="abschnitt h-full flex flex-col">
    <div class="flex items-center justify-between mb-3 gap-2">
      <h2 class="abschnitt-titel">{{ t('abschnitt.vorschau') }}</h2>
      <span class="label transition-opacity duration-200" :class="laedt ? 'opacity-100' : 'opacity-0'">
        {{ t('vorschau.laedt') }}
      </span>
    </div>

    <p v-if="fehler && zeigtEtwas" class="text-signal-ink text-[13px] mb-2">{{ fehler }}</p>

    <div v-if="fehler && !zeigtEtwas"
         class="grow flex flex-col items-center justify-center gap-3 text-center p-4">
      <p class="text-signal-ink text-sm">{{ fehler }}</p>
      <button type="button" class="knopf" @click="erzeugen">{{ t('vorschau.erneut') }}</button>
    </div>

    <div v-else-if="zeigtEtwas" class="grow relative border border-rule rounded overflow-hidden bg-white">
      <iframe v-for="rahmen in RAHMEN" :key="rahmen" :src="anzeige(rahmen)" title="PDF"
              class="absolute inset-0 w-full h-full transition-opacity duration-300"
              :class="aktiv === rahmen ? 'opacity-100' : 'opacity-0 pointer-events-none'"
              @load="geladen(rahmen)"/>
    </div>

    <p v-else class="grow flex items-center justify-center text-muted text-sm">
      {{ t('vorschau.leer') }}
    </p>
  </div>
</template>
