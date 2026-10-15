# PawsWell Veterinary Group: Data Modeling & Analytics

> 🚧 **Work in progress.** This is my final project for ISTA 431 (Data Warehousing and Analytics in the Cloud, Fall 2026). Pieces are still being built, and the structure and results will change.

PawsWell Veterinary Group is a **fictional** chain of four veterinary clinics in the Charlotte, NC area that opened in 2020. Like many small businesses, it tracks every visit in one big spreadsheet. Owner, pet and clinic details are copied onto every row, and staff have entered dates, names and addresses inconsistently.

This project takes that spreadsheet from a messy, unnormalized (0NF) log to a clean relational database, and then to a reporting layer that answers real business questions.

## Project roadmap

- [x] **Synthetic data generator**: simulates each pet's visit history and writes the 0NF workbook
- [ ] **Data cleaning**: standardize dates and names, fill in or flag missing values
- [ ] **Normalization**: 0NF → 1NF → 2NF → 3NF
- [ ] **Data models**: conceptual, logical and physical (ERDs)
- [ ] **MySQL implementation**: DDL, data loading, and SELECT queries for business questions
- [ ] **Star schema**: a reporting layer with a visit/service fact table and dimension tables
- [ ] **Dashboard**: revenue, service mix, vaccine compliance, client retention

## The data

All data is **synthetic**: no real clinics, people or pets. The generator simulates each pet's life as a timeline of events:

- an **initial visit** when the pet joins the clinic
- yearly **wellness exams**, with vaccines given only when they're due
- **dental cleanings** every couple of years for adult pets
- **spay/neuter** surgery around six months of age for most young pets
- random **sick** and **emergency** visits that become more frequent as pets age
- **end-of-life care** as the pet's final visit

Visit types, services and medications are configured in JSON (`data/visit_types.json`, `data/services.json`, `data/medications.json`). Each visit type defines how often it happens and which services and medications it's likely to include, with optional age, sex and species rules.

### Output: `data/PawsWell_Visits_0nf.xlsx`

| Sheet | Contents |
| --- | --- |
| `PawsWell_Visits` | The visit log: ~2,000 visits (Jan 2020 – Sep 2026), one row per visit, 25 columns |
| `Supplement_Clinics` | Each clinic's phone number, veterinarians and technicians |
| `Supplement_Services` | Service price list with category and species |
| `Supplement_Medications` | Medication list with category, form and dosage range |

The visit log is deliberately unnormalized and messy:

- No IDs except the invoice number. Every row repeats the owner, pet, clinic and vet details.
- Repeating groups in a single cell (services, prescriptions, technicians)
- Dates written in three different formats
- The same veterinarian's name written three different ways
- Missing emails and ZIP codes, and owners who change address
- Partially paid and unpaid invoices

## Getting started

Requires Python 3.13+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run gen-data          # writes data/PawsWell_Visits_0nf.xlsx
```

The output is reproducible. The generator is seeded with `"PawsWell"` by default; set `FAKER_SEED` to get a different dataset:

```bash
FAKER_SEED=my-seed uv run gen-data
```

## Repository layout

```
data/                       JSON config, name/breed lists, generated workbook
src/vet_clinic/gen_data/
├── generator.py            simulation (Pet, Customer, Clinic, Visit) and the workbook writer
├── utils.py                loaders and dataclasses for the JSON config
├── providers.py            custom Faker providers (pets, vets, messy addresses)
└── faker_instance.py       shared, seeded Faker instance
```

## Tools

- **Data generation:** Python, Faker, pandas, openpyxl, uv
- **Database:** MySQL 8.4
- **Modeling:** draw.io
- **Reporting:** Tableau Public (planned)

## Credits

Name and breed lists come from:

- https://github.com/chrisvogt/dog-breeds
- https://github.com/sindresorhus/dog-names
- https://github.com/amirachaudhry/cat-breeds/
