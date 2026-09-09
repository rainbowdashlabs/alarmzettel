<script setup lang="ts">
import {computed, onMounted, ref, watch} from 'vue'
import {t} from '../../i18n'
import {codeAnzeige} from '../../scripts/code'
import {ladeBaum, suchen} from '../../api/sna'
import type {SnaBaum, SnaDisziplin, SnaSchritt, SnaTreffer} from '../../interfaces/Sna'

const emit = defineEmits<{ schliessen: [], uebernehmen: [treffer: SnaTreffer, meldung: string] }>()

const baum = ref<SnaBaum | null>(null)
const fehler = ref<string | null>(null)
const disziplin = ref<SnaDisziplin | null>(null)
const knotenId = ref<string | null>(null)
const pfad = ref<SnaSchritt[]>([])
const meldung = ref('')
const suchtext = ref('')
const eingegeben = ref('')

onMounted(async () => {
  try {
    baum.value = await ladeBaum()
  } catch (error) {
    fehler.value = (error as Error).message
  }
})

const knoten = computed(() => {
  if (!baum.value || !knotenId.value) return null
  return baum.value.knoten[knotenId.value] ?? null
})

const amEnde = computed(() => knoten.value?.code !== undefined)

const treffer = computed<SnaTreffer | null>(() => {
  const ziel = knoten.value
  if (!ziel || ziel.code === undefined || !disziplin.value) return null
  return {
    code: ziel.code,
    kategorie: ziel.kategorie ?? '',
    anlass: ziel.anlass ?? '',
    stichwort: ziel.stichwort ?? '',
    disziplin: disziplin.value,
    pfad: pfad.value,
  }
})

/** The Legende describes the resources in prose; it guides, it does not fill anything in. */
const aufgebot = computed(() => {
  const schluessel = treffer.value?.kategorie
  return schluessel ? baum.value?.notfallkategorien?.[schluessel] : undefined
})

const gefunden = computed(() =>
    baum.value && suchtext.value.trim().length >= 2 ? suchen(baum.value, suchtext.value) : [])

function starten(gewaehlt: SnaDisziplin) {
  disziplin.value = gewaehlt
  knotenId.value = gewaehlt.einstieg
  pfad.value = []
  eingegeben.value = ''
}

function antworten(label: string, aussage: string, ziel: string) {
  const eigen = knoten.value?.eingabe?.eigen === true
  pfad.value = [...pfad.value, {label, aussage, knoten: knotenId.value ?? undefined, eigen}]
  knotenId.value = ziel
  eingegeben.value = ''
}

/**
 * Takes a typed answer. Left empty the question is passed over — recorded where the gap itself
 * says something, as an age asked for and not known does, and silently where it does not: not
 * every call happens on a floor.
 */
function eintragen() {
  const wert = eingegeben.value.trim()
  const eingabe = knoten.value?.eingabe
  const ziel = knoten.value?.ziel
  if (!eingabe || !ziel) return
  if (wert) antworten(wert, eingabe.vorlage.replace('{wert}', wert), ziel)
  else if (eingabe.leer) antworten(eingabe.leer.label, eingabe.leer.aussage, ziel)
  else {
    knotenId.value = ziel
    eingegeben.value = ''
  }
}

/**
 * Steps back to the state before the given answer, so a wrong turn costs one click. Every step
 * carries the question it answered, so this is a lookup rather than a walk back down the graph —
 * which also holds for a path that came out of the search and never passed some questions.
 */
function zurueckZu(index: number) {
  if (!disziplin.value) return
  knotenId.value = pfad.value[index]?.knoten ?? disziplin.value.einstieg
  pfad.value = pfad.value.slice(0, index)
  eingegeben.value = ''
}

function neuStarten() {
  disziplin.value = null
  knotenId.value = null
  pfad.value = []
}

