export interface SnaAntwort {
    /** What the dispatcher clicks. */
    label: string
    /** The sentence this answer contributes to the Hinweise. */
    aussage: string
    ziel: string
    nr?: string
}

/** A question answered by typing: an age is a number the caller says, not one of a list. */
export interface SnaEingabe {
    /** The sentence for the Hinweise, with `{wert}` standing for what was typed. */
    vorlage: string
    platzhalter: string
    /** What is recorded when the field is left empty. Absent where nothing is worth recording. */
    leer?: { label: string, aussage: string }
    /** This answer is a Hinweis of its own, not one of the numbered sentences after the code. */
    eigen?: boolean
}

/** A node is a question with answers, a question answered by typing, or an endpoint. */
export interface SnaKnoten {
    frage?: string
    antworten?: SnaAntwort[]
    eingabe?: SnaEingabe
    /** Where a typed answer leads; a question with answers has one per answer instead. */
    ziel?: string
    code?: string
    kategorie?: string
    anlass?: string
    stichwort?: string
}

export interface SnaDisziplin {
    id: string
    label: string
    /** `bf-open-data` for the real medical codes, `erfunden` for the authored branches. */
    quelle: string
    hinweis?: string
    einstieg: string
}

export interface SnaBaum {
    stand: string
    notfallkategorien: Record<string, string>
    knoten: Record<string, SnaKnoten>
    disziplinen: SnaDisziplin[]
}

export interface SnaSchritt {
    label: string
    aussage: string
    /** The question this answered, so stepping back needs no replay of the way here. */
    knoten?: string
    /** Belongs on the sheet as its own Hinweis rather than among the numbered answers. */
    eigen?: boolean
}

export interface SnaTreffer {
    code: string
    kategorie: string
    anlass: string
    stichwort: string
    disziplin: SnaDisziplin
    pfad: SnaSchritt[]
}
