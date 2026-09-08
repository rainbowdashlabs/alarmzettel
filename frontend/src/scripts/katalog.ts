/**
 * What a vehicle on an Alarm actually is, once the catalogue has had its say.
 *
 * A vehicle names a Funkrufname and nothing more; EZP, Stärke, Status and Trupp are left empty
 * to mean "whatever the catalogue says", so correcting a vehicle once corrects every sheet that
 * calls for it. Writing a value on the Alarm overrides that one field.
 *
 * Mirrors `backend/src/data/katalog.py`, which is what the rendered sheet goes through. This
 * side is only for showing the editor what will print.
 */
import {truppText} from './staerke'
import type {Fahrzeug, Fahrzeugvorlage} from '../interfaces/Alarm'

export interface Fahrzeugwerte {
    ezp: string
    status: string
    staerke: string
    trupp: string
}

function truppAusStaerke(staerke: string): string {
    const ziffern = staerke.trim()
    return /^\d+$/.test(ziffern) ? truppText(Number(ziffern)) : ''
}

export function fahrzeugwerte(fahrzeug: Fahrzeug, vorlage?: Fahrzeugvorlage): Fahrzeugwerte {
    const ezp = fahrzeug.ezp || vorlage?.ezp || ''
    const status = fahrzeug.status || vorlage?.status || ''
    const staerke = fahrzeug.staerke || vorlage?.staerke || ''
    return {ezp, status, staerke, trupp: fahrzeug.trupp || truppAusStaerke(staerke)}
}

/** True where the Alarm says nothing of its own and the catalogue is answering for it. */
export function geerbt(eigen: string): boolean {
    return !eigen.trim()
}
