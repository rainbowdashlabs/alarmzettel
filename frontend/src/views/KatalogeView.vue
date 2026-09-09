<script setup lang="ts">
import {computed, reactive, ref, watch} from 'vue'
import AdresseFeld from '../components/base/AdresseFeld.vue'
import KlappAbschnitt from '../components/base/KlappAbschnitt.vue'
import TextFeld from '../components/base/TextFeld.vue'
import {t} from '../i18n'
import {arbeitsmappe} from '../store/arbeitsmappe'
import {
  entfernen as ausListe, ortAnlegen, personAnlegen, tagAnlegen, umschalten,
  verfuegbarkeitAnlegen, wortHinzufuegen,
} from '../store/planung'
import {truppText} from '../scripts/staerke'
import {STICHWOERTER} from '../interfaces/Alarm'
import type {
  Fahrzeugvorlage, Kataloge, Materialvorlage, Stichwortvorlage,
} from '../interfaces/Alarm'
import type {Ort} from '../interfaces/Planung'

type Wortliste = Extract<keyof Kataloge, 'status' | 'trupp' | 'rollen' | 'fahrerlaubnisse'>

const listen: { schluessel: Wortliste, titel: string }[] = [
  {schluessel: 'status', titel: t('kataloge.status')},
  {schluessel: 'trupp', titel: t('kataloge.trupp')},
  {schluessel: 'rollen', titel: t('planung.rollen')},
  {schluessel: 'fahrerlaubnisse', titel: t('planung.fahrerlaubnisse')},
]

/**
 * Eine Anzeigereihenfolge, die stillsteht, solange jemand im Abschnitt schreibt.
 *
 * Der Aufbau sortiert die Kataloge nach Namen. Täte die Ansicht das bei jedem Tastendruck mit,
 * wanderte die Zeile unter dem Cursor weg und der nächste Buchstabe landete in einem fremden
 * Feld. Neu geordnet wird deshalb erst, wenn der Abschnitt den Fokus verliert — und wenn ein
 * Eintrag dazukommt oder verschwindet.
 */
function geordnet<T extends { id: string }>(quelle: () => T[], lesen: (eintrag: T) => string) {
  const reihenfolge = ref<string[]>([])

  function ordnen() {
    reihenfolge.value = [...quelle()]
        .sort((a, b) => lesen(a).localeCompare(lesen(b), 'de') || a.id.localeCompare(b.id))
        .map(eintrag => eintrag.id)
  }

  /** Was neu ist, hängt hinten an, bis neu geordnet wird — dort sieht man es auch. */
  const liste = computed(() => {
    const nachId = new Map(quelle().map(eintrag => [eintrag.id, eintrag]))
    const bekannt = reihenfolge.value
        .map(id => nachId.get(id))
        .filter((eintrag): eintrag is T => Boolean(eintrag))
    const gesehen = new Set(bekannt.map(eintrag => eintrag.id))
    return [...bekannt, ...quelle().filter(eintrag => !gesehen.has(eintrag.id))]
  })

  watch(() => quelle().map(eintrag => eintrag.id).join(), ordnen, {immediate: true})
  // Als `reactive`, damit die Vorlage `liste` ohne `.value` liest — in einem einfachen Objekt
  // packt Vue eine Referenz nicht aus.
  return reactive({liste, ordnen})
}

/** Erst wenn der Fokus den Abschnitt ganz verlässt, nicht schon beim Sprung ins nächste Feld. */
function verlassen(ereignis: FocusEvent, ordnen: () => void) {
  const ziel = ereignis.relatedTarget
  if (!(ziel instanceof Node) || !(ereignis.currentTarget as Node).contains(ziel)) ordnen()
}

const fahrzeuge = geordnet(() => arbeitsmappe.kataloge.fahrzeuge, eintrag => eintrag.funkrufname)
const stichwoerter = geordnet(() => arbeitsmappe.kataloge.stichwoerter, eintrag => eintrag.text)
const materialliste = geordnet(() => arbeitsmappe.kataloge.material, eintrag => eintrag.name)

const stichwort = ref('')

/**
 * Was die Wache üblicherweise führt und in diesem Katalog noch fehlt. Wer eine Liste geleert
 * oder aus einer Tabelle geladen hat, muss die Standardstichwörter nicht abtippen.
 */
const stichwortvorschlaege = computed(() => {
  const vorhanden = new Set(arbeitsmappe.kataloge.stichwoerter.map(e => e.text.trim()))
  return STICHWOERTER.filter(text => !vorhanden.has(text))
})
const materialname = ref('')

