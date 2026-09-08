<script setup lang="ts">
import {computed} from 'vue'
import {t} from '../../i18n'
import {arbeitsmappe} from '../../store/arbeitsmappe'
import {ortName, plandaten} from '../../store/planung'
import {personenplan, pruefen} from '../../scripts/ablauf'
import type {Befund, Personenschritt} from '../../scripts/ablauf'
import {uhrzeit} from '../../scripts/zeit'

/**
 * Der Plan einer Person wird nirgends gepflegt: er ist die Summe der Schritte, in deren Besatzung
 * sie steht, plus ihre eigenen. Personenplan und Fahrzeugplan können sich deshalb nicht
 * widersprechen.
 */
const plaene = computed(() => arbeitsmappe.planung.personen.map(person => ({
  person,
  eintraege: personenplan(plandaten(), person.id),
})))

const befunde = computed(() => {
  const nachPerson = new Map<string, Befund[]>()
  for (const befund of pruefen(plandaten())) {
    if (!befund.personId) continue
    nachPerson.set(befund.personId, [...(nachPerson.get(befund.personId) ?? []), befund])
  }
  return nachPerson
})

function fahrzeugName(fahrzeugId: string): string {
  return arbeitsmappe.kataloge.fahrzeuge.find(v => v.id === fahrzeugId)?.funkrufname
      || t('ablauf.ohneName')
}

function was(eintrag: Personenschritt): string {
  const ort = ortName(eintrag.nachOrtId) || t('ablauf.ohneName')
  return eintrag.schritt.art === 'fahrt' ? `→ ${ort}` : ort
}

function womit(eintrag: Personenschritt): string {
  if (eintrag.lauf.fahrzeugId) {
    return fahrzeugName(eintrag.lauf.fahrzeugId) +
        (eintrag.faehrt ? ` · ${t('ablauf.faehrt')}` : '')
  }
  if (eintrag.schritt.art !== 'fahrt') return ''
  return t(`ablauf.${eintrag.schritt.mittel === 'eigen' ? 'eigen' : 'zuFuss'}`)
}

function lage(eintrag: Personenschritt): string {
  return arbeitsmappe.planung.programmpunkte
      .find(punkt => punkt.id === eintrag.schritt.programmpunktId)?.name ?? ''
}
</script>

<template>
  <div class="grid gap-5">
    <section v-for="plan in plaene" :key="plan.person.id" class="abschnitt">
      <h2 class="abschnitt-titel">
        {{ plan.person.name || t('ablauf.ohneName') }}
        <span v-if="plan.person.anzahl > 1" class="text-muted">({{ plan.person.anzahl }})</span>
      </h2>
      <p v-if="!plan.eintraege.length" class="text-muted text-sm">{{ t('ablauf.ohnePlan') }}</p>
      <table v-else class="w-full text-sm">
        <tbody>
          <tr v-for="eintrag in plan.eintraege" :key="eintrag.schritt.id"
              class="border-t border-rule">
            <td class="tabular py-1 pr-3 whitespace-nowrap">
              {{ uhrzeit(eintrag.schritt.von) }}–{{ uhrzeit(eintrag.schritt.bis) }}
            </td>
            <td class="py-1 pr-3">{{ was(eintrag) }}</td>
            <td class="py-1 pr-3 text-muted">{{ lage(eintrag) }}</td>
            <td class="py-1 text-muted whitespace-nowrap">{{ womit(eintrag) }}</td>
          </tr>
        </tbody>
      </table>
      <p v-for="(befund, nummer) in befunde.get(plan.person.id)" :key="nummer"
         class="text-signal-ink text-[13px] mt-1">
        {{ t(`ablauf.befund.${befund.art}`, befund.werte ?? {}) }}
      </p>
    </section>
    <p v-if="!plaene.length" class="text-muted text-sm">{{ t('ablauf.keinePersonen') }}</p>
  </div>
</template>
