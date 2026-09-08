/**
 * Made-up callers and numbers for exercise sheets.
 *
 * These slips are written for practice, not from real calls, so the personal details on them are
 * generated rather than typed. That keeps real names and real numbers off a document that gets
 * printed and handed around. Nothing here is drawn from a real directory.
 *
 * The names are meant to look like the people who actually ring the Berlin fire brigade, because
 * a slip full of storybook German names trains the eye for the wrong thing. Roughly a quarter of
 * Berlin holds a non-German passport and about a third of the city has a migration background;
 * the largest groups are Turkish, Ukrainian, Indian, Polish and Syrian, with a Vietnamese
 * population concentrated in the eastern districts. The weights below reflect that shape. They
 * are a plausible mix, not a distribution derived from the registry — nobody publishes surname
 * frequencies per city.
 *
 * First names span the ages, since callers do: the names common among people born in the GDR sit
 * beside the ones given to children today.
 */

interface Vorname {
    name: string
    /** Only needed where the surname inflects — Polish and Ukrainian ones do. */
    weiblich: boolean
}

/** A surname that reads the same either way, or the two forms it takes. */
type Nachname = string | { maennlich: string, weiblich: string }

interface Herkunft {
    gewicht: number
    vornamen: Vorname[]
    nachnamen: Nachname[]
}

const m = (name: string): Vorname => ({name, weiblich: false})
const w = (name: string): Vorname => ({name, weiblich: true})

const HERKUENFTE: Herkunft[] = [
    {
        // The top of the national surname list, and given names from every decade a caller might
        // have been born in — Manfred and Renate as readily as Leon and Mia.
        gewicht: 68,
        vornamen: [
            m('Michael'), m('Thomas'), m('Andreas'), m('Frank'), m('Peter'), m('Uwe'),
            m('Manfred'), m('Hartmut'), m('Jörg'), m('Christian'), m('Stefan'), m('Sebastian'),
            m('Daniel'), m('Tobias'), m('Lukas'), m('Paul'), m('Leon'), m('Jonas'), m('Felix'),
            w('Sabine'), w('Petra'), w('Renate'), w('Christa'), w('Kerstin'), w('Ines'),
            w('Anke'), w('Susanne'), w('Claudia'), w('Nicole'), w('Anja'), w('Julia'),
            w('Katrin'), w('Stefanie'), w('Laura'), w('Hannah'), w('Emma'), w('Mia'), w('Marie'),
        ],
        nachnamen: [
            'Müller', 'Schmidt', 'Schneider', 'Fischer', 'Weber', 'Meyer', 'Wagner', 'Schulz',
            'Bauer', 'Becker', 'Hoffmann', 'Koch', 'Klein', 'Richter', 'Wolf', 'Schwarz',
            'Neumann', 'Schröder', 'Braun', 'Zimmermann', 'Krüger', 'Hartmann', 'Werner',
            'Lange', 'Lehmann', 'König', 'Kaiser', 'Krause', 'Schulze', 'Winkler', 'Sommer',
        ],
    },
    {
        // The largest group holding a foreign passport, and one settled here for generations.
        gewicht: 9,
        vornamen: [
            m('Mehmet'), m('Mustafa'), m('Ali'), m('Hasan'), m('Emre'), m('Murat'), m('Yusuf'),
            m('Kerem'), w('Ayşe'), w('Fatma'), w('Emine'), w('Zeynep'), w('Elif'), w('Leyla'),
            w('Merve'),
        ],
        nachnamen: ['Yılmaz', 'Kaya', 'Demir', 'Şahin', 'Çelik', 'Yıldız', 'Öztürk', 'Aydın',
                    'Arslan', 'Doğan', 'Koç'],
    },
    {
        gewicht: 6,
        vornamen: [
            m('Oleksandr'), m('Serhij'), m('Andrij'), m('Dmytro'), m('Wolodymyr'),
            w('Olena'), w('Natalija'), w('Iryna'), w('Oksana'), w('Kateryna'),
        ],
        // The -enko and -uk endings read the same for everyone, which most Slavic ones do not.
        nachnamen: ['Melnyk', 'Kowalenko', 'Schewtschenko', 'Bondarenko', 'Tkatschuk',
                    'Kowaltschuk', 'Boyko', 'Kravets'],
    },
    {
        gewicht: 5,
        vornamen: [
            m('Piotr'), m('Tomasz'), m('Marek'), m('Krzysztof'), m('Andrzej'),
            w('Agnieszka'), w('Katarzyna'), w('Małgorzata'), w('Magdalena'), w('Joanna'),
        ],
        nachnamen: [
            'Nowak', 'Wójcik', 'Mazur', 'Kaczmarek', 'Zieliński',
            {maennlich: 'Kowalski', weiblich: 'Kowalska'},
            {maennlich: 'Wiśniewski', weiblich: 'Wiśniewska'},
            {maennlich: 'Kamiński', weiblich: 'Kamińska'},
            {maennlich: 'Lewandowski', weiblich: 'Lewandowska'},
        ],
    },
    {
        gewicht: 5,
        vornamen: [
            m('Ahmad'), m('Omar'), m('Mohammed'), m('Khaled'), m('Yassin'), m('Bilal'),
            w('Fatima'), w('Layla'), w('Nour'), w('Rania'), w('Amina'),
        ],
        nachnamen: ['Haddad', 'Khalil', 'Hassan', 'Ibrahim', 'Saleh', 'Nasser', 'Aziz',
                    'Al-Ahmad', 'Darwisch'],
    },
    {
        // Concentrated in the eastern districts, and written here the way a German form takes it.
        gewicht: 4,
        vornamen: [
            m('Minh'), m('Tuan'), m('Duc'), m('Hieu'), m('Long'),
            w('Lan'), w('Mai'), w('Thuy'), w('Huong'), w('Ngoc'),
        ],
        nachnamen: ['Nguyen', 'Tran', 'Pham', 'Le', 'Hoang', 'Vu', 'Dang'],
    },
    {
        gewicht: 3,
        vornamen: [
            m('Rahul'), m('Amit'), m('Arjun'), m('Vikram'), m('Rohit'),
            w('Priya'), w('Neha'), w('Ananya'), w('Divya'), w('Kavya'),
        ],
        nachnamen: ['Kumar', 'Singh', 'Sharma', 'Patel', 'Gupta', 'Reddy', 'Nair', 'Verma'],
    },
]

