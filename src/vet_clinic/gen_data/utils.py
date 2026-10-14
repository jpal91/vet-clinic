import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Literal

from .faker_instance import fake

DATA_PATH = Path(__file__).resolve().parents[3] / "data"


def dirty_date(d: date) -> str:
    choices = ["%m/%d/%Y", "%Y/%m/%d", "%Y-%m-%d"]
    pick = fake.random_element(choices)
    return d.strftime(pick)


def random_bool() -> bool:
    return bool(fake.random_int(0, 1))


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


def get_services() -> dict[str, "Service"]:
    with open(DATA_PATH / "services.json") as f:
        res = json.load(f)
        return {r.name: Service(**r) for r in res}


def get_medications() -> dict[tuple[str, str], list["Medication"]]:
    with open(DATA_PATH / "medications.json") as f:
        res = json.load(f)
        map = {}

        for item in res:
            cat = item["category"]

            for s in item["species"]:
                key = (s, cat)

                if not key in map:
                    map[key] = []

                map[key].append(Medication(**item))

        return map


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


@dataclass
class Schedule:
    kind: Literal["once", "terminal"]


@dataclass
class ScheduleRecurring:
    interval_days: int
    jitter_days: int
    skip_probability: float
    min_age_years: float = 0.0
    kind: Literal["recurring"] = "recurring"


@dataclass
class ScheduleRandom:
    annual_rate: float
    senior_multiplier: float = 1.0
    weekend_multiplier: float = 1.0
    spay_neuter_probability: float | None = None
    spay_neuter_age_years: tuple[float, float] | None = None
    kind: Literal["random"] = "random"

    def __post_init__(self):
        if self.spay_neuter_age_years is not None:
            self.spay_neuter_age_years = tuple(self.spay_neuter_age_years)


def parse_schedule(data: dict) -> Schedule | ScheduleRecurring | ScheduleRandom:
    match data["kind"]:
        case "recurring":
            return ScheduleRecurring(**data)
        case "random":
            return ScheduleRandom(**data)
        case "once" | "terminal":
            return Schedule(**data)
        case kind:
            raise ValueError(f"Unknown schedule kind: {kind}")


@dataclass
class ServiceOption:
    service: str
    weight: int = 1
    quantity: tuple[int, int] = (1, 1)
    min_age_years: float | None = None
    max_age_years: float | None = None
    interval_days: int | None = None
    sex: Literal["M", "F"] | None = None
    requires_intact: bool = False

    def __post_init__(self):
        self.quantity = tuple(self.quantity)


@dataclass
class VisitService:
    probability: float
    options: list[ServiceOption]
    pick_one: bool

    @classmethod
    def from_dict(cls, data: dict) -> "VisitService":
        data = dict(data)
        probability = data.pop("probability")

        if "one_of" in data:
            options = [ServiceOption(**opt) for opt in data["one_of"]]
        else:
            options = [ServiceOption(**data)]

        return cls(probability, options, "one_of" in data)

    @property
    def is_group(self) -> bool:
        return len(self.options) > 1


@dataclass
class VisitMedication:
    category: str
    probability: float
    count: tuple[int, int] = (1, 1)
    min_age_years: float | None = None
    max_age_years: float | None = None

    def __post_init__(self):
        self.count = tuple(self.count)


@dataclass
class VisitType:
    name: str
    description: str
    schedule: Schedule | ScheduleRecurring | ScheduleRandom
    services: list[VisitService]
    medications: list[VisitMedication]

    @classmethod
    def from_dict(cls, data: dict) -> "VisitType":
        return cls(
            name=data["name"],
            description=data["description"],
            schedule=parse_schedule(data["schedule"]),
            services=[VisitService.from_dict(s) for s in data["services"]],
            medications=[VisitMedication(**m) for m in data["medications"]],
        )

    def spay_neuter_info(self) -> tuple[float, float, float]:
        assert (
            self.schedule.kind == "random"
            and self.name == "Surgery"
            and self.schedule.spay_neuter_age_years
            and self.schedule.spay_neuter_probability
        )

        return (
            *self.schedule.spay_neuter_age_years,
            self.schedule.spay_neuter_probability,
        )


def load_visit_types(path: Path = DATA_PATH) -> dict[str, VisitType]:
    with open(path) as f:
        res = json.load(f)
        return {vt["name"]: VisitType.from_dict(vt) for vt in res}
