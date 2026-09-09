<script setup lang="ts">
import {computed, ref, watch} from 'vue'
import BewegungsTag from './BewegungsTag.vue'
import {t} from '../../i18n'
import {plandaten} from '../../store/planung'
import {bewegungsbild, bewegungsspuren, bewegungstage} from '../../scripts/bewegungen'
import type {Modus} from '../../scripts/bewegungen'

/**
 * Die Gesamtansicht: der Tag, wahlweise je Fahrzeug oder je Person erzählt. Beides ist dieselbe
 * Rechnung — der Personenplan entsteht aus denselben Ketten wie das Fahrzeugbild und kann ihm
 * deshalb nicht widersprechen.
 *
 * Wer viel eingeplant hat, sieht bald mehr Bänder als Bild. Deshalb lässt sich die Auswahl
 * einschränken; ausgeblendet wird vor dem Anordnen, damit keine leeren Bänder stehen bleiben.
 */
const MODI: Modus[] = ['fahrzeuge', 'personen']
const modus = ref<Modus>('fahrzeuge')
const gewaehlt = ref<string | null>(null)
const versteckt = ref(new Set<string>())

const tage = computed(() => bewegungstage(plandaten()))

/** Wer an diesem Tag vorkommt, in dieser Erzählweise — die Knöpfe des Filters. */
const spuren = computed(() => {
  const gesehen = new Map<string, string>()
  for (const tag of tage.value) {
    for (const spur of bewegungsspuren(plandaten(), tag, modus.value)) {
      if (!gesehen.has(spur.id)) gesehen.set(spur.id, spur.name)
    }
  }
  return [...gesehen].map(([id, name]) => ({id, name}))
})

const sichtbar = computed(() =>
    new Set(spuren.value.filter(spur => !versteckt.value.has(spur.id)).map(spur => spur.id)))

const bilder = computed(() => tage.value
    .map(tag => bewegungsbild(plandaten(), tag, modus.value, sichtbar.value))
    .filter(bild => bild.baender.length > 0))

function umschalten(gewaehlterModus: Modus) {
  modus.value = gewaehlterModus
  gewaehlt.value = null
}

/** Eine Spur an- oder abschalten. Die Auswahl gilt für beide Erzählweisen getrennt. */
function zeigen(id: string) {
  const naechste = new Set(versteckt.value)
  if (naechste.has(id)) naechste.delete(id)
  else naechste.add(id)
  versteckt.value = naechste
  if (gewaehlt.value === id) gewaehlt.value = null
}

function alleZeigen() {
  versteckt.value = new Set()
}

function nurEine(id: string) {
  versteckt.value = new Set(spuren.value.filter(spur => spur.id !== id).map(spur => spur.id))
  gewaehlt.value = null
}

watch(modus, () => alleZeigen())
</script>

<template>
  <div class="grid gap-5">
    <p v-if="!tage.length" class="text-muted text-sm">{{ t('ablauf.keineBewegung') }}</p>

    <section v-if="spuren.length" class="abschnitt">
      <div class="flex items-baseline gap-3 flex-wrap mb-3">
        <h2 class="abschnitt-titel">{{ t('ablauf.bewegung') }}</h2>
        <span class="grow"></span>
        <div class="flex gap-2 flex-wrap">
          <button v-for="name in MODI" :key="name" type="button" class="knopf knopf-klein"
                  :class="modus === name ? 'knopf-primaer' : ''" @click="umschalten(name)">
            {{ t(`ablauf.modus.${name}`) }}
          </button>
        </div>
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <span class="label mr-1">{{ t('ablauf.zeigen') }}</span>
        <button v-for="spur in spuren" :key="spur.id" type="button" class="knopf knopf-klein"
                :class="versteckt.has(spur.id) ? 'ist-aus' : 'knopf-primaer'"
                :title="t('ablauf.nurDiese')"
                @click="zeigen(spur.id)" @dblclick="nurEine(spur.id)">
          <font-awesome-icon
            :icon="versteckt.has(spur.id) ? 'fa-solid fa-xmark' : 'fa-solid fa-check'"/>
          {{ spur.name || t('ablauf.ohneName') }}
        </button>
        <button v-if="versteckt.size" type="button" class="knopf knopf-klein" @click="alleZeigen">
          {{ t('ablauf.alleZeigen') }}
        </button>
      </div>
      <p class="text-muted text-[13px] mt-2">{{ t('ablauf.zeigenHinweis') }}</p>
    </section>

    <p v-if="tage.length && !bilder.length" class="text-muted text-sm">
      {{ t('ablauf.nichtsAusgewaehlt') }}
    </p>

    <section v-for="bild in bilder" :key="`${bild.modus}-${bild.datum}`" class="abschnitt">
      <div class="flex items-baseline gap-3 flex-wrap mb-3">
        <h2 class="abschnitt-titel">{{ bild.datum }}</h2>
        <span class="grow"></span>
        <button v-if="gewaehlt" type="button" class="knopf knopf-klein" @click="gewaehlt = null">
          {{ t('ablauf.alleHervorheben') }}
        </button>
      </div>

      <BewegungsTag v-model:gewaehlt="gewaehlt" :bild="bild"/>
    </section>
  </div>
</template>
