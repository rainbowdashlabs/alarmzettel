/** Codes are stored the way the dataset writes them, `67B03`, and printed as `67-B-3`. */
export function codeAnzeige(code: string): string {
    const roh = code.trim()
    if (roh.length < 4) return roh
    const ziffern = roh.slice(3).match(/^\d+/)?.[0] ?? ''
    const suffix = roh.slice(3 + ziffern.length)
    const stufe = ziffern ? String(Number(ziffern)) : ''
    return [roh.slice(0, 2), roh.slice(2, 3), stufe + suffix].join('-')
}
