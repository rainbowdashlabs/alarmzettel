<script setup lang="ts">
import {computed, onBeforeUnmount, onMounted, ref} from 'vue'
import {useRoute} from 'vue-router'
import {t} from '../i18n'
import {sitzungLesen} from '../api/sitzung'
import {fehlertext, renderBlatt} from '../api/render'
import {plandatenVon} from '../store/planung'
import {anfahrt, einsaetze, einsaetzeAmOrt, lagenName, personenplan} from '../scripts/ablauf'
import type {Einsatz, Plandaten} from '../scripts/ablauf'
import {kartenLinks} from '../scripts/karten'
import {tagwechsel, uhrzeit} from '../scripts/zeit'
import type {Arbeitsmappe} from '../interfaces/Alarm'
import type {Lauf, Ort} from '../interfaces/Planung'

/**
 * Ein Blatt für eine Person oder ein Fahrzeug, hinter einem eigenen Link.
 *
 * Es liest die Sitzung, ohne in sie zu wechseln: wer den Link bekommt, sieht seinen Tag und
 * sonst nichts — kein Editor, keine fremden Ketten, kein Cookie. Dieselben Zeilen wie auf dem
 * gedruckten Zettel, nur dass sie sich von selbst auffrischen.
 */
const TAKT = 30000

const route = useRoute()
const mappe = ref<Arbeitsmappe | null>(null)
const fehler = ref<string | null>(null)
let uhr: ReturnType<typeof setInterval> | undefined

const art = computed(() => String(route.params.art))
const kennung = computed(() => String(route.params.id))

const daten = computed<Plandaten | null>(() => mappe.value ? plandatenVon(mappe.value) : null)

const alleEinsaetze = computed<Einsatz[]>(() => daten.value ? einsaetze(daten.value) : [])

const person = computed(() =>
    mappe.value?.kataloge.personen.find(eintrag => eintrag.id === kennung.value))

const fahrzeug = computed(() =>
    mappe.value?.kataloge.fahrzeuge.find(eintrag => eintrag.id === kennung.value))

const name = computed(() =>
    art.value === 'person' ? person.value?.name : fahrzeug.value?.funkrufname)

const nebentitel = computed(() => {
  const wer = person.value
  if (art.value !== 'person' || !wer) return ''
  return [wer.anzahl > 1 ? t('blatt.koepfe', {n: wer.anzahl}) : '', wer.rollen.join(', ')]
      .filter(Boolean).join(' · ')
})

interface Zeile {
  schluessel: string
  von: string
  bis: string
  was: string
  lage: string
  womit: string
  beiwerk: string
  ortId: string
}

function ortName(ortId: string): string {
  return daten.value?.orte.find(ort => ort.id === ortId)?.name ?? ''
}

function personName(personId: string): string {
  return daten.value?.personen.find(eintrag => eintrag.id === personId)?.name ?? ''
}

function materialtext(schritt: {material: {materialId: string, anzahl: number}[]}): string {
  return schritt.material
      .map(posten => {
        const stueck = mappe.value?.kataloge.material.find(m => m.id === posten.materialId)
        if (!stueck?.name) return ''
        return posten.anzahl > 1 ? `${posten.anzahl} × ${stueck.name}` : stueck.name
      })
      .filter(Boolean)
      .join(', ')
}

