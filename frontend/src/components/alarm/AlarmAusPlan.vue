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
    <table v-if="abgeleitet.blaetter.length" class="w-full text-sm mt-2">
      <tbody>
        <tr v-for="(blatt, nummer) in abgeleitet.blaetter" :key="nummer"
            class="border-t border-rule">
          <td class="py-1 pr-3 font-bold">{{ blatt.funkrufname }}</td>
          <td class="tabular py-1 pr-3">{{ blatt.einsatzDatum }} {{ blatt.einsatzZeit }}</td>
          <td class="tabular py-1 pr-3 text-muted">{{ blatt.einsatzNr }}</td>
          <td v-if="blatt.ezp" class="tabular py-1 pr-3 text-muted">
            {{ t('ausPlan.ezp', {n: blatt.ezp}) }}
          </td>
          <td class="py-1 text-muted">{{ t('ausPlan.staerke', {n: blatt.staerke}) }}</td>
        </tr>
      </tbody>
    </table>
    <p v-else class="text-signal-ink text-[13px] mt-2">{{ t('ausPlan.ohneFahrzeug') }}</p>
  </section>
</template>
