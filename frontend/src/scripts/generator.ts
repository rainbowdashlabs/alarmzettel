/**
 * Made-up callers and numbers for exercise sheets.
 *
 * These slips are written for practice, not from real calls, so the personal details on them are
 * generated rather than typed. That keeps real names and real numbers off a document that gets
 * printed and handed around. Nothing here is drawn from a real directory.
 */
const VORNAMEN = [
    'Anna', 'Ben', 'Clara', 'David', 'Elena', 'Felix', 'Greta', 'Hannes', 'Ida', 'Jonas',
    'Katrin', 'Lukas', 'Marie', 'Nils', 'Olivia', 'Paul', 'Quirin', 'Rieke', 'Sophie', 'Tobias',
    'Ulrike', 'Viktor', 'Wanda', 'Yusuf', 'Zeynep', 'Emre', 'Leyla', 'Milan', 'Nora', 'Piet',
]

const NACHNAMEN = [
    'Albrecht', 'Bauer', 'Christ', 'Dietrich', 'Engel', 'Fischer', 'Gruber', 'Hartmann',
    'Ibrahim', 'Jansen', 'Kaiser', 'Lehmann', 'Mertens', 'Neumann', 'Ostermann', 'Petersen',
    'Quandt', 'Richter', 'Schuster', 'Thiel', 'Ulrich', 'Vogt', 'Wagner', 'Yilmaz', 'Zimmer',
]

const MOBILVORWAHLEN = ['151', '152', '157', '160', '162', '163', '170', '171', '175', '176']

function eines<T>(werte: T[]): T {
    return werte[Math.floor(Math.random() * werte.length)]!
}

function ziffern(anzahl: number): string {
    return Array.from({length: anzahl}, () => Math.floor(Math.random() * 10)).join('')
}

export function zufallsname(): string {
    return `${eines(VORNAMEN)} ${eines(NACHNAMEN)}`
}

/** A Berlin landline in the format the dispatch system records: country, area, then the number. */
export function festnetznummer(): string {
    return `4930${ziffern(8)}`
}

export function mobilnummer(): string {
    return `49${eines(MOBILVORWAHLEN)}${ziffern(7)}`
}
