import os

from faker import Faker

fake = Faker()
fake.seed_instance(os.environ.get("FAKER_SEED", "PawsWell"))
