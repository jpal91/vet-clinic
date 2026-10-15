import csv
import heapq
from collections import OrderedDict
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import ClassVar

from .faker_instance import fake
from .providers import DirtyAddressProvider, PetProvider, VetProvider
from .utils import (
    DATA_PATH,
    Medication,
    Service,
    VisitType,
    dirty_date,
    get_medications,
    get_services,
    load_visit_types,
    random_bool,
)

fake.add_provider(VetProvider)
fake.add_provider(DirtyAddressProvider)
fake.add_provider(PetProvider)

WINDOW_START, WINDOW_END = date(2020, 1, 1), date(2026, 9, 30)
VISIT_TYPES = load_visit_types()
SERVICES = get_services()
MEDICATIONS = get_medications()


def random_chance(prob: float):
    return fake.random.random() <= prob


@dataclass
class Visit:
    visit_date: date
    visit_type: str
    pet: "Pet"
    services: list[Service]
    prescriptions: list[Medication]
    invoice_no: int | None = None

    def csv_row(self):
        owner = self.pet.owner
        clinic = self.pet.owner.clinic
        total_due = self.invoiced_total()

        match owner.paid_amount():
            case "full":
                amount_paid = total_due
            case "partial":
                amount_paid = fake.random_int(1, int(total_due))
            case _:
                amount_paid = 0

        return [
            str(self.invoice_no),
            dirty_date(self.visit_date),
            self.visit_type,
            clinic.name,
            clinic.phone_no,
            owner.first_name,
            owner.last_name,
            owner.phone_number,
            owner.email_address,
            owner.customer_address(self.visit_date),
            self.pet.name,
            self.pet.dirty_dob,
            self.pet.sex,
            self.pet.species,
            self.pet.breed,
            self.pet.weight,
            clinic.random_vet().dirty_name,
            ";".join(
                fake.random_elements(
                    clinic.technicians, length=fake.random_int(1, 3), unique=True
                )
            ),
            ";".join(s.to_string() for s in self.services),
            ";".join(med.to_string() for med in self.prescriptions),
            owner.insurance,
            self.pet.policy_id,
            float(f"{total_due:.2f}"),
            float(f"{amount_paid:.2f}"),
            fake.random_element(["Cash", "Credit", "Check"])
            if amount_paid > 0
            else None,
        ]

    def invoiced_total(self):
        return sum(s.cost for s in self.services)


