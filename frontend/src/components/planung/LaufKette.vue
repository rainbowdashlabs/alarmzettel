<script setup lang="ts">
import SchrittFelder from './SchrittFelder.vue'
import {t} from '../../i18n'
import {entfernen, mehrereTage, schrittAnhaengen, schrittEinfuegen} from '../../store/planung'
import {tagVon, uhrzeit} from '../../scripts/zeit'
import type {Lauf} from '../../interfaces/Planung'

/**
 * Die Kette als Folge von Karten. Was an einem Schritt hängt, steht in `SchrittFelder` — dieselben
 * Felder benutzt der Tagesplan in seinem Fenster.
 */
const {lauf} = defineProps<{ lauf: Lauf }>()
</script>

<template>
  <div class="grid gap-2">
    <div v-for="(schritt, stelle) in lauf.schritte" :key="schritt.id"
         class="border border-rule rounded p-3 bg-page grid gap-2">
      <div class="flex items-center gap-2 flex-wrap">
        <span class="label">{{ stelle + 1 }}.</span>
        <span class="flex">
          <button type="button" class="knopf knopf-klein rounded-r-none px-2"
                  :title="t('ablauf.aufenthaltDavor')"
                  @click="schrittEinfuegen(lauf, stelle, 'aufenthalt')">
            <font-awesome-icon icon="fa-solid fa-plus"/>
          </button>
          <button type="button" class="knopf knopf-klein rounded-l-none border-l-0 px-2"
                  :title="t('ablauf.fahrtDavor')"
                  @click="schrittEinfuegen(lauf, stelle, 'fahrt')">
            <font-awesome-icon icon="fa-solid fa-angle-right"/>
          </button>
        </span>
        <span class="tabular text-sm">
          <span v-if="mehrereTage()" class="text-muted">{{ tagVon(schritt.von) }}</span>
          {{ uhrzeit(schritt.von) }}–{{ uhrzeit(schritt.bis) }}
        </span>
        <span class="grow"></span>
        <button type="button" class="knopf knopf-klein knopf-gefahr"
                @click="entfernen(lauf.schritte, schritt)">
          <font-awesome-icon icon="fa-solid fa-xmark"/>
        </button>
      </div>

      <SchrittFelder :lauf="lauf" :schritt="schritt"/>
    </div>

    <div class="flex gap-2 flex-wrap">
      <button type="button" class="knopf knopf-klein"
              @click="schrittAnhaengen(lauf, 'aufenthalt')">
        <font-awesome-icon icon="fa-solid fa-plus"/>
        {{ t('ablauf.aufenthalt') }}
      </button>
      <button type="button" class="knopf knopf-klein" @click="schrittAnhaengen(lauf, 'fahrt')">
        <font-awesome-icon icon="fa-solid fa-angle-right"/>
        {{ t('ablauf.fahrt') }}
      </button>
    </div>
  </div>
</template>
