import type {RouteLocation} from 'vue-router'
import {createRouter, createWebHistory, type RouteRecordRaw} from 'vue-router'
import {t} from '../i18n'
import {sitzung} from '../store/sitzung'

const routes: RouteRecordRaw[] = [
    {path: '/', name: 'Alarme', component: () => import('../views/AlarmeView.vue'),
        meta: {titleKey: 'routes.alarme'}},
    {path: '/alarm/:id', name: 'Alarm', component: () => import('../views/AlarmView.vue'),
        meta: {titleKey: 'routes.alarm'}},
    {path: '/ablauf', name: 'Ablauf', component: () => import('../views/AblaufView.vue'),
        meta: {titleKey: 'routes.ablauf'}},
    {path: '/ansicht', name: 'Ansicht', component: () => import('../views/AnsichtView.vue'),
        meta: {titleKey: 'routes.ansicht'}},
    // Die Stammdaten stehen im Katalog; alte Links sollen weiter irgendwo landen.
    {path: '/planung', redirect: '/kataloge'},
    {path: '/sitzung/:token', name: 'Sitzung', component: () => import('../views/FreigabeView.vue'),
        meta: {titleKey: 'routes.freigabe'}},
    // Links, die schon herumgereicht wurden, zeigen auf den alten Pfad und sollen weiter gehen.
    {path: '/freigabe/:token', redirect: (ziel: RouteLocation) => `/sitzung/${ziel.params.token}`},
    {path: '/kataloge', name: 'Kataloge', component: () => import('../views/KatalogeView.vue'),
        meta: {titleKey: 'routes.kataloge'}},
    {path: '/:pathMatch(.*)*', name: 'NotFound', component: () => import('../views/NotFoundView.vue'),
        meta: {titleKey: 'routes.notFound'}},
]

const router = createRouter({history: createWebHistory(), routes})

const NUR_ZUM_LESEN = ['Ansicht', 'Ablauf', 'Sitzung', 'NotFound']

/**
 * Wer nur zusieht, landet in der Übersicht statt in einem Editor. Die Felder änderten ohnehin
 * nichts — der Server nimmt von einem Lesetoken keine Änderung an —, und ein Formular, das man
 * ausfüllen kann und das nichts bewirkt, ist schlimmer als keins.
 */
router.beforeEach((ziel) => {
    if (!sitzung.nurLesen || NUR_ZUM_LESEN.includes(String(ziel.name))) return true
    return {name: 'Ansicht'}
})

router.afterEach((to) => {
    const key = to.meta?.titleKey as string | undefined
    document.title = key ? `${t(key)} | ${t('app.name')}` : t('app.name')
})

export default router
