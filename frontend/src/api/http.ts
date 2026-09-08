import axios, {type AxiosInstance} from 'axios'

const client: AxiosInstance = axios.create({
    baseURL: import.meta.env?.VITE_API_BASE_URL || '',
    headers: {'Content-Type': 'application/json'},
})

let sessionId: string | null = null

export function setSessionId(id: string | null) {
    sessionId = id
}

export function getSessionId(): string | null {
    return sessionId
}

client.interceptors.request.use((config) => {
    if (sessionId) config.headers['X-Session-Id'] = sessionId
    return config
})

export default client
