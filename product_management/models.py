from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models, transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from model_utils import FieldTracker
from treebeard.mp_tree import MP_Node

from openunited.mixins import TimeStampMixin, UUIDMixin
from product_management.mixins import ProductMixin
from engagement.models import Notification
from talent.models import Person, Skill, Expertise
from product_management.utils import get_person_data, to_dict


class Tag(TimeStampMixin):
    name = models.CharField(max_length=128)

    def __str__(self):
        return self.name


# ProductTree is made up from Capabilities
class Capability(MP_Node):
    name = models.CharField(max_length=255)
    description = models.TextField(max_length=1000, default="")
    video_link = models.CharField(max_length=255, blank=True, null=True)
    comments_start = models.ForeignKey(
        to="talent.capabilitycomment",
        on_delete=models.SET_NULL,
        null=True,
        editable=False,
    )

    class Meta:
        db_table = "capability"
        verbose_name_plural = "capabilities"

    def __str__(self):
        return self.name


class Attachment(models.Model):
    name = models.CharField(max_length=512)
    path = models.URLField()
    file_type = models.CharField(max_length=5, null=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class CapabilityAttachment(models.Model):
    capability = models.ForeignKey(Capability, on_delete=models.CASCADE)
    attachment = models.ForeignKey(Attachment, on_delete=models.CASCADE)

    class Meta:
        db_table = "capability_attachment"


class Product(ProductMixin):
    attachment = models.ManyToManyField(
        Attachment, related_name="product_attachments", blank=True
    )
    capability_start = models.ForeignKey(
        Capability, on_delete=models.CASCADE, null=True, editable=False
    )
    owner = models.ForeignKey(
        "commerce.Organisation", on_delete=models.CASCADE, blank=True, null=True
    )

    def get_members_emails(self):
        return self.productrole_set.all().values_list(
            "person__email_address", flat=True
        )

    def get_members_ids(self):
        return self.productrole_set.all().values_list("person__id", flat=True)

    def is_product_member(self, person):
        return self.productrole_set.filter(person=person).exists()

    def get_product_owner(self):
        product_owner = self.owner
        return (
            product_owner.organisation
            if product_owner.organisation
            else product_owner.person.user
        )

    def save(self, *args, **kwargs):
        # We show the preview of the video in ProductListing. Therefore, we have to
        # convert the given URL to an embed
        from .services import ProductService

        self.video_url = ProductService.convert_youtube_link_to_embed(self.video_url)
        super(Product, self).save(*args, **kwargs)

    def __str__(self):
        return self.name


class Initiative(TimeStampMixin, UUIDMixin):
    INITIATIVE_STATUS = (
        (1, "Active"),
        (2, "Completed"),
        (3, "Draft"),
        (4, "Cancelled"),
    )
    name = models.TextField()
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, blank=True, null=True
    )
    description = models.TextField(blank=True, null=True)
    status = models.IntegerField(choices=INITIATIVE_STATUS, default=1)
    video_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # TODO: move the below method to a utility class
        from .services import ProductService

        self.video_url = ProductService.convert_youtube_link_to_embed(self.video_url)
        super(Initiative, self).save(*args, **kwargs)

    def get_available_challenges_count(self):
        return self.challenge_set.filter(
            status=Challenge.CHALLENGE_STATUS_AVAILABLE
        ).count()

    def get_completed_challenges_count(self):
        return self.challenge_set.filter(status=Challenge.CHALLENGE_STATUS_DONE).count()

    def get_challenge_tags(self):
        return Challenge.objects.filter(task_tags__initiative=self).distinct("id").all()

    @staticmethod
    def get_filtered_data(input_data, filter_data=None, exclude_data=None):
        if filter_data is None:
            filter_data = {}
        if not filter_data:
            filter_data = dict()

        if not input_data:
            input_data = dict()

        statuses = input_data.get("statuses", [])
        tags = input_data.get("tags", [])
        categories = input_data.get("categories", None)

        if statuses:
            filter_data["status__in"] = statuses

        if tags:
            filter_data["challenge__tag__in"] = tags

        if categories:
            filter_data["challenge__category__parent__in"] = categories

        queryset = Initiative.objects.filter(**filter_data)
        if exclude_data:
            queryset = queryset.exclude(**exclude_data)

        return queryset.distinct("id").all()


