import client from './http'
import type {Arbeitsmappe} from '../interfaces/Alarm'

export interface Freigabe {
    token: string
    url: string
    laeuftAb: string
    tage: number
}

export interface GeleseneFreigabe extends Omit<Freigabe, 'token'> {
    arbeitsmappe: Arbeitsmappe
}

/**
 * Puts a copy of the working set behind a link. The token in that link is the only thing
 * protecting it, so the link itself is the secret — anyone holding it can read the share.
 */
export async function teilen(arbeitsmappe: Arbeitsmappe): Promise<Freigabe> {
    const {data} = await client.post<Freigabe>('/api/freigabe', arbeitsmappe)
    return data
}

export async function freigabeLesen(token: string): Promise<GeleseneFreigabe> {
    const {data} = await client.get<GeleseneFreigabe>(`/api/freigabe/${token}`)
    return data
}
