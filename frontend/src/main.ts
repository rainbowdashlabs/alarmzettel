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
    faFileZipper,
    faBox,
    faListCheck,
    faMoon,
    faPen,
    faPlus,
    faRotate,
    faShareNodes,
    faSun,
    faTable,
    faLocationDot,
    faPersonWalking,
    faTrash,
    faTruck,
    faUpload,
    faUsers,
    faXmark,
} from '@fortawesome/free-solid-svg-icons'
import {faCircle} from '@fortawesome/free-regular-svg-icons'
import {faGithub} from '@fortawesome/free-brands-svg-icons'
import {FontAwesomeIcon} from '@fortawesome/vue-fontawesome'
import {initTheme} from './theme'
import {sitzungStarten} from './store/sitzung'


library.add(faAngleDown, faAngleRight, faAngleUp, faArrowLeft, faBox, faCheck, faCircle,
    faCircleCheck, faCopy, faDownload, faFilePdf, faFileZipper, faListCheck, faLocationDot,
    faMoon, faPen, faPersonWalking, faPlus, faRotate, faShareNodes, faSun, faTable, faTrash,
    faTruck, faUpload, faUsers, faXmark, faGithub)

initTheme()
void sitzungStarten()

createApp(App)
    .use(router)
    .use(i18n)
    .component('font-awesome-icon', FontAwesomeIcon)
    .mount('#app')
