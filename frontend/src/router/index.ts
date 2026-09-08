import {createRouter, createWebHistory, type RouteRecordRaw} from 'vue-router'
import {t} from '../i18n'

const routes: RouteRecordRaw[] = [
    {path: '/', name: 'Alarme', component: () => import('../views/AlarmeView.vue'),
        meta: {titleKey: 'routes.alarme'}},
    {path: '/alarm/:id', name: 'Alarm', component: () => import('../views/AlarmView.vue'),
        meta: {titleKey: 'routes.alarm'}},
    {path: '/freigabe/:token', name: 'Freigabe', component: () => import('../views/FreigabeView.vue'),
        meta: {titleKey: 'routes.freigabe'}},
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