const MOBILVORWAHLEN = ['151', '152', '157', '160', '162', '163', '170', '171', '175', '176']

function eines<T>(werte: T[]): T {
    return werte[Math.floor(Math.random() * werte.length)]!
}

function ziffern(anzahl: number): string {
    return Array.from({length: anzahl}, () => Math.floor(Math.random() * 10)).join('')
}

/** Picks a group by weight, so the mix comes out roughly as the city looks. */
function herkunft(): Herkunft {
    const gesamt = HERKUENFTE.reduce((summe, eintrag) => summe + eintrag.gewicht, 0)
    let wurf = Math.random() * gesamt
    for (const eintrag of HERKUENFTE) {
        wurf -= eintrag.gewicht
        if (wurf <= 0) return eintrag
    }
    return HERKUENFTE[0]!
}

/**
 * First and last name are drawn from the same group, or the result is a name nobody has:
 * "Zeynep Wiśniewska" is not a Berliner, it is two Berliners stapled together.
 */
export function zufallsname(): string {
    const gruppe = herkunft()
    const vorname = eines(gruppe.vornamen)
    const nachname = eines(gruppe.nachnamen)
    const geschrieben = typeof nachname === 'string'
        ? nachname
        : (vorname.weiblich ? nachname.weiblich : nachname.maennlich)
    return `${vorname.name} ${geschrieben}`
}

/** A Berlin landline in the format the dispatch system records: country, area, then the number. */
export function festnetznummer(): string {
    return `4930${ziffern(8)}`
}

export function mobilnummer(): string {
    return `49${eines(MOBILVORWAHLEN)}${ziffern(7)}`
}

/**
 * The A-Platz is a cipher rather than a readable place: a fixed prefix, four more letters and a
 * two-digit number, as in `PRLTSCMN-31`.
 */
export function aPlatzKennung(): string {
    const buchstaben = Array.from({length: 4},
        () => 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'[Math.floor(Math.random() * 26)]).join('')
    return `PRLT${buchstaben}-${ziffern(2)}`
}
