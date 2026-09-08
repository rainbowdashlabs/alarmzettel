export interface Sortierbar {
    sortierung: number
}

/**
 * Moves one entry up or down by giving it a sort key between its new neighbours, rather than by
 * renumbering the list. Only the moved entry changes, so two people reordering different parts
 * of the same list do not overwrite one another.
 */
export function neuSortieren<T extends Sortierbar>(liste: T[], index: number, richtung: -1 | 1): boolean {
    const geordnet = [...liste].sort((a, b) => a.sortierung - b.sortierung)
    const stelle = geordnet.indexOf(liste[index] as T)
    const ziel = stelle + richtung
    if (stelle < 0 || ziel < 0 || ziel >= geordnet.length) return false

    const eintrag = geordnet[stelle]!
    const nachbar = geordnet[ziel]!
    const dahinter = geordnet[ziel + richtung]
    eintrag.sortierung = dahinter
        ? (nachbar.sortierung + dahinter.sortierung) / 2
        : nachbar.sortierung + richtung
    liste.sort((a, b) => a.sortierung - b.sortierung)
    return true
}
