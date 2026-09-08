import {createApp} from 'vue'
import './style.css'
import App from './App.vue'
import router from './router'
import {i18n} from './i18n'
import {library} from '@fortawesome/fontawesome-svg-core'
import {
    faAngleDown,
    faAngleUp,
    faAngleRight,
    faArrowLeft,
    faCheck,
    faCircleCheck,
    faCopy,
    faDownload,
    faFilePdf,
    faListCheck,
    faMoon,
    faPen,
    faPlus,
    faRotate,
    faShareNodes,
    faSun,
    faTable,
    faTrash,
    faUpload,
    faUsers,
    faXmark,
} from '@fortawesome/free-solid-svg-icons'
import {faCircle} from '@fortawesome/free-regular-svg-icons'
import {FontAwesomeIcon} from '@fortawesome/vue-fontawesome'
import {initTheme} from './theme'
import {ensureSession} from './api/session'
import {wiederaufnehmen} from './store/sync'

library.add(faAngleDown, faAngleRight, faAngleUp, faArrowLeft, faCheck, faCircle, faCircleCheck,
    faCopy, faDownload, faFilePdf, faListCheck, faMoon, faPen, faPlus, faRotate, faShareNodes, faSun, faTable, faTrash,
    faUpload, faUsers, faXmark)

initTheme()
void ensureSession()
void wiederaufnehmen()

createApp(App)
    .use(router)
    .use(i18n)
    .component('font-awesome-icon', FontAwesomeIcon)
    .mount('#app')
