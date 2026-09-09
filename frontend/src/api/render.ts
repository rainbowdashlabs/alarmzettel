import client from './http'

/**
 * Die Arbeitsmappe liegt auf dem Server, also wird sie nicht mitgeschickt — gedruckt wird, was
 * die laufende Sitzung hält.
 */
async function datei(pfad: string): Promise<Blob> {
    const {data} = await client.post(pfad, null, {responseType: 'blob'})
    return data as Blob
}

export function renderAlle(): Promise<Blob> {
    return datei('/api/render')
}

export function renderEinen(alarmId: string): Promise<Blob> {
    return datei(`/api/render/${alarmId}`)
}

/** Der Ablaufplan: ein Blatt je Person, eines je Fahrzeug, und der Gesamtplan quer. */
export function renderAblaufplan(): Promise<Blob> {
    return datei('/api/render/plan/ablauf')
}

/** Derselbe Plan als Archiv, ein PDF je Person und je Fahrzeug. */
export function renderAblaufplanZip(): Promise<Blob> {
    return datei('/api/render/plan/ablauf/zip')
}

/** Turns the error body a failed render returns — a Blob — back into readable text. */
export async function fehlertext(error: unknown): Promise<string> {
    const body = (error as {response?: {data?: unknown}})?.response?.data
    if (body instanceof Blob) {
        try {
            return JSON.parse(await body.text()).detail
        } catch {
            return await body.text()
        }
    }
    return (error as Error)?.message ?? 'Unbekannter Fehler'
}
