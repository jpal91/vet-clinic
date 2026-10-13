import csv
import json
from collections import OrderedDict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, ClassVar, Literal

from faker import Faker
from faker.providers import BaseProvider
from faker_healthcare import HealthcareProvider

DATA_PATH = Path(__file__).parent.parent.parent / "data"
fake = Faker()

# fake.seed_instance(os.environ.get("FAKER_SEED", "PawsWell"))
fake.add_provider(HealthcareProvider)

_csv = csv


def get_all_pet_names():
    with open(DATA_PATH / "male-dog-names.json") as f:
        male: list[Any] = json.load(f)

    with open(DATA_PATH / "female-dog-names.json") as f:
        female: list[Any] = json.load(f)

    return [*male, *female]


def get_dog_breeds() -> list[str]:
    with open(DATA_PATH / "dog-breeds.json") as f:
        res = json.load(f)
        return [breed["name"] for breed in res]


def get_cat_breeds() -> list[str]:
    with open(DATA_PATH / "cat-breeds.json") as f:
        res = json.load(f)
        return [breed["name"] for breed in res]


def get_services() -> list["Service"]:
    with open(DATA_PATH / "services.json") as f:
        res = json.load(f)
        return [Service(**r) for r in res]


def get_medications() -> list["Medication"]:
    with open(DATA_PATH / "medications.json") as f:
        res = json.load(f)
        return [Medication(**r) for r in res]


class DirtyAddressProvider(BaseProvider):
    def __init__(self, *args):
        super().__init__(*args)
        self.suffixes = ["Ln.", "Rd.", "Cir.", "Cv.", "Dr.", "Hwy."]
        self.city_dict = OrderedDict([
            ("Charlotte", 0.7),
            ("Gastonia", 0.05),
            ("Concord", 0.05),
            ("Davidson", 0.05),
            ("Fort Mill", 0.05),
            ("Raleigh", 0.05),
            ("Boone", 0.05),
        ])

    def dirty_suffix(self) -> str:
        pick = self.random_int(0, 10)

        if pick <= 3:
            return self.random_element(self.suffixes)
        else:
            return fake.street_suffix()

    def dirty_zip(self) -> str:
        pick = self.random_int(0, 10)

        if pick <= 2:
            return ""
        else:
            return fake.zipcode_in_state("NC")

    def _city(self):
        return self.random_elements(
            self.city_dict, length=1, unique=False, use_weighting=True
        )[0]

    def dirty_address(self) -> str:
        st_nbr = self.random_int(0, 10_001)
        st_name = fake.street_name()
        suffix = self.dirty_suffix()
        city = self._city()
        zip_code = self.dirty_zip()

        return f"{st_nbr} {st_name} {suffix}, {city}, NC {zip_code}"


@dataclass
class Medication:
    name: str
    category: str
    species: list[Literal["Dog", "Cat"]]
    form: str
    min_dosage: int
    max_dosage: int
    measurement: str

    def to_string(self):
        quantity = fake.random_int(1, 30)

        if self.min_dosage % 5 == 0:
            step = 5
        else:
            step = 1

        dosage = fake.random_int(self.min_dosage, self.max_dosage, step)

        return f"{self.name} {dosage}{self.measurement} x{quantity}"


@dataclass
class Service:
    name: str
    category: str
    species: list[Literal["Dog", "Cat"]]
    cost: float

    def to_string(self):
        return f"{self.name} (${self.cost:.2f})"


class VetProvider(BaseProvider):
    services = get_services()
    medications = get_medications()

    def vet_name(self):
        pick = self.random_int(0, 3)

        match pick:
            case 0:
                last_name = fake.last_name()
                return "Dr. " + last_name
            case 1:
                last_name = fake.last_name()
                first_initial = fake.first_name()[0]
                return f"Dr. {first_initial}. {last_name}"
            case 2:
                name = fake.name().split(" ")
                return f"{name[1]}, {name[0]}"

    def vet_services(self, species: str):
        eligible_services = [serv for serv in self.services if species in serv.species]
        services = self.random_elements(
            eligible_services, length=self.random_int(1, 5), unique=True
        )

        return services

    def vet_medications(self, species: str):
        eligible_medications = [
            serv for serv in self.medications if species in serv.species
        ]
        medications = self.random_elements(
            eligible_medications, length=self.random_int(1, 5), unique=True
        )
        return medications


class PetProvider(BaseProvider):
    all_names: list[str] = get_all_pet_names()
    all_dog_breeds: list[str] = get_dog_breeds()
    all_cat_breeds: list[str] = get_cat_breeds()

    def pet_name(self):
        return self.random_element(self.all_names)

    def pet_species_w_breed(self):
        species = "Dog" if random_bool() else "Cat"

        if species == "Dog":
            return species, self.random_element(self.all_dog_breeds)
        else:
            return species, self.random_element(self.all_cat_breeds)


