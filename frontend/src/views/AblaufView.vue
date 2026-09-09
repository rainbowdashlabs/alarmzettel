<script setup lang="ts">
import {computed, defineAsyncComponent, ref, watch} from 'vue'
import {RouterLink} from 'vue-router'
import LagenAnsicht from '../components/planung/LagenAnsicht.vue'
import KlappAbschnitt from '../components/base/KlappAbschnitt.vue'
import LaufKette from '../components/planung/LaufKette.vue'
import TagesPlan from '../components/planung/TagesPlan.vue'
import OrtsSicht from '../components/planung/OrtsSicht.vue'
import PersonenPlan from '../components/planung/PersonenPlan.vue'
import {t} from '../i18n'
import {fehlertext, renderAblaufplan, renderAblaufplanZip, renderAlle} from '../api/render'
import {arbeitsmappe} from '../store/arbeitsmappe'
import {alleOrte, entfernen, laufAnlegen, laufVon, personName, punkteLaden} from '../store/planung'
import {jetztAbgleichen} from '../store/sync'
import {sitzung} from '../store/sitzung'

watch(() => alleOrte().map(ort => Object.values(ort.adresse).join()).join('|'),
    () => punkteLaden(), {immediate: true})

/** Ein Fahrzeug oder eine Person bekommt eine Kette, sobald es eingeplant wird. */
function einplanen(fuer: {fahrzeugId?: string, personId?: string}) {
  if (!laufVon(fuer)) laufAnlegen(fuer)
}

function beschriftung(lauf: {fahrzeugId: string, personId: string}): string {
  if (lauf.fahrzeugId) {
    return arbeitsmappe.kataloge.fahrzeuge.find(v => v.id === lauf.fahrzeugId)?.funkrufname
        || t('ablauf.ohneName')
  }
  return personName(lauf.personId) || t('ablauf.ohneName')
}

function offen(fuer: {fahrzeugId?: string, personId?: string}): boolean {
  return !laufVon(fuer)
}

/** Geplant wird in den Ketten; die drei anderen Ansichten sind dieselben Daten von anderer Seite. */
/**
 * Bild und Karte bringen ihre Zeichenbibliotheken mit und werden deshalb erst geladen, wenn
 * jemand sie auch aufschlägt — der Rest der Seite soll davon nichts merken.
 */
const BewegungsBild = defineAsyncComponent(
    () => import('../components/planung/BewegungsBild.vue'))
const LageKarte = defineAsyncComponent(() => import('../components/planung/LageKarte.vue'))

const ANSICHTEN = ['tag', 'ketten', 'bewegung', 'karte', 'personen', 'orte', 'lagen'] as const
type Ansicht = typeof ANSICHTEN[number]

const SPEICHER = 'alarmplaner_ablaufansicht'

/**
 * Dieselben Daten von sieben Seiten; keine ist die richtige. Womit jemand arbeitet, merkt sich
 * der Browser — es gehört zu ihm und nicht zur Arbeitsmappe, so wie das Farbthema.
 */
function gemerkteAnsicht(): Ansicht {
  const gemerkt = localStorage.getItem(SPEICHER) as Ansicht | null
  return gemerkt && ANSICHTEN.includes(gemerkt) ? gemerkt : 'tag'
}

const ansicht = ref<Ansicht>(gemerkteAnsicht())

/** Wer nur zusieht, bekommt die Ketten nicht — dort wird gearbeitet, nicht gelesen. */
const reiter = computed<readonly Ansicht[]>(() =>
    sitzung.nurLesen ? ANSICHTEN.filter(name => name !== 'ketten') : ANSICHTEN)

watch(reiter, liste => {
  if (!liste.includes(ansicht.value)) ansicht.value = liste[0] ?? 'tag'
}, {immediate: true})

watch(ansicht, gewaehlt => {
  try {
    localStorage.setItem(SPEICHER, gewaehlt)
  } catch { /* ein Browser ohne Speicher fängt eben jedes Mal beim Tagesplan an */ }
})
const fehler = ref<string | null>(null)

/**
 * Vor dem Drucken abgleichen, damit die Blätter den Stand tragen, den alle haben, und nicht den,
 * den dieser Browser vor ein paar Sekunden gesehen hat.
 */
async function drucken(holen: () => Promise<Blob>, name: string) {
  fehler.value = null
  try {
    await jetztAbgleichen()
    const url = URL.createObjectURL(await holen())
    const link = document.createElement('a')
    link.href = url
    link.download = name
    link.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    fehler.value = await fehlertext(error)
  }
}
</script>

