<script setup lang="ts">
import {computed, ref} from 'vue'
import {t} from '../../i18n'
import {plandaten} from '../../store/planung'
import {bewegungsbild, bewegungstage} from '../../scripts/bewegungen'
import type {Balken, Band, Bewegungsbild, Linie} from '../../scripts/bewegungen'

/**
 * Die Gesamtansicht: jeder Ort ein Band, die Zeit nach rechts, jede Kette eine Linie darin. Was
 * sich bewegt, zieht schräg von einem Band ins nächste — die Bewegung selbst ist das Bild.
 */
const MINUTE = 2.4
const REIHE = 30
const BANDLUFT = 10
const RAND = 26
const SPALTE = 150

const bilder = computed(() => bewegungstage(plandaten())
    .map(tag => bewegungsbild(plandaten(), tag)))

const gewaehlt = ref<string | null>(null)

function breite(bild: Bewegungsbild): number {
  return SPALTE + (bild.bis - bild.von) * MINUTE + 20
}

function hoehe(bild: Bewegungsbild): number {
  return RAND + bild.baender.reduce((summe, band) => summe + band.reihen * REIHE + BANDLUFT, 0)
}

function x(bild: Bewegungsbild, minute: number): number {
  return SPALTE + (minute - bild.von) * MINUTE
}

/** Die Oberkante eines Bandes, aufsummiert aus den Höhen der Bänder darüber. */
function bandOben(bild: Bewegungsbild, ortId: string): number {
  let oben = RAND
  for (const band of bild.baender) {
    if (band.ortId === ortId) return oben
    oben += band.reihen * REIHE + BANDLUFT
  }
  return oben
}

function y(bild: Bewegungsbild, ortId: string, reihe: number): number {
  return bandOben(bild, ortId) + reihe * REIHE + REIHE / 2
}

function bandHoehe(band: Band): number {
  return band.reihen * REIHE
}

function stunden(bild: Bewegungsbild): number[] {
  const marken = []
  for (let minute = bild.von; minute <= bild.bis; minute += 60) marken.push(minute)
  return marken
}

function uhr(minute: number): string {
  const innerhalb = ((minute % 1440) + 1440) % 1440
  return `${String(Math.floor(innerhalb / 60)).padStart(2, '0')}:` +
      String(innerhalb % 60).padStart(2, '0')
}

function beschriftung(balken: Balken): string {
  const wer = balken.besatzung.filter(Boolean)
  return wer.length ? `${balken.name} · ${wer.join(', ')}` : balken.name
}

function hervorgehoben(laufId: string): boolean {
  return gewaehlt.value === null || gewaehlt.value === laufId
}

function pfad(bild: Bewegungsbild, linie: Linie): string {
  const x1 = x(bild, linie.von), x2 = x(bild, linie.bis)
  const y1 = y(bild, linie.vonOrtId, linie.vonReihe)
  const y2 = y(bild, linie.nachOrtId, linie.nachReihe)
  const knick = (x1 + x2) / 2
  return `M ${x1} ${y1} C ${knick} ${y1}, ${knick} ${y2}, ${x2} ${y2}`
}
</script>

<template>
  <div class="grid gap-5">
    <p v-if="!bilder.length" class="text-muted text-sm">{{ t('ablauf.keineBewegung') }}</p>

    <section v-for="bild in bilder" :key="bild.datum" class="abschnitt">
      <div class="flex items-baseline gap-3 flex-wrap mb-3">
        <h2 class="abschnitt-titel mb-0">{{ t('ablauf.bewegung') }}</h2>
        <span class="text-muted text-sm">{{ bild.datum }}</span>
        <span class="grow"></span>
        <button v-if="gewaehlt" type="button" class="knopf knopf-klein" @click="gewaehlt = null">
          {{ t('ablauf.alleZeigen') }}
        </button>
      </div>

      <div class="overflow-x-auto">
        <svg :viewBox="`0 0 ${breite(bild)} ${hoehe(bild)}`"
             :width="breite(bild)" :height="hoehe(bild)" class="max-w-none">
          <g>
            <template v-for="minute in stunden(bild)" :key="minute">
              <line :x1="x(bild, minute)" :y1="RAND - 6" :x2="x(bild, minute)"
                    :y2="hoehe(bild)" stroke="currentColor" stroke-opacity="0.15"/>
              <text :x="x(bild, minute)" :y="RAND - 12" text-anchor="middle"
                    fill="currentColor" fill-opacity="0.55" font-size="11">{{ uhr(minute) }}</text>
            </template>
          </g>

          <g v-for="band in bild.baender" :key="band.ortId">
            <rect :x="SPALTE" :y="bandOben(bild, band.ortId)"
                  :width="breite(bild) - SPALTE - 20" :height="bandHoehe(band)"
                  fill="currentColor" fill-opacity="0.04" rx="3"/>
            <text :x="SPALTE - 10" :y="bandOben(bild, band.ortId) + bandHoehe(band) / 2 + 4"
                  text-anchor="end" fill="currentColor" font-size="12" font-weight="600">
              {{ band.name || t('ablauf.ohneName') }}
            </text>
          </g>

          <g v-for="linie in bild.linien" :key="linie.schrittId"
             :opacity="hervorgehoben(linie.laufId) ? 1 : 0.15"
             class="cursor-pointer" @click="gewaehlt = linie.laufId">
            <path :d="pfad(bild, linie)" fill="none" stroke="currentColor" stroke-width="2"
                  :stroke-dasharray="linie.mittel === 'fahrzeug' ? '' : '5 4'"/>
            <title>{{ linie.name }} · {{ uhr(linie.von) }}–{{ uhr(linie.bis) }}</title>
          </g>

          <g v-for="balken in bild.balken" :key="balken.schrittId"
             :opacity="hervorgehoben(balken.laufId) ? 1 : 0.2"
             class="cursor-pointer" @click="gewaehlt = balken.laufId">
            <rect :x="x(bild, balken.von)"
                  :y="y(bild, balken.ortId, balken.reihe) - REIHE / 2 + 3"
                  :width="Math.max(6, (balken.bis - balken.von) * MINUTE)"
                  :height="REIHE - 6" rx="4"
                  fill="currentColor" fill-opacity="0.18" stroke="currentColor"
                  stroke-opacity="0.5"/>
            <text :x="x(bild, balken.von) + 6" :y="y(bild, balken.ortId, balken.reihe) + 4"
                  fill="currentColor" font-size="11">
              {{ beschriftung(balken) }}
              <tspan v-if="balken.lage" fill-opacity="0.6"> · {{ balken.lage }}</tspan>
            </text>
            <title>{{ uhr(balken.von) }}–{{ uhr(balken.bis) }} {{ beschriftung(balken) }}</title>
          </g>
        </svg>
      </div>

      <p class="text-muted text-[13px] mt-2">{{ t('ablauf.bewegungHinweis') }}</p>
    </section>
  </div>
</template>
