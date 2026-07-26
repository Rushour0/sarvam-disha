"""Generate data/scholarships.json from officially sourced scheme listings.

Scholarship facts are money advice to a seventeen-year-old. An invented income
ceiling or amount is worse than no answer, so this file follows one rule: a
field is populated only if an official page states it, and every record carries
`source_url` and `fetched_on`. Where the amount or income ceiling could not be
read off an official page, it stays null and Disha treats it as not-in-list.

`applies_to` are coarse tags matched against a student's shortlisted paths — a
scheme is surfaced when the tag fits, never as a promise of eligibility. The
eligibility text is what gets spoken; the tags only drive retrieval.

Run: python3 scripts/build_scholarships.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = REPO_ROOT / "data" / "scholarships.json"

FETCHED_ON = "2026-07-26"
NSP = "https://scholarships.gov.in/All-Scholarships"

# Tags: school (class 9-12), higher-ed (degree), technical (engineering/
# polytechnic), vocational (ITI/skills), defence-family, disability, ner,
# agriculture, research.
MAHADBT = "https://mahadbt.maharashtra.gov.in/"

# Maharashtra schemes. The personas this agent is built for are Marathi-speaking
# students in tier-3/4 Maharashtra, and the state schemes are the ones that
# actually move their decision — a hostel allowance answers "hostel_needed" and
# a 100% fee waiver answers "fee_ceiling" far more concretely than any central
# merit scheme does.
STATE_SCHEMES: list[dict] = [
    {
        "id": "mh-shahu-fee-reimbursement",
        "name": "Rajarshi Chhatrapati Shahu Maharaj Education Fee Scholarship Scheme",
        "provider": "Directorate of Technical Education, Government of Maharashtra",
        "state": "Maharashtra",
        "level": "Higher Education",
        "amount": (
            "100% of tuition and examination fees for female students; 50% for male "
            "students (100% for girls from the 2024-25 academic year)"
        ),
        "income_ceiling": "Rs. 8.00 lakh per annum (combined parental income)",
        "eligibility": (
            "EBC, EWS and SEBC students admitted to professional courses in "
            "government, government-aided or permanent unaided institutions under "
            "the Directorate of Technical Education. Applied on the MahaDBT portal; "
            "paid in two instalments to an Aadhaar-linked bank account."
        ),
        "applies_to": ["higher-ed", "technical", "maharashtra", "girls"],
        "source_url": "https://dte.maharashtra.gov.in/rajarshi-chhatrapati-shahu-maharaj/",
        "fetched_on": FETCHED_ON,
    },
    {
        "id": "mh-panjabrao-hostel-allowance",
        "name": "Dr. Panjabrao Deshmukh Vasatigruh Nirvah Bhatta Yojna (hostel maintenance allowance)",
        "provider": "Directorate of Technical Education, Government of Maharashtra",
        "state": "Maharashtra",
        "level": "Higher Education",
        "amount": (
            "Rs. 60,000 per year in Mumbai, Mumbai suburbs, Navi Mumbai, Thane, Pune, "
            "Pimpri Chinchwad and Nagpur; Rs. 51,000 in revenue division cities and "
            "C-class municipalities; Rs. 43,000 in other districts; Rs. 38,000 in "
            "taluka areas"
        ),
        "income_ceiling": (
            "No income limit for children of small-landholding farmers or registered "
            "labourers; unlimited seats up to Rs. 1 lakh; 500 seats for Rs. 1 lakh to "
            "Rs. 8 lakh"
        ),
        "eligibility": (
            "EBC, EWS and SEBC students admitted through centralised admission to "
            "professional courses in government, government-aided and permanent "
            "unaided institutions under the Directorate of Technical Education."
        ),
        "applies_to": ["higher-ed", "technical", "maharashtra", "hostel"],
        "source_url": (
            "https://dte.maharashtra.gov.in/dr-panjabrao-deshmukh-vastigruh-nirvah-bhatta-yojna/"
        ),
        "fetched_on": FETCHED_ON,
    },
    {
        "id": "mh-goi-post-matric-sc",
        "name": "Government of India Post-Matric Scholarship Scheme (Maharashtra)",
        "provider": (
            "Social Justice & Special Assistance Department, Government of Maharashtra"
        ),
        "state": "Maharashtra",
        "level": "Post Matric",
        "amount": (
            "Maintenance allowance of Rs. 250 to Rs. 700 per month for non-hostel "
            "students and Rs. 400 to Rs. 1,350 per month for hostel residents, "
            "depending on course category, plus tuition, examination and other "
            "approved fees"
        ),
        "income_ceiling": "Rs. 2.50 lakh per annum for the full scholarship",
        "eligibility": (
            "Scheduled Caste or Navbouddha students who are residents of Maharashtra "
            "and studying above 10th standard. Applied on the MahaDBT portal."
        ),
        "applies_to": ["higher-ed", "maharashtra", "hostel"],
        "source_url": (
            "https://sjsa.maharashtra.gov.in/en/scheme/"
            "government-of-india-post-matric-scholarship-scheme/"
        ),
        "fetched_on": FETCHED_ON,
    },
]

# Maharashtra schemes confirmed on the MahaDBT portal listing, name and
# department only — the listing does not state amounts.
MAHADBT_LISTED: list[tuple[str, str, str, list[str]]] = [
    (
        "mh-post-matric-st",
        "Post Matric Scholarship to S.T. Students",
        "Tribal Development Department, Government of Maharashtra",
        ["higher-ed", "maharashtra"],
    ),
    (
        "mh-post-matric-sbc",
        "Post Matric Scholarship to SBC Students",
        "Social Justice & Special Assistance Department, Government of Maharashtra",
        ["higher-ed", "maharashtra"],
    ),
    (
        "mh-freeship-tuition-exam",
        "Post-Matric Tuition Fee and Examination Fee (Freeship)",
        "Government of Maharashtra",
        ["higher-ed", "maharashtra"],
    ),
    (
        "mh-shahu-merit-vjnt-sbc",
        (
            "Rajarshi Chhatrapati Shahu Maharaj Merit Scholarship for VJNT and SBC "
            "students in 11th and 12th standard"
        ),
        "Social Justice & Special Assistance Department, Government of Maharashtra",
        ["school", "maharashtra"],
    ),
    (
        "mh-obc-girls-professional",
        (
            "Post Matric Scholarship to Girls of Other Backward Classes taking "
            "admission in Professional Courses"
        ),
        "Other Backward Bahujan Welfare Department, Government of Maharashtra",
        ["higher-ed", "maharashtra", "girls"],
    ),
    (
        "mh-obc-girls-fees",
        "Payment of Tuition Fees and Examination Fees to OBC Girls Pursuing Professional Courses",
        "Other Backward Bahujan Welfare Department, Government of Maharashtra",
        ["higher-ed", "maharashtra", "girls"],
    ),
    (
        "mh-vjnt-sbc-hostel-allowance",
        (
            "Maintenance Allowance to VJNT and SBC Students in Professional Courses "
            "living in hostels attached to professional colleges"
        ),
        "Social Justice & Special Assistance Department, Government of Maharashtra",
        ["higher-ed", "maharashtra", "hostel"],
    ),
]

SCHEMES: list[dict] = [
    {
        "id": "nmms",
        "name": "National Means-cum-Merit Scholarship (NMMS)",
        "provider": "Department of School Education & Literacy, Ministry of Education",
        "level": "Pre Matric",
        "amount": "Rs. 12,000 per annum (Rs. 1,000 per month)",
        "income_ceiling": "Rs. 3.50 lakh per annum",
        "eligibility": (
            "Class IX students who clear the state selection test, with at least 55% "
            "marks in Class VII (relaxable by 5% for SC/ST). Renewed from Class X to "
            "XII on academic performance. Only for students in State Government, "
            "Government-aided and local body schools."
        ),
        "applies_to": ["school"],
        "source_url": "https://dsel.education.gov.in/scheme/nmmss",
        "fetched_on": FETCHED_ON,
    },
    {
        "id": "sc-merit-upgradation",
        "name": "Upgradation of Merit of SC Students",
        "provider": "Department of Social Justice & Empowerment",
        "level": "Pre Matric",
        "amount": "Package grant of Rs. 25,000 per student per year",
        "income_ceiling": "Rs. 3.00 lakh per annum",
        "eligibility": (
            "SC students in classes IX to XII. The grant covers remedial and "
            "competitive exam coaching along with boarding, lodging, pocket money "
            "and books."
        ),
        "applies_to": ["school"],
        "source_url": "https://socialjustice.gov.in/schemes/26",
        "fetched_on": FETCHED_ON,
    },
    {
        "id": "aicte-pragati-degree",
        "name": "AICTE Pragati Scholarship for Girl Students (Technical Degree)",
        "provider": "All India Council for Technical Education (AICTE)",
        "level": "Higher Education",
        "amount": "Rs. 50,000 per year as incidentals",
        "income_ceiling": None,
        "eligibility": (
            "Girl students admitted to a degree course at an AICTE-approved technical "
            "institution. 10,000 scholarships are awarded each year."
        ),
        "applies_to": ["higher-ed", "technical", "girls"],
        "source_url": (
            "https://www.aicte-india.org/schemes/students-development-schemes/"
            "Pragati/General-Instructions"
        ),
        "fetched_on": FETCHED_ON,
    },
    {
        "id": "aicte-pragati-diploma",
        "name": "AICTE Pragati Scholarship for Girl Students (Technical Diploma)",
        "provider": "All India Council for Technical Education (AICTE)",
        "level": "Higher Education",
        "amount": "Rs. 50,000 per year as incidentals",
        "income_ceiling": None,
        "eligibility": (
            "Girl students admitted to a diploma course at an AICTE-approved technical "
            "institution."
        ),
        "applies_to": ["higher-ed", "technical", "vocational", "girls"],
        "source_url": (
            "https://www.aicte-india.org/schemes/students-development-schemes/"
            "Pragati/General-Instructions"
        ),
        "fetched_on": FETCHED_ON,
    },
    {
        "id": "aicte-saksham-degree",
        "name": "AICTE Saksham Scholarship for Specially Abled Students (Technical Degree)",
        "provider": "All India Council for Technical Education (AICTE)",
        "level": "Higher Education",
        "amount": "Rs. 50,000 per year as incidentals",
        "income_ceiling": None,
        "eligibility": (
            "Differently abled students admitted to a degree course at an "
            "AICTE-approved technical institution."
        ),
        "applies_to": ["higher-ed", "technical", "disability"],
        "source_url": (
            "https://www.aicte-india.org/schemes/students-development-schemes/"
            "Saksham/General-Instructions"
        ),
        "fetched_on": FETCHED_ON,
    },
    {
        "id": "aicte-saksham-diploma",
        "name": "AICTE Saksham Scholarship for Specially Abled Students (Technical Diploma)",
        "provider": "All India Council for Technical Education (AICTE)",
        "level": "Higher Education",
        "amount": "Rs. 50,000 per year as incidentals",
        "income_ceiling": None,
        "eligibility": (
            "Differently abled students admitted to a diploma course at an "
            "AICTE-approved technical institution."
        ),
        "applies_to": ["higher-ed", "technical", "vocational", "disability"],
        "source_url": (
            "https://www.aicte-india.org/schemes/students-development-schemes/"
            "Saksham/General-Instructions"
        ),
        "fetched_on": FETCHED_ON,
    },
]

# Schemes confirmed to exist on the National Scholarship Portal listing, with
# provider and level only. Amounts and income ceilings are deliberately absent:
# the listing does not state them, and guessing is not an option here.
NSP_LISTED: list[tuple[str, str, str, list[str]]] = [
    (
        "aicte-swanath-degree",
        "AICTE Swanath Scholarship Scheme (Technical Degree)",
        "All India Council for Technical Education (AICTE)",
        ["higher-ed", "technical"],
    ),
    (
        "aicte-swanath-diploma",
        "AICTE Swanath Scholarship Scheme (Technical Diploma)",
        "All India Council for Technical Education (AICTE)",
        ["higher-ed", "technical", "vocational"],
    ),
    (
        "pm-usp-csss",
        "PM-USP Central Sector Scheme of Scholarship for College and University Students (CSSS)",
        "Department of Higher Education, Ministry of Education",
        ["higher-ed"],
    ),
    (
        "pm-usp-jk-ladakh",
        "PM USP Special Scholarship Scheme for Jammu Kashmir and Ladakh",
        "All India Council for Technical Education (AICTE)",
        ["higher-ed"],
    ),
    (
        "pm-yasasvi-school",
        "PM YASASVI Top Class Education in Schools for OBC, EBC and DNT Students",
        "Department of Social Justice & Empowerment (Backward Classes)",
        ["school"],
    ),
    (
        "pm-yasasvi-college",
        "PM YASASVI Top Class Education in Colleges for OBC, EBC and DNT Students",
        "Department of Social Justice & Empowerment (Backward Classes)",
        ["higher-ed"],
    ),
    (
        "sc-top-class",
        "Central Sector Scholarship of Top Class Education for SC Students",
        "Department of Social Justice & Empowerment",
        ["higher-ed"],
    ),
    (
        "st-national-fellowship",
        "National Fellowship and Scholarship for Higher Education of ST Students",
        "Ministry of Tribal Affairs",
        ["higher-ed"],
    ),
    (
        "disability-pre-matric",
        "Pre Matric Scholarship for Students with Disabilities",
        "Department of Empowerment of Persons with Disabilities",
        ["school", "disability"],
    ),
    (
        "disability-post-matric",
        "Post Matric Scholarship for Students with Disabilities",
        "Department of Empowerment of Persons with Disabilities",
        ["higher-ed", "disability"],
    ),
    (
        "disability-top-class",
        "Scholarship for Top Class Education for Students with Disabilities",
        "Department of Empowerment of Persons with Disabilities",
        ["higher-ed", "disability"],
    ),
    (
        "beedi-pre-matric",
        "Financial Assistance for Education to the Wards of Beedi/Cine/IOMC/LSDM Workers (Pre Matric)",
        "Ministry of Labour & Employment",
        ["school"],
    ),
    (
        "beedi-post-matric",
        "Financial Assistance for Education to the Wards of Beedi/Cine/IOMC/LSDM Workers (Post Matric)",
        "Ministry of Labour & Employment",
        ["higher-ed"],
    ),
    (
        "capf-pmss",
        "Prime Minister's Scholarship Scheme for Central Armed Police Forces and Assam Rifles",
        "Ministry of Home Affairs",
        ["higher-ed", "defence-family"],
    ),
    (
        "police-martyrs-pmss",
        "PM's Scholarship Scheme for Wards of State/UT Police Personnel Martyred in Terror/Naxal Attacks",
        "Ministry of Home Affairs",
        ["higher-ed", "defence-family"],
    ),
    (
        "railways-pmss",
        "Prime Minister's Scholarship Scheme for Ministry of Railways",
        "Ministry of Railways (Railway Board)",
        ["higher-ed"],
    ),
    (
        "ishan-uday",
        "Ishan Uday Special Scholarship Scheme for North Eastern Region",
        "University Grants Commission (UGC)",
        ["higher-ed", "ner"],
    ),
    (
        "ugc-pg-national",
        "National Scholarship for Post Graduate Studies",
        "University Grants Commission (UGC)",
        ["higher-ed", "research"],
    ),
    (
        "nec-merit",
        "Financial Support to Students of NER for Higher Professional Courses (NEC Merit Scholarship)",
        "North Eastern Council, Ministry of DoNER",
        ["higher-ed", "ner"],
    ),
    (
        "icar-nts-ug",
        "ICAR National Talent Scholarship (NTS-UG)",
        "Department of Agriculture Research and Education",
        ["higher-ed", "agriculture"],
    ),
    (
        "icar-nts-pg",
        "ICAR National Talent Scholarship (NTS-PG)",
        "Department of Agriculture Research and Education",
        ["higher-ed", "agriculture", "research"],
    ),
    (
        "icar-pgs",
        "ICAR Post Graduate Scholarship (PGS)",
        "Department of Agriculture Research and Education",
        ["higher-ed", "agriculture", "research"],
    ),
    (
        "icar-jrf-srf",
        "ICAR Junior and Senior Research Fellowships (JRF/SRF)",
        "Department of Agriculture Research and Education",
        ["research", "agriculture"],
    ),
    (
        "mnre-fellowship",
        "National Renewable Energy Fellowship Scheme",
        "Ministry of New and Renewable Energy",
        ["higher-ed", "research", "technical"],
    ),
    (
        "isi-kolkata-stipend",
        "Stipend Scheme for UG and PG Studies at Indian Statistical Institute, Kolkata",
        "Ministry of Statistics and Programme Implementation",
        ["higher-ed"],
    ),
]


def build() -> list[dict]:
    records = [{**scheme, "state": scheme.get("state")} for scheme in SCHEMES]
    records.extend(STATE_SCHEMES)

    listings = [
        (NSP_LISTED, None, NSP, "the National Scholarship Portal"),
        (MAHADBT_LISTED, "Maharashtra", MAHADBT, "the MahaDBT portal"),
    ]
    for entries, state, source_url, portal in listings:
        for scheme_id, name, provider, tags in entries:
            records.append(
                {
                    "id": scheme_id,
                    "name": name,
                    "provider": provider,
                    "state": state,
                    "level": "Higher Education" if "higher-ed" in tags else "Pre/Post Matric",
                    "amount": None,
                    "income_ceiling": None,
                    "eligibility": (
                        f"Listed on {portal}. Detailed eligibility, amount and last "
                        f"date are published in the scheme guidelines there."
                    ),
                    "applies_to": tags,
                    "source_url": source_url,
                    "fetched_on": FETCHED_ON,
                }
            )
    return records


def main() -> None:
    records = build()
    with_amount = sum(1 for record in records if record["amount"])
    state_count = sum(1 for record in records if record.get("state"))
    print(f"  {state_count} are state schemes (Maharashtra)")
    OUTPUT_PATH.write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"wrote {len(records)} schemes to {OUTPUT_PATH}")
    print(f"  {with_amount} carry a sourced amount; the rest are name+provider only")


if __name__ == "__main__":
    main()
