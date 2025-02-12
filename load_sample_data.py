import os
import datetime
import django
from random import choice, sample, randint
from django.apps import apps
import json
from utility.utils import *


# Utility function to clear rows by model name
# Deletes all the existing records before populating sample data according to the dictionary
def clear_rows_by_model_name(model_names_mapping: dict) -> None:
    for model_name, app_name in model_names_mapping.items():
        model = apps.get_model(app_name, model_name)
        model.objects.all().delete()


def create_capabilities() -> list:
    fancy_out("Create Capability records")
    get = lambda node_id: Capability.objects.get(pk=node_id)
    root_1 = Capability.add_root(
        name="Root Capability 1", description="Root Description of Capability 1"
    )
    root_2 = Capability.add_root(
        name="Root Capability 2", description="Root Description of Capability 2"
    )
    node_root_2 = get(root_2.pk).add_child(
        name="Child of a Root Capability 2",
        description="Child Description of Capability 2",
    )
    get(node_root_2.pk).add_sibling(
        name="Sibling of Child of Root Capability 1",
        description="Sibling Description of Child of Root Capability 1",
    )
    get(node_root_2.pk).add_sibling(
        name="Sibling of Child of Root Capability 2",
        description="Sibling Description of Child of Root Capability 2",
    )
    get(node_root_2.pk).add_child(
        name="Sibling of Child of Root Capability 3",
        description="Sibling Description of Child of Root Capability 3",
    )
    node = get(root_1.pk).add_child(
        name="Capability 2", description="Description of Capability 2"
    )
    get(node.pk).add_sibling(
        name="Capability 3", description="Description of Capability 3"
    )
    get(node.pk).add_sibling(
        name="Capability 4", description="Description of Capability 4"
    )
    get(node.pk).add_child(
        name="Capability 5", description="Description of Capability 5"
    )
    get(node.pk).add_child(
        name="Capability 6", description="Description of Capability 6"
    )
    get(node.pk).add_child(
        name="Capability 7", description="Description of Capability 7"
    )

    return Capability.objects.all()


# Function to read data from a JSON file
def read_json_data(file_name: str, model_name: str = None) -> dict | list:
    if model_name:
        fancy_out(f"Create {model_name.title()} records")
    with open(file_name, "r") as json_file:
        return json.load(json_file)


