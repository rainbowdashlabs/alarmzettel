<script setup lang="ts">
import {computed} from 'vue'
import {t} from '../../i18n'
import {arbeitsmappe} from '../../store/arbeitsmappe'
import {alleOrte, lageName, mehrereTage, personName, plandaten} from '../../store/planung'
import {ortssicht} from '../../scripts/ablauf'
import type {Ortsbelegung} from '../../scripts/ablauf'
import {tagwechsel, uhrzeit} from '../../scripts/zeit'

/**
 * Wer und was zu welcher Zeit an einem Ort steht. Das beantwortet „stehen die beiden Fahrzeuge
 * samt Leuten gerade zusammen?“ und macht Fahrerwechsel, Abholung und Übergabe sichtbar, statt
 * sie nur zu melden.
 */
const sichten = computed(() => alleOrte().map(ort => {
  const belegungen = ortssicht(plandaten(), ort.id)
  return {ort, belegungen, tage: tagwechsel(belegungen.map(belegung => belegung.von))}
}))

function wer(belegung: Ortsbelegung): string {
  const namen = belegung.personIds.map(id => personName(id) || t('ablauf.ohneName'))
  const fahrzeug = belegung.lauf.fahrzeugId
      ? arbeitsmappe.kataloge.fahrzeuge.find(v => v.id === belegung.lauf.fahrzeugId)?.funkrufname
      : ''
  return [fahrzeug, namen.join(', ')].filter(Boolean).join(': ')
}

function lage(belegung: Ortsbelegung): string {
  return lageName(belegung.schritt.programmpunktId)
}
</script>

<template>
  <div class="grid gap-5">
    <section v-for="sicht in sichten" :key="sicht.ort.id" class="abschnitt">
      <h2 class="abschnitt-titel">
        {{ sicht.ort.name || t('ablauf.ohneName') }}
        <span class="text-muted font-normal">{{ sicht.ort.adresse.strasse }}
          {{ sicht.ort.adresse.hnr }}</span>
      </h2>
      <p v-if="!sicht.belegungen.length" class="text-muted text-sm">{{ t('ablauf.ortLeer') }}</p>
      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm">
          <tbody>
          <tr v-for="(belegung, zeile) in sicht.belegungen" :key="belegung.schritt.id"
              class="border-t border-rule">
            <td v-if="mehrereTage()" class="tabular py-1 pr-3 text-muted whitespace-nowrap">
              {{ sicht.tage[zeile] }}
            </td>
            <td class="tabular py-1 pr-3 whitespace-nowrap">
              {{ uhrzeit(belegung.von) }}–{{ uhrzeit(belegung.bis) }}
            </td>
            <td class="py-1 pr-3">{{ wer(belegung) }}</td>
            <td class="py-1 text-muted">{{ lage(belegung) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
    <p v-if="!sichten.length" class="text-muted text-sm">{{ t('ablauf.ersteOrte') }}</p>
  </div>
</template>