class Pet:
    def __init__(self, owner: "Customer"):
        self.name = fake.pet_name()
        self.dob = fake.date_between(
            WINDOW_START - timedelta(days=365 * 12), WINDOW_END - timedelta(weeks=8)
        )
        self.sex = "M" if random_bool() else "F"
        self.weight = fake.random_int(20, 100)
        self.owner = owner

        self.policy_id = self.insurance_policy()

        species, breed = fake.pet_species_w_breed()
        self.species = species
        self.breed = breed

        self.interval_map: dict[str, int] = {}
        self.alive = True
        self.death_date = fake.date_between(
            self.dob + timedelta(days=365 * 8), self.dob + timedelta(365 * 20)
        )
        self.death_date = max(self.death_date, WINDOW_START + timedelta(days=30))
        self.first_visit_date = fake.date_between(
            max(self.dob + timedelta(weeks=8), WINDOW_START),
            min(self.death_date, WINDOW_END),
        )

        first_visit_delta = self.first_visit_date - self.dob
        age_at_first = first_visit_delta.days / 365
        spn_min, spn_max, prob = VISIT_TYPES["Surgery"].spay_neuter_info()
        self.sn_date = None

        if age_at_first < spn_max:
            self.intact = True

            if random_chance(prob):
                self.sn_date = fake.date_between(
                    max(
                        self.dob + timedelta(days=int(spn_min * 365)),
                        self.first_visit_date,
                    ),
                    self.dob + timedelta(days=int(spn_max * 365)),
                )
        else:
            self.intact = random_chance(0.2)

    def visit_date(self):
        return fake.date_between(self.dob)

    @property
    def dirty_dob(self):
        return dirty_date(self.dob)

    def simulate(self) -> list[Visit]:
        heap: list[tuple[date, str, bool]] = []
        visits = []

        if self.sn_date:
            heapq.heappush(heap, (self.sn_date, "Surgery", True))

        for vt in VISIT_TYPES.values():
            if vt.schedule.kind == "once":
                heapq.heappush(heap, (self.first_visit_date, "Initial Visit", False))
            elif vt.schedule.kind != "terminal":
                if vt.name == "Surgery" and self.sn_date:
                    continue
                nxt = self.next_visit(vt.name, self.first_visit_date)
                if nxt:
                    heapq.heappush(heap, (nxt, vt.name, False))
            elif self.death_date < WINDOW_END:
                heapq.heappush(heap, (self.death_date, "End of Life Care", False))

        while heap and self.alive:
            when, vt_name, planned = heapq.heappop(heap)

            assert when >= WINDOW_START
            if when > WINDOW_END:
                break

            visit = self.build_visit(when, VISIT_TYPES[vt_name], planned)
            visits.append(visit)

            nxt = self.next_visit(vt_name, when)
            if nxt:
                heapq.heappush(heap, (nxt, vt_name, False))

        return visits

    def build_visit(self, when: date, vt: VisitType, planned_neuter=False) -> Visit:
        age_days = (when - self.dob).days
        services = []
        medications = []

        for service in vt.services:
            if not (random_chance(service.probability)):
                continue

            possible_choices = [
                opt
                for opt in service.options
                if not (
                    age_days < (opt.min_age_years or 0) * 365
                    or age_days > (opt.max_age_years or age_days) * 365
                    or self.sex != (opt.sex or self.sex)
                    or (opt.requires_intact and not self.intact)
                    or (planned_neuter and service.pick_one and not opt.requires_intact)
                    or self.species not in SERVICES[opt.service].species
                )
            ]

            if not possible_choices:
                continue

            opt = fake.random.choices(
                possible_choices, weights=[o.weight for o in possible_choices]
            )[0]

            serv = SERVICES[opt.service]

            if opt.interval_days:
                last = self.interval_map.get(opt.service)

                if last is not None and age_days < last + opt.interval_days:
                    continue

                self.interval_map[opt.service] = age_days

            if opt.requires_intact:
                self.intact = False

            quant = fake.random_int(*opt.quantity)

            for _ in range(quant):
                services.append(serv)

        age_years = age_days / 365

        for meds in vt.medications:
            if (
                not random_chance(meds.probability)
                or (meds.min_age_years and age_years < meds.min_age_years)
                or (meds.max_age_years and age_years > meds.max_age_years)
            ):
                continue

            key = (self.species, meds.category)
            if not key in MEDICATIONS:
                continue

            rand_meds = fake.random_elements(
                MEDICATIONS[key], length=fake.random_int(*meds.count), unique=True
            )

            medications.extend(rand_meds)

        if vt.schedule.kind == "terminal":
            self.alive = False

        return Visit(
            when,
            vt.name,
            self,
            services,
            medications,
        )

    def next_visit(self, vt_name: str, last: date):
        vt = VISIT_TYPES[vt_name]

        if vt.schedule.kind == "once" or vt.schedule.kind == "terminal":
            return
        elif vt.schedule.kind == "recurring":
            interval_date = last + timedelta(days=vt.schedule.interval_days)
            nxt_date = fake.date_between(
                interval_date - timedelta(days=vt.schedule.jitter_days),
                interval_date + timedelta(days=vt.schedule.jitter_days),
            )

            if random_chance(vt.schedule.skip_probability):
                nxt_date += timedelta(days=vt.schedule.interval_days)

            min_age = vt.schedule.min_age_years * 365
            age_at_time = nxt_date - self.dob
            death_delta = self.death_date - self.dob

            if age_at_time.days >= death_delta.days:
                return

            while age_at_time.days < min_age:
                if age_at_time.days >= death_delta.days:
                    return

                nxt_date += timedelta(days=vt.schedule.interval_days)
                age_at_time = nxt_date - self.dob

            return nxt_date
        elif vt.schedule.kind == "random":
            age = last - self.dob
            rate = vt.schedule.annual_rate

            if (age.days / 365) >= 7.0:
                rate *= vt.schedule.senior_multiplier

            gap_days = fake.random.expovariate(rate) * 365

            return last + timedelta(days=gap_days)

    def insurance_policy(self):
        if not self.owner.insurance:
            return

        nbrs = str(fake.unique.random_int(100_000_000, 999_999_999))
        match self.owner.insurance:
            case "InsuraPet":
                ltrs = "".join(fake.random_letters(5))
                return f"insurapet-{ltrs}-{nbrs[::-1]}"
            case "PawShield":
                ltrs = "".join(fake.random_letters(10))
                return f"{nbrs}-{ltrs}-ps"
            case _:
                seq = list(fake.random_letters(9)) + [*nbrs]
                fake.random.shuffle(seq)
                return "".join(seq)


