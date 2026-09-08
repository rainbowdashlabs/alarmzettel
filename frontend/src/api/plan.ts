import client from './http'
import type {Adresse} from '../interfaces/Alarm'

/** Ein Blatt, das aus dem Ablaufplan entsteht — eines je Fahrzeug an der Lage. */
export interface Planblatt {
    funkrufname: string
    staerke: string
    einsatzDatum: string
    einsatzZeit: string
}

export interface Alarmableitung {
    lage: string
    einsatzadresse: Adresse | null
    blaetter: Planblatt[]
}

/**
 * Was der Ablaufplan zu diesem Alarm beisteuert, gerechnet auf dem Server. Der Editor zeigt es
 * an, statt dieselbe Ableitung ein zweites Mal zu schreiben — gedruckt wird, was hier steht.
 */
export async function alarmableitung(alarmId: string): Promise<Alarmableitung | null> {
    try {
        const {data} = await client.get(`/api/render/plan/alarm/${alarmId}`)
        return data?.abgeleitet ?? null
    } catch {
        return null
    }
}
