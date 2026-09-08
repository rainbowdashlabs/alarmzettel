<script setup lang="ts">
import {t} from '../../i18n'
import {arbeitsmappe} from '../../store/arbeitsmappe'
import {
  besatzungHinzufuegen, entfernen, fahrerSetzen, fahrzeitSchaetzen, letzterSchritt, nachziehen,
  personName, plaetze, programmpunkt, programmpunktAnlegen, schrittAnhaengen,
} from '../../store/planung'
import {dauer, uhrzeit} from '../../scripts/zeit'
import type {Lauf, Schritt} from '../../interfaces/Planung'

const {lauf} = defineProps<{ lauf: Lauf }>()

/** Wie viele Köpfe an Bord sind — „Mimen (4)“ zählt vier. */
function koepfe(schritt: Schritt): number {
  return schritt.besatzung.reduce((summe, sitzt) => {
    const person = arbeitsmappe.planung.personen.find(p => p.id === sitzt.personId)
    return summe + (person?.anzahl || 1)
  }, 0)
}

function zuVoll(schritt: Schritt): boolean {
  const grenze = plaetze(lauf.fahrzeugId)
  return grenze !== null && koepfe(schritt) > grenze
}

/** Fährt jemand, der die Klasse des Fahrzeugs nicht hat? */
function fahrerOhneErlaubnis(schritt: Schritt): string | null {
  const klasse = arbeitsmappe.kataloge.fahrzeuge
      .find(v => v.id === lauf.fahrzeugId)?.fuehrerschein?.trim()
  if (!klasse) return null
  const fahrer = schritt.besatzung.find(sitzt => sitzt.faehrt)
  if (!fahrer) return null
  const person = arbeitsmappe.planung.personen.find(p => p.id === fahrer.personId)
  return person && !person.fahrerlaubnis.includes(klasse) ? person.name : null
}

function ohneFahrer(schritt: Schritt): boolean {
  return Boolean(lauf.fahrzeugId) && schritt.art === 'fahrt' &&
      !schritt.besatzung.some(sitzt => sitzt.faehrt)
}

async function anhaengen(art: Schritt['art']) {
  const vorher = letzterSchritt(lauf)
  const schritt = schrittAnhaengen(lauf, art)
  if (art === 'fahrt' && vorher) {
    // Das Ziel steht noch nicht fest; die Schätzung kommt, sobald es gewählt ist.
    schritt.ortId = vorher.ortId
  }
}

/** Beim Wechsel des Ziels die geschätzte Fahrzeit vorschlagen — überschreiben bleibt möglich. */
async function zielGewaehlt(schritt: Schritt) {
  if (schritt.art !== 'fahrt') return
  const stelle = lauf.schritte.indexOf(schritt)
  const vorher = lauf.schritte[stelle - 1]
  if (!vorher) return
  const minuten = await fahrzeitSchaetzen(vorher.ortId, schritt.ortId, schritt.mittel)
  if (minuten === null) return
  schritt.bis = new Date(Date.parse(`${schritt.von}:00Z`) + minuten * 60000)
      .toISOString().slice(0, 16)
  nachziehen(lauf, schritt)
}

function lageAnlegen(schritt: Schritt) {
  schritt.programmpunktId = programmpunktAnlegen(schritt.ortId).id
}
</script>

<template>
  <div class="grid gap-2">
    <div v-for="(schritt, stelle) in lauf.schritte" :key="schritt.id"
         class="border border-rule rounded p-3 bg-page grid gap-2">
      <div class="flex items-center gap-2 flex-wrap">
        <span class="label">{{ stelle + 1 }}.</span>
        <span class="tabular text-sm">{{ uhrzeit(schritt.von) }}–{{ uhrzeit(schritt.bis) }}</span>
        <span class="text-muted text-[13px]">{{ dauer(schritt.von, schritt.bis) }} min</span>
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
                 @change="nachziehen(lauf, schritt)"/>
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
            <option v-for="ort in arbeitsmappe.planung.orte" :key="ort.id" :value="ort.id">
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
                {{ punkt.name || t('ablauf.ohneName') }}
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
        <div>
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
          <button v-for="sitzt in schritt.besatzung" :key="sitzt.id" type="button"
                  class="knopf knopf-klein" :class="sitzt.faehrt ? 'knopf-primaer' : ''"
                  :title="t('ablauf.fahrerUmschalten')"
                  @click="fahrerSetzen(schritt, sitzt.personId)">
            <font-awesome-icon v-if="sitzt.faehrt" icon="fa-solid fa-check"/>
            {{ personName(sitzt.personId) }}
          </button>
          <select class="field w-auto" @change="besatzungHinzufuegen(schritt, ($event.target as HTMLSelectElement).value); ($event.target as HTMLSelectElement).value = ''">
            <option value="">{{ t('ablauf.personDazu') }}</option>
            <option v-for="person in arbeitsmappe.planung.personen" :key="person.id"
                    :value="person.id">{{ person.name || t('ablauf.ohneName') }}</option>
          </select>
        </div>
        <div class="flex flex-wrap gap-3 mt-1">
          <span v-if="zuVoll(schritt)" class="text-signal-ink text-[13px]">
            {{ t('ablauf.zuVoll', {plaetze: plaetze(lauf.fahrzeugId)}) }}
          </span>
          <span v-if="ohneFahrer(schritt)" class="text-signal-ink text-[13px]">
            {{ t('ablauf.ohneFahrer') }}
          </span>
          <span v-if="fahrerOhneErlaubnis(schritt)" class="text-signal-ink text-[13px]">
            {{ t('ablauf.ohneErlaubnis', {wer: fahrerOhneErlaubnis(schritt)}) }}
          </span>
        </div>
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
