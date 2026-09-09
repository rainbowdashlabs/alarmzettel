<script setup lang="ts">
import {computed} from 'vue'
import {t} from '../../i18n'
import {codeAnzeige} from '../../scripts/code'
import type {Adresse, Alarm} from '../../interfaces/Alarm'

/**
 * Ein Alarm zum Lesen: dieselben Angaben wie auf dem Zettel, nur als Seite statt als Formular.
 * Was leer ist, steht nicht da — ein Feld ohne Inhalt sagt nichts und nimmt nur Platz.
 */
const {alarm} = defineProps<{ alarm: Alarm }>()

function adresszeile(adresse: Adresse): string {
  const strasse = [adresse.strasse, adresse.hnr].filter(Boolean).join(' ')
  const ort = [adresse.plz, adresse.ort].filter(Boolean).join(' ')
  return [strasse, adresse.objekt, ort].filter(Boolean).join(', ')
}

/** Was der Kopf sonst noch trägt. Nummer und Einsatzzeit stehen schon in der Überschrift. */
const kopf = computed(() => [
  {label: t('feld.meldung'), wert: `${alarm.meldungDatum} ${alarm.meldungZeit}`.trim()},
  {label: t('feld.aPlatz'), wert: alarm.aPlatz},
  {label: t('feld.polizei'), wert: alarm.polizei},
  {label: t('feld.sonderrechte'), wert: alarm.sonderrechte},
  {label: t('feld.arbeitsgruppe'), wert: alarm.arbeitsgruppe},
  {label: t('feld.wachalarmNr'), wert: alarm.wachalarmNr},
].filter(feld => feld.wert))

const meldung = computed(() => [
  {label: t('feld.meldungsquelle'), wert: alarm.meldungsquelle},
  {label: t('feld.anrufer'), wert: alarm.anrufer},
  {label: t('feld.rueckrufnummer'), wert: alarm.rueckrufnummer},
  {label: t('feld.betroffener'), wert: alarm.betroffener},
  {label: t('feld.meldender'), wert: alarm.meldender},
].filter(feld => feld.wert))

const karte = computed(() => [
  {label: t('feld.kab'), wert: alarm.karte.kab},
  {label: t('feld.fwPlan'), wert: alarm.karte.fwPlan},
  {label: t('feld.ePlan'), wert: alarm.karte.ePlan},
  {label: t('feld.polarKoordinaten'), wert: alarm.karte.polarKoordinaten},
].filter(feld => feld.wert))

const fahrzeuge = computed(() =>
    alarm.einsatzmittel.flatMap(gruppe => gruppe.fahrzeuge.map(fahrzeug => ({
      gruppe: gruppe.gruppe, ...fahrzeug,
    }))))
</script>

<template>
  <section class="abschnitt grid gap-4">
    <div>
      <div class="flex items-baseline gap-3 flex-wrap">
        <h2 class="headline text-xl">{{ alarm.stichwort || t('liste.ohneStichwort') }}</h2>
        <span v-if="alarm.einsatzNr" class="tabular text-muted">{{ alarm.einsatzNr }}</span>
        <span class="grow"></span>
        <span class="tabular text-sm">
          {{ `${alarm.einsatzDatum} ${alarm.einsatzZeit}`.trim() }}
        </span>
      </div>
      <p v-if="alarm.kurzinfo" class="text-muted mt-1">{{ alarm.kurzinfo }}</p>
    </div>

    <div v-if="adresszeile(alarm.einsatzadresse)" class="border-t border-rule pt-3">
      <span class="label block mb-1">{{ t('adresse.einsatz') }}</span>
      <p class="text-lg">{{ adresszeile(alarm.einsatzadresse) }}</p>
      <p v-if="adresszeile(alarm.anfahrtsadresse)
             && adresszeile(alarm.anfahrtsadresse) !== adresszeile(alarm.einsatzadresse)"
         class="text-muted text-sm mt-1">
        {{ t('adresse.anfahrt') }}: {{ adresszeile(alarm.anfahrtsadresse) }}
      </p>
    </div>

    <div v-if="fahrzeuge.length" class="border-t border-rule pt-3">
      <span class="label block mb-2">{{ t('abschnitt.einsatzmittel') }}</span>
      <table class="w-full text-sm">
        <tbody>
          <tr v-for="fahrzeug in fahrzeuge" :key="fahrzeug.id" class="border-t border-hairline">
            <td class="py-1 pr-3 font-bold whitespace-nowrap">
              <span v-if="fahrzeug.alarmFuer" class="label text-signal-ink mr-2">
                {{ t('ansicht.fuerDich') }}
              </span>
              {{ fahrzeug.funkrufname }}
            </td>
            <td class="py-1 pr-3 text-muted whitespace-nowrap">{{ fahrzeug.ezp }}</td>
            <td class="py-1 pr-3 text-muted whitespace-nowrap">{{ fahrzeug.status }}</td>
            <td class="py-1 pr-3 text-muted">{{ fahrzeug.trupp || fahrzeug.staerke }}</td>
            <td class="py-1 text-muted">{{ fahrzeug.hinweis }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="alarm.hinweise.length" class="border-t border-rule pt-3">
      <span class="label block mb-2">{{ t('abschnitt.hinweise') }}</span>
      <ul class="grid gap-2 text-sm">
        <li v-for="hinweis in alarm.hinweise" :key="hinweis.id" class="flex gap-2">
          <span class="text-muted">–</span>
          <span v-if="hinweis.typ === 'text'">{{ hinweis.text }}</span>
          <span v-else>
            <span class="tabular font-bold mr-2">{{ codeAnzeige(hinweis.code) }}</span>
            {{ hinweis.meldung }}
            <span v-for="(antwort, nummer) in hinweis.antworten" :key="nummer" class="text-muted">
              <span class="tabular ml-2">{{ nummer + 1 }}.</span> {{ antwort }}
            </span>
          </span>
        </li>
      </ul>
    </div>

    <div v-if="alarm.wasIstPassiert" class="border-t border-rule pt-3">
      <span class="label block mb-1">{{ t('feld.wasIstPassiert') }}</span>
      <p class="text-sm">{{ alarm.wasIstPassiert }}</p>
    </div>

    <div v-if="meldung.length || kopf.length || karte.length"
         class="border-t border-rule pt-3 grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
      <div v-for="feld in [...kopf, ...meldung, ...karte]" :key="feld.label">
        <span class="feld-label">{{ feld.label }}</span>
        <p class="text-sm tabular">{{ feld.wert }}</p>
      </div>
    </div>
  </section>
</template>
