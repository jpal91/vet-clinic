from collections import OrderedDict
from datetime import date
from pprint import pprint
from typing import ClassVar

from .faker_instance import fake
from .providers import DirtyAddressProvider, PetProvider, VetProvider
from .utils import Service, random_bool

fake.add_provider(VetProvider)
fake.add_provider(DirtyAddressProvider)
fake.add_provider(PetProvider)


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


def main():
    generator = GenData()
    for _ in range(5):
        pprint(generator.create_visit())
