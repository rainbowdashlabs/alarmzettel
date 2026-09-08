<script setup lang="ts">
import {computed, useId} from 'vue'

const props = defineProps<{
  label: string
  vorschlaege?: string[]
  platzhalter?: string
  breit?: boolean
}>()

defineEmits<{ change: [] }>()
const model = defineModel<string>({default: ''})
const id = useId()
const listenId = computed(() => props.vorschlaege?.length ? `${id}-liste` : undefined)
</script>

<template>
  <div :class="breit ? 'col-span-2' : ''">
    <label class="feld-label" :for="id">{{ label }}</label>
    <input :id="id" v-model="model" type="text" class="field"
           :list="listenId" :placeholder="platzhalter" @change="$emit('change')"/>
    <datalist v-if="listenId" :id="listenId">
      <option v-for="wert in vorschlaege" :key="wert" :value="wert"/>
    </datalist>
  </div>
</template>