function ausSuche(gewaehlt: SnaTreffer) {
  disziplin.value = gewaehlt.disziplin
  pfad.value = gewaehlt.pfad
  suchtext.value = ''
  const knotenEintrag = Object.entries(baum.value?.knoten ?? {}).find(
      ([, wert]) => wert.code === gewaehlt.code && wert.anlass === gewaehlt.anlass)
  knotenId.value = knotenEintrag?.[0] ?? null
}

/**
 * The numbered answers, as they will be written into the Hinweis. Choosing a discipline or a
 * protocol is a turn in the graph rather than something the caller said, so those steps carry no
 * statement and are not numbered — the Hinweis drops them too, and the two have to agree or the
 * preview would promise a line the slip does not print.
 */
const abfrageweg = computed(() => treffer.value?.pfad
    .filter(schritt => schritt.aussage.trim() && !schritt.eigen) ?? [])

/** Answers that print as Hinweise of their own, above the code — where to go, before what for. */
const eigeneHinweise = computed(() => treffer.value?.pfad
    .filter(schritt => schritt.eigen && schritt.aussage.trim()) ?? [])

function uebernehmen() {
  if (treffer.value) emit('uebernehmen', treffer.value, meldung.value.trim())
}

watch(amEnde, (erreicht) => {
  if (erreicht && !meldung.value) meldung.value = treffer.value?.anlass ?? ''
})
</script>

