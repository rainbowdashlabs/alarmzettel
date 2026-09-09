<script setup lang="ts">
import {ref} from 'vue'
import TextFeld from '../components/base/TextFeld.vue'
import {t} from '../i18n'
import {
  entfernen, personAnlegen, planung, tagAnlegen, umschalten,
  verfuegbarkeitAnlegen, wortHinzufuegen,
} from '../store/planung'

const rolle = ref('')
const klasse = ref('')

const listen = [
  {schluessel: 'rollen' as const, titel: 'planung.rollen', entwurf: rolle},
  {schluessel: 'fahrerlaubnisse' as const, titel: 'planung.fahrerlaubnisse', entwurf: klasse},
]

function wortAnlegen(schluessel: 'rollen' | 'fahrerlaubnisse', entwurf: {value: string}) {
  wortHinzufuegen(planung()[schluessel], entwurf.value)
  entwurf.value = ''
}
</script>

<template>
  <div class="grid gap-5">
    <div>
      <h1 class="headline text-2xl">{{ t('planung.titel') }}</h1>
      <p class="text-muted text-sm mt-1">{{ t('planung.beschreibung') }}</p>
    </div>

    <section class="abschnitt">
      <div class="flex items-center justify-between mb-3 gap-2 flex-wrap">
        <h2 class="abschnitt-titel mb-0">{{ t('planung.tage') }}</h2>
        <button type="button" class="knopf knopf-klein" @click="tagAnlegen">
          <font-awesome-icon icon="fa-solid fa-plus"/>
          {{ t('planung.tagNeu') }}
        </button>
      </div>
      <p v-if="!planung().tage.length" class="text-muted text-sm">{{ t('planung.keineTage') }}</p>

      <div class="grid gap-2">
        <div v-for="tag in planung().tage" :key="tag.id"
             class="grid md:grid-cols-[10rem_1fr_auto] gap-2 items-end">
          <div>
            <label class="feld-label">{{ t('planung.datum') }}</label>
            <input v-model="tag.datum" type="date" class="field"/>
          </div>
          <TextFeld v-model="tag.name" :label="t('planung.tagName')"
                    :platzhalter="t('planung.tagPlatzhalter')"/>
          <button type="button" class="knopf knopf-klein knopf-gefahr"
                  @click="entfernen(planung().tage, tag)">
            <font-awesome-icon icon="fa-solid fa-xmark"/>
          </button>
        </div>
      </div>
    </section>

    <div class="grid md:grid-cols-2 gap-4">
      <section v-for="liste in listen" :key="liste.schluessel" class="abschnitt">
        <h2 class="abschnitt-titel">{{ t(liste.titel) }}</h2>
        <form class="flex gap-2 mb-3" @submit.prevent="wortAnlegen(liste.schluessel, liste.entwurf)">
          <input v-model="liste.entwurf.value" type="text" class="field"/>
          <button type="submit" class="knopf shrink-0">
            <font-awesome-icon icon="fa-solid fa-plus"/>
          </button>
        </form>
        <ul class="flex flex-wrap gap-2">
          <li v-for="wert in planung()[liste.schluessel]" :key="wert"
              class="flex items-center gap-2 border border-rule rounded px-2 py-1 bg-page">
            <span class="text-sm">{{ wert }}</span>
            <button type="button" class="text-muted hover:text-signal"
                    @click="entfernen(planung()[liste.schluessel], wert)">
              <font-awesome-icon icon="fa-solid fa-xmark"/>
            </button>
          </li>
        </ul>
      </section>
    </div>

    <section class="abschnitt">
      <div class="flex items-center justify-between mb-3 gap-2 flex-wrap">
        <h2 class="abschnitt-titel mb-0">{{ t('planung.personen') }}</h2>
        <button type="button" class="knopf knopf-klein" @click="personAnlegen">
          <font-awesome-icon icon="fa-solid fa-plus"/>
          {{ t('planung.personNeu') }}
        </button>
      </div>
      <p class="text-muted text-[13px] mb-3">{{ t('planung.personenHinweis') }}</p>
      <p v-if="!planung().personen.length" class="text-muted text-sm">
        {{ t('planung.keinePersonen') }}
      </p>

      <div class="grid gap-4">
        <div v-for="person in planung().personen" :key="person.id"
             class="border border-rule rounded p-3 bg-page grid gap-3">
          <div class="grid md:grid-cols-[1fr_6rem_auto] gap-3 items-end">
            <TextFeld v-model="person.name" :label="t('planung.personName')"/>
            <div>
              <label class="feld-label">{{ t('planung.anzahl') }}</label>
              <input v-model.number="person.anzahl" type="number" min="1" class="field"/>
            </div>
            <button type="button" class="knopf knopf-klein knopf-gefahr"
                    @click="entfernen(planung().personen, person)">
              <font-awesome-icon icon="fa-solid fa-trash"/>
            </button>
          </div>

          <div class="grid md:grid-cols-2 gap-3">
            <div>
              <span class="feld-label">{{ t('planung.rollen') }}</span>
              <div class="flex flex-wrap gap-2">
                <button v-for="wert in planung().rollen" :key="wert" type="button"
                        class="knopf knopf-klein"
                        :class="person.rollen.includes(wert) ? 'knopf-primaer' : ''"
                        @click="umschalten(person.rollen, wert)">
                  {{ wert }}
                </button>
              </div>
            </div>
            <div>
              <span class="feld-label">{{ t('planung.fahrerlaubnis') }}</span>
              <div class="flex flex-wrap gap-2">
                <button v-for="wert in planung().fahrerlaubnisse" :key="wert" type="button"
                        class="knopf knopf-klein"
                        :class="person.fahrerlaubnis.includes(wert) ? 'knopf-primaer' : ''"
                        @click="umschalten(person.fahrerlaubnis, wert)">
                  {{ wert }}
                </button>
              </div>
            </div>
          </div>

          <div>
            <div class="flex items-center gap-3 mb-2 flex-wrap">
              <span class="feld-label mb-0">{{ t('planung.verfuegbar') }}</span>
              <button type="button" class="knopf knopf-klein"
                      @click="verfuegbarkeitAnlegen(person)">
                <font-awesome-icon icon="fa-solid fa-plus"/>
                {{ t('planung.fensterNeu') }}
              </button>
            </div>
            <p v-if="!person.verfuegbar.length" class="text-muted text-[13px]">
              {{ t('planung.immerDa') }}
            </p>
            <div class="grid gap-2">
              <div v-for="fenster in person.verfuegbar" :key="fenster.id"
                   class="grid md:grid-cols-[1fr_1fr_auto] gap-2 items-end">
                <div>
                  <label class="feld-label">{{ t('planung.von') }}</label>
                  <input v-model="fenster.von" type="datetime-local" class="field"/>
                </div>
                <div>
                  <label class="feld-label">{{ t('planung.bis') }}</label>
                  <input v-model="fenster.bis" type="datetime-local" class="field"/>
                </div>
                <button type="button" class="knopf knopf-klein knopf-gefahr"
                        @click="entfernen(person.verfuegbar, fenster)">
                  <font-awesome-icon icon="fa-solid fa-xmark"/>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>
