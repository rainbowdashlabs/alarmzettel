import client from './http'
import {pushArbeitsmappe} from './session'
import type {Arbeitsmappe} from '../interfaces/Alarm'

async function pdf(path: string, arbeitsmappe: Arbeitsmappe): Promise<Blob> {
    await pushArbeitsmappe(arbeitsmappe)
    const {data} = await client.post(path, null, {responseType: 'blob'})
    return data as Blob
}

export function renderAlle(arbeitsmappe: Arbeitsmappe): Promise<Blob> {
    return pdf('/api/render', arbeitsmappe)
}

export function renderEinen(arbeitsmappe: Arbeitsmappe, alarmId: string): Promise<Blob> {
    return pdf(`/api/render/${alarmId}`, arbeitsmappe)
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
