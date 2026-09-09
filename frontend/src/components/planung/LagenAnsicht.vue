<script setup lang="ts">
import {computed} from 'vue'
import {t} from '../../i18n'
import {arbeitsmappe} from '../../store/arbeitsmappe'
import {lageName, mehrereTage, ortName, personName, plandaten} from '../../store/planung'
import {lagensicht} from '../../scripts/ablauf'
import {tagVon, uhrzeit} from '../../scripts/zeit'

/** Dieselbe Sache von der anderen Seite: die Lage, und was an ihr hängt. */
const lagen = computed(() => arbeitsmappe.planung.programmpunkte
    .map(punkt => lagensicht(plandaten(), punkt)))

function fahrzeugName(fahrzeugId: string): string {
  return arbeitsmappe.kataloge.fahrzeuge.find(v => v.id === fahrzeugId)?.funkrufname
      || t('ablauf.ohneName')
}

function alarmStichwort(alarmId: string): string {
  return arbeitsmappe.alarme.find(alarm => alarm.id === alarmId)?.stichwort ?? ''
}
</script>

<template>
  <div class="grid gap-5">
    <section v-for="sicht in lagen" :key="sicht.programmpunkt.id" class="abschnitt">
      <div class="flex items-baseline gap-3 flex-wrap">
        <h2 class="abschnitt-titel">
          {{ lageName(sicht.programmpunkt.id) || t('ablauf.ohneName') }}
        </h2>
        <span class="text-muted text-sm">{{ ortName(sicht.ortId) }}</span>
        <span v-if="sicht.von" class="tabular text-sm">
          <span v-if="mehrereTage() || tagVon(sicht.von) !== tagVon(sicht.bis)" class="text-muted">
            {{ tagVon(sicht.von) }}
          </span>
          {{ uhrzeit(sicht.von) }}–{{ uhrzeit(sicht.bis) }}
        </span>
      </div>
      <p v-if="!sicht.laeufe.length" class="text-signal-ink text-[13px] mt-2">
        {{ t('ablauf.befund.lageLeer', {was: lageName(sicht.programmpunkt.id) || t('ablauf.ohneName')}) }}
      </p>
      <div v-else class="grid gap-1 mt-2 text-sm">
        <p>
          <span class="label mr-2">{{ t('ablauf.fahrzeuge') }}</span>
          {{ sicht.laeufe.filter(lauf => lauf.fahrzeugId)
              .map(lauf => fahrzeugName(lauf.fahrzeugId)).join(', ') || '—' }}
        </p>
        <p>
          <span class="label mr-2">{{ t('ablauf.beteiligte') }}</span>
          {{ sicht.personIds.map(id => personName(id) || t('ablauf.ohneName')).join(', ') || '—' }}
        </p>
        <p v-if="sicht.programmpunkt.alarmId">
          <span class="label mr-2">{{ t('ablauf.lageAlarm') }}</span>
          {{ alarmStichwort(sicht.programmpunkt.alarmId) || t('ablauf.ohneName') }}
        </p>
      </div>
    </section>
    <p v-if="!lagen.length" class="text-muted text-sm">{{ t('ablauf.keineLagen') }}</p>
  </div>
</template>
