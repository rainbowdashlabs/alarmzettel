import client, {getSessionId, setSessionId} from './http'
import type {Arbeitsmappe} from '../interfaces/Alarm'

interface SessionInfo {
    id: string
    secondsLeft: number
}

/**
 * The backend session is scratch space for rendering and holds nothing the browser does not
 * already have. It is thrown away after half an hour idle, so it is simply recreated whenever
 * it has gone — the working set is resent and nothing is lost.
 */
export async function ensureSession(): Promise<string> {
    const existing = getSessionId()
    if (existing) {
        try {
            await client.get<SessionInfo>('/api/session')
            return existing
        } catch {
            setSessionId(null)
        }
    }
    const {data} = await client.post<SessionInfo>('/api/session')
    setSessionId(data.id)
    return data.id
}

export async function pushArbeitsmappe(arbeitsmappe: Arbeitsmappe): Promise<void> {
    await ensureSession()
    await client.put('/api/session/arbeitsmappe', arbeitsmappe)
}
