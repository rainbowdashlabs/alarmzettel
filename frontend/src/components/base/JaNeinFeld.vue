<script setup lang="ts">
import {t} from '../../i18n'

defineProps<{ label: string }>()
const model = defineModel<string>({default: 'N'})
</script>

<template>
  <div>
    <span class="feld-label">{{ label }}</span>
    <div class="janein">
      <button type="button" :class="model === 'J' ? 'ist-gewaehlt' : ''"
              :title="t('feld.ja')" @click="model = 'J'">J
      </button>
      <button type="button" :class="model === 'N' ? 'ist-gewaehlt' : ''"
              :title="t('feld.nein')" @click="model = 'N'">N
      </button>
    </div>
  </div>
</template>
