<script setup lang="ts">
import {useId} from 'vue'

defineProps<{ label: string, platzhalter?: string, zeilen?: number }>()
const model = defineModel<string>({default: ''})
const id = useId()
</script>

<template>
  <div>
    <label class="feld-label" :for="id">{{ label }}</label>
    <textarea :id="id" v-model="model" class="field" :rows="zeilen ?? 3" :placeholder="platzhalter"/>
  </div>
</template>
