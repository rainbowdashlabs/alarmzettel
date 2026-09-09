<script setup lang="ts">
import {computed} from 'vue'
import {t} from '../../i18n'
import {arbeitsmappe} from '../../store/arbeitsmappe'
import {lageName, mehrereTage, ortName, plandaten} from '../../store/planung'
import {anfahrt, personenplan, pruefen} from '../../scripts/ablauf'
import type {Befund, Personenschritt} from '../../scripts/ablauf'
import {tagwechsel, uhrzeit} from '../../scripts/zeit'

/** Eine Zeile des Plans: ein Schritt, oder die Fahrt, die zu ihm hinführt. */
interface Planzeile {
  schluessel: string
  von: string
  bis: string
  was: string
  lage: string
  womit: string
}

/**
 * Der Plan einer Person wird nirgends gepflegt: er ist die Summe der Schritte, in deren Besatzung
 * sie steht, plus ihre eigenen. Personenplan und Fahrzeugplan können sich deshalb nicht
 * widersprechen.
 */
const plaene = computed(() => arbeitsmappe.kataloge.personen.map(person => {
  const zeilen = personenplan(plandaten(), person.id).flatMap(zeilenVon)
  return {person, zeilen, tage: tagwechsel(zeilen.map(zeile => zeile.von))}
}))

/**
 * Die Zeilen zu einem Schritt. Fährt jemand die erzeugte Anfahrt mit, bekommt sie eine eigene —
 * sonst stünde da, er sei um 7:50 schon dort, wo er erst hinfährt.
 */
function zeilenVon(eintrag: Personenschritt): Planzeile[] {
  const zeilen: Planzeile[] = []
  const weg = eintrag.vonOrtId === eintrag.schritt.ortId
      ? null : anfahrt(plandaten(), eintrag.lauf, eintrag.schritt)
  if (weg && eintrag.schritt.art === 'aufenthalt') {
    zeilen.push({
      schluessel: `${eintrag.schritt.id}-anfahrt`, von: weg.von, bis: weg.bis,
      was: `→ ${ortName(weg.nachOrtId) || t('ablauf.ohneName')}`, lage: '',
      womit: womit(eintrag, 'fahrt'),
    })
  }
  zeilen.push({
    schluessel: eintrag.schritt.id, von: eintrag.ankunft, bis: eintrag.schritt.bis,
    was: was(eintrag), lage: lage(eintrag), womit: womit(eintrag, eintrag.schritt.art),
  })
  return zeilen
}

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

function womit(eintrag: Personenschritt, art: string): string {
  if (eintrag.lauf.fahrzeugId) {
    return fahrzeugName(eintrag.lauf.fahrzeugId) +
        (eintrag.faehrt ? ` · ${t('ablauf.faehrt')}` : '')
  }
  if (art !== 'fahrt') return ''
  return t(`ablauf.${eintrag.schritt.mittel === 'eigen' ? 'eigen' : 'zuFuss'}`)
}

function lage(eintrag: Personenschritt): string {
  return lageName(eintrag.schritt.programmpunktId)
}
</script>

<template>
  <div class="grid gap-5">
    <section v-for="plan in plaene" :key="plan.person.id" class="abschnitt">
      <h2 class="abschnitt-titel">
        {{ plan.person.name || t('ablauf.ohneName') }}
        <span v-if="plan.person.anzahl > 1" class="text-muted">({{ plan.person.anzahl }})</span>
      </h2>
      <p v-if="!plan.zeilen.length" class="text-muted text-sm">{{ t('ablauf.ohnePlan') }}</p>
      <table v-else class="w-full text-sm">
        <tbody>
          <tr v-for="(zeile, nummer) in plan.zeilen" :key="zeile.schluessel"
              class="border-t border-rule">
            <td v-if="mehrereTage()" class="tabular py-1 pr-3 text-muted whitespace-nowrap">
              {{ plan.tage[nummer] }}
            </td>
            <td class="tabular py-1 pr-3 whitespace-nowrap">
              {{ uhrzeit(zeile.von) }}–{{ uhrzeit(zeile.bis) }}
            </td>
            <td class="py-1 pr-3">{{ zeile.was }}</td>
            <td class="py-1 pr-3 text-muted">{{ zeile.lage }}</td>
            <td class="py-1 text-muted whitespace-nowrap">{{ zeile.womit }}</td>
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
