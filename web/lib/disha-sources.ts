/**
 * The public places this product's answers come from.
 *
 * Mirrors the `sources` block of data/pathway_tree.json plus the two handbooks
 * and the scholarship portals. It is duplicated here rather than fetched
 * because the case API is server-only and a student on the summary screen
 * should not need a live backend to be told where an answer came from.
 *
 * Entries carrying a `state` are only shown when the conversation actually
 * touched that state, so a student in Bihar is not handed Maharashtra portals.
 */
export interface DishaSource {
  title: string;
  url: string;
  note: string;
  state?: string;
}

export const DISHA_SOURCES: DishaSource[] = [
  {
    title: 'National Scholarship Portal',
    url: 'https://scholarships.gov.in/',
    note: 'Central government scholarship applications',
  },
  {
    title: 'Bharat Skills — Craftsmen Training Scheme trades',
    url: 'https://bharatskills.gov.in/Home/CTS',
    note: 'The official ITI trade list (DGT/NCVT)',
  },
  {
    title: 'Join Indian Army — entry schemes',
    url: 'https://joinindianarmy.nic.in/',
    note: 'Entry routes after Class 10 and 12',
  },
  {
    title: 'Department of Social Justice & Empowerment',
    url: 'https://socialjustice.gov.in/',
    note: 'Pre-matric and post-matric scheme rules',
  },
  {
    title: 'AICTE schemes',
    url: 'https://www.aicte-india.org/schemes/students-development-schemes',
    note: 'Technical-education scholarships',
  },
  {
    title: 'Directorate of Vocational Education & Training, Maharashtra',
    url: 'https://dvet.gov.in/',
    note: 'State ITI admissions and trades',
    state: 'Maharashtra',
  },
  {
    title: 'MahaDBT scholarships',
    url: 'https://mahadbt.maharashtra.gov.in/',
    note: 'Maharashtra state scholarship applications',
    state: 'Maharashtra',
  },
  {
    title: 'Directorate of Technical Education, Maharashtra',
    url: 'https://dte.maharashtra.gov.in/',
    note: 'State diploma and degree admissions',
    state: 'Maharashtra',
  },
];

/** Sources worth showing given the states this conversation actually named. */
export function sourcesForStates(states: string[]): DishaSource[] {
  const named = new Set(states.filter(Boolean));
  return DISHA_SOURCES.filter((source) => !source.state || named.has(source.state));
}
