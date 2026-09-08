<script setup lang="ts">
import TextFeld from './TextFeld.vue'
import {t} from '../../i18n'
import type {Adresse} from '../../interfaces/Alarm'

defineProps<{ titel: string }>()
const adresse = defineModel<Adresse>({required: true})
</script>

<template>
  <div>
    <div class="label mb-2">{{ titel }}</div>
    <div class="grid grid-cols-3 gap-3">
      <TextFeld v-model="adresse.strasse" :label="t('feld.strasse')" breit/>
      <TextFeld v-model="adresse.hnr" :label="t('feld.hnr')"/>
      <TextFeld v-model="adresse.objekt" :label="t('feld.objekt')" breit/>
      <TextFeld v-model="adresse.plz" :label="t('feld.plz')"/>
      <TextFeld v-model="adresse.ort" :label="t('feld.ort')" breit/>
    </div>
  </div>
</template>