class Challenge(TimeStampMixin, UUIDMixin):
    CHALLENGE_STATUS_DRAFT = 0
    CHALLENGE_STATUS_BLOCKED = 1
    CHALLENGE_STATUS_AVAILABLE = 2
    CHALLENGE_STATUS_CLAIMED = 3
    CHALLENGE_STATUS_DONE = 4
    CHALLENGE_STATUS_IN_REVIEW = 5

    CHALLENGE_STATUS = (
        (CHALLENGE_STATUS_DRAFT, "Draft"),
        (CHALLENGE_STATUS_BLOCKED, "Blocked"),
        (CHALLENGE_STATUS_AVAILABLE, "Available"),
        (CHALLENGE_STATUS_CLAIMED, "Claimed"),
        (CHALLENGE_STATUS_DONE, "Done"),
        (CHALLENGE_STATUS_IN_REVIEW, "In review"),
    )
    CHALLENGE_PRIORITY = ((0, "High"), (1, "Medium"), (2, "Low"))

    SKILL_MODE = ((0, "Single Skill"), (1, "Multiple Skills"))

    REWARD_TYPE = (
        (0, "Liquid Points"),
        (1, "Non-liquid Points"),
    )

    initiative = models.ForeignKey(
        Initiative, on_delete=models.SET_NULL, blank=True, null=True
    )
    capability = models.ForeignKey(
        Capability, on_delete=models.SET_NULL, blank=True, null=True
    )
    title = models.TextField()
    description = models.TextField()
    short_description = models.TextField(max_length=256)
    status = models.IntegerField(choices=CHALLENGE_STATUS, default=0)
    attachment = models.ManyToManyField(
        Attachment, related_name="challenge_attachements", blank=True
    )
    tag = models.ManyToManyField(Tag, related_name="challenge_tags", blank=True)
    skill = models.ForeignKey(
        Skill,
        on_delete=models.CASCADE,
        related_name="challenge",
        blank=True,
        null=True,
        default=None,
    )
    expertise = models.ManyToManyField(Expertise, related_name="challenge_expertise")
    blocked = models.BooleanField(default=False)
    featured = models.BooleanField(default=False)
    priority = models.IntegerField(choices=CHALLENGE_PRIORITY, default=1)
    published_id = models.IntegerField(default=0, blank=True, editable=False)
    auto_approve_task_claims = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        "talent.Person",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="created_by",
    )
    updated_by = models.ForeignKey(
        "talent.Person",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="updated_by",
    )
    tracker = FieldTracker()
    comments_start = models.ForeignKey(
        to="talent.challengecomment",
        on_delete=models.SET_NULL,
        null=True,
        editable=False,
    )
    reviewer = models.ForeignKey("talent.Person", on_delete=models.SET_NULL, null=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True)
    video_url = models.URLField(blank=True, null=True)
    contribution_guide = models.ForeignKey(
        "ContributorGuide",
        null=True,
        default=None,
        blank=True,
        on_delete=models.SET_NULL,
    )
    skill_mode = models.IntegerField(choices=SKILL_MODE, default=0)
    reward_type = models.IntegerField(choices=REWARD_TYPE, default=1)

    class Meta:
        verbose_name_plural = "Challenges"

    def __str__(self):
        return self.title

    @staticmethod
    def get_filtered_data(input_data, filter_data=None, exclude_data=None):
        if not filter_data:
            filter_data = {}

        if not input_data:
            input_data = {}

        sorted_by = input_data.get("sorted_by", "title")
        statuses = input_data.get("statuses", [])
        tags = input_data.get("tags", [])
        priority = input_data.get("priority", [])
        assignee = input_data.get("assignee", [])
        task_creator = input_data.get("task_creator", [])
        skills = input_data.get("skils", [])

        if statuses:
            filter_data["status__in"] = statuses

        if tags:
            filter_data["tag__in"] = tags

        if priority:
            filter_data["priority__in"] = priority

        if task_creator:
            filter_data["created_by__in"] = task_creator

        if assignee:
            filter_data["bountyclaim__kind__in"] = [0, 1]
            filter_data["bountyclaim__person_id__in"] = assignee

        if skills:
            filter_data["skill__parent__in"] = skills

        queryset = Challenge.objects.filter(**filter_data)
        if exclude_data:
            queryset = queryset.exclude(**exclude_data)

        return queryset.order_by(sorted_by).all()

    def get_challenge_link(self, show_domain_name=True):
        try:
            product = self.productchallenge_set.first().product
            product_owner = product.get_product_owner()
            domain_name = settings.FRONT_END_SERVER if show_domain_name else ""
            return f"{domain_name}/{product_owner.username}/{product.slug}/challenges/{self.published_id}"
        except ProductChallenge.DoesNotExist:
            return None


