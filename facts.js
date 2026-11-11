// A short fact about women in business and innovation for the top of the Today page, tied to the calendar.
//  1. A fact whose date is today's date shows as "On this day".
//  2. Otherwise an undated fact shows, rotating daily, so a past day's fact never lingers.
//  The date is always today's date in Central time (America/Chicago), whatever time zone the visitor is in.
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
  { on: "11-11", year: 1914, text: "Daisy Bates was born in Huttig, Arkansas. As president of the Arkansas NAACP she mentored the Little Rock Nine during the 1957 integration of Central High School." },
  { on: "11-12", year: 1815, text: "Elizabeth Cady Stanton was born in Johnstown, New York. She helped organize the 1848 Seneca Falls Convention and drafted its Declaration of Sentiments." },
  { on: "11-13", year: 1938, text: "Mother Frances Xavier Cabrini was beatified. The founder of the Missionary Sisters of the Sacred Heart, she was canonized in 1946 as the first U.S. citizen to become a saint." },
  { on: "11-14", year: 1889, text: "Nellie Bly set out from Hoboken, New Jersey, to beat the 80 days of Jules Verne's fictional Phileas Fogg. She returned on January 25, 1890, having circled the globe in 72 days." },
  { on: "11-15", year: 1887, text: "Georgia O'Keeffe was born in Sun Prairie, Wisconsin. Her large-scale flower paintings and New Mexico landscapes made her one of the best-known American painters of the 20th century." },
  { on: "11-16", year: 1899, text: "Mary Margaret McBride was born. She became one of the most popular radio talk-show hosts in the United States, interviewing thousands of guests over several decades." },
  { on: "11-17", year: 1903, text: "Molly Spotted Elk was born on the Penobscot reservation in Maine. She became a dancer, actress and author who performed in the United States and Europe and wrote about her Penobscot heritage." },
  { on: "11-18", year: 1975, text: "Reshma Saujani was born. She went on to found Girls Who Code, a nonprofit working to close the gender gap in technology." },
  { on: "11-19", year: 1917, text: "Indira Gandhi was born in Allahabad. She became India's first woman prime minister and led the country from 1966 to 1977 and again from 1980 until 1984." },
  { on: "11-20", year: 1910, text: "Pauli Murray was born in Baltimore. A lawyer and civil rights advocate, she wrote States' Laws on Race and Color and in 1977 became the first Black woman ordained an Episcopal priest." },
  { on: "11-21", year: 1834, text: "Hetty Green was born in New Bedford, Massachusetts. She built a fortune investing in railroads, real estate and bonds, and became known as the Witch of Wall Street." },
  { on: "11-22", year: 1943, text: "Billie Jean King was born in Long Beach, California. She co-founded the Women's Tennis Association in 1973 and campaigned for equal prize money for women." },
  { on: "11-23", year: 1963, text: "Gwynne Shotwell was born in Evanston, Illinois. She became president and COO of SpaceX, which she joined in 2002." },
  { on: "11-24", year: 1910, text: "Lucy Covington was born. A Colville tribal leader, she led the campaign against termination, the federal policy that would have ended recognition of the Colville Confederated Tribes." },
  { on: "11-25", year: 1900, text: "Helen Gahagan Douglas was born in Boonton, New Jersey. An opera singer and actress, she became a U.S. representative from California, serving from 1945 to 1951." },
  { on: "11-26", year: 1792, text: "Sarah Grimke was born in Charleston, South Carolina. She became an abolitionist and a pioneering writer on women's rights, publishing Letters on the Equality of the Sexes in 1838." },
  { on: "11-27", year: 1999, text: "Helen Clark led New Zealand's Labour Party to victory in a general election, becoming the country's first woman to be elected prime minister." },
  { on: "11-28", year: 1919, text: "Nancy Astor won a by-election in Plymouth Sutton. On December 1 she took her seat as the first woman to sit in the British House of Commons." },
  { on: "11-29", year: 1832, text: "Louisa May Alcott was born in Germantown, Pennsylvania. Her novel Little Women, published in 1868, drew on her own family and became a classic." },
  { on: "11-30", year: 1924, text: "Shirley Chisholm was born in Brooklyn. In 1968 she became the first Black woman elected to the U.S. Congress, and in 1972 she ran for the Democratic presidential nomination." },
  { on: "12-01", year: 1955, text: "Rosa Parks was arrested in Montgomery, Alabama, for refusing to give up her bus seat. Her arrest led to the Montgomery bus boycott." },
  { on: "12-02", year: 1969, text: "Marie Van Brittan Brown, a nurse in Queens, and her husband were granted a patent for a home security system with a camera, monitor and remote door lock." },
  { on: "12-03", year: 1842, text: "Ellen Swallow Richards was born in Dunstable, Massachusetts. In 1873 she became the first woman to earn a degree at MIT, and she went on to help found the field of home economics." },
  { on: "12-04", year: 1978, text: "Dianne Feinstein was chosen by San Francisco's Board of Supervisors to serve as mayor, the first woman to hold the office, after the assassination of Mayor George Moscone." },
  { on: "12-05", year: 1935, text: "Mary McLeod Bethune founded the National Council of Negro Women in New York City, bringing national Black women's organizations together under one umbrella." },
  { on: "12-06", year: 1927, text: "Patsy Mink was born in Maui, Hawaii. In 1964 she became the first woman of color elected to the U.S. House of Representatives, and she co-authored Title IX." },
  { on: "12-07", year: 1873, text: "Willa Cather was born in Back Creek Valley, Virginia. She grew up in Nebraska, and her novel One of Ours won the Pulitzer Prize in 1923." },
  { on: "12-08", year: 1919, text: "Julia Robinson was born in St. Louis. Her work on decision problems was key to the solution of Hilbert's tenth problem, and in 1983 she became the first woman president of the American Mathematical Society." },
  { on: "12-09", year: 1906, text: "Grace Hopper was born. She created A-0, often described as the first compiler, and became a rear admiral in the U.S. Navy." },
  { on: "12-10", year: 1815, text: "Ada Lovelace was born. Her notes on Charles Babbage's Analytical Engine contain what many consider the first algorithm written for a machine." },
  { on: "12-11", year: 1892, text: "Harriet Stratemeyer Adams was born in Newark, New Jersey. She took over the Stratemeyer Syndicate and wrote and oversaw the Nancy Drew and Hardy Boys series for decades." },
  { on: "12-12", year: 1928, text: "Helen Frankenthaler was born in New York City. She pioneered the soak-stain technique, pouring thinned paint onto raw canvas, and became a leading figure in color field painting." },
  { on: "12-13", year: 1903, text: "Ella Baker was born in Norfolk, Virginia. She became a key organizer of the civil rights movement, helped found the Student Nonviolent Coordinating Committee in 1960, and championed grassroots leadership." },
  { on: "12-14", year: 1985, text: "Wilma Mankiller was sworn in as principal chief of the Cherokee Nation, the first woman to lead a major Native American tribe in modern times." },
  { on: "12-15", year: 1913, text: "Muriel Rukeyser was born in New York City. A poet and activist, she wrote about social justice, and her 1935 collection Theory of Flight won the Yale Series of Younger Poets prize." },
  { on: "12-16", year: 1901, text: "Margaret Mead was born in Philadelphia. The cultural anthropologist became widely known for Coming of Age in Samoa, published in 1928." },
  { on: "12-17", year: 1853, text: "Harriet Taylor Upton was born in Ravenna, Ohio. She was treasurer of the National American Woman Suffrage Association and a leader of the movement in Ohio." },
  { on: "12-18", year: 1922, text: "Esther Lederberg was born in the Bronx. A microbiologist, she discovered the lambda bacteriophage and invented replica plating, a technique used to study bacterial genetics." },
  { on: "12-19", year: 1919, text: "Sally Lilienthal was born in San Francisco. A peace activist, she founded the Ploughshares Fund in 1981 to support efforts to reduce nuclear weapons." },
  { on: "12-20", year: 1954, text: "Sandra Cisneros was born in Chicago. Her novel The House on Mango Street, published in 1984, became a staple of American classrooms." },
  { on: "12-21", year: 1959, text: "Florence Griffith Joyner was born in Los Angeles. At the 1988 Seoul Olympics she won three gold medals and one silver, and her 100 m and 200 m world records still stand." },
  { on: "12-22", year: 1912, text: "Lady Bird Johnson was born in Karnack, Texas. As First Lady she championed highway beautification and Head Start, and she ran the family's Austin broadcasting business." },
  { on: "12-23", year: 1867, text: "Sarah Breedlove, later known as Madam C.J. Walker, was born in Delta, Louisiana. She built a hair-care manufacturing company and is often cited as the first self-made female millionaire in the United States." },
  { on: "12-24", year: 1961, text: "Mary Barra was born. She became CEO of General Motors in 2014." },
  { on: "12-25", year: "c. 1872", text: "Helena Rubinstein was born in Kraków (sources give 1870 or 1872). She built a global cosmetics business that began with a single salon in Melbourne." },
  { on: "12-26", year: 1954, text: "Susan Butcher was born in Cambridge, Massachusetts. She won the Iditarod Trail Sled Dog Race four times, in 1986, 1987, 1988 and 1990." },
  { on: "12-27", year: 1953, text: "Marillyn Hewson was born. She led Lockheed Martin as chairman, president and CEO from 2013 to 2020." },
  { on: "12-28", year: 1886, text: "Josephine Cochrane was granted a patent for her dish washing machine, and went on to build a company to sell it to hotels and restaurants." },
  { on: "12-28", year: 1967, text: "Muriel Siebert became the first woman to own a seat on the New York Stock Exchange, at a time when it had about 1,365 male members." },
  { on: "12-29", year: 1937, text: "Thea Bowman was born in Yazoo City, Mississippi. A Franciscan sister, she became a gospel singer and teacher, and she urged the Catholic Church to embrace Black culture." },
  { on: "12-30", year: 1912, text: "Margaret Wade was born in McCool, Mississippi. As coach at Delta State she won 453 games and three national titles, and the Wade Trophy honors her." },
  { on: "12-31", year: 1900, text: "Selma Burke was born in Mooresville, North Carolina. A sculptor, she made a 1944 relief portrait of Franklin D. Roosevelt that is widely credited as the basis for the Roosevelt dime." },

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
const _utcDay = (y, m, d) => Math.floor(Date.UTC(y, m, d) / 86400000);

// Today's calendar date in Central time, as [year, monthIndex, day].
function _centralToday(now = new Date()) {
  const p = Object.fromEntries(new Intl.DateTimeFormat("en-US", { timeZone: "America/Chicago", year: "numeric", month: "numeric", day: "numeric" })
    .formatToParts(now).filter(x => x.type !== "literal").map(x => [x.type, Number(x.value)]));
  return [p.year, p.month - 1, p.day];
}

// The fact for a calendar date. A Date is read in its own local time (tests); with no argument it is today in Central time.
function pickFact(date) {
  const [y, m, d] = date ? [date.getFullYear(), date.getMonth(), date.getDate()] : _centralToday(), today = _utcDay(y, m, d);
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
  const f = _EVERGREEN[today % _EVERGREEN.length];
  return { label: `Women in business · ${f.year}`, text: f.text };
}

if (typeof module !== "undefined") module.exports = { FACTS, pickFact };