function materialHinzufuegen() {
  const name = materialname.value.trim()
  if (!name || arbeitsmappe.kataloge.material.some(stueck => stueck.name === name)) return
  arbeitsmappe.kataloge.material.push({id: crypto.randomUUID(), name, bestand: 0})
  materialname.value = ''
}

function materialEntfernen(stueck: Materialvorlage) {
  const stelle = arbeitsmappe.kataloge.material.indexOf(stueck)
  if (stelle >= 0) arbeitsmappe.kataloge.material.splice(stelle, 1)
}

/**
 * Ein Wort an einer Person: was der Katalog noch nicht kennt, kommt dort dazu — so wie ein neu
 * geschriebenes Stichwort oder ein neues Materialstück. Die Knöpfe daneben bleiben der schnelle
 * Weg für alles, was schon geführt wird.
 */
function wortGeben(liste: 'rollen' | 'fahrerlaubnisse', an: string[], feld: HTMLInputElement) {
  const wert = feld.value.trim()
  feld.value = ''
  if (!wert) return
  wortHinzufuegen(arbeitsmappe.kataloge[liste], wert)
  if (!an.includes(wert)) an.push(wert)
}

function ortEntfernen(ort: Ort) {
  const stelle = arbeitsmappe.kataloge.orte.indexOf(ort)
  if (stelle >= 0) arbeitsmappe.kataloge.orte.splice(stelle, 1)
}

function stichwortHinzufuegen() {
  const text = stichwort.value.trim()
  if (!text || arbeitsmappe.kataloge.stichwoerter.some(e => e.text === text)) return
  arbeitsmappe.kataloge.stichwoerter.push({id: crypto.randomUUID(), text})
  stichwort.value = ''
}

/**
 * Removing a Stichwort leaves the Alarme that pointed at it holding the text they last printed,
 * so a sheet already written does not go blank because the catalogue was tidied up.
 */
/** Ein Vorschlag mit einem Klick: das Standardstichwort steht danach im Katalog. */
function stichwortUebernehmen(text: string) {
  arbeitsmappe.kataloge.stichwoerter.push({id: crypto.randomUUID(), text})
}

function stichwortEntfernen(index: number) {
  const eintrag = arbeitsmappe.kataloge.stichwoerter[index]
  if (!eintrag) return
  for (const alarm of arbeitsmappe.alarme) {
    if (alarm.stichwortId !== eintrag.id) continue
    alarm.stichwort = eintrag.text
    alarm.stichwortId = ''
  }
  arbeitsmappe.kataloge.stichwoerter.splice(index, 1)
}

const entwurf = ref<Record<string, string>>({})

function hinzufuegen(schluessel: Wortliste) {
  const wert = (entwurf.value[schluessel] ?? '').trim()
  if (!wert || arbeitsmappe.kataloge[schluessel].includes(wert)) return
  arbeitsmappe.kataloge[schluessel].push(wert)
  entwurf.value[schluessel] = ''
}

function entfernen(schluessel: Wortliste, index: number) {
  arbeitsmappe.kataloge[schluessel].splice(index, 1)
}

function fahrzeugHinzufuegen() {
  arbeitsmappe.kataloge.fahrzeuge.push({
    id: crypto.randomUUID(), funkrufname: '',
    staerke: '', ezp: '', status: '', plaetze: '', fuehrerschein: '',
  })
}

/** As with a Stichwort: what the vehicle rows last printed stays on them. */
function fahrzeugEntfernen(index: number) {
  const vorlage = arbeitsmappe.kataloge.fahrzeuge[index]
  if (!vorlage) return
  for (const alarm of arbeitsmappe.alarme) {
    for (const gruppe of alarm.einsatzmittel) {
      for (const fahrzeug of gruppe.fahrzeuge) {
        if (fahrzeug.vorlageId !== vorlage.id) continue
        fahrzeug.funkrufname = vorlage.funkrufname
        fahrzeug.vorlageId = ''
      }
    }
  }
  arbeitsmappe.kataloge.fahrzeuge.splice(index, 1)
}

/**
 * Renaming an entry reaches every Alarm pointing at it — which is the whole reason the catalogue
 * has ids. An Alarm that merely happens to read the same, because someone typed the word rather
 * than picking it, is left alone: it was never linked to this entry.
 */