class Bounty(TimeStampMixin):
    BOUNTY_STATUS_DRAFT = 0
    BOUNTY_STATUS_BLOCKED = 1
    BOUNTY_STATUS_AVAILABLE = 2
    BOUNTY_STATUS_CLAIMED = 3
    BOUNTY_STATUS_DONE = 4
    BOUNTY_STATUS_IN_REVIEW = 5

    BOUNTY_STATUS = (
        (BOUNTY_STATUS_DRAFT, "Draft"),
        (BOUNTY_STATUS_BLOCKED, "Blocked"),
        (BOUNTY_STATUS_AVAILABLE, "Available"),
        (BOUNTY_STATUS_CLAIMED, "Claimed"),
        (BOUNTY_STATUS_DONE, "Done"),
        (BOUNTY_STATUS_IN_REVIEW, "In review"),
    )

    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE)
    skill = models.ForeignKey(
        Skill,
        on_delete=models.CASCADE,
        related_name="bounty_skill",
        blank=True,
        null=True,
        default=None,
    )
    expertise = models.ManyToManyField(Expertise, related_name="bounty_expertise")
    points = models.IntegerField()
    status = models.IntegerField(choices=BOUNTY_STATUS, default=BOUNTY_STATUS_AVAILABLE)
    is_active = models.BooleanField(default=True)


class ChallengeDependency(models.Model):
    preceding_challenge = models.ForeignKey(to=Challenge, on_delete=models.CASCADE)
    subsequent_challenge = models.ForeignKey(
        to=Challenge, on_delete=models.CASCADE, related_name="Challenge"
    )

    class Meta:
        db_table = "product_management_challenge_dependencies"


class ProductChallenge(TimeStampMixin, UUIDMixin):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE)


@receiver(post_save, sender=ProductChallenge)
def save_product_task(sender, instance, created, **kwargs):
    if created:
        challenge = instance.challenge
        last_product_challenge = (
            Challenge.objects.filter(productchallenge__product=instance.product)
            .order_by("-published_id")
            .first()
        )
        challenge.published_id = (
            last_product_challenge.published_id + 1 if last_product_challenge else 1
        )
        challenge.save()


class ContributorAgreement(models.Model):
    product = models.ForeignKey(
        to=Product,
        on_delete=models.CASCADE,
        related_name="product_contributor_agreement",
    )
    agreement_content = models.TextField()

    class Meta:
        db_table = "contribution_management_contributor_agreement"


class ContributorAgreementAcceptance(models.Model):
    agreement = models.ForeignKey(to=ContributorAgreement, on_delete=models.CASCADE)
    person = models.ForeignKey(
        to="talent.Person",
        on_delete=models.CASCADE,
        related_name="person_contributor_agreement_acceptance",
    )
    accepted_at = models.DateTimeField(auto_now_add=True, null=True)

    class Meta:
        db_table = "contribution_management_contributor_agreement_acceptance"


class ContributorGuide(models.Model):
    product = models.ForeignKey(
        to=Product, on_delete=models.CASCADE, related_name="product_contributor_guide"
    )
    title = models.CharField(max_length=60, unique=True)
    description = models.TextField(null=True, blank=True)
    skill = models.ForeignKey(
        Skill,
        on_delete=models.CASCADE,
        related_name="category_contributor_guide",
        blank=True,
        null=True,
        default=None,
    )

    def __str__(self):
        return self.title


class Idea(models.Model):
    title = models.CharField(max_length=256)
    description = models.TextField()
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    vote_count = models.PositiveSmallIntegerField()

    def __str__(self):
        return f"{self.person} - {self.title}"
