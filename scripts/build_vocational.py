"""Generate data/vocational_paths.json — the branch the career tree is missing.

The 89-node career tree is degree-only: `Vocational Education` has no children
and `Defence` has two generic ones. So a student asking about ITI, an army
entry, tailoring, or cooking gets a refusal even though those are the most
relevant options for the tier-3/4 audience this agent is built for.

Every record here comes from an official source and carries `source_url` and
`fetched_on`. Fields that could not be sourced per-record — notably per-trade
duration and per-trade minimum qualification, which Bharat Skills does not
publish on its index page — are left null on purpose. Disha would rather say
"that detail is not in my list" than quote a duration it guessed.

Run: python3 scripts/build_vocational.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = REPO_ROOT / "data" / "vocational_paths.json"

FETCHED_ON = "2026-07-26"
BHARAT_SKILLS = "https://bharatskills.gov.in/Home/CTS"
JOIN_ARMY = "https://joinindianarmy.nic.in/"

# Craftsmen Training Scheme trades, as listed on the Bharat Skills CTS index.
ITI_ENGINEERING = [
    "Electrician",
    "Fitter",
    "Electronics Mechanic",
    "Computer Operator and Programming Assistant (COPA)",
    "Mechanic Motor Vehicle (MMV)",
    "Welder",
    "Wireman",
    "Mechanic Diesel",
    "Draughtsman (Civil)",
    "Refrigeration and Air Conditioning Technician",
    "Turner",
    "Machinist",
    "Plumber",
    "Draughtsman Mechanical",
    "Information & Communication Technology System Maintenance (ICTSM)",
    "Instrument Mechanic",
    "Wood Work Technician",
    "Surveyor",
    "Painter (General)",
    "Mechanic Tractor",
    "Machinist Grinder",
    "Sheet Metal Worker",
    "Fire Technology and Industrial Safety Management",
    "Computer Hardware & Network Maintenance",
    "Mechanic Machine Tool Maintenance",
    "Foundryman",
    "Desktop Publishing Operator",
    "Technician Power Electronics Systems",
    "Mechanic Auto Electrical and Electronics",
    "Interior Design & Decoration",
    "Information Technology",
    "Hospital Housekeeping",
    "Mechanic Auto Body Repair",
    "Mechanic Agricultural Machinery",
    "Electroplater",
    "Operator Advanced Machine Tool",
    "Computer Aided Embroidery & Designing",
    "Lift and Escalator Mechanic",
    "Mechanic Consumer Electronic Appliances",
    "Architectural Draughtsman",
    "Laboratory Assistant (Chemical Plant)",
    "Solar Technician (Electrical)",
    "Multimedia, Animation & Special Effects",
    "Leather Goods Maker",
    "Footwear Maker",
    "Finance Executive",
    "Food Beverage",
    "Spa Therapy",
]

ITI_NON_ENGINEERING = [
    "Health Sanitary Inspector",
    "Sewing Technology",
    "Stenographer Secretarial Assistant (Hindi)",
    "Stenographer Secretarial Assistant (English)",
    "Cosmetology",
    "Dress Making",
    "Fashion Design and Technology",
    "Food Production (General)",
    "Plastic Processing Operator",
    "Tool & Die Maker (Dies & Moulds, Press Tools)",
    "Tool & Die Maker (Press Tools, Jigs & Fixtures)",
    "Physiotherapy Technician",
    "Secretarial Practice (English)",
    "Mason (Building Constructor)",
    "Front Office Assistant",
    "Dental Laboratory Equipment Technician",
    "Driver cum Mechanic (LMV)",
    "Radiology Technician",
    "Mechanic Auto Body Painting",
    "Fruits and Vegetables Processing",
    "Catering & Hospitality Assistant",
    "Soil Testing and Crop Technician",
]

# The jobs text is what makes a trade findable when a student describes the
# work rather than the qualification ("khana banane ka kaam", "gaadi theek
# karna"). Only plain restatements of the trade name are used — no invented
# employers, salaries, or placement claims.
TRADE_JOBS = {
    "Electrician": "Electrician, wiring technician, electrical maintenance work",
    "Fitter": "Fitter, machine assembly and maintenance work",
    "Welder": "Welder, welding and fabrication work",
    "Wireman": "Wireman, electrical wiring work",
    "Plumber": "Plumber, pipe fitting and sanitation work",
    "Mechanic Motor Vehicle (MMV)": "Motor vehicle mechanic, car and vehicle repair work",
    "Mechanic Diesel": "Diesel mechanic, engine repair work",
    "Mechanic Tractor": "Tractor mechanic, farm vehicle repair work",
    "Mechanic Agricultural Machinery": "Agricultural machinery mechanic, farm equipment repair",
    "Computer Operator and Programming Assistant (COPA)": (
        "Computer operator, data entry operator, office computer work"
    ),
    "Information Technology": "IT assistant, computer support work",
    "Computer Hardware & Network Maintenance": "Computer hardware technician, network support",
    "Desktop Publishing Operator": "Desktop publishing operator, printing and design work",
    "Cosmetology": "Beautician, beauty parlour work, salon work, cosmetology",
    "Spa Therapy": "Spa therapist, wellness and salon work",
    "Sewing Technology": "Tailor, sewing machine operator, garment stitching work",
    "Dress Making": "Dress maker, tailor, boutique stitching work",
    "Fashion Design and Technology": "Fashion designer assistant, garment design work",
    "Computer Aided Embroidery & Designing": "Embroidery designer, machine embroidery work",
    "Food Production (General)": (
        "Cook, chef, kitchen work, food production, hotel and restaurant kitchen work"
    ),
    "Catering & Hospitality Assistant": (
        "Catering assistant, hotel service work, restaurant and hospitality work"
    ),
    "Food Beverage": "Food and beverage service, restaurant service work",
    "Front Office Assistant": "Front office assistant, hotel reception work",
    "Hospital Housekeeping": "Hospital housekeeping staff, hospital support work",
    "Health Sanitary Inspector": "Health sanitary inspector, public health work",
    "Physiotherapy Technician": "Physiotherapy technician, hospital rehabilitation support",
    "Radiology Technician": "Radiology technician, X-ray and imaging work in hospitals",
    "Dental Laboratory Equipment Technician": "Dental laboratory technician",
    "Laboratory Assistant (Chemical Plant)": "Laboratory assistant, chemical plant testing work",
    "Soil Testing and Crop Technician": "Soil testing technician, agriculture and farming support work",
    "Fruits and Vegetables Processing": "Food processing worker, fruit and vegetable processing",
    "Mason (Building Constructor)": "Mason, building construction work",
    "Surveyor": "Surveyor, land measurement work",
    "Draughtsman (Civil)": "Civil draughtsman, building drawing work",
    "Architectural Draughtsman": "Architectural draughtsman, building design drawing",
    "Draughtsman Mechanical": "Mechanical draughtsman, machine drawing work",
    "Interior Design & Decoration": "Interior designer assistant, decoration work",
    "Multimedia, Animation & Special Effects": "Animator, multimedia and video editing work",
    "Refrigeration and Air Conditioning Technician": "AC and fridge repair technician",
    "Solar Technician (Electrical)": "Solar panel technician, solar installation work",
    "Lift and Escalator Mechanic": "Lift and escalator mechanic",
    "Mechanic Consumer Electronic Appliances": "TV and home appliance repair technician",
    "Electronics Mechanic": "Electronics mechanic, electronic repair work",
    "Instrument Mechanic": "Instrument mechanic, industrial instrument repair",
    "Technician Power Electronics Systems": "Power electronics technician",
    "Mechanic Auto Electrical and Electronics": "Auto electrician, vehicle electrical repair",
    "Mechanic Auto Body Repair": "Auto body repair mechanic, denting work",
    "Mechanic Auto Body Painting": "Auto body painter, vehicle painting work",
    "Driver cum Mechanic (LMV)": "Driver, light motor vehicle driving and repair work",
    "Painter (General)": "Painter, building and general painting work",
    "Sheet Metal Worker": "Sheet metal worker, fabrication work",
    "Turner": "Turner, lathe machine work",
    "Machinist": "Machinist, machine shop work",
    "Machinist Grinder": "Grinding machine operator",
    "Operator Advanced Machine Tool": "CNC machine operator, advanced machine tool work",
    "Mechanic Machine Tool Maintenance": "Machine tool maintenance mechanic",
    "Foundryman": "Foundryman, metal casting work",
    "Electroplater": "Electroplater, metal plating work",
    "Wood Work Technician": "Carpenter, wood work technician, furniture work",
    "Leather Goods Maker": "Leather goods maker, bag and accessory making",
    "Footwear Maker": "Footwear maker, shoe making work",
    "Plastic Processing Operator": "Plastic processing machine operator",
    "Fire Technology and Industrial Safety Management": "Fireman, industrial safety work",
    "Tool & Die Maker (Dies & Moulds, Press Tools)": "Tool and die maker",
    "Tool & Die Maker (Press Tools, Jigs & Fixtures)": "Tool and die maker",
    "Stenographer Secretarial Assistant (Hindi)": "Stenographer, office secretarial work in Hindi",
    "Stenographer Secretarial Assistant (English)": "Stenographer, office secretarial work in English",
    "Secretarial Practice (English)": "Office secretary, clerical work",
    "Finance Executive": "Finance executive, accounts assistant work",
    "Information & Communication Technology System Maintenance (ICTSM)": (
        "ICT system maintenance technician"
    ),
}

# Army entry routes, as listed on the Join Indian Army portal. Only the minimum
# qualification the portal itself states is recorded.
ARMY_ENTRIES = [
    ("Agniveer (General Duty)", None),
    ("Agniveer Tradesmen (10th)", "10th pass"),
    ("Agniveer Tradesmen (8th)", "8th pass"),
    ("Agniveer Tech", None),
    ("Agniveer (Clerk and Store Keeper Technical)", None),
    ("Agniveer GD (Women Military Police)", None),
    ("Soldier Technical (Nursing Assistant)", None),
    ("Sepoy (Pharma)", None),
    ("Havildar Education", None),
    ("Junior Commissioned Officer (Religious Teacher)", None),
]


# Hindi/Marathi words students actually use for the work. These are language
# aliases for retrieval only — a translation of the trade name, never a claim
# about the course. Without them "silai ka kaam" finds nothing, because every
# word in the dataset is English.
TRADE_ALIASES = {
    "Sewing Technology": "silai, silai ka kaam, kapde silna, shivan",
    "Dress Making": "silai, darzi, kapde silna, tailor ka kaam",
    "Cosmetology": "beauty parlour, parlour ka kaam, saundarya, makeup ka kaam",
    "Food Production (General)": "khana banane ka kaam, rasoi, cooking, bawarchi, swayampak",
    "Catering & Hospitality Assistant": "hotel ka kaam, catering, hotel madhil kaam",
    "Electrician": "bijli ka kaam, wiring ka kaam, vij kaam",
    "Plumber": "nal ka kaam, pipe ka kaam, plumbing",
    "Welder": "welding ka kaam, jodne ka kaam",
    "Fitter": "machine ka kaam, fitting",
    "Mechanic Motor Vehicle (MMV)": "gaadi theek karna, garage ka kaam, motor mechanic",
    "Mechanic Diesel": "engine theek karna, diesel gaadi ka kaam",
    "Mechanic Tractor": "tractor theek karna, kheti ki gaadi",
    "Mechanic Agricultural Machinery": "kheti ke aujaar, farming machine",
    "Soil Testing and Crop Technician": "kheti, mitti ki jaanch, sheti, crop",
    "Mason (Building Constructor)": "raj mistri, gharkaam banane ka kaam, construction",
    "Wood Work Technician": "lakdi ka kaam, sutar, carpenter ka kaam",
    "Painter (General)": "rang ka kaam, painting ka kaam",
    "Driver cum Mechanic (LMV)": "driver, gaadi chalana, driving",
    "Computer Operator and Programming Assistant (COPA)": (
        "computer ka kaam, typing, data entry"
    ),
    "Refrigeration and Air Conditioning Technician": "AC fridge theek karna, cooling ka kaam",
    "Health Sanitary Inspector": "safai vibhag, swasthya nirikshak",
    "Radiology Technician": "x-ray ka kaam, hospital ka kaam",
    "Physiotherapy Technician": "hospital ka kaam, physiotherapy",
    "Fashion Design and Technology": "fashion designing, kapde design karna",
    "Footwear Maker": "chappal jute banana, footwear",
    "Leather Goods Maker": "chamde ka kaam, bag banana",
    "Solar Technician (Electrical)": "solar panel ka kaam, saur urja",
}

ARMY_ALIASES = "sena bharti, fauj, army bharti, sainik, lashkar"

DVET = "https://dvet.gov.in/"
DVET_ADMISSION = "https://admission.dvet.gov.in"

# Maharashtra-specific routes. The ITI trades above are the national NCVT list;
# these are how a Maharashtra student actually enters one, plus the two
# apprenticeship schemes that pay while you train.
MAHARASHTRA_ROUTES = [
    {
        "name": "ITI admission in Maharashtra (DVET centralised admission)",
        "path": "Vocational Education > Maharashtra routes > ITI admission (DVET)",
        "jobs": (
            "ITI pravesh, ITI admission Maharashtra, औद्योगिक प्रशिक्षण संस्था, "
            "ITI form bharne"
        ),
        "note": (
            "Admission to every ITI in Maharashtra runs through the DVET centralised "
            "admission portal. Trade availability and cut-offs differ by district."
        ),
        "source_url": DVET_ADMISSION,
    },
    {
        "name": "National Apprenticeship Promotion Scheme (NAPS)",
        "path": "Vocational Education > Maharashtra routes > Apprenticeship (NAPS)",
        "jobs": "apprenticeship, shikau umedvar, earn while you learn, on-job training",
        "note": (
            "Apprenticeship promotion scheme run through DVET Maharashtra. Stipend "
            "terms and trade availability are set per employer."
        ),
        "source_url": DVET,
    },
    {
        "name": "Maharashtra Apprenticeship Promotion Scheme (MAPS)",
        "path": "Vocational Education > Maharashtra routes > Apprenticeship (MAPS)",
        "jobs": "apprenticeship, shikau umedvar, Maharashtra apprenticeship, on-job training",
        "note": (
            "State apprenticeship promotion scheme run by DVET Maharashtra. Stipend "
            "terms and trade availability are set per employer."
        ),
        "source_url": DVET,
    },
    {
        "name": "ITI Short Term Training (STEP)",
        "path": "Vocational Education > Maharashtra routes > ITI Short Term Training (STEP)",
        "jobs": "short term course, quick skill course, certificate course",
        "note": (
            "Short-term certificate training run through Maharashtra ITIs. Course "
            "list and duration vary by institute."
        ),
        "source_url": DVET,
    },
]


def slugify(text: str) -> str:
    keep = [char.lower() if char.isalnum() else "-" for char in text]
    return "-".join("".join(keep).split("-")) or "unknown"


def build() -> list[dict]:
    records: list[dict] = []

    for trade in ITI_ENGINEERING + ITI_NON_ENGINEERING:
        engineering = trade in ITI_ENGINEERING
        group = "Engineering trades" if engineering else "Non-engineering trades"
        records.append(
            {
                "id": f"iti-{slugify(trade)}",
                "name": trade,
                "path": f"Vocational Education > ITI ({group}) > {trade}",
                "category": "ITI trade (Craftsmen Training Scheme)",
                "awarding_body": "Directorate General of Training (DGT), NCVT",
                "duration": None,
                "eligibility": None,
                "eligibility_note": (
                    "Minimum qualification varies by trade (commonly 8th or 10th pass). "
                    "Confirm with the ITI before applying."
                ),
                "jobs": ", ".join(
                    part
                    for part in (TRADE_JOBS.get(trade, trade), TRADE_ALIASES.get(trade, ""))
                    if part
                ),
                "source_url": BHARAT_SKILLS,
                "fetched_on": FETCHED_ON,
            }
        )

    for name, eligibility in ARMY_ENTRIES:
        records.append(
            {
                "id": f"army-{slugify(name)}",
                "name": name,
                "path": f"Defence > Indian Army entry > {name}",
                "category": "Defence entry route",
                "awarding_body": "Indian Army",
                "duration": None,
                "eligibility": eligibility,
                "eligibility_note": (
                    "Age, physical standards and exact qualification are notified per "
                    "recruitment rally on the Join Indian Army portal."
                ),
                "jobs": f"Indian Army, army job, defence job, soldier, {ARMY_ALIASES}",
                "source_url": JOIN_ARMY,
                "fetched_on": FETCHED_ON,
            }
        )

    for route in MAHARASHTRA_ROUTES:
        records.append(
            {
                "id": f"mh-{slugify(route['name'])}",
                "name": route["name"],
                "path": route["path"],
                "category": "State route",
                "state": "Maharashtra",
                "awarding_body": (
                    "Directorate of Vocational Education and Training (DVET), Maharashtra"
                ),
                "duration": None,
                "eligibility": None,
                "eligibility_note": route["note"],
                "jobs": route["jobs"],
                "source_url": route["source_url"],
                "fetched_on": FETCHED_ON,
            }
        )

    return records


def main() -> None:
    records = build()
    OUTPUT_PATH.write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"wrote {len(records)} vocational paths to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
