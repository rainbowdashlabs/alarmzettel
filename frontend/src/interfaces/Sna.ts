export interface SnaAntwort {
    /** What the dispatcher clicks. */
    label: string
    /** The sentence this answer contributes to the Hinweise. */
    aussage: string
    ziel: string
    nr?: string
}

/** A node is either a question with answers, or an endpoint carrying a code. */
export interface SnaKnoten {
    frage?: string
    antworten?: SnaAntwort[]
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
}

export interface SnaTreffer {
    code: string
    kategorie: string
    anlass: string
    stichwort: string
    disziplin: SnaDisziplin
    pfad: SnaSchritt[]
}