fake.add_provider(VetProvider)
fake.add_provider(DirtyAddressProvider)
fake.add_provider(PetProvider)


def random_bool():
    return bool(fake.random_int(0, 1))


def dirty_date(d: date) -> str:
    choices = ["%m/%d/%Y", "%Y/%m/%d", "%Y-%m-%d"]
    pick = fake.random_element(choices)
    return d.strftime(pick)


class Pet:
    def __init__(self):
        self.name = fake.pet_name()
        self.dob = fake.date_this_decade()
        self.sex = "Male" if random_bool() else "Female"
        self.weight = fake.random_int(20, 100)

        species, breed = fake.pet_species_w_breed()
        self.species = species
        self.breed = breed

    def visit_date(self):
        return fake.date_between(self.dob)

    @property
    def dirty_dob(self):
        return dirty_date(self.dob)


class Customer:
    pet_dist: ClassVar[OrderedDict] = OrderedDict([(1, 0.7), (2, 0.25), (3, 0.05)])

    def __init__(self):
        self.first_name = fake.first_name()
        self.last_name = fake.last_name()
        self.phone_number = fake.basic_phone_number()
        self.email_address = fake.free_email() if random_bool() else None
        self.address = fake.dirty_address()
        self.old_address = fake.dirty_address() if random_bool() else None
        self.pets = []

        n: int = fake.random_elements(self.pet_dist, length=1, use_weighting=True)[0]

        for _ in range(n):
            self.pets.append(Pet())

        self._customer_since = min(p.dob for p in self.pets)

    def random_pet(self):
        return fake.random_element(self.pets)

    def customer_address(self):
        if self.old_address and random_bool():
            return self.old_address
        else:
            return self.address


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

    def random_vet(self):
        return fake.random_element(self.vets)


class GenData:
    visit_type_dict: ClassVar[OrderedDict] = OrderedDict([
        ("Wellness", 0.6),
        ("Sick", 0.1),
        ("Emergency", 0.05),
        ("Surgery", 0.05),
        ("Dental", 0.2),
    ])

    def __init__(self):
        self.customers = [Customer() for _ in range(50)]
        self.clinics = [Clinic() for _ in range(4)]
        self.invoice_start = fake.random_int(1000, 1_000_000)

    def create_visit(self):
        invoice_no = self.invoice_start
        self.invoice_start += 1

        customer = fake.random_element(self.customers)
        pet: Pet = customer.random_pet()
        clinic = fake.random_element(self.clinics)
        vet: Veterinarian = clinic.random_vet()
        visit_date = dirty_date(pet.visit_date())
        visit_type: str = fake.random_elements(
            self.visit_type_dict, length=1, use_weighting=True
        )[0]
        services: list[Service] = fake.vet_services(pet.species)
        invoiced_total = sum(s.cost for s in services)
        invoiced_owner = invoiced_total
        insurance = fake.random_element(["InsuraPet", "PawShield", None])

        if insurance:
            insurer_servs = fake.random_elements(
                services, length=fake.random_int(0, len(services)), unique=True
            )
            invoiced_insurer = sum(s.cost for s in insurer_servs)
            invoiced_owner -= invoiced_insurer
            insurance_paid = invoiced_insurer * (fake.random_int(0, 100) / 100.0)
        else:
            invoiced_insurer = 0.0
            insurance_paid = 0

        owner_paid = invoiced_owner * (fake.random_int(0, 100) / 100.0)

        return [
            str(invoice_no),
            visit_date,
            visit_type,
            clinic.name,
            clinic.phone_no,
            customer.first_name,
            customer.last_name,
            customer.phone_number,
            customer.email_address,
            customer.customer_address(),
            pet.name,
            pet.dirty_dob,
            pet.sex,
            pet.species,
            pet.breed,
            pet.weight,
            vet.dirty_name,
            ";".join(fake.random_elements(clinic.technicians, unique=True)),
            ";".join(s.to_string() for s in services),
            ";".join(med.to_string() for med in fake.vet_medications(pet.species)),
            insurance,
            float(f"{invoiced_owner:.2f}"),
            float(f"{invoiced_insurer:.2f}"),
            float(f"{owner_paid:.2f}"),
            float(f"{insurance_paid:.2f}"),
            fake.random_element(["Cash", "Credit", "Check", None]),
        ]


if __name__ == "__main__":
    from pprint import pprint

    generator = GenData()
    for _ in range(5):
        pprint(generator.create_visit())
