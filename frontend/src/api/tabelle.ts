import client from './http'
import type {Arbeitsmappe} from '../interfaces/Alarm'

/**
 * Converts the old spreadsheet into a working set. The backend does the reading — the formats are
 * zipped XML, which Python handles without a dependency — and stores nothing.
 */
export async function tabelleImportieren(datei: File): Promise<Arbeitsmappe> {
    const koerper = new FormData()
    koerper.append('datei', datei)
    const {data} = await client.post<Arbeitsmappe>('/api/import', koerper,
        {headers: {'Content-Type': 'multipart/form-data'}})
    return data
}