/** Der Tag einer Person: ihre eigenen Schritte, die Fahrten dazu und was am Ort läuft. */
function personenzeilen(): Zeile[] {
  if (!daten.value || !person.value) return []
  const gesehen = new Set<string>()
  const zeilen: Zeile[] = []
  for (const eintrag of personenplan(daten.value, person.value.id)) {
    const schritt = eintrag.schritt
    const fahrzeugName = eintrag.lauf.fahrzeugId
        ? daten.value.fahrzeuge.find(v => v.id === eintrag.lauf.fahrzeugId)?.funkrufname ?? ''
        : ''
    const weg = eintrag.vonOrtId === schritt.ortId
        ? null : anfahrt(daten.value, eintrag.lauf, schritt)
    if (weg && schritt.art === 'aufenthalt') {
      zeilen.push({
        schluessel: `${schritt.id}-anfahrt`, von: weg.von, bis: weg.bis,
        was: `→ ${ortName(weg.nachOrtId) || t('ablauf.ohneName')}`, lage: '',
        womit: fahrzeugName || t(`ablauf.${weg.mittel === 'eigen' ? 'eigen' : 'zuFuss'}`),
        beiwerk: '', ortId: weg.nachOrtId,
      })
    }
    zeilen.push({
      schluessel: schritt.id, von: eintrag.ankunft, bis: eintrag.bis,
      was: (schritt.art === 'fahrt' ? '→ ' : '') + (ortName(schritt.ortId) || t('ablauf.ohneName')),
      lage: lagenName(daten.value, schritt.programmpunktId),
      womit: fahrzeugName + (eintrag.faehrt ? ` · ${t('ablauf.faehrt')}` : ''),
      beiwerk: [materialtext(schritt), schritt.notiz].filter(Boolean).join(' · '),
      ortId: schritt.ortId,
    })
    for (const einsatz of einsaetzeAmOrt(eintrag, alleEinsaetze.value)) {
      const schluessel = `${einsatz.programmpunkt.id}-${einsatz.nummer}`
      if (gesehen.has(schluessel)) continue
      gesehen.add(schluessel)
      zeilen.push({
        schluessel, von: einsatz.da, bis: einsatz.bis,
        was: t('ablauf.amOrt', {
          was: lagenName(daten.value, einsatz.programmpunkt.id) || t('ablauf.ohneName')}),
        lage: '',
        womit: [...new Set(einsatz.beteiligte
            .filter(teil => teil.aufgebot && teil.lauf.fahrzeugId)
            .map(teil => daten.value!.fahrzeuge
                .find(v => v.id === teil.lauf.fahrzeugId)?.funkrufname ?? ''))]
            .filter(Boolean).join(', '),
        beiwerk: '', ortId: einsatz.ortId,
      })
    }
  }
  return zeilen.sort((a, b) => a.von < b.von ? -1 : a.von > b.von ? 1 : 0)
}

/** Der Tag eines Fahrzeugs: seine Kette, samt Besatzung. */
function fahrzeugzeilen(): Zeile[] {
  if (!daten.value || !fahrzeug.value) return []
  const lauf: Lauf | undefined = daten.value.planung.laeufe
      .find(eintrag => eintrag.fahrzeugId === fahrzeug.value!.id)
  if (!lauf) return []
  const zeilen: Zeile[] = []
  for (const schritt of lauf.schritte) {
    const weg = anfahrt(daten.value, lauf, schritt)
    if (weg) {
      zeilen.push({
        schluessel: `${schritt.id}-anfahrt`, von: weg.von, bis: weg.bis,
        was: `→ ${ortName(weg.nachOrtId) || t('ablauf.ohneName')}`, lage: '',
        womit: '', beiwerk: '', ortId: weg.nachOrtId,
      })
    }
    zeilen.push({
      schluessel: schritt.id, von: weg?.bis ?? schritt.von, bis: schritt.bis,
      was: (schritt.art === 'fahrt' ? '→ ' : '') + (ortName(schritt.ortId) || t('ablauf.ohneName')),
      lage: lagenName(daten.value, schritt.programmpunktId),
      womit: schritt.besatzung
          .map(sitzt => personName(sitzt.personId) + (sitzt.faehrt ? ` · ${t('ablauf.faehrt')}` : ''))
          .filter(Boolean).join(', '),
      beiwerk: [materialtext(schritt), schritt.notiz].filter(Boolean).join(' · '),
      ortId: schritt.ortId,
    })
  }
  return zeilen
}

const zeilen = computed(() => art.value === 'person' ? personenzeilen() : fahrzeugzeilen())
const tage = computed(() => tagwechsel(zeilen.value.map(zeile => zeile.von)))

/** Die Orte des Blattes mit Adresse und Weg dorthin — der Zettel soll für sich genügen. */
const orte = computed(() => {
  const gesehen: string[] = []
  for (const zeile of zeilen.value) {
    if (zeile.ortId && !gesehen.includes(zeile.ortId)) gesehen.push(zeile.ortId)
  }
  return gesehen
      .map(ortId => daten.value?.orte.find(ort => ort.id === ortId))
      .filter((ort): ort is Ort => Boolean(ort?.name))
})