<template>
  <div class="fixed inset-0 z-50 bg-black/55 flex items-start justify-center p-4 overflow-auto"
       @click.self="emit('schliessen')">
    <div class="abschnitt w-full max-w-3xl my-6">
      <div class="flex items-start justify-between gap-3 mb-4">
        <div>
          <h2 class="abschnitt-titel mb-1">{{ t('sna.titel') }}</h2>
          <p class="text-muted text-sm">{{ t('sna.beschreibung') }}</p>
        </div>
        <button type="button" class="knopf knopf-klein" @click="emit('schliessen')">
          <font-awesome-icon icon="fa-solid fa-xmark"/>
          {{ t('aktion.abbrechen') }}
        </button>
      </div>

      <p v-if="fehler" class="text-signal-ink text-sm">{{ t('sna.ladefehler') }} {{ fehler }}</p>
      <p v-else-if="!baum" class="text-muted text-sm">{{ t('sna.laedt') }}</p>

      <template v-else>
        <div class="mb-4">
          <label class="feld-label">{{ t('sna.suche') }}</label>
          <input v-model="suchtext" type="text" class="field" :placeholder="t('sna.suchePlatzhalter')"/>
          <ul v-if="gefunden.length" class="mt-2 grid gap-1 max-h-64 overflow-auto">
            <li v-for="fund in gefunden" :key="`${fund.disziplin.id}-${fund.code}-${fund.anlass}`">
              <button type="button"
                      class="w-full text-left border border-rule rounded px-3 py-2 bg-page hover:bg-raised"
                      @click="ausSuche(fund)">
                <span class="tabular text-signal-ink">{{ codeAnzeige(fund.code) }}</span>
                <span class="ml-2">{{ fund.anlass }}</span>
                <span class="label ml-2">{{ fund.disziplin.label }}</span>
              </button>
            </li>
          </ul>
        </div>

        <div v-if="!disziplin" class="grid gap-2">
          <button v-for="wahl in baum.disziplinen" :key="wahl.id" type="button"
                  class="border border-rule rounded p-3 bg-page hover:bg-raised text-left"
                  @click="starten(wahl)">
            <div class="flex items-center gap-2">
              <span class="font-condensed font-bold uppercase tracking-wide">{{ wahl.label }}</span>
              <span v-if="wahl.quelle === 'erfunden'"
                    class="label text-signal-ink border border-signal rounded px-1.5">
                {{ t('sna.erfunden') }}
              </span>
            </div>
            <p v-if="wahl.hinweis" class="text-muted text-[13px] mt-1">{{ wahl.hinweis }}</p>
          </button>
        </div>

        <template v-else>
          <div class="flex items-center gap-2 flex-wrap mb-3">
            <button type="button" class="knopf knopf-klein" @click="neuStarten">
              {{ disziplin.label }}
            </button>
            <template v-for="(schritt, index) in pfad" :key="index">
              <font-awesome-icon icon="fa-solid fa-angle-right" class="text-faint text-xs"/>
              <button type="button" class="knopf knopf-klein" @click="zurueckZu(index)">
                {{ schritt.label }}
              </button>
            </template>
          </div>

          <p v-if="disziplin.quelle === 'erfunden'" class="text-signal-ink text-[13px] mb-3">
            {{ t('sna.erfundenWarnung') }}
          </p>

          <div v-if="!amEnde && knoten" class="grid gap-2">
            <p class="font-condensed font-bold uppercase tracking-wide">{{ knoten.frage }}</p>

            <form v-if="knoten.eingabe" class="flex gap-2 flex-wrap" @submit.prevent="eintragen">
              <input v-model="eingegeben" type="text" class="field grow min-w-40"
                     :placeholder="knoten.eingabe.platzhalter" autofocus/>
              <button type="submit" class="knopf knopf-primaer shrink-0">
                {{ eingegeben.trim() ? t('sna.weiter')
                   : (knoten.eingabe.leer?.label ?? t('sna.ueberspringen')) }}
              </button>
            </form>

            <button v-for="antwort in knoten.antworten" :key="antwort.ziel + antwort.label"
                    type="button"
                    class="border border-rule rounded px-3 py-2 bg-page hover:bg-raised text-left"
                    @click="antworten(antwort.label, antwort.aussage, antwort.ziel)">
              <span v-if="antwort.nr" class="tabular text-muted mr-2">{{ antwort.nr }}</span>
              {{ antwort.label }}
            </button>
          </div>

          <div v-else-if="treffer" class="grid gap-3">
            <div class="border border-rule rounded p-3 bg-page grid gap-2">
              <div class="flex items-baseline gap-3 flex-wrap">
                <span class="headline text-xl tabular">{{ codeAnzeige(treffer.code) }}</span>
                <span v-if="treffer.kategorie" class="label">{{ treffer.kategorie }}</span>
              </div>
              <p v-if="treffer.anlass">{{ treffer.anlass }}</p>
              <p v-if="aufgebot" class="text-muted text-[13px]">
                <strong>{{ t('sna.aufgebot') }}:</strong> {{ aufgebot }}
              </p>
            </div>

            <div>
              <label class="feld-label">{{ t('sna.meldung') }}</label>
              <input v-model="meldung" type="text" class="field"/>
            </div>

            <div v-if="eigeneHinweise.length">
              <div class="feld-label">{{ t('sna.eigeneHinweise') }}</div>
              <ul class="grid gap-1">
                <li v-for="(schritt, index) in eigeneHinweise" :key="index"
                    class="text-sm flex gap-2">
                  <span class="text-muted w-6 text-right shrink-0">–</span>
                  <span>{{ schritt.aussage }}</span>
                </li>
              </ul>
            </div>

            <div>
              <div class="feld-label">{{ t('sna.abfrageweg') }}</div>
              <ol class="grid gap-1">
                <li v-for="(schritt, index) in abfrageweg" :key="index" class="text-sm flex gap-2">
                  <span class="tabular text-muted w-6 text-right shrink-0">{{ index + 1 }}.</span>
                  <span>{{ schritt.aussage }}</span>
                </li>
              </ol>
            </div>

            <p class="text-muted text-[13px]">{{ t('sna.wasPassiert') }}</p>

            <div class="flex gap-2 flex-wrap">
              <button type="button" class="knopf knopf-primaer" @click="uebernehmen">
                <font-awesome-icon icon="fa-solid fa-check"/>
                {{ t('sna.uebernehmen') }}
              </button>
              <button type="button" class="knopf" @click="neuStarten">{{ t('sna.neu') }}</button>
            </div>
          </div>
        </template>
      </template>
    </div>
  </div>
</template>