<template>
  <div class="grid gap-5">
    <div class="flex items-start justify-between gap-3 flex-wrap">
      <div class="min-w-0">
        <h1 class="headline text-2xl">{{ t('ablauf.titel') }}</h1>
        <p class="text-muted text-sm mt-1">{{ t('ablauf.beschreibung') }}</p>
      </div>
      <div class="flex gap-2 flex-wrap">
        <button type="button" class="knopf knopf-klein"
                @click="drucken(renderAblaufplan, 'ablaufplan.pdf')">
          <font-awesome-icon icon="fa-solid fa-file-pdf"/>
          {{ t('ablauf.drucken') }}
        </button>
        <button type="button" class="knopf knopf-klein" :title="t('ablauf.archivHinweis')"
                @click="drucken(renderAblaufplanZip, 'ablaufplan.zip')">
          <font-awesome-icon icon="fa-solid fa-file-zipper"/>
          {{ t('ablauf.archiv') }}
        </button>
        <button type="button" class="knopf knopf-klein" :title="t('ablauf.zettelHinweis')"
                :disabled="!arbeitsmappe.alarme.length"
                @click="drucken(renderAlle, 'alarmzettel.pdf')">
          <font-awesome-icon icon="fa-solid fa-file-pdf"/>
          {{ t('ablauf.zettel') }}
        </button>
        <RouterLink to="/kataloge" class="knopf knopf-klein">{{ t('ablauf.stammdaten') }}</RouterLink>
      </div>
    </div>

    <p v-if="fehler" class="text-signal-ink text-sm">{{ fehler }}</p>

    <div class="flex flex-wrap gap-2">
      <button v-for="name in reiter" :key="name" type="button" class="knopf knopf-klein"
              :class="ansicht === name ? 'knopf-primaer' : ''" @click="ansicht = name">
        {{ t(`ablauf.ansicht.${name}`) }}
      </button>
    </div>

    <TagesPlan v-if="ansicht === 'tag'"/>
    <BewegungsBild v-else-if="ansicht === 'bewegung'"/>
    <LageKarte v-else-if="ansicht === 'karte'"/>
    <PersonenPlan v-else-if="ansicht === 'personen'"/>
    <OrtsSicht v-else-if="ansicht === 'orte'"/>
    <LagenAnsicht v-else-if="ansicht === 'lagen'"/>

    <template v-else>
    <section v-if="alleOrte().length < 2" class="abschnitt">
      <p class="text-muted text-sm">{{ t('ablauf.ersteOrte') }}</p>
    </section>

    <section class="abschnitt">
      <h2 class="abschnitt-titel">{{ t('ablauf.einplanen') }}</h2>
      <div class="flex flex-wrap gap-2">
        <button v-for="fahrzeug in arbeitsmappe.kataloge.fahrzeuge.filter(v => offen({fahrzeugId: v.id}))"
                :key="fahrzeug.id" type="button" class="knopf knopf-klein"
                @click="einplanen({fahrzeugId: fahrzeug.id})">
          <font-awesome-icon icon="fa-solid fa-plus"/>
          {{ fahrzeug.funkrufname || t('ablauf.ohneName') }}
        </button>
        <button v-for="person in arbeitsmappe.kataloge.personen.filter(p => offen({personId: p.id}))"
                :key="person.id" type="button" class="knopf knopf-klein"
                @click="einplanen({personId: person.id})">
          <font-awesome-icon icon="fa-solid fa-plus"/>
          {{ person.name || t('ablauf.ohneName') }}
        </button>
      </div>
      <p class="text-muted text-[13px] mt-2">{{ t('ablauf.einplanenHinweis') }}</p>
    </section>

    <p v-if="!arbeitsmappe.planung.laeufe.length" class="text-muted text-sm">
      {{ t('ablauf.keineKetten') }}
    </p>

    <KlappAbschnitt v-for="lauf in arbeitsmappe.planung.laeufe" :key="lauf.id"
                    :name="`kette-${lauf.id}`" :titel="beschriftung(lauf)"
                    :symbol="lauf.fahrzeugId ? 'fa-solid fa-table' : 'fa-solid fa-users'"
                    :anzahl="lauf.schritte.length" vorgabe>
      <template #werkzeug>
        <button type="button" class="knopf knopf-klein knopf-gefahr"
                @click="entfernen(arbeitsmappe.planung.laeufe, lauf)">
          <font-awesome-icon icon="fa-solid fa-trash"/>
          {{ t('ablauf.ketteEntfernen') }}
        </button>
      </template>
      <LaufKette :lauf="lauf"/>
    </KlappAbschnitt>
    </template>
  </div>
</template>
