// A short fact about women in business and innovation for the top of the Today page, tied to the calendar.
//  1. A fact whose date is today's date shows as "On this day".
//  2. Otherwise the nearest dated fact within a week shows, labelled with its real date ("Nov 10, 1903 · 3 days ago"),
//     so every day from now through January has something that happened close to that date.
//  3. Only when nothing dated is within a week does an undated fact take its place (rotating daily).
// Dates were checked against sources (births, patents, appointments); where sources disagree the text is hedged.
// The list is hand-written: add to it any time, as { on: "MM-DD", year, text }.
const FACTS = [
  // ---- dated ----
  { on: "01-01", year: 2012, text: "Ginni Rometty became CEO of IBM, the first woman to lead the company." },
  { on: "01-05", year: 1904, text: "Lizzie Magie was granted a U.S. patent for The Landlord's Game, a board game meant to show the harm of land monopolies. It was a forerunner of Monopoly." },
  { on: "01-10", year: 1898, text: "Katharine Burr Blodgett was born. She became the first woman research scientist at General Electric's laboratories and is credited with inventing non-reflective glass." },
  { on: "01-15", year: 2014, text: "Mary Barra became CEO of General Motors, the first woman to lead a major global automaker." },
  { on: "01-29", year: 1954, text: "Oprah Winfrey was born in Kosciusko, Mississippi. In 1986 she formed Harpo Productions, the company behind her television empire." },
  { on: "03-09", year: 1959, text: "The Barbie doll debuted at the American International Toy Fair in New York. Ruth Handler, who co-founded Mattel, created her." },
  { on: "08-11", year: 1942, text: "Actress Hedy Lamarr and composer George Antheil were granted a patent for a frequency-hopping secret communication system. The idea lies behind much modern wireless technology." },
  { on: "11-02", year: 1903, text: "Maggie Lena Walker opened the St. Luke Penny Savings Bank in Richmond, Virginia, becoming the first African American woman to charter and lead a U.S. bank." },
  { on: "11-03", year: 1914, text: "Mary Phelps Jacob was granted a patent for her \"backless brassiere\". She sold the rights to a corset company for $1,500." },
  { on: "11-07", year: 1867, text: "Marie Curie was born in Warsaw. She went on to win Nobel Prizes in both physics and chemistry, and to found research institutes that carried her work forward." },
  { on: "11-09", year: 1914, text: "Hedy Lamarr was born in Vienna. Besides acting, she co-invented a frequency-hopping communication system, patented in 1942." },
  { on: "11-10", year: 1903, text: "Mary Anderson was granted a U.S. patent for a window-cleaning device operated from inside the vehicle: the windshield wiper." },
  { on: "11-18", year: 1975, text: "Reshma Saujani was born. She went on to found Girls Who Code, a nonprofit working to close the gender gap in technology." },
  { on: "11-23", year: 1963, text: "Gwynne Shotwell was born in Evanston, Illinois. She became president and COO of SpaceX, which she joined in 2002." },
  { on: "12-02", year: 1969, text: "Marie Van Brittan Brown, a nurse in Queens, and her husband were granted a patent for a home security system with a camera, monitor and remote door lock." },
  { on: "12-09", year: 1906, text: "Grace Hopper was born. She created A-0, often described as the first compiler, and became a rear admiral in the U.S. Navy." },
  { on: "12-10", year: 1815, text: "Ada Lovelace was born. Her notes on Charles Babbage's Analytical Engine contain what many consider the first algorithm written for a machine." },
  { on: "12-23", year: 1867, text: "Sarah Breedlove, later known as Madam C.J. Walker, was born in Delta, Louisiana. She built a hair-care manufacturing company and is often cited as the first self-made female millionaire in the United States." },
  { on: "12-24", year: 1961, text: "Mary Barra was born. She became CEO of General Motors in 2014." },
  { on: "12-25", year: "c. 1872", text: "Helena Rubinstein was born in Kraków (sources give 1870 or 1872). She built a global cosmetics business that began with a single salon in Melbourne." },
  { on: "12-27", year: 1953, text: "Marillyn Hewson was born. She led Lockheed Martin as chairman, president and CEO from 2013 to 2020." },
  { on: "12-28", year: 1886, text: "Josephine Cochrane was granted a patent for her dish washing machine, and went on to build a company to sell it to hotels and restaurants." },
  { on: "12-28", year: 1967, text: "Muriel Siebert became the first woman to own a seat on the New York Stock Exchange, at a time when it had about 1,365 male members." },

  // ---- any day ----
  { year: 1843, text: "Ada Lovelace published notes on Charles Babbage's Analytical Engine that contain what many consider the first algorithm written for a machine." },
  { year: 1825, text: "Rebecca Lukens took over her late husband's Pennsylvania ironworks and ran it for decades, and is often described as America's first female CEO of an industrial company." },
  { year: 1871, text: "Margaret Knight patented a machine that folded and glued flat-bottomed paper bags, the kind still in use at grocery stores." },
  { year: 1886, text: "Josephine Cochrane patented a hand-operated dishwasher and then built a company to sell it to hotels and restaurants." },
  { year: 1902, text: "Helena Rubinstein opened a beauty salon in Melbourne, Australia, the start of a global cosmetics business." },
  { year: 1910, text: "Madam C.J. Walker built a hair-care manufacturing company headquartered in Indianapolis. She is often cited as the first self-made female millionaire in the United States." },
  { year: 1910, text: "Coco Chanel opened her first shop, a hat boutique, in Paris. She went on to remake women's fashion." },
  { year: 1938, text: "Katharine Blodgett, a physicist at General Electric, developed non-reflective glass, now used in camera lenses and eyeglasses." },
  { year: 1946, text: "Estée Lauder and her husband Joseph launched a small line of skin care products, the beginning of Estée Lauder Companies." },
  { year: 1951, text: "Marion Donovan patented a waterproof diaper cover made from a shower curtain, an early step toward the disposable diaper." },
  { year: 1952, text: "Grace Hopper created A-0, often described as the first compiler, helping make programming in near-English possible." },
  { year: 1963, text: "Mary Kay Ash founded Mary Kay Cosmetics in Dallas with $5,000 in savings." },
  { year: 1965, text: "Stephanie Kwolek, a chemist at DuPont, invented the fiber that became Kevlar, used in body armor and tires." },
  { year: 1965, text: "Industrial engineer Lillian Gilbreth, a pioneer of time-and-motion study, became the first woman elected to the National Academy of Engineering." },
  { year: 1968, text: "Mary Wells Lawrence's advertising agency, Wells Rich Greene, went public, making her the first woman to be CEO of a company listed on the New York Stock Exchange." },
  { year: 1976, text: "Anita Roddick opened the first Body Shop in Brighton, England, selling cosmetics with a focus on ethical sourcing." },
  { year: 1979, text: "Bette Nesmith Graham sold Liquid Paper, the correction fluid she began mixing in her kitchen, to Gillette for $47.5 million." },
  { year: 1984, text: "Susan Kare designed the original icons and typefaces for the Apple Macintosh, including the smiling computer and the trash can." },
  { year: 1985, text: "Sophie Wilson designed the instruction set of the ARM processor, now at the heart of billions of phones and devices." },
  { year: 1988, text: "Patricia Bath received a patent for a laser device to remove cataracts, the first U.S. medical patent granted to a Black American woman physician." },
  { year: 1998, text: "Google started in a garage in Menlo Park rented from Susan Wojcicki, who later became CEO of YouTube." },
  { year: 2000, text: "Sara Blakely founded Spanx with $5,000 in savings. In 2012 Forbes named her the youngest self-made female billionaire." },
  { year: 2006, text: "Frances Allen became the first woman to win the Turing Award, computing's highest honor, for her work on optimizing compilers at IBM." },
  { year: 2006, text: "Indra Nooyi became CEO of PepsiCo, a role she held until 2018." },
  { year: 2008, text: "Gwynne Shotwell became president of SpaceX, which she joined in 2002 and helped grow into a leading launch company." },
  { year: 2009, text: "Ursula Burns became CEO of Xerox, the first Black woman to lead a Fortune 500 company, succeeding another woman, Anne Mulcahy." },
  { year: 2021, text: "Whitney Wolfe Herd took Bumble public at age 31, widely reported as the youngest woman to take a company public." },
];