function stichwortUmbenannt(eintrag: Stichwortvorlage) {
  for (const alarm of arbeitsmappe.alarme) {
    if (alarm.stichwortId === eintrag.id) alarm.stichwort = eintrag.text
  }
}

function fahrzeugUmbenannt(vorlage: Fahrzeugvorlage) {
  for (const alarm of arbeitsmappe.alarme) {
    for (const gruppe of alarm.einsatzmittel) {
      for (const fahrzeug of gruppe.fahrzeuge) {
        if (fahrzeug.vorlageId === vorlage.id) fahrzeug.funkrufname = vorlage.funkrufname
      }
    }
  }
}

/** Shows what the strength will print as, so a wrong number is visible before it is used. */
function truppVorschau(staerke: string): string {
  const zahl = Number(staerke)
  return Number.isFinite(zahl) && zahl > 0 ? truppText(zahl) : ''
}
</script>

<template>
  <div class="grid gap-5">
    <datalist id="rollenliste">
      <option v-for="wert in arbeitsmappe.kataloge.rollen" :key="wert" :value="wert"/>
    </datalist>
    <datalist id="klassenliste">
      <option v-for="wert in arbeitsmappe.kataloge.fahrerlaubnisse" :key="wert" :value="wert"/>
    </datalist>
    <datalist id="stichwortliste">
      <option v-for="text in stichwortvorschlaege" :key="text" :value="text"/>
    </datalist>
    <div>
      <h1 class="headline text-2xl">{{ t('kataloge.titel') }}</h1>
      <p class="text-muted text-sm mt-1">{{ t('kataloge.beschreibung') }}</p>
    </div>

    <section class="abschnitt">
      <h2 class="abschnitt-titel">{{ t('planung.titel') }}</h2>
      <label class="flex items-center gap-3 cursor-pointer">
        <input v-model="arbeitsmappe.planung.aktiv" type="checkbox" class="h-4 w-4"/>
        <span class="text-sm">{{ t('planung.einschalten') }}</span>
      </label>
      <p class="text-muted text-[13px] mt-2">{{ t('planung.einschaltenHinweis') }}</p>
    </section>

    <KlappAbschnitt name="dienststelle" :titel="t('kataloge.dienststelle')">
      <div class="grid md:grid-cols-3 gap-3">
        <TextFeld v-model="arbeitsmappe.kataloge.arbeitsgruppe" :label="t('feld.arbeitsgruppe')"/>
        <TextFeld v-model="arbeitsmappe.kataloge.wacheName" :label="t('kataloge.wacheName')"
                  :platzhalter="t('kataloge.wachePlatzhalter')"/>
      </div>
      <p class="text-muted text-[13px] mt-3 mb-4">{{ t('kataloge.arbeitsgruppeHinweis') }}</p>

      <AdresseFeld v-model="arbeitsmappe.kataloge.wache" :titel="t('kataloge.wache')"/>
      <p class="text-muted text-[13px] mt-3">{{ t('kataloge.wacheHinweis') }}</p>
    </KlappAbschnitt>

    <KlappAbschnitt name="orte" :titel="t('kataloge.orte')"
                    :anzahl="arbeitsmappe.kataloge.orte.length + 1">
      <template #werkzeug>
        <button type="button" class="knopf knopf-klein" @click="ortAnlegen">
          <font-awesome-icon icon="fa-solid fa-plus"/>
          {{ t('kataloge.ortNeu') }}
        </button>
      </template>
      <p class="text-muted text-[13px] mb-3">{{ t('kataloge.orteHinweis') }}</p>

      <div class="grid gap-4">
        <div class="border border-rule rounded p-3 bg-page">
          <span class="label">{{ arbeitsmappe.kataloge.wacheName || t('kataloge.dienststelle') }}</span>
          <p class="text-muted text-[13px] mt-1">{{ t('kataloge.dienststelleOrt') }}</p>
        </div>

        <div v-for="ort in arbeitsmappe.kataloge.orte" :key="ort.id"
             class="border border-rule rounded p-3 bg-page grid gap-3">
          <div class="grid md:grid-cols-[1fr_auto] gap-3 items-end">
            <TextFeld v-model="ort.name" :label="t('kataloge.ortName')"
                      :platzhalter="t('kataloge.ortPlatzhalter')"/>
            <button type="button" class="knopf knopf-klein knopf-gefahr"
                    @click="ortEntfernen(ort)">
              <font-awesome-icon icon="fa-solid fa-trash"/>
              {{ t('kataloge.ortEntfernen') }}
            </button>
          </div>
          <AdresseFeld v-model="ort.adresse" :titel="t('kataloge.ortAdresse')"/>
        </div>
      </div>
    </KlappAbschnitt>

    <KlappAbschnitt name="fahrzeuge" :titel="t('kataloge.fahrzeuge')"
                    :anzahl="arbeitsmappe.kataloge.fahrzeuge.length">
      <template #werkzeug>
        <button type="button" class="knopf knopf-klein" @click="fahrzeugHinzufuegen">
          <font-awesome-icon icon="fa-solid fa-plus"/>
          {{ t('kataloge.hinzufuegen') }}
        </button>
      </template>
      <p class="text-muted text-[13px] mb-3">{{ t('kataloge.fahrzeugeHinweis') }}</p>

      <p v-if="!arbeitsmappe.kataloge.fahrzeuge.length" class="text-muted text-sm">
        {{ t('kataloge.leer') }}
      </p>

      <div class="grid gap-2" @focusout="verlassen($event, fahrzeuge.ordnen)">
        <div v-for="fahrzeug in fahrzeuge.liste" :key="fahrzeug.id"
             class="grid md:grid-cols-[1fr_auto] gap-2 items-end">
          <div class="grid grid-cols-2 gap-2"
               :class="arbeitsmappe.planung.aktiv ? 'md:grid-cols-6' : 'md:grid-cols-4'">
            <TextFeld v-model="fahrzeug.funkrufname" :label="t('feld.funkrufname')"
                      @change="fahrzeugUmbenannt(fahrzeug)"/>
            <TextFeld v-model="fahrzeug.staerke" :label="t('feld.staerke')"/>
            <TextFeld v-model="fahrzeug.ezp" :label="t('feld.ezp')"/>
            <TextFeld v-model="fahrzeug.status" :label="t('feld.status')"/>
            <TextFeld v-if="arbeitsmappe.planung.aktiv" v-model="fahrzeug.plaetze"
                      :label="t('planung.plaetze')"/>
            <TextFeld v-if="arbeitsmappe.planung.aktiv" v-model="fahrzeug.fuehrerschein"
                      :label="t('planung.fuehrerschein')"
                      :vorschlaege="arbeitsmappe.kataloge.fahrerlaubnisse"/>
          </div>
          <button type="button" class="knopf knopf-klein knopf-gefahr"
                  :title="t('kataloge.eintragEntfernen')"
                  @click="fahrzeugEntfernen(arbeitsmappe.kataloge.fahrzeuge.indexOf(fahrzeug))">
            <font-awesome-icon icon="fa-solid fa-xmark"/>
          </button>
          <p v-if="truppVorschau(fahrzeug.staerke)" class="tabular text-[13px] text-muted md:col-span-2">
            {{ truppVorschau(fahrzeug.staerke) }}
          </p>
        </div>
      </div>
    </KlappAbschnitt>

    <KlappAbschnitt name="material" :titel="t('kataloge.material')"
                    :anzahl="arbeitsmappe.kataloge.material.length">
      <p class="text-muted text-[13px] mb-3">{{ t('kataloge.materialHinweis') }}</p>
      <form class="flex gap-2 mb-3" @submit.prevent="materialHinzufuegen">
        <input v-model="materialname" type="text" class="field"
               :placeholder="t('kataloge.materialPlatzhalter')"/>
        <button type="submit" class="knopf shrink-0">
          <font-awesome-icon icon="fa-solid fa-plus"/>
        </button>
      </form>
      <p v-if="!arbeitsmappe.kataloge.material.length" class="text-muted text-sm">
        {{ t('kataloge.keinMaterial') }}
      </p>
      <div class="grid gap-2" @focusout="verlassen($event, materialliste.ordnen)">
        <div v-for="stueck in materialliste.liste" :key="stueck.id"
             class="flex gap-2 items-center">
          <input v-model="stueck.name" type="text" class="field"/>
          <input v-model.number="stueck.bestand" type="number" min="0" step="1"
                 class="field field-menge shrink-0 tabular" :title="t('kataloge.bestand')"
                 :placeholder="t('kataloge.bestandPlatzhalter')"/>
          <button type="button" class="knopf knopf-klein knopf-gefahr shrink-0"
                  @click="materialEntfernen(stueck)">
            <font-awesome-icon icon="fa-solid fa-trash"/>
          </button>
        </div>
      </div>
    </KlappAbschnitt>

    <KlappAbschnitt name="stichwoerter" :titel="t('kataloge.stichwoerter')"
                    :anzahl="arbeitsmappe.kataloge.stichwoerter.length">
      <p class="text-muted text-[13px] mb-3">{{ t('kataloge.stichwoerterHinweis') }}</p>

      <form class="flex gap-2 mb-3" @submit.prevent="stichwortHinzufuegen">
        <input v-model="stichwort" type="text" class="field" list="stichwortliste"
               :placeholder="t('kataloge.stichwortPlatzhalter')"/>
        <button type="submit" class="knopf shrink-0">
          <font-awesome-icon icon="fa-solid fa-plus"/>
        </button>
      </form>
      <p v-if="stichwortvorschlaege.length" class="text-muted text-[13px] mb-3">
        {{ t('kataloge.stichwortFehlen') }}
        <button v-for="text in stichwortvorschlaege" :key="text" type="button"
                class="knopf knopf-klein ml-2 mb-1" @click="stichwortUebernehmen(text)">
          {{ text }}
        </button>
      </p>

      <p v-if="!arbeitsmappe.kataloge.stichwoerter.length" class="text-muted text-sm">
        {{ t('kataloge.leer') }}
      </p>

      <div class="grid md:grid-cols-2 gap-2" @focusout="verlassen($event, stichwoerter.ordnen)">
        <div v-for="eintrag in stichwoerter.liste" :key="eintrag.id"
             class="flex gap-2 items-center">
          <input v-model="eintrag.text" type="text" class="field"
                 @change="stichwortUmbenannt(eintrag)"/>
          <button type="button" class="knopf knopf-klein knopf-gefahr shrink-0"
                  :title="t('kataloge.eintragEntfernen')"
                  @click="stichwortEntfernen(arbeitsmappe.kataloge.stichwoerter.indexOf(eintrag))">
            <font-awesome-icon icon="fa-solid fa-xmark"/>
          </button>
        </div>
      </div>
    </KlappAbschnitt>

    <KlappAbschnitt name="tage" :titel="t('planung.tage')"
                    :anzahl="arbeitsmappe.kataloge.tage.length">
      <template #werkzeug>
        <button type="button" class="knopf knopf-klein" @click="tagAnlegen">
          <font-awesome-icon icon="fa-solid fa-plus"/>
          {{ t('planung.tagNeu') }}
        </button>
      </template>
      <p v-if="!arbeitsmappe.kataloge.tage.length" class="text-muted text-sm">{{ t('planung.keineTage') }}</p>

      <div class="grid gap-2">
        <div v-for="tag in arbeitsmappe.kataloge.tage" :key="tag.id"
             class="grid md:grid-cols-[10rem_1fr_auto] gap-2 items-end">
          <div>
            <label class="feld-label">{{ t('planung.datum') }}</label>
            <input v-model="tag.datum" type="date" class="field"/>
          </div>
          <TextFeld v-model="tag.name" :label="t('planung.tagName')"
                    :platzhalter="t('planung.tagPlatzhalter')"/>
          <button type="button" class="knopf knopf-klein knopf-gefahr"
                  @click="ausListe(arbeitsmappe.kataloge.tage, tag)">
            <font-awesome-icon icon="fa-solid fa-xmark"/>
          </button>
        </div>
      </div>
    </KlappAbschnitt>

    <KlappAbschnitt name="personen" :titel="t('planung.personen')"
                    :anzahl="arbeitsmappe.kataloge.personen.length">
      <template #werkzeug>
        <button type="button" class="knopf knopf-klein" @click="personAnlegen">
          <font-awesome-icon icon="fa-solid fa-plus"/>
          {{ t('planung.personNeu') }}
        </button>
      </template>
      <p class="text-muted text-[13px] mb-3">{{ t('planung.personenHinweis') }}</p>
      <p v-if="!arbeitsmappe.kataloge.personen.length" class="text-muted text-sm">
        {{ t('planung.keinePersonen') }}
      </p>

      <div class="grid gap-4">
        <div v-for="person in arbeitsmappe.kataloge.personen" :key="person.id"
             class="border border-rule rounded p-3 bg-page grid gap-3">
          <div class="grid md:grid-cols-[1fr_6rem_auto] gap-3 items-end">
            <TextFeld v-model="person.name" :label="t('planung.personName')"/>
            <div>
              <label class="feld-label">{{ t('planung.anzahl') }}</label>
              <input v-model.number="person.anzahl" type="number" min="1" class="field"/>
            </div>
            <button type="button" class="knopf knopf-klein knopf-gefahr"
                    @click="ausListe(arbeitsmappe.kataloge.personen, person)">
              <font-awesome-icon icon="fa-solid fa-trash"/>
            </button>
          </div>

          <div class="grid md:grid-cols-2 gap-3">
            <div>
              <span class="feld-label">{{ t('planung.rollen') }}</span>
              <div class="flex flex-wrap gap-2 items-center">
                <button v-for="wert in arbeitsmappe.kataloge.rollen" :key="wert" type="button"
                        class="knopf knopf-klein"
                        :class="person.rollen.includes(wert) ? 'knopf-primaer' : ''"
                        @click="umschalten(person.rollen, wert)">
                  {{ wert }}
                </button>
                <input type="text" class="field w-auto" list="rollenliste"
                       :placeholder="t('planung.rolleDazu')"
                       @change="wortGeben('rollen', person.rollen, $event.target as HTMLInputElement)"/>
              </div>
            </div>
            <div>
              <span class="feld-label">{{ t('planung.fahrerlaubnis') }}</span>
              <div class="flex flex-wrap gap-2 items-center">
                <button v-for="wert in arbeitsmappe.kataloge.fahrerlaubnisse" :key="wert" type="button"
                        class="knopf knopf-klein"
                        :class="person.fahrerlaubnis.includes(wert) ? 'knopf-primaer' : ''"
                        @click="umschalten(person.fahrerlaubnis, wert)">
                  {{ wert }}
                </button>
                <input type="text" class="field w-auto" list="klassenliste"
                       :placeholder="t('planung.klasseDazu')"
                       @change="wortGeben('fahrerlaubnisse', person.fahrerlaubnis,
                                          $event.target as HTMLInputElement)"/>
              </div>
            </div>
          </div>

          <div>
            <div class="flex items-center gap-3 mb-2 flex-wrap">
              <span class="feld-label mb-0">{{ t('planung.verfuegbar') }}</span>
              <button type="button" class="knopf knopf-klein"
                      @click="verfuegbarkeitAnlegen(person)">
                <font-awesome-icon icon="fa-solid fa-plus"/>
                {{ t('planung.fensterNeu') }}
              </button>
            </div>
            <p v-if="!person.verfuegbar.length" class="text-muted text-[13px]">
              {{ t('planung.immerDa') }}
            </p>
            <div class="grid gap-2">
              <div v-for="fenster in person.verfuegbar" :key="fenster.id"
                   class="grid md:grid-cols-[1fr_1fr_auto] gap-2 items-end">
                <div>
                  <label class="feld-label">{{ t('planung.von') }}</label>
                  <input v-model="fenster.von" type="datetime-local" class="field"/>
                </div>
                <div>
                  <label class="feld-label">{{ t('planung.bis') }}</label>
                  <input v-model="fenster.bis" type="datetime-local" class="field"/>
                </div>
                <button type="button" class="knopf knopf-klein knopf-gefahr"
                        @click="ausListe(person.verfuegbar, fenster)">
                  <font-awesome-icon icon="fa-solid fa-xmark"/>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </KlappAbschnitt>
    <div class="grid md:grid-cols-2 gap-4">
      <KlappAbschnitt v-for="liste in listen" :key="liste.schluessel" :name="liste.schluessel"
                      :titel="liste.titel" :anzahl="arbeitsmappe.kataloge[liste.schluessel].length">

        <form class="flex gap-2 mb-3" @submit.prevent="hinzufuegen(liste.schluessel)">
          <input v-model="entwurf[liste.schluessel]" type="text" class="field"/>
          <button type="submit" class="knopf shrink-0">
            <font-awesome-icon icon="fa-solid fa-plus"/>
          </button>
        </form>

        <p v-if="!arbeitsmappe.kataloge[liste.schluessel].length" class="text-muted text-sm">
          {{ t('kataloge.leer') }}
        </p>

        <ul class="flex flex-wrap gap-2">
          <li v-for="(wert, index) in arbeitsmappe.kataloge[liste.schluessel]" :key="wert"
              class="flex items-center gap-2 border border-rule rounded px-2 py-1 bg-page">
            <span class="text-sm">{{ wert }}</span>
            <button type="button" class="text-muted hover:text-signal"
                    :title="t('kataloge.eintragEntfernen')"
                    @click="entfernen(liste.schluessel, index)">
              <font-awesome-icon icon="fa-solid fa-xmark"/>
            </button>
          </li>
        </ul>
      </KlappAbschnitt>
    </div>
  </div>
</template>