class Customer:
    pet_dist: ClassVar[OrderedDict] = OrderedDict([(1, 0.7), (2, 0.25), (3, 0.05)])
    payment_amt: ClassVar[OrderedDict] = OrderedDict([
        ("full", 0.9),
        ("partial", 0.05),
        ("none", 0.05),
    ])

    def __init__(self, clinic: "Clinic"):
        self.first_name = fake.first_name()
        self.last_name = fake.last_name()
        self.phone_number = fake.basic_phone_number()
        self.email_address = fake.free_email() if random_chance(0.9) else None
        self.address = fake.dirty_address()
        self.old_address = fake.dirty_address()
        self.moved = fake.date_between("-20y")
        self.clinic = clinic
        self.insurance = fake.random_element([
            "InsuraPet",
            "PawShield",
            "Universal Animal",
            None,
        ])

    def no_of_pets(self):
        return fake.random_elements(self.pet_dist, length=1, use_weighting=True)[0]

    def customer_address(self, when: date):
        if when < self.moved:
            return self.old_address
        else:
            return self.address

    def paid_amount(self):
        return fake.random_elements(self.payment_amt, length=1, use_weighting=True)[0]


class Veterinarian:
    def __init__(self):
        self.first_name = fake.first_name()
        self.last_name = fake.last_name()

    @property
    def dirty_name(self) -> str:
        pick = fake.random_int(0, 3)

        match pick:
            case 0:
                return "Dr. " + self.last_name
            case 1:
                first_initial = self.first_name[0]
                return f"Dr. {first_initial}. {self.last_name}"
            case _:
                return f"{self.last_name}, {self.first_name}"


class Clinic:
    def __init__(self):
        self.name = "PawsWell - " + fake.street_name()
        self.vets = [Veterinarian() for _ in range(3)]
        self.technicians = [fake.name() for _ in range(5)]
        self.phone_no = fake.basic_phone_number()

    def random_vet(self) -> Veterinarian:
        return fake.random_element(self.vets)


def generate_visits(target: int) -> list[Visit]:
    clinics = [Clinic() for _ in range(4)]
    visits: list[Visit] = []
    while len(visits) < target:
        customer = Customer(fake.random_element(clinics))
        for _ in range(customer.no_of_pets()):
            visits.extend(Pet(customer).simulate())
    visits.sort(key=lambda v: v.visit_date)
    return visits


CSV_HEADER = [
    "InvoiceNo",
    "VisitDate",
    "VisitType",
    "Clinic",
    "ClinicPhone",
    "OwnerFirstName",
    "OwnerLastName",
    "OwnerPhone",
    "OwnerEmail",
    "OwnerAddress",
    "PetName",
    "PetDOB",
    "PetSex",
    "Species",
    "Breed",
    "PetWeightLbs",
    "AttendingVet",
    "Technicians",
    "Services",
    "Prescriptions",
    "InsuranceProvider",
    "PolicyNumber",
    "InvoiceTotal",
    "AmountPaid",
    "PaymentMethod",
]


def write_csv(visits: list[Visit], path: Path, start_invoice: int | None = None) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    invoice_no = (
        start_invoice if start_invoice is not None else fake.random_int(10_000, 99_999)
    )

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADER)

        for visit in sorted(visits, key=lambda v: v.visit_date):
            visit.invoice_no = invoice_no
            invoice_no += 1

            row = visit.csv_row()
            assert len(row) == len(CSV_HEADER), (
                "csv_row() and CSV_HEADER are out of sync"
            )
            writer.writerow(row)

    return len(visits)


def main(count=2000):
    visits = generate_visits(count)
    n = write_csv(visits, DATA_PATH / "PawsWell_Visits_0nf.csv")
    print(f"{n} rows written")
