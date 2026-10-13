from collections import OrderedDict

from faker.providers import BaseProvider

from .faker_instance import fake
from .utils import (
    get_all_pet_names,
    get_cat_breeds,
    get_dog_breeds,
    get_medications,
    get_services,
    random_bool,
)

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