const _EVERGREEN = FACTS.filter(f => !f.on);
const _DATED = FACTS.filter(f => f.on);
const _MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const _NEAR_DAYS = 7;
const _utcDay = (y, m, d) => Math.floor(Date.UTC(y, m, d) / 86400000);

// The fact for a calendar date (a Date, read in its own local time). Returns { label, text }.
function pickFact(date = new Date()) {
  const y = date.getFullYear(), m = date.getMonth(), d = date.getDate(), today = _utcDay(y, m, d);
  // distance in days from today to each dated fact's anniversary (the nearest one, counting across New Year)
  const scored = _DATED.map(f => {
    const [fm, fd] = f.on.split("-").map(Number);
    const diff = [y - 1, y, y + 1].map(yy => _utcDay(yy, fm - 1, fd) - today).sort((a, b) => Math.abs(a) - Math.abs(b) || a - b)[0];
    return { f, diff };
  });
  const exact = scored.filter(s => s.diff === 0).map(s => s.f);
  if (exact.length) {
    const f = exact[y % exact.length];  // two facts on one date alternate by year
    return { label: `On this day · ${f.year}`, text: f.text };
  }
  const near = scored.filter(s => Math.abs(s.diff) <= _NEAR_DAYS)
    .sort((a, b) => Math.abs(a.diff) - Math.abs(b.diff) || a.diff - b.diff)[0];  // a tie goes to the earlier date
  if (near) {
    const [fm, fd] = near.f.on.split("-").map(Number), n = Math.abs(near.diff);
    const when = near.diff < 0 ? (n === 1 ? "yesterday" : `${n} days ago`) : (n === 1 ? "tomorrow" : `in ${n} days`);
    return { label: `${_MONTHS[fm - 1]} ${fd}, ${near.f.year} · ${when}`, text: near.f.text };
  }
  const f = _EVERGREEN[today % _EVERGREEN.length];
  return { label: `Women in business · ${f.year}`, text: f.text };
}

if (typeof module !== "undefined") module.exports = { FACTS, pickFact };
