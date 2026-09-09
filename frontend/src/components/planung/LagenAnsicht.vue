<script setup lang="ts">
import {computed} from 'vue'
import {t} from '../../i18n'
import {arbeitsmappe} from '../../store/arbeitsmappe'
import {lageName, mehrereTage, ortName, personName, plandaten} from '../../store/planung'
import {einsaetze, pruefen} from '../../scripts/ablauf'
import type {Befund, Beteiligter} from '../../scripts/ablauf'
import {dauer, tagVon, uhrzeit} from '../../scripts/zeit'

/**
 * Wann welcher Einsatz läuft und wer dort ist. Eine Lage ist der Anlass, ein Einsatz das eine
 * Mal, das sie läuft: zwei Fahrzeuge nacheinander an derselben Lage sind zwei Einsätze, und
 * jeder steht hier für sich.
 */
const liste = computed(() => einsaetze(plandaten()))

/** Ein Befund ohne Schritt und ohne Person hängt an der Lage — sonst stünde er nirgends. */
const befunde = computed(() => {
  const nachLage = new Map<string, Befund[]>()
  for (const befund of pruefen(plandaten())) {
    if (!befund.programmpunktId) continue
    nachLage.set(befund.programmpunktId,
        [...(nachLage.get(befund.programmpunktId) ?? []), befund])
  }
  return nachLage
})

function fahrzeugName(fahrzeugId: string): string {
  return arbeitsmappe.kataloge.fahrzeuge.find(v => v.id === fahrzeugId)?.funkrufname
      || t('ablauf.ohneName')
}

function wer(eintrag: Beteiligter): string {
  return eintrag.lauf.fahrzeugId
      ? fahrzeugName(eintrag.lauf.fahrzeugId)
      : personName(eintrag.lauf.personId) || t('ablauf.ohneName')
}

function besatzung(eintrag: Beteiligter): string {
  return eintrag.schritt.besatzung
      .map(sitzt => personName(sitzt.personId))
      .filter(Boolean)
      .join(', ')
}

function alarmStichwort(alarmId: string): string {
  return arbeitsmappe.alarme.find(alarm => alarm.id === alarmId)?.stichwort ?? ''
}

function zeit(wann: string): string {
  return (mehrereTage() ? `${tagVon(wann)} ` : '') + uhrzeit(wann)
}
</script>

<template>
  <div class="grid gap-5">
    <p v-if="!liste.length" class="text-muted text-sm">{{ t('ablauf.keineLagen') }}</p>

    <section v-for="einsatz in liste" :key="`${einsatz.programmpunkt.id}-${einsatz.nummer}`"
             class="abschnitt">
      <div class="flex items-baseline gap-3 flex-wrap">
        <span class="tabular text-lg">{{ zeit(einsatz.von) }}</span>
        <h2 class="abschnitt-titel">
          {{ lageName(einsatz.programmpunkt.id) || t('ablauf.ohneName') }}
        </h2>
        <span v-if="einsatz.nummer > 1" class="label text-muted">
          {{ t('ablauf.derWievielte', {n: einsatz.nummer}) }}
        </span>
        <span class="text-muted text-sm">{{ ortName(einsatz.ortId) }}</span>
        <span class="grow"></span>
        <span class="tabular text-sm text-muted">
          {{ t('ablauf.einsatzZeiten', {
            da: uhrzeit(einsatz.da), bis: uhrzeit(einsatz.bis),
            n: dauer(einsatz.da, einsatz.bis) ?? 0}) }}
        </span>
      </div>

      <p v-if="einsatz.programmpunkt.alarmId" class="text-muted text-[13px] mt-1">
        <font-awesome-icon icon="fa-solid fa-file-pdf" class="mr-1"/>
        {{ alarmStichwort(einsatz.programmpunkt.alarmId) || t('ablauf.ohneName') }}
      </p>

      <table class="w-full text-sm mt-3">
        <tbody>
          <tr v-for="eintrag in einsatz.beteiligte" :key="eintrag.schritt.id"
              class="border-t border-rule">
            <td class="py-1 pr-3 font-bold whitespace-nowrap">{{ wer(eintrag) }}</td>
            <td class="tabular py-1 pr-3 whitespace-nowrap">
              {{ uhrzeit(eintrag.aufbruch) }}–{{ uhrzeit(eintrag.bis) }}
            </td>
            <td class="py-1 pr-3 text-muted">{{ besatzung(eintrag) }}</td>
            <td class="py-1 text-muted text-[13px] whitespace-nowrap">
              <span v-if="eintrag.lauf.fahrzeugId && !eintrag.aufgebot">
                {{ t('ablauf.nurVorOrt') }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>

      <p v-for="(befund, nummer) in befunde.get(einsatz.programmpunkt.id)" :key="nummer"
         class="text-signal-ink text-[13px] mt-2">
        {{ t(`ablauf.befund.${befund.art}`, {
          ...befund.werte, was: lageName(einsatz.programmpunkt.id) || t('ablauf.ohneName')}) }}
      </p>
    </section>
  </div>
</template>
