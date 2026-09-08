import type {RouteLocation} from 'vue-router'
import {createRouter, createWebHistory, type RouteRecordRaw} from 'vue-router'
import {t} from '../i18n'

const routes: RouteRecordRaw[] = [
    {path: '/', name: 'Alarme', component: () => import('../views/AlarmeView.vue'),
        meta: {titleKey: 'routes.alarme'}},
    {path: '/alarm/:id', name: 'Alarm', component: () => import('../views/AlarmView.vue'),
        meta: {titleKey: 'routes.alarm'}},
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

router.afterEach((to) => {
    const key = to.meta?.titleKey as string | undefined
    document.title = key ? `${t(key)} | ${t('app.name')}` : t('app.name')
})

export default router