# Generate sample data for various models and populate the database
def generate_sample_data():
    model_app_mapping = read_json_data("utility/sample_data/model_app_mapping.json")

    clear_rows_by_model_name(model_app_mapping)

    # Create User model instances
    user_data = read_json_data("utility/sample_data/user.json", "user")

    users = []
    for ud in user_data:
        users.append(UserService.create(**ud))

    # Create Person model instances
    person_data = read_json_data("utility/sample_data/person.json", "person")

    # Person model has a non-nullable OneToOneField to User model. Make sure the length of `user.json`
    # and `person.json` are the same. Otherwise, the script throws an error
    for index, pd in enumerate(person_data):
        pd["user"] = users[index]

    people = []
    for pd in person_data:
        people.append(PersonService.create(**pd))

    # Create ProductRoleAssignment model instances
    product_role_assignment_data = read_json_data(
        "utility/sample_data/product_role_assignment.json", "product_role_assignment"
    )

    copy_people = people.copy()
    for ppd in product_role_assignment_data:
        p = choice(copy_people)
        copy_people.remove(p)
        ppd["person"] = p

    product_people = []
    for ppd in product_role_assignment_data:
        product_people.append(ProductRoleAssignmentService.create(**ppd))

    # Create Organisation model instances
    organisation_data = read_json_data(
        "utility/sample_data/organisation.json", "organisation"
    )

    organisations = []
    for org_data in organisation_data:
        organisations.append(OrganisationService.create(**org_data))

    # Create Product model instances
    product_data = read_json_data("utility/sample_data/product.json", "product")

    products = []
    for pd in product_data:
        pd["owner"] = choice(organisations)
        products.append(ProductService.create(**pd))

    # Create Idea model instances
    idea_data = read_json_data("utility/sample_data/idea.json", "idea")

    for elem in idea_data:
        elem["product"] = choice(products)
        elem["person"] = choice(people)

    ideas = []
    for i_data in idea_data:
        ideas.append(IdeaService.create(**i_data))

    # Create Initiative model instances
    initiative_data = read_json_data(
        "utility/sample_data/initiative.json", "initiative"
    )

    for elem in initiative_data:
        elem["product"] = choice(products)

    initiatives = []
    for i_data in initiative_data:
        initiatives.append(InitiativeService.create(**i_data))

    # Create Capability model instances
    capabilities = create_capabilities()

    # Create Skill model instances
    skill_data = read_json_data("utility/sample_data/skill.json", "skill")

    skills = []
    for sk in skill_data:
        skills.append(SkillService.create(**sk))

    # Create Expertise model instances
    expertise_data = read_json_data("utility/sample_data/expertise.json", "expertise")

    expertise = []
    for exp in expertise_data:
        expertise.append(ExpertiseService.create(**exp))

    # Create Tag model instances
    tag_data = read_json_data("utility/sample_data/tag.json", "tag")

    tags = []
    for tag in tag_data:
        tags.append(TagService.create(**tag))

    # Create Challenge model instances
    challenge_data = read_json_data("utility/sample_data/challenge.json", "challenge")

    for elem in challenge_data:
        elem["initiative"] = choice(initiatives)
        elem["capability"] = choice(capabilities)
        elem["created_by"] = choice(people)
        elem["updated_by"] = choice(people)
        elem["reviewer"] = choice(people)
        elem["product"] = choice(products)
        elem["skill"] = choice(skills)

    challenges = []
    for cd in challenge_data:
        challenge = ChallengeService.create(**cd)
        challenge.expertise.set(sample(expertise, k=randint(1, 3)))
        challenges.append(challenge)

    # Create Bounty model instances
    bounty_data = read_json_data("utility/sample_data/bounty.json", "bounty")

    for elem in bounty_data:
        elem["challenge"] = choice(challenges)
        elem["skill"] = choice(skills)

    bounties = []
    for bd in bounty_data:
        bounty = BountyService.create(**bd)
        bounty.expertise.set(sample(expertise, k=randint(1, 4)))
        bounties.append(bounty)

    # Create OrganisationAccount model instances
    organisation_account_data = read_json_data(
        "utility/sample_data/organisation_account.json", "organisation account"
    )

    for index, oad in enumerate(organisation_account_data):
        oad["organisation"] = organisations[index]

    organisation_accounts = []
    for oad in organisation_account_data:
        organisation_accounts.append(OrganisationAccountService.create(**oad))

    # Create OrganisationAccountCredit model instances
    organisation_account_credit_data = read_json_data(
        "utility/sample_data/organisation_account_credit.json",
        "organisation account credit",
    )

    for index, oac in enumerate(organisation_account_credit_data):
        oac["organisation_account"] = organisation_accounts[index]

    organisation_account_credits = []
    for oacd in organisation_account_credit_data:
        organisation_account_credits.append(
            OrganisationAccountCreditService.create(**oacd)
        )

    # Create PointPriceConfiguration instance
    fancy_out("Create a PointPriceConfiguration record")

    point_price_conf_service = PointPriceConfigurationService()
    point_price_conf_service.create(
        applicable_from_date=datetime.date.today(),
        usd_point_inbound_price_in_cents=2,
        eur_point_inbound_price_in_cents=2,
        gbp_point_inbound_price_in_cents=2,
        usd_point_outbound_price_in_cents=1,
        eur_point_outbound_price_in_cents=1,
        gbp_point_outbound_price_in_cents=1,
    )

    # Create Cart model instances
    cart_data = read_json_data("utility/sample_data/cart.json", "cart")

    for index, cd in enumerate(cart_data):
        cd["creator"] = choice(people)
        cd["organisation_account"] = organisation_accounts[index]

    carts = []
    for cd in cart_data:
        carts.append(CartService.create(**cd))

    fancy_out("Complete!")


def run_data_generation():
    proceed = input(
        "Running this script will replace all your current data. Ok? (Y/N)"
    ).lower()

    if not proceed or proceed[0] != "y":
        fancy_out("Execution Abandoned")
        exit()

    generate_sample_data()


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "openunited.settings")
    django.setup()

    from commerce.services import (
        OrganisationService,
        OrganisationAccountService,
        OrganisationAccountCreditService,
        CartService,
        PointPriceConfigurationService,
    )
    from security.services import ProductRoleAssignmentService, UserService
    from product_management.models import Capability
    from talent.services import PersonService, SkillService, ExpertiseService
    from product_management.services import (
        InitiativeService,
        TagService,
        ProductService,
        ChallengeService,
        BountyService,
        IdeaService,
    )

    run_data_generation()
