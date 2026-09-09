<script setup lang="ts">
import {computed, ref} from 'vue'
import BewegungsTag from './BewegungsTag.vue'
import {t} from '../../i18n'
import {plandaten} from '../../store/planung'
import {bewegungsbild, bewegungstage} from '../../scripts/bewegungen'
import type {Modus} from '../../scripts/bewegungen'

/**
 * Die Gesamtansicht: der Tag, wahlweise je Fahrzeug oder je Person erzählt. Beides ist dieselbe
 * Rechnung — der Personenplan entsteht aus denselben Ketten wie das Fahrzeugbild und kann ihm
 * deshalb nicht widersprechen.
 */
const MODI: Modus[] = ['fahrzeuge', 'personen']
const modus = ref<Modus>('fahrzeuge')
const gewaehlt = ref<string | null>(null)

const bilder = computed(() => bewegungstage(plandaten())
    .map(tag => bewegungsbild(plandaten(), tag, modus.value))
    .filter(bild => bild.baender.length > 0))

function umschalten(gewaehlterModus: Modus) {
  modus.value = gewaehlterModus
  gewaehlt.value = null
}
</script>

<template>
  <div class="grid gap-5">
    <p v-if="!bilder.length" class="text-muted text-sm">{{ t('ablauf.keineBewegung') }}</p>

    <section v-for="bild in bilder" :key="`${bild.modus}-${bild.datum}`" class="abschnitt">
      <div class="flex items-baseline gap-3 flex-wrap mb-3">
        <h2 class="abschnitt-titel mb-0">{{ t('ablauf.bewegung') }}</h2>
        <span class="text-muted text-sm">{{ bild.datum }}</span>
        <span class="grow"></span>
        <button v-if="gewaehlt" type="button" class="knopf knopf-klein" @click="gewaehlt = null">
          {{ t('ablauf.alleZeigen') }}
        </button>
        <div class="flex gap-2">
          <button v-for="name in MODI" :key="name" type="button" class="knopf knopf-klein"
                  :class="modus === name ? 'knopf-primaer' : ''" @click="umschalten(name)">
            {{ t(`ablauf.modus.${name}`) }}
          </button>
        </div>
      </div>

      <BewegungsTag v-model:gewaehlt="gewaehlt" :bild="bild"/>
    </section>
  </div>
</template>
