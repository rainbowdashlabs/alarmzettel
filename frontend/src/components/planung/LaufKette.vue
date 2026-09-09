<script setup lang="ts">
import {computed} from 'vue'
import {t} from '../../i18n'
import {arbeitsmappe} from '../../store/arbeitsmappe'
import {
  besatzungHinzufuegen, entfernen, fahrerSetzen, fahrzeitSchaetzen, letzterSchritt, nachziehen,
  alleOrte, darfFahren, lageName, materialHinzufuegen, materialName, materialSichern,
  mehrereTage, personName, plandaten, programmpunkt, programmpunktAnlegen, schrittAnhaengen,
} from '../../store/planung'
import {fahrzeitSchaetzung, pruefen} from '../../scripts/ablauf'
import type {Befund} from '../../scripts/ablauf'
import {alsMinuten, dauer, tagVon, uhrzeit, verschieben} from '../../scripts/zeit'
import type {Lauf, Schritt} from '../../interfaces/Planung'

const {lauf} = defineProps<{ lauf: Lauf }>()

/**
 * Geprüft wird der ganze Plan, angezeigt wird am Schritt. Ein Zustieg ins Nichts oder eine
 * Person an zwei Orten entsteht zwischen zwei Ketten, gehört aber dorthin, wo man es abstellen
 * kann — an den Schritt, in dem sie steht.
 */
const befunde = computed(() => {
  const nachSchritt = new Map<string, Befund[]>()
  for (const befund of pruefen(plandaten())) {
    if (!befund.schrittId) continue
    const bisher = nachSchritt.get(befund.schrittId) ?? []
    bisher.push(befund)
    nachSchritt.set(befund.schrittId, bisher)
  }
  return nachSchritt
})

/**
 * Wie lange die Luftlinie zwischen den beiden Orten dauern würde. Sie steht neben der geplanten
 * Zeit, statt beim Anlegen einmal aufzublitzen und dann zu verschwinden — überschrieben wird sie
 * weiterhin, sie ist ein Vorschlag und keine Vorschrift.
 */
function schaetzung(schritt: Schritt): number | null {
  return fahrzeitSchaetzung(plandaten(), lauf, schritt)
}

function meldung(befund: Befund): string {
  return t(`ablauf.befund.${befund.art}`, befund.werte ?? {})
}

/** Wie viele Köpfe an Bord sind — „Mimen (4)“ zählt vier. */
function koepfe(schritt: Schritt): number {
  return schritt.besatzung.reduce((summe, sitzt) => {
    const person = arbeitsmappe.kataloge.personen.find(p => p.id === sitzt.personId)
    return summe + (person?.anzahl || 1)
  }, 0)
}

/**
 * Was zuletzt als Fahrzeit vorgeschlagen wurde. Eine Dauer, die noch genau so dasteht, darf ein
 * neuer Vorschlag ersetzen; eine von Hand gesetzte bleibt stehen, auch wenn sich das Ziel noch
 * einmal ändert — die Schätzung wird vorgeschlagen und nicht gesetzt.
 */
const vorgeschlagen = new Map<string, number>()

async function anhaengen(art: Schritt['art']) {
  const vorher = letzterSchritt(lauf)
  const schritt = schrittAnhaengen(lauf, art)
  if (art === 'fahrt' && vorher) {
    schritt.ortId = vorher.ortId
    vorgeschlagen.set(schritt.id, dauer(schritt.von, schritt.bis) ?? 0)
  }
}

/** Beim Wechsel des Ziels die geschätzte Fahrzeit vorschlagen, solange keine eigene dasteht. */
async function zielGewaehlt(schritt: Schritt) {
  if (schritt.art !== 'fahrt') return
  const stelle = lauf.schritte.indexOf(schritt)
  const vorher = lauf.schritte[stelle - 1]
  if (!vorher) return
  const eigene = dauer(schritt.von, schritt.bis)
  if (eigene !== null && eigene !== vorgeschlagen.get(schritt.id)) return
  const minuten = await fahrzeitSchaetzen(vorher.ortId, schritt.ortId, schritt.mittel)
  if (minuten === null) return
  vorgeschlagen.set(schritt.id, minuten)
  schritt.bis = verschieben(schritt.von, minuten)
  nachziehen(lauf, schritt)
}

/**
 * Ein Schritt fängt an, wo der vorige aufhört. Wird der Beginn vorgezogen, endet der vorige
 * eben früher; wird er nach hinten geschoben, bleibt eine Lücke — die ist erlaubt und heißt,
 * dass hier gewartet wird. Was nicht entstehen darf, ist eine Überschneidung.
 */
function beginnGesetzt(schritt: Schritt) {
  const stelle = lauf.schritte.indexOf(schritt)
  const vorher = lauf.schritte[stelle - 1]
  const beginn = alsMinuten(schritt.von)
  if (vorher && beginn !== null && beginn < (alsMinuten(vorher.bis) ?? 0)) vorher.bis = schritt.von
  if (beginn !== null && beginn >= (alsMinuten(schritt.bis) ?? 0)) {
    schritt.bis = verschieben(schritt.von, 5)
  }
  nachziehen(lauf, schritt)
}

