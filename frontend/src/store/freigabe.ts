/**
 * The link this working set already has.
 *
 * Sharing twice used to hand out two links to two copies, which drift apart from the moment the
 * second one is made — and someone who shares while already in a shared workspace means to
 * invite a colleague into it, not to fork it. A working set has one share; asking again returns
 * the same link.
 */
import {freigabeLesen} from '../api/freigabe'
import {verbindung} from './sync'

const SPEICHER = 'alarmzettel_freigabe'

function gemerkt(): string | null {
    try {
        return localStorage.getItem(SPEICHER)
    } catch {
        return null
    }
}

export function freigabeMerken(token: string) {
    try {
        localStorage.setItem(SPEICHER, token)
    } catch { /* a browser that refuses to store simply asks again next time */ }
}

export function freigabeVergessen() {
    try {
        localStorage.removeItem(SPEICHER)
    } catch { /* nothing to do */ }
}

/**
 * The link this working set already has, or nothing if it has none. A workspace this browser has
 * joined is that share; otherwise it is whichever one this browser opened for it.
 *
 * The server is asked rather than trusted from memory, because a share expires and the token of
 * a share that is gone must not be handed to anyone. Asking also counts as use, which is what
 * keeps a link that is still being passed around alive.
 */
export async function bestehendeFreigabe(): Promise<string | null> {
    const beigetreten = verbindung.token
    const token = beigetreten ?? gemerkt()
    if (!token) return null
    try {
        return (await freigabeLesen(token)).url
    } catch {
        if (!beigetreten) freigabeVergessen()
        return null
    }
}
