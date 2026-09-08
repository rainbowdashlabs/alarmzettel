<script setup lang="ts">
import {t} from '../i18n'
</script>

<template>
  <div class="abschnitt text-center py-12">
    <h1 class="headline text-2xl">{{ t('nichtGefunden.titel') }}</h1>
    <RouterLink to="/" class="knopf mt-4 inline-flex">{{ t('nichtGefunden.zurueck') }}</RouterLink>
  </div>
</template>