/** Ein Name, den es noch nicht gibt, wird angelegt; einer aus der Liste wird nur ausgewählt. */
function materialGewaehlt(schritt: Schritt, feld: HTMLInputElement) {
  const materialId = materialSichern(feld.value)
  if (materialId) materialHinzufuegen(schritt, materialId)
  feld.value = ''
}

function lageAnlegen(schritt: Schritt) {
  schritt.programmpunktId = programmpunktAnlegen(schritt.ortId).id
}
</script>

<template>
  <div class="grid gap-2">
    <datalist id="materialliste">
      <option v-for="stueck in arbeitsmappe.kataloge.material" :key="stueck.id"
              :value="stueck.name"/>
    </datalist>
    <div v-for="(schritt, stelle) in lauf.schritte" :key="schritt.id"
         class="border border-rule rounded p-3 bg-page grid gap-2">
      <div class="flex items-center gap-2 flex-wrap">
        <span class="label">{{ stelle + 1 }}.</span>
        <span class="tabular text-sm">
          <span v-if="mehrereTage()" class="text-muted">{{ tagVon(schritt.von) }}</span>
          {{ uhrzeit(schritt.von) }}–{{ uhrzeit(schritt.bis) }}
        </span>
        <span class="text-muted text-[13px]">{{ dauer(schritt.von, schritt.bis) }} min</span>
        <span v-if="schaetzung(schritt) !== null" class="text-muted text-[13px]"
              :title="t('ablauf.schaetzungHinweis')">
          <font-awesome-icon
            :icon="schritt.mittel === 'fahrzeug' ? 'fa-solid fa-truck' : 'fa-solid fa-person-walking'"
            class="mr-1"/>
          {{ t('ablauf.geschaetzt', {n: schaetzung(schritt)}) }}
        </span>
        <span class="grow"></span>
        <button type="button" class="knopf knopf-klein knopf-gefahr"
                @click="entfernen(lauf.schritte, schritt)">
          <font-awesome-icon icon="fa-solid fa-xmark"/>
        </button>
      </div>

      <div class="grid md:grid-cols-4 gap-2 items-end">
        <div>
          <label class="feld-label">{{ t('ablauf.beginn') }}</label>
          <input v-model="schritt.von" type="datetime-local" step="300" class="field"
                 @change="beginnGesetzt(schritt)"/>
        </div>
        <div>
          <label class="feld-label">{{ t('ablauf.ende') }}</label>
          <input v-model="schritt.bis" type="datetime-local" step="300" class="field"
                 @change="nachziehen(lauf, schritt)"/>
        </div>
        <div>
          <label class="feld-label">
            {{ schritt.art === 'fahrt' ? t('ablauf.ziel') : t('ablauf.ort') }}
          </label>
          <select v-model="schritt.ortId" class="field" @change="zielGewaehlt(schritt)">
            <option v-for="ort in alleOrte()" :key="ort.id" :value="ort.id">
              {{ ort.name || t('ablauf.ohneName') }}
            </option>
          </select>
        </div>
        <div v-if="schritt.art === 'fahrt' && !lauf.fahrzeugId">
          <label class="feld-label">{{ t('ablauf.mittel') }}</label>
          <select v-model="schritt.mittel" class="field" @change="zielGewaehlt(schritt)">
            <option value="fuss">{{ t('ablauf.zuFuss') }}</option>
            <option value="eigen">{{ t('ablauf.eigen') }}</option>
          </select>
        </div>
        <div v-else-if="schritt.art === 'aufenthalt'" class="md:col-span-1">
          <label class="feld-label">{{ t('ablauf.lage') }}</label>
          <div class="flex gap-2">
            <select v-model="schritt.programmpunktId" class="field">
              <option value="">{{ t('ablauf.keineLage') }}</option>
              <option v-for="punkt in arbeitsmappe.planung.programmpunkte" :key="punkt.id"
                      :value="punkt.id">
                {{ lageName(punkt.id) || t('ablauf.ohneName') }}
              </option>
            </select>
            <button type="button" class="knopf knopf-klein shrink-0" :title="t('ablauf.lageNeu')"
                    @click="lageAnlegen(schritt)">
              <font-awesome-icon icon="fa-solid fa-plus"/>
            </button>
          </div>
        </div>
      </div>

      <div v-if="schritt.programmpunktId && programmpunkt(schritt.programmpunktId)"
           class="grid md:grid-cols-2 gap-2">
        <label v-if="lauf.fahrzeugId" class="flex items-center gap-2 text-sm md:col-span-2">
          <input v-model="schritt.aufgebot" type="checkbox"/>
          {{ t('ablauf.imAufgebot') }}
          <span class="text-muted text-[13px]">{{ t('ablauf.imAufgebotHinweis') }}</span>
        </label>
        <div v-if="!programmpunkt(schritt.programmpunktId)!.alarmId">
          <label class="feld-label">{{ t('ablauf.lageName') }}</label>
          <input v-model="programmpunkt(schritt.programmpunktId)!.name" type="text" class="field"/>
        </div>
        <div>
          <label class="feld-label">{{ t('ablauf.lageAlarm') }}</label>
          <select v-model="programmpunkt(schritt.programmpunktId)!.alarmId" class="field">
            <option value="">{{ t('ablauf.ohneAlarm') }}</option>
            <option v-for="alarm in arbeitsmappe.alarme" :key="alarm.id" :value="alarm.id">
              {{ alarm.stichwort || t('ablauf.ohneName') }}
            </option>
          </select>
        </div>
      </div>

      <div v-if="lauf.fahrzeugId">
        <span class="feld-label">{{ t('ablauf.besatzung') }} ({{ koepfe(schritt) }})</span>
        <div class="flex flex-wrap gap-2">
          <span v-for="sitzt in schritt.besatzung" :key="sitzt.id" class="flex">
            <button type="button" class="knopf knopf-klein rounded-r-none"
                    :class="sitzt.faehrt ? 'knopf-primaer' : ''"
                    :disabled="!sitzt.faehrt && !darfFahren(lauf.fahrzeugId, sitzt.personId)"
                    :title="darfFahren(lauf.fahrzeugId, sitzt.personId)
                      ? t('ablauf.fahrerUmschalten')
                      : t('ablauf.darfNichtFahren', {wer: personName(sitzt.personId)})"
                    @click="fahrerSetzen(lauf, schritt, sitzt.personId)">
              <font-awesome-icon v-if="sitzt.faehrt" icon="fa-solid fa-check"/>
              {{ personName(sitzt.personId) }}
            </button>
            <button type="button" class="knopf knopf-klein rounded-l-none border-l-0 px-2"
                    :title="t('ablauf.besatzungEntfernen', {wer: personName(sitzt.personId)})"
                    @click="entfernen(schritt.besatzung, sitzt)">
              <font-awesome-icon icon="fa-solid fa-xmark"/>
            </button>
          </span>
          <select class="field w-auto" @change="besatzungHinzufuegen(schritt, ($event.target as HTMLSelectElement).value); ($event.target as HTMLSelectElement).value = ''">
            <option value="">{{ t('ablauf.personDazu') }}</option>
            <option v-for="person in arbeitsmappe.kataloge.personen" :key="person.id"
                    :value="person.id">{{ person.name || t('ablauf.ohneName') }}</option>
          </select>
        </div>
      </div>

      <div class="grid md:grid-cols-2 gap-3">
        <div>
          <span class="feld-label">{{ t('ablauf.material') }}</span>
          <div class="flex flex-wrap gap-2 items-center">
            <span v-for="stueck in schritt.material" :key="stueck.id" class="flex">
              <input v-model.number="stueck.anzahl" type="number" min="1" step="1"
                     class="field field-menge rounded-r-none tabular"
                     :title="t('ablauf.materialAnzahl')"/>
              <span class="knopf knopf-klein rounded-none border-l-0 cursor-default">
                <font-awesome-icon icon="fa-solid fa-box" class="text-muted"/>
                {{ materialName(stueck.materialId) || t('ablauf.ohneName') }}
              </span>
              <button type="button" class="knopf knopf-klein rounded-l-none border-l-0 px-2"
                      :title="t('ablauf.materialEntfernen',
                                {was: materialName(stueck.materialId)})"
                      @click="entfernen(schritt.material, stueck)">
                <font-awesome-icon icon="fa-solid fa-xmark"/>
              </button>
            </span>
            <input type="text" class="field w-auto" list="materialliste"
                   :placeholder="t('ablauf.materialDazu')"
                   @change="materialGewaehlt(schritt, $event.target as HTMLInputElement)"/>
          </div>
        </div>

        <div>
          <label class="feld-label">{{ t('ablauf.notiz') }}</label>
          <input v-model="schritt.notiz" type="text" class="field"
                 :placeholder="t('ablauf.notizPlatzhalter')"/>
        </div>
      </div>

      <div v-if="befunde.get(schritt.id)?.length" class="flex flex-wrap gap-3">
        <span v-for="(befund, nummer) in befunde.get(schritt.id)" :key="nummer"
              class="text-signal-ink text-[13px]">{{ meldung(befund) }}</span>
      </div>
    </div>

    <div class="flex gap-2">
      <button type="button" class="knopf knopf-klein" @click="anhaengen('aufenthalt')">
        <font-awesome-icon icon="fa-solid fa-plus"/>
        {{ t('ablauf.aufenthalt') }}
      </button>
      <button type="button" class="knopf knopf-klein" @click="anhaengen('fahrt')">
        <font-awesome-icon icon="fa-solid fa-angle-right"/>
        {{ t('ablauf.fahrt') }}
      </button>
    </div>
  </div>
</template>