function adresstext(ort: Ort): string {
  const strasse = [ort.adresse.strasse, ort.adresse.hnr].filter(Boolean).join(' ')
  const wo = [ort.adresse.plz, ort.adresse.ort].filter(Boolean).join(' ')
  return [strasse, ort.adresse.objekt, wo].filter(Boolean).join(', ')
}

/** Derselbe Zettel zum Mitnehmen: was hier steht, gedruckt, ohne den Stapel aller anderen. */
async function pdf() {
  fehler.value = null
  try {
    const url = URL.createObjectURL(
        await renderBlatt(String(route.params.token), art.value, kennung.value))
    const link = document.createElement('a')
    link.href = url
    link.download = `${art.value}-${name.value || 'blatt'}.pdf`
    link.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    fehler.value = await fehlertext(error)
  }
}

async function laden() {
  try {
    mappe.value = (await sitzungLesen(String(route.params.token))).arbeitsmappe
    fehler.value = null
  } catch (error) {
    fehler.value = await fehlertext(error)
  }
}

onMounted(async () => {
  await laden()
  uhr = setInterval(laden, TAKT)
})

onBeforeUnmount(() => {
  if (uhr) clearInterval(uhr)
})
</script>

<template>
  <div class="grid gap-4 max-w-3xl">
    <p v-if="fehler" class="abschnitt text-signal-ink">{{ fehler }}</p>
    <p v-else-if="!mappe" class="text-muted text-sm">{{ t('freigabe.laedt') }}</p>

    <template v-else-if="!name">
      <p class="abschnitt text-signal-ink">{{ t('blatt.unbekannt') }}</p>
    </template>

    <template v-else>
      <div class="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <div class="flex items-baseline gap-3 flex-wrap">
            <h1 class="headline text-2xl">{{ name }}</h1>
            <span v-if="nebentitel" class="text-muted text-sm">{{ nebentitel }}</span>
          </div>
          <p class="text-muted text-[13px] mt-1">{{ t('blatt.hinweis') }}</p>
        </div>
        <button v-if="zeilen.length" type="button" class="knopf knopf-klein" @click="pdf">
          <font-awesome-icon icon="fa-solid fa-file-pdf"/>
          {{ t('blatt.pdf') }}
        </button>
      </div>

      <p v-if="!zeilen.length" class="abschnitt text-muted text-sm">{{ t('ablauf.ohnePlan') }}</p>

      <section v-else class="abschnitt">
        <div v-for="(zeile, nummer) in zeilen" :key="zeile.schluessel"
             class="border-t border-rule first:border-t-0 py-2 grid gap-0.5">
          <div class="flex items-baseline gap-3 flex-wrap">
            <span v-if="tage[nummer]" class="label text-muted">{{ tage[nummer] }}</span>
            <span class="tabular font-bold whitespace-nowrap">
              {{ uhrzeit(zeile.von) }}–{{ uhrzeit(zeile.bis) }}
            </span>
            <span class="grow min-w-0">{{ zeile.was }}</span>
            <span v-if="zeile.womit" class="text-muted text-sm">{{ zeile.womit }}</span>
          </div>
          <div v-if="zeile.lage || zeile.beiwerk" class="flex flex-wrap gap-x-3 text-[13px]">
            <span v-if="zeile.lage" class="text-signal-ink">{{ zeile.lage }}</span>
            <span v-if="zeile.beiwerk" class="text-muted">{{ zeile.beiwerk }}</span>
          </div>
        </div>
      </section>

      <section v-if="orte.length" class="abschnitt">
        <h2 class="abschnitt-titel">{{ t('blatt.orte') }}</h2>
        <div v-for="ort in orte" :key="ort.id" class="border-t border-rule py-2 first:border-t-0">
          <div class="flex items-baseline gap-3 flex-wrap">
            <span class="font-bold">{{ ort.name }}</span>
            <span class="text-muted text-sm grow min-w-0">{{ adresstext(ort) }}</span>
            <span v-if="adresstext(ort)" class="flex gap-3 text-[13px]">
              <a :href="kartenLinks(adresstext(ort)).apple" target="_blank" rel="noreferrer">
                Apple Maps
              </a>
              <a :href="kartenLinks(adresstext(ort)).google" target="_blank" rel="noreferrer">
                Google Maps
              </a>
            </span>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>
