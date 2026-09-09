<script setup lang="ts">
import {t} from '../../i18n'
import type {Alarmableitung} from '../../api/plan'

defineProps<{ abgeleitet: Alarmableitung }>()
</script>

<template>
  <section class="abschnitt">
    <h2 class="abschnitt-titel">{{ t('ausPlan.titel') }}</h2>
    <p class="text-muted text-sm">{{ t('ausPlan.erklaerung', {lage: abgeleitet.lage}) }}</p>
    <p v-if="abgeleitet.einsatzadresse" class="text-sm mt-2">
      <span class="label mr-2">{{ t('adresse.einsatz') }}</span>
      {{ abgeleitet.einsatzadresse.strasse }} {{ abgeleitet.einsatzadresse.hnr }},
      {{ abgeleitet.einsatzadresse.plz }} {{ abgeleitet.einsatzadresse.ort }}
    </p>
    <div v-if="abgeleitet.blaetter.length" class="text-sm mt-2">
      <div v-for="(blatt, nummer) in abgeleitet.blaetter" :key="nummer"
           class="border-t border-rule py-1 flex flex-wrap items-baseline gap-x-3">
        <span class="font-bold">{{ blatt.funkrufname }}</span>
        <span class="tabular">{{ blatt.einsatzDatum }} {{ blatt.einsatzZeit }}</span>
        <span class="tabular text-muted">{{ blatt.einsatzNr }}</span>
        <span v-if="blatt.ezp" class="tabular text-muted">
          {{ t('ausPlan.ezp', {n: blatt.ezp}) }}
        </span>
        <span class="text-muted">{{ t('ausPlan.staerke', {n: blatt.staerke}) }}</span>
      </div>
    </div>
    <p v-else class="text-signal-ink text-[13px] mt-2">{{ t('ausPlan.ohneFahrzeug') }}</p>
  </section>
</template>
