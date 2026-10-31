import uuid
import hmac
import hashlib
import base64
import secrets
from datetime import date, datetime, timedelta
from django.utils import timezone
from django.db import models
from django.db.models import Q
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from cryptography.fernet import Fernet


class Organization(models.Model):
    """
    Multi-tenant organization entity.
    Top of the tenant hierarchy: Organization -> Companies (brands) -> Projects.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    requires_writer_approval = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def to_dict(self):
        return {
            'id': str(self.id),
            'name': self.name,
            'slug': self.slug,
            'requires_writer_approval': self.requires_writer_approval,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __str__(self):
        return self.name


class Company(models.Model):
    """
    Brand entity within an Organization.
    Scopes rules, facts, repo connections, submissions, and telemetry.
    Hierarchy: Organization -> Company (Brand) -> Project (Campaign).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='companies')
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    is_archived = models.BooleanField(default=False)

    # Per-Company Visual Identity & Settings
    brand_profile = models.ForeignKey('BrandProfile', null=True, blank=True, on_delete=models.SET_NULL, related_name='companies')
    allowed_hex_palette = models.JSONField(default=list)
    allowed_fonts = models.JSONField(default=list)
    wcag_min_ratio = models.FloatField(default=4.5)
    logo_aspect_ratio = models.FloatField(default=3.5)

    # Per-Company Governance Config
    ruleset_version = models.CharField(max_length=32, default='v3.2')
    confidential_mode_default = models.BooleanField(default=True)
    min_triggers = models.IntegerField(default=10)
    minutes_per_audit = models.IntegerField(default=5)
    repo_connection = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Companies'
        unique_together = [('organization', 'slug')]

    def to_dict(self):
        return {
            'id': str(self.id),
            'organization_id': str(self.organization_id),
            'organization_name': self.organization.name if self.organization else None,
            'name': self.name,
            'slug': self.slug,
            'is_archived': self.is_archived,
            'allowed_hex_palette': self.allowed_hex_palette or [
                {"name": "Midnight Emerald", "hex": "#0A3423", "max_delta_e": 4.0},
                {"name": "Teal", "hex": "#00D4B6", "max_delta_e": 4.5},
                {"name": "Pure White", "hex": "#FFFFFF", "max_delta_e": 2.0},
                {"name": "Muted Panel", "hex": "#F8FAF9", "max_delta_e": 2.0},
            ],
            'allowed_fonts': self.allowed_fonts or ["Inter", "JetBrains Mono", "Plus Jakarta Sans"],
            'wcag_min_ratio': self.wcag_min_ratio,
            'logo_aspect_ratio': self.logo_aspect_ratio,
            'ruleset_version': self.ruleset_version,
            'confidential_mode_default': self.confidential_mode_default,
            'min_triggers': self.min_triggers,
            'minutes_per_audit': self.minutes_per_audit,
            'repo_connection': self.repo_connection,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __str__(self):
        return f"{self.name} ({self.organization.name})"


class Project(models.Model):
    """
    Campaigns or marketing initiatives within a Company (brand).
    Hierarchy: Organization -> Company -> Project.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='projects')
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)
    description = models.TextField(blank=True, default='')
    channel = models.CharField(max_length=64, default='ALL')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = [('company', 'slug')]

    def to_dict(self):
        return {
            'id': str(self.id),
            'company_id': str(self.company_id),
            'company_name': self.company.name,
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'channel': self.channel,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __str__(self):
        return f"{self.name} ({self.company.name})"


class Membership(models.Model):
    """
    Multi-company membership mapping.
    A user can belong to several companies with a role in each.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey('BrandGuardUser', on_delete=models.CASCADE, related_name='memberships')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='memberships')
    company = models.ForeignKey(Company, null=True, blank=True, on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField(max_length=32, choices=[
        ('ADMIN', 'Admin / Brand Governance Lead'),
        ('CONTENT_WRITER', 'Content Writer'),
    ], default='CONTENT_WRITER')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['organization', 'company', 'role']
        unique_together = [('user', 'organization', 'company')]

    def to_dict(self):
        return {
            'id': str(self.id),
            'user_id': self.user_id,
            'username': self.user.username,
            'organization_id': str(self.organization_id),
            'organization_name': self.organization.name,
            'company_id': str(self.company_id) if self.company_id else None,
            'company_name': self.company.name if self.company else None,
            'role': self.role,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __str__(self):
        comp = self.company.name if self.company else 'All Companies (Org-wide)'
        return f"{self.user.username} -> {comp} ({self.role})"


class BrandGuardUser(AbstractUser):
    """
    Custom user model for BrandGuard supporting exactly two roles:
    - ADMIN: Full governance control, rules, scraper, playground, reviews, team management, telemetry
    - CONTENT_WRITER: Pre-flight audit, patch application, scoped voice/tone exceptions, submissions
    """
    ROLE_CHOICES = [
        ('ADMIN', 'Admin / Brand Governance Lead'),
        ('CONTENT_WRITER', 'Content Writer'),
    ]

    brand_profile = models.ForeignKey('BrandProfile', null=True, blank=True, on_delete=models.SET_NULL, related_name='users')
    organization = models.ForeignKey(Organization, null=True, blank=True, on_delete=models.SET_NULL, related_name='users')
    company = models.ForeignKey(Company, null=True, blank=True, on_delete=models.SET_NULL, related_name='active_users')
    role = models.CharField(max_length=32, choices=ROLE_CHOICES, default='CONTENT_WRITER')
    department = models.CharField(max_length=128, default='Marketing')
    avatar_color = models.CharField(max_length=32, default='#0A3423')

    # Security & Workflow Attributes
    is_email_verified = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=True)
    failed_login_attempts = models.IntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)

    @property
    def is_admin_user(self):
        return self.role == 'ADMIN' or self.is_superuser

    @property
    def is_writer_user(self):
        return self.role == 'CONTENT_WRITER'

    def get_allowed_companies(self):
        """Returns QuerySet of Company objects this user has access to."""
        if self.is_superuser:
            return Company.objects.filter(is_archived=False)
        # 1. Companies with direct membership or explicit assignment
        comp_ids = set(self.memberships.filter(is_active=True, company__isnull=False).values_list('company_id', flat=True))
        if self.company_id:
            comp_ids.add(self.company_id)
        if self.brand_profile_id:
            bp = self.brand_profile
            if bp and bp.company_id:
                comp_ids.add(bp.company_id)

        # 2. If user is an Admin of the Organization, they can access all companies in that org
        is_org_admin = self.memberships.filter(is_active=True, company__isnull=True, role='ADMIN').exists() or (self.role == 'ADMIN' and self.organization_id)
        if is_org_admin and self.organization_id:
            return Company.objects.filter(Q(id__in=comp_ids) | Q(organization=self.organization), is_archived=False).distinct()
        return Company.objects.filter(id__in=comp_ids, is_archived=False)

    def has_company_access(self, company_id, required_role=None):
        """Checks if user has permission to access a specific company."""
        if not company_id:
            return False
        if self.is_superuser:
            return True
        allowed_companies = self.get_allowed_companies()
        if not allowed_companies.filter(id=company_id).exists():
            return False
        if required_role == 'ADMIN':
            has_comp_admin = self.memberships.filter(company_id=company_id, role='ADMIN', is_active=True).exists()
            has_org_admin = self.memberships.filter(organization=self.organization, company__isnull=True, role='ADMIN', is_active=True).exists() or self.role == 'ADMIN'
            return has_comp_admin or has_org_admin
        return True

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'name': self.get_full_name() or self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'role': self.role,
            'brand_profile_id': str(self.brand_profile_id) if self.brand_profile_id else None,
            'organization_id': str(self.organization_id) if self.organization_id else None,
            'organization_name': self.organization.name if self.organization else None,
            'company_id': str(self.company_id) if self.company_id else None,
            'company_name': self.company.name if self.company else None,
            'department': self.department,
            'avatar_color': self.avatar_color,
            'is_active': self.is_active,
            'is_email_verified': self.is_email_verified,
            'is_approved': self.is_approved,
            'locked_until': self.locked_until.isoformat() if self.locked_until else None,
            'date_joined': self.date_joined.isoformat() if self.date_joined else None,
        }

    def __str__(self):
        return f"{self.username} ({self.role})"


class SystemSettings(models.Model):
    """
    Global BrandGuard settings configurable by Admins.
    Maintains defaults as fallbacks.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    confidential_mode_default = models.BooleanField(default=True)
    ruleset_version = models.CharField(max_length=32, default='v3.2')
    blocker_penalty = models.FloatField(default=18.0)
    warning_penalty = models.FloatField(default=8.0)
    approved_exception_deduction = models.FloatField(default=4.0)
    color_distance_algorithm = models.CharField(max_length=32, default='CIEDE2000')  # CIEDE2000 | CIE76
    color_distance_threshold = models.FloatField(default=4.0)
    friction_min_triggers = models.IntegerField(default=20)
    min_triggers = models.IntegerField(default=10)
    minutes_per_audit = models.IntegerField(default=5)
    notification_email = models.CharField(max_length=255, blank=True, default='brand-ops@novapay.io')
    notification_slack_webhook = models.CharField(max_length=512, blank=True, default='')
    languages_supported = models.JSONField(default=list)
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def get_settings(cls):
        obj = cls.objects.first()
        if not obj:
            obj = cls.objects.create(
                confidential_mode_default=True,
                ruleset_version='v3.2',
                blocker_penalty=18.0,
                warning_penalty=8.0,
                approved_exception_deduction=4.0,
                color_distance_algorithm='CIEDE2000',
                color_distance_threshold=4.0,
                friction_min_triggers=20,
                min_triggers=10,
                minutes_per_audit=5,
                languages_supported=["en", "es", "fr", "de", "ja"]
            )
        return obj

    def to_dict(self):
        return {
            'confidential_mode_default': self.confidential_mode_default,
            'ruleset_version': self.ruleset_version,
            'blocker_penalty': self.blocker_penalty,
            'warning_penalty': self.warning_penalty,
            'approved_exception_deduction': self.approved_exception_deduction,
            'color_distance_algorithm': self.color_distance_algorithm,
            'color_distance_threshold': self.color_distance_threshold,
            'friction_min_triggers': self.friction_min_triggers,
            'min_triggers': self.min_triggers,
            'minutes_per_audit': self.minutes_per_audit,
            'notification_email': self.notification_email,
            'notification_slack_webhook': self.notification_slack_webhook,
            'languages_supported': self.languages_supported or ["en", "es", "fr", "de", "ja"],
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __str__(self):
        return f"SystemSettings ({self.ruleset_version})"


class BrandProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, null=True, blank=True, on_delete=models.SET_NULL, related_name='brand_profiles')
    org_name = models.CharField(max_length=255)
    allowed_hex_palette = models.JSONField(default=list)  # list of {"name": str, "hex": str, "max_delta_e": float}
    allowed_fonts = models.JSONField(default=list)  # list of strings
    wcag_min_ratio = models.FloatField(default=4.5)
    logo_aspect_ratio = models.FloatField(default=3.5)

    def to_dict(self):
        return {
            'id': str(self.id),
            'company_id': str(self.company_id) if self.company_id else None,
            'org_name': self.org_name,
            'allowed_hex_palette': self.allowed_hex_palette,
            'allowed_fonts': self.allowed_fonts,
            'wcag_min_ratio': self.wcag_min_ratio,
            'logo_aspect_ratio': self.logo_aspect_ratio,
            'rules': [r.to_dict() for r in self.rules.filter(is_active=True).order_by('rule_code')],
            'facts': [f.to_dict() for f in self.facts.all().order_by('fact_code')],
        }

    def __str__(self):
        return self.org_name


class BrandRule(models.Model):
    PILLAR_CHOICES = [
        ('VISUAL', 'Visual'),
        ('FACTUAL', 'Factual'),
        ('TONE', 'Tone'),
    ]
    SEVERITY_CHOICES = [
        ('BLOCKER', 'Blocker'),
        ('WARNING', 'Warning'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(BrandProfile, on_delete=models.CASCADE, related_name='rules')
    company = models.ForeignKey(Company, null=True, blank=True, on_delete=models.CASCADE, related_name='rules')
    pillar = models.CharField(max_length=32, choices=PILLAR_CHOICES)
    rule_code = models.CharField(max_length=64, db_index=True)
    title = models.CharField(max_length=255)
    version = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)
    severity = models.CharField(max_length=32, choices=SEVERITY_CHOICES, default='WARNING')
    enforcement = models.CharField(max_length=64, default='Block publish')
    claims_allowed = models.TextField(blank=True, default='')
    claims_disallowed = models.TextField(blank=True, default='')
    source = models.CharField(max_length=255, blank=True, default='NovaPay Brand Guidelines')
    applies_to = models.CharField(max_length=128, default='All channels')
    language = models.CharField(max_length=16, default='en')
    owner = models.CharField(max_length=128, default='Jordan Lee, Brand Governance Lead')
    structured_spec = models.JSONField(default=dict)
    rule_description = models.TextField(blank=True)
    trigger_count = models.IntegerField(default=0)
    override_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def override_rate(self):
        if self.trigger_count == 0:
            return 0.0
        return round((self.override_count / self.trigger_count) * 100, 1)

    def to_dict(self):
        return {
            'id': str(self.id),
            'profile_id': str(self.profile_id),
            'pillar': self.pillar,
            'rule_code': self.rule_code,
            'title': self.title,
            'version': self.version,
            'is_active': self.is_active,
            'severity': self.severity,
            'enforcement': self.enforcement,
            'claims_allowed': self.claims_allowed,
            'claims_disallowed': self.claims_disallowed,
            'source': self.source,
            'applies_to': self.applies_to,
            'language': self.language,
            'owner': self.owner,
            'structured_spec': self.structured_spec,
            'rule_description': self.rule_description,
            'trigger_count': self.trigger_count,
            'override_count': self.override_count,
            'override_rate': self.override_rate,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __str__(self):
        return f"{self.rule_code} - {self.title} (v{self.version})"


class BrandRuleVersion(models.Model):
    """Immutable version snapshot for rollback and historical comparison."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rule = models.ForeignKey(BrandRule, on_delete=models.CASCADE, related_name='versions')
    version_number = models.IntegerField()
    title = models.CharField(max_length=255)
    pillar = models.CharField(max_length=32)
    severity = models.CharField(max_length=32)
    structured_spec = models.JSONField(default=dict)
    rule_description = models.TextField(blank=True)
    claims_allowed = models.TextField(blank=True)
    claims_disallowed = models.TextField(blank=True)
    enforcement = models.CharField(max_length=64)
    source = models.CharField(max_length=255, blank=True)
    change_note = models.TextField(blank=True)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-version_number']

    def to_dict(self):
        return {
            'id': str(self.id),
            'rule_id': str(self.rule_id),
            'rule_code': self.rule.rule_code,
            'version_number': self.version_number,
            'title': self.title,
            'pillar': self.pillar,
            'severity': self.severity,
            'structured_spec': self.structured_spec,
            'rule_description': self.rule_description,
            'claims_allowed': self.claims_allowed,
            'claims_disallowed': self.claims_disallowed,
            'enforcement': self.enforcement,
            'source': self.source,
            'change_note': self.change_note,
            'changed_by': self.changed_by.username if self.changed_by else 'System',
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __str__(self):
        return f"{self.rule.rule_code} v{self.version_number}"


class DraftRule(models.Model):
    """
    Parsed or scraped rule awaiting Admin review and activation.
    Never auto-activated.
    """
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]
    SOURCE_TYPE_CHOICES = [
        ('UPLOAD', 'File Upload'),
        ('SCRAPE', 'URL Scraper'),
        ('MANUAL', 'Manual Draft'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, null=True, blank=True, on_delete=models.CASCADE, related_name='draft_rules')
    rule_code = models.CharField(max_length=64)
    pillar = models.CharField(max_length=32, default='TONE')
    title = models.CharField(max_length=255)
    severity = models.CharField(max_length=32, default='WARNING')
    enforcement = models.CharField(max_length=64, default='Block publish')
    claims_allowed = models.TextField(blank=True)
    claims_disallowed = models.TextField(blank=True)
    source = models.CharField(max_length=255, default='Uploaded document')
    source_type = models.CharField(max_length=32, choices=SOURCE_TYPE_CHOICES, default='UPLOAD')
    structured_spec = models.JSONField(default=dict)
    rule_description = models.TextField(blank=True)
    language = models.CharField(max_length=16, default='en')
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='DRAFT')
    review_notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    def to_dict(self):
        return {
            'id': str(self.id),
            'company_id': str(self.company_id) if self.company_id else None,
            'rule_code': self.rule_code,
            'pillar': self.pillar,
            'title': self.title,
            'severity': self.severity,
            'enforcement': self.enforcement,
            'claims_allowed': self.claims_allowed,
            'claims_disallowed': self.claims_disallowed,
            'source': self.source,
            'source_type': self.source_type,
            'structured_spec': self.structured_spec,
            'rule_description': self.rule_description,
            'language': self.language,
            'status': self.status,
            'review_notes': self.review_notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __str__(self):
        return f"[DRAFT] {self.rule_code} - {self.title} ({self.status})"


class FactLedger(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(BrandProfile, on_delete=models.CASCADE, related_name='facts')
    company = models.ForeignKey(Company, null=True, blank=True, on_delete=models.CASCADE, related_name='facts')
    fact_code = models.CharField(max_length=64, db_index=True)
    category = models.CharField(max_length=128)
    claim_truth = models.TextField()
    last_verified = models.DateField()
    valid_until = models.DateField()
    superseded_by_text = models.TextField(blank=True)
    is_verified = models.BooleanField(default=True)  # Scraped facts are unverified until admin checks
    source = models.CharField(max_length=255, default='NovaPay Product Facts')
    trigger_count = models.IntegerField(default=0)
    override_count = models.IntegerField(default=0)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

    @property
    def is_expired(self):
        return self.valid_until < date.today()

    @property
    def days_until_expiry(self):
        delta = self.valid_until - date.today()
        return delta.days

    @property
    def blast_radius_count(self):
        try:
            count = 0
            for sub in self.profile.submissions.all():
                latest_v = sub.versions.order_by('-version_number').first()
                if not latest_v:
                    continue
                if (latest_v.findings.filter(rule_citation_code=self.fact_code).exists()
                    or self.fact_code.lower() in latest_v.raw_text.lower()
                    or any(w.lower() in latest_v.raw_text.lower() for w in self.claim_truth.split() if len(w) > 5)):
                    count += 1
            return max(count, 1 if self.is_expired else 0)
        except Exception:
            return 0

    def to_dict(self):
        return {
            'id': str(self.id),
            'profile_id': str(self.profile_id),
            'fact_code': self.fact_code,
            'category': self.category,
            'claim_truth': self.claim_truth,
            'last_verified': self.last_verified.isoformat() if self.last_verified else None,
            'valid_until': self.valid_until.isoformat() if self.valid_until else None,
            'superseded_by_text': self.superseded_by_text,
            'is_expired': self.is_expired,
            'is_verified': self.is_verified,
            'source': self.source,
            'days_until_expiry': self.days_until_expiry,
            'blast_radius_count': self.blast_radius_count,
            'trigger_count': self.trigger_count,
            'override_count': self.override_count,
        }

    def __str__(self):
        return f"{self.fact_code} - {self.category} ({'EXPIRED' if self.is_expired else 'ACTIVE'})"


class Submission(models.Model):
    CHANNEL_CHOICES = [
        ('LINKEDIN_POST', 'LinkedIn Post'),
        ('PRESS_RELEASE', 'Press Release'),
        ('PITCH_DECK', 'Pitch Deck'),
        ('LANDING_PAGE', 'Landing Page'),
    ]
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('IN_REVIEW', 'In Review'),
        ('EXCEPTION_PENDING', 'Exception Pending'),
        ('APPROVED', 'Brand-Compliance Cleared'),
        ('STALE_REAUDIT_REQUIRED', 'Stale Re-Audit Required'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(BrandProfile, on_delete=models.CASCADE, related_name='submissions')
    company = models.ForeignKey(Company, null=True, blank=True, on_delete=models.CASCADE, related_name='submissions')
    project = models.ForeignKey(Project, null=True, blank=True, on_delete=models.SET_NULL, related_name='submissions')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='submissions')
    title = models.CharField(max_length=255)
    channel_context = models.CharField(max_length=64, choices=CHANNEL_CHOICES)
    status = models.CharField(max_length=64, choices=STATUS_CHOICES, default='IN_REVIEW')
    confidential_mode = models.BooleanField(default=False)
    clearance_hash = models.CharField(max_length=128, blank=True)
    clearance_signature = models.TextField(blank=True)
    signed_file_url = models.CharField(max_length=512, blank=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='approved_submissions')
    approved_at = models.DateTimeField(null=True, blank=True)
    audit_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def to_dict(self, user=None):
        latest_ver = self.versions.order_by('-version_number').first()
        return {
            'id': str(self.id),
            'profile_id': str(self.profile_id),
            'company_id': str(self.company_id) if self.company_id else None,
            'project_id': str(self.project_id) if self.project_id else None,
            'project_name': self.project.name if self.project else None,
            'author': self.author.to_dict() if self.author else None,
            'title': self.title,
            'channel_context': self.channel_context,
            'status': self.status,
            'confidential_mode': self.confidential_mode,
            'clearance_hash': self.clearance_hash,
            'clearance_signature': self.clearance_signature,
            'signed_file_url': self.signed_file_url,
            'approved_by': self.approved_by.username if self.approved_by else None,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'audit_notes': self.audit_notes,
            'latest_score': latest_ver.compliance_score if latest_ver else 100.0,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'versions': [v.to_dict(user=user) for v in self.versions.all().order_by('version_number')],
        }

    def __str__(self):
        return f"{self.title} ({self.status})"


class SubmissionVersion(models.Model):
    FILE_TYPE_CHOICES = [
        ('TEXT', 'Text'),
        ('IMAGE', 'Image'),
        ('PDF', 'PDF'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name='versions')
    version_number = models.IntegerField(default=1)
    raw_text = models.TextField(blank=True)
    uploaded_file = models.FileField(upload_to='uploads/', null=True, blank=True)
    file_type = models.CharField(max_length=32, choices=FILE_TYPE_CHOICES, default='TEXT')
    compliance_score = models.FloatField(default=100.0)
    score_breakdown = models.JSONField(default=dict, blank=True)
    voice_fingerprint = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def to_dict(self, user=None):
        return {
            'id': str(self.id),
            'submission_id': str(self.submission_id),
            'version_number': self.version_number,
            'raw_text': self.raw_text,
            'uploaded_file_url': self.uploaded_file.url if self.uploaded_file else None,
            'file_type': self.file_type,
            'compliance_score': round(self.compliance_score, 1),
            'score_breakdown': self.score_breakdown,
            'voice_fingerprint': self.voice_fingerprint,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'findings': [f.to_dict(user=user) for f in self.findings.all()],
        }

    def __str__(self):
        return f"{self.submission.title} v{self.version_number}"


class AuditFinding(models.Model):
    PILLAR_CHOICES = [
        ('VISUAL', 'Visual'),
        ('FACTUAL', 'Factual'),
        ('TONE', 'Tone'),
    ]
    SEVERITY_CHOICES = [
        ('BLOCKER', 'Blocker'),
        ('WARNING', 'Warning'),
    ]
    PROVENANCE_CHOICES = [
        ('DETERMINISTIC_CV', 'Deterministic CV'),
        ('DETERMINISTIC_LEXICON', 'Deterministic Lexicon'),
        ('HYBRID_RAG_LLM', 'Hybrid RAG LLM'),
    ]
    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('ACCEPTED', 'Accepted'),
        ('OVERRIDDEN_PENDING', 'Overridden Pending'),
        ('OVERRIDE_APPROVED', 'Override Approved'),
        ('REJECTED', 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    version = models.ForeignKey(SubmissionVersion, on_delete=models.CASCADE, related_name='findings')
    pillar = models.CharField(max_length=32, choices=PILLAR_CHOICES)
    severity = models.CharField(max_length=32, choices=SEVERITY_CHOICES)
    engine_provenance = models.CharField(max_length=64, choices=PROVENANCE_CHOICES)
    confidence = models.FloatField(default=1.0)
    rule_citation_code = models.CharField(max_length=64)
    rule_citation_title = models.CharField(max_length=255)
    source_excerpt = models.TextField(blank=True)
    location_json = models.JSONField(default=dict)
    explanation = models.TextField()
    suggested_fixes = models.JSONField(default=list)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='OPEN')
    override_reason = models.TextField(blank=True)
    reviewer_comment = models.TextField(blank=True)

    def to_dict(self, user=None):
        explanation = self.explanation
        loc = self.location_json or {}
        code_ver = loc.get('code_verification')
        if code_ver and code_ver.get('is_code_verified'):
            if user and getattr(user, 'role', '') == 'CONTENT_WRITER':
                explanation = code_ver.get('writer_citation') or f"Verified against product code: correct value is {code_ver.get('normalized_value', '')}."
            else:
                admin_cit = code_ver.get('admin_citation') or code_ver.get('code_location', '')
                if admin_cit and admin_cit not in explanation:
                    explanation = f"{self.explanation} [Source: {admin_cit}]"

        return {
            'id': str(self.id),
            'version_id': str(self.version_id),
            'pillar': self.pillar,
            'severity': self.severity,
            'engine_provenance': self.engine_provenance,
            'confidence': self.confidence,
            'rule_citation_code': self.rule_citation_code,
            'rule_citation_title': self.rule_citation_title,
            'source_excerpt': self.source_excerpt,
            'location_json': self.location_json,
            'explanation': explanation,
            'suggested_fixes': self.suggested_fixes,
            'status': self.status,
            'override_reason': self.override_reason,
            'reviewer_comment': self.reviewer_comment,
        }

    def __str__(self):
        return f"[{self.severity}] {self.rule_citation_code}: {self.rule_citation_title}"


class BrandComplianceSignature(models.Model):
    """
    Cryptographic HMAC-SHA256 clearance signature stored in database
    to withstand social media platforms stripping PNG/PDF metadata.
    Verified against (file hash + draft id + ruleset version + approver + timestamp).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name='signatures')
    file_sha256 = models.CharField(max_length=128, db_index=True)
    draft_id = models.CharField(max_length=128, db_index=True)
    ruleset_version = models.CharField(max_length=32)
    approver_username = models.CharField(max_length=150)
    timestamp = models.DateTimeField()
    hmac_signature = models.CharField(max_length=256, db_index=True)
    ed25519_signature = models.CharField(max_length=256, blank=True, default='')
    ed25519_public_key = models.CharField(max_length=256, blank=True, default='')
    canonical_payload = models.TextField()
    legal_notice = models.TextField(default="Brand-compliance cleared. Not a substitute for formal legal review.")
    is_revoked = models.BooleanField(default=False)
    revocation_reason = models.TextField(blank=True, default='')
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @classmethod
    def create_signature(cls, submission, file_bytes, approver_username):
        from governance.crypto_sign import (
            build_canonical_payload, sign_hmac_sha256, sign_ed25519, get_ed25519_keys, LEGAL_NOTICE
        )
        settings_obj = SystemSettings.get_settings()
        ruleset_ver = settings_obj.ruleset_version
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        now = datetime.utcnow()
        now_iso = now.isoformat() + 'Z'
        payload = build_canonical_payload(file_hash, str(submission.id), ruleset_ver, approver_username, now_iso)
        hmac_sig = sign_hmac_sha256(payload)
        _, _, ed25519_pub_hex = get_ed25519_keys()
        ed25519_sig = sign_ed25519(payload)

        return cls.objects.create(
            submission=submission,
            file_sha256=file_hash,
            draft_id=str(submission.id),
            ruleset_version=ruleset_ver,
            approver_username=approver_username,
            timestamp=now,
            hmac_signature=hmac_sig,
            ed25519_signature=ed25519_sig,
            ed25519_public_key=ed25519_pub_hex,
            canonical_payload=payload,
            legal_notice=LEGAL_NOTICE
        )

    def to_dict(self):
        return {
            'id': str(self.id),
            'submission_id': str(self.submission_id),
            'file_sha256': self.file_sha256,
            'draft_id': self.draft_id,
            'ruleset_version': self.ruleset_version,
            'approver_username': self.approver_username,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'hmac_signature': self.hmac_signature,
            'ed25519_signature': self.ed25519_signature,
            'ed25519_public_key': self.ed25519_public_key,
            'canonical_payload': self.canonical_payload,
            'legal_notice': self.legal_notice,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __str__(self):
        return f"Sig-{self.hmac_signature[:16]} ({self.draft_id})"


class ExceptionRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('DECLINED', 'Declined'),
    ]

    id = models.CharField(max_length=64, primary_key=True)  # e.g. "EX-2041"
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, null=True, blank=True, related_name='exceptions')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='exceptions_created')
    draft_id = models.CharField(max_length=64, default='DRAFT_024')
    rule_code = models.CharField(max_length=64, default='VOICE_004')
    title = models.CharField(max_length=255, default='Global ambition. Local simplicity.')
    requester_name = models.CharField(max_length=128, default='Alex Morgan')
    requester_dept = models.CharField(max_length=128, default='Marketing')
    requested_date = models.DateField(default=date.today)
    warning_type = models.CharField(max_length=128, default='Warning · Voice')
    quote_text = models.TextField(default="Don't get wrecked by banks!")
    rule_description = models.TextField(default="Aggressive comparison tone is outside the default voice range.")
    justification = models.TextField(default="This is an intentional challenger voice for NovaPay's 'Global ambition' campaign.")
    campaign_reference = models.CharField(max_length=255, default='Global ambition · Q3 2026 launch')
    scope = models.CharField(max_length=128, default='This draft only')
    channel = models.CharField(max_length=128, default='LinkedIn post')
    expires_on = models.DateField(default=date(2026, 10, 31))
    reviewer_name = models.CharField(max_length=128, default='Jordan Lee')
    reviewer_title = models.CharField(max_length=128, default='Brand Governance Lead')
    hard_blockers_count = models.IntegerField(default=0)
    supporting_file_name = models.CharField(max_length=255, default='Q3_challenger_campaign.pdf')
    supporting_file_size = models.CharField(max_length=64, default='1.2 MB')
    evidence_file = models.FileField(upload_to='evidence/', null=True, blank=True)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='PENDING')
    decision_note = models.TextField(blank=True, default='')
    decided_at = models.DateTimeField(null=True, blank=True)
    decided_by = models.CharField(max_length=128, blank=True, default='')
    decided_by_user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='exceptions_decided')
    created_at = models.DateTimeField(auto_now_add=True)

    def to_dict(self):
        return {
            'id': self.id,
            'draft_id': self.draft_id,
            'submission_id': str(self.submission_id) if self.submission_id else None,
            'rule_code': self.rule_code,
            'title': self.title,
            'requester_name': self.requester_name,
            'requester_dept': self.requester_dept,
            'requested_date': self.requested_date.strftime('%b %d, %Y') if self.requested_date else '',
            'warning_type': self.warning_type,
            'quote_text': self.quote_text,
            'rule_description': self.rule_description,
            'justification': self.justification,
            'campaign_reference': self.campaign_reference,
            'scope': self.scope,
            'channel': self.channel,
            'expires_on': self.expires_on.strftime('%b %d, %Y') if self.expires_on else '',
            'reviewer_name': self.reviewer_name,
            'reviewer_title': self.reviewer_title,
            'hard_blockers_count': self.hard_blockers_count,
            'supporting_file_name': self.supporting_file_name,
            'supporting_file_size': self.supporting_file_size,
            'evidence_file_url': self.evidence_file.url if self.evidence_file else None,
            'status': self.status,
            'decision_note': self.decision_note,
            'decided_at': self.decided_at.isoformat() if self.decided_at else None,
            'decided_by': self.decided_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __str__(self):
        return f"{self.id} - {self.title} ({self.status})"


class Notification(models.Model):
    """In-app notifications for exception decisions and expiring facts."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, null=True, blank=True, on_delete=models.CASCADE, related_name='notifications')
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=64, default='INFO')  # EXCEPTION_DECIDED, FACT_EXPIRING, AUDIT_COMPLETE
    link_url = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def to_dict(self):
        return {
            'id': str(self.id),
            'recipient_id': self.recipient_id,
            'title': self.title,
            'message': self.message,
            'notification_type': self.notification_type,
            'link_url': self.link_url,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __str__(self):
        return f"Notification to {self.recipient.username}: {self.title}"


class AuditTrail(models.Model):
    """
    Immutable audit trail logging who did what and when
    for every rule change, decision, override, and publication download.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    user_display = models.CharField(max_length=150)
    user_role = models.CharField(max_length=64, default='')
    action = models.CharField(max_length=64)  # RULE_CREATED, RULE_UPDATED, EXCEPTION_APPROVED, FILE_DOWNLOADED, AUDIT_EXECUTED
    entity_type = models.CharField(max_length=64)  # RULE, EXCEPTION, SUBMISSION, FACT, SETTINGS
    entity_id = models.CharField(max_length=128)
    description = models.TextField()
    metadata_json = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    @classmethod
    def log(cls, request, action, entity_type, entity_id, description, metadata=None):
        user = getattr(request, 'user', None) if request else None
        username = 'System'
        role = 'SYSTEM'
        ip = None
        if user and user.is_authenticated:
            username = getattr(user, 'username', 'User')
            role = getattr(user, 'role', 'UNKNOWN')
        if request:
            ip = request.META.get('REMOTE_ADDR')

        return cls.objects.create(
            user=user if user and user.is_authenticated else None,
            user_display=username,
            user_role=role,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            description=description,
            metadata_json=metadata or {},
            ip_address=ip
        )

    def to_dict(self):
        return {
            'id': str(self.id),
            'user_display': self.user_display,
            'user_role': self.user_role,
            'action': self.action,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'description': self.description,
            'metadata_json': self.metadata_json,
            'ip_address': self.ip_address,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __str__(self):
        return f"[{self.action}] {self.user_display} on {self.entity_type}:{self.entity_id}"


class AuditEvent(models.Model):
    """
    Append-only governance telemetry event stream.
    Emitted on: SCAN, RULE_VIOLATED, EXCEPTION_REQUESTED, EXCEPTION_APPROVED, EXCEPTION_DECLINED, FIX_ACCEPTED.
    All live metrics and ambiguity diagnostics are computed dynamically from these rows.
    """
    EVENT_CHOICES = [
        ('SCAN', 'Audit Scan Executed'),
        ('RULE_VIOLATED', 'Rule or Fact Violated'),
        ('EXCEPTION_REQUESTED', 'Exception Requested'),
        ('EXCEPTION_APPROVED', 'Exception Approved'),
        ('EXCEPTION_DECLINED', 'Exception Declined'),
        ('FIX_ACCEPTED', 'Fix Accepted'),
        ('REPO_SCANNED', 'Repository Scanned'),
        ('FACT_CHANGE_PROPOSED', 'Fact Change Proposed'),
        ('FACT_CHANGE_APPROVED', 'Fact Change Approved'),
        ('FACT_CHANGE_REJECTED', 'Fact Change Rejected'),
        ('ASSET_MARKED_STALE', 'Asset Marked Stale'),
        ('BLAST_RADIUS_COMPUTED', 'Blast Radius Computed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(BrandProfile, on_delete=models.CASCADE, related_name='audit_events')
    company = models.ForeignKey(Company, null=True, blank=True, on_delete=models.CASCADE, related_name='audit_events')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='audit_events')
    event_type = models.CharField(max_length=32, choices=EVENT_CHOICES, db_index=True)
    submission = models.ForeignKey('Submission', null=True, blank=True, on_delete=models.CASCADE, related_name='audit_events')
    submission_version = models.ForeignKey('SubmissionVersion', null=True, blank=True, on_delete=models.CASCADE, related_name='audit_events')
    rule_code = models.CharField(max_length=64, blank=True, db_index=True)
    fact_code = models.CharField(max_length=64, blank=True, db_index=True)
    rule = models.ForeignKey('BrandRule', null=True, blank=True, on_delete=models.SET_NULL)
    fact = models.ForeignKey('FactLedger', null=True, blank=True, on_delete=models.SET_NULL)
    severity = models.CharField(max_length=32, blank=True)  # Derived strictly from rule's own severity field
    channel = models.CharField(max_length=64, blank=True, db_index=True)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['profile', 'event_type', 'timestamp']),
            models.Index(fields=['profile', 'rule_code', 'timestamp']),
            models.Index(fields=['profile', 'channel', 'timestamp']),
        ]

    @classmethod
    def emit(cls, profile, event_type, user=None, submission=None, submission_version=None,
             rule_code='', fact_code='', rule=None, fact=None, severity='', channel='', timestamp=None, metadata=None):
        if not channel and submission:
            channel = getattr(submission, 'channel_context', '')
        if not timestamp:
            timestamp = timezone.now()
        if rule and not rule_code:
            rule_code = rule.rule_code
        if rule and not severity:
            severity = rule.severity
        if fact and not fact_code:
            fact_code = fact.fact_code
        if fact and not severity:
            severity = 'BLOCKER'

        return cls.objects.create(
            profile=profile,
            user=user,
            event_type=event_type,
            submission=submission,
            submission_version=submission_version,
            rule_code=rule_code or '',
            fact_code=fact_code or '',
            rule=rule,
            fact=fact,
            severity=severity or '',
            channel=channel or '',
            timestamp=timestamp,
            metadata=metadata or {}
        )

    def to_dict(self):
        return {
            'id': str(self.id),
            'profile_id': str(self.profile_id),
            'user_id': self.user_id,
            'event_type': self.event_type,
            'submission_id': str(self.submission_id) if self.submission_id else None,
            'submission_version_id': str(self.submission_version_id) if self.submission_version_id else None,
            'rule_code': self.rule_code,
            'fact_code': self.fact_code,
            'severity': self.severity,
            'channel': self.channel,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'metadata': self.metadata,
        }

    def __str__(self):
        return f"[{self.event_type}] {self.rule_code or self.fact_code} @ {self.timestamp}"


class Job(models.Model):
    """
    Background job execution record.
    Used for long-running operations (repo scan, blast radius, re-audit).
    Exposes status, progress, logs/errors, and result payload via GET /api/jobs/{id}/.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RUNNING', 'Running'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(BrandProfile, on_delete=models.CASCADE, related_name='jobs')
    company = models.ForeignKey(Company, null=True, blank=True, on_delete=models.CASCADE, related_name='jobs')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='jobs')
    job_type = models.CharField(max_length=64, db_index=True)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='PENDING', db_index=True)
    progress = models.IntegerField(default=0)
    status_message = models.CharField(max_length=255, blank=True, default='')
    result_payload = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def to_dict(self):
        return {
            'id': str(self.id),
            'job_type': self.job_type,
            'status': self.status,
            'progress': self.progress,
            'status_message': self.status_message,
            'result': self.result_payload,
            'error': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }

    def __str__(self):
        return f"Job {self.job_type} ({self.status}) - {self.id}"


def get_fernet_cipher():
    key_material = hashlib.sha256(settings.SECRET_KEY.encode('utf-8')).digest()
    fernet_key = base64.urlsafe_b64encode(key_material)
    return Fernet(fernet_key)


class CodebaseRepo(models.Model):
    """
    Connected GitHub / Git repository configuration.
    Token is stored AES-encrypted via Fernet and never displayed again in APIs.
    """
    SCAN_STATUS_CHOICES = [
        ('IDLE', 'Idle'),
        ('SCANNING', 'Scanning'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(BrandProfile, on_delete=models.CASCADE, related_name='codebase_repos')
    company = models.ForeignKey(Company, null=True, blank=True, on_delete=models.CASCADE, related_name='codebase_repos')
    repo_name = models.CharField(max_length=255)
    repo_url = models.CharField(max_length=512)
    branch = models.CharField(max_length=128, default='main')
    auth_token_encrypted = models.BinaryField(null=True, blank=True)
    webhook_secret = models.CharField(max_length=128, blank=True, default='')
    last_scanned_at = models.DateTimeField(null=True, blank=True)
    last_commit_sha = models.CharField(max_length=64, blank=True, default='')
    scan_status = models.CharField(max_length=32, choices=SCAN_STATUS_CHOICES, default='IDLE')
    scan_error = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def set_auth_token(self, token_str: str):
        if token_str:
            cipher = get_fernet_cipher()
            self.auth_token_encrypted = cipher.encrypt(token_str.strip().encode('utf-8'))
        else:
            self.auth_token_encrypted = None

    def get_auth_token(self) -> str:
        if not self.auth_token_encrypted:
            return ''
        try:
            cipher = get_fernet_cipher()
            raw_bytes = bytes(self.auth_token_encrypted)
            return cipher.decrypt(raw_bytes).decode('utf-8')
        except Exception:
            return ''

    def to_dict(self):
        return {
            'id': str(self.id),
            'profile_id': str(self.profile_id),
            'repo_name': self.repo_name,
            'repo_url': self.repo_url,
            'branch': self.branch,
            'has_token': bool(self.auth_token_encrypted),
            'has_webhook_secret': bool(self.webhook_secret),
            'last_scanned_at': self.last_scanned_at.isoformat() if self.last_scanned_at else None,
            'last_commit_sha': self.last_commit_sha,
            'scan_status': self.scan_status,
            'scan_error': self.scan_error,
            'constants_count': self.constants.count(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def __str__(self):
        return f"{self.repo_name} ({self.branch})"


class CodeSymbolMapping(models.Model):
    """
    Admin-editable mapping table linking code symbols/patterns to semantic fact keys.
    Supports unit scaling and display format conversion.
    """
    UNIT_CHOICES = [
        ('PERCENTAGE', 'Percentage'),
        ('HOURS', 'Hours'),
        ('DAYS', 'Days'),
        ('COUNT', 'Count'),
        ('CURRENCY', 'Currency'),
        ('RAW', 'Raw / Literal'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(BrandProfile, on_delete=models.CASCADE, related_name='symbol_mappings')
    company = models.ForeignKey(Company, null=True, blank=True, on_delete=models.CASCADE, related_name='symbol_mappings')
    symbol_name = models.CharField(max_length=255, db_index=True)
    pattern = models.CharField(max_length=255, blank=True, default='')
    semantic_key = models.CharField(max_length=128, db_index=True)
    target_fact = models.ForeignKey(FactLedger, null=True, blank=True, on_delete=models.SET_NULL, related_name='code_mappings')
    unit_type = models.CharField(max_length=32, choices=UNIT_CHOICES, default='RAW')
    scale_factor = models.FloatField(default=1.0)
    display_format = models.CharField(max_length=64, default='{value}')
    confidence_weight = models.FloatField(default=1.0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def normalize_value(self, raw_value: str) -> str:
        """Applies scale factor and display format to raw code value."""
        try:
            clean_str = raw_value.strip().strip("'\"")
            val_num = float(clean_str)
            scaled = val_num * self.scale_factor
            if scaled.is_integer():
                scaled_str = str(int(scaled))
            else:
                scaled_str = f"{scaled:g}"
            if self.display_format and '{value}' in self.display_format:
                return self.display_format.replace('{value}', scaled_str)
            return scaled_str
        except Exception:
            return raw_value.strip().strip("'\"")

    def to_dict(self):
        return {
            'id': str(self.id),
            'profile_id': str(self.profile_id),
            'symbol_name': self.symbol_name,
            'pattern': self.pattern,
            'semantic_key': self.semantic_key,
            'target_fact_id': str(self.target_fact_id) if self.target_fact_id else None,
            'target_fact_code': self.target_fact.fact_code if self.target_fact else None,
            'target_fact_truth': self.target_fact.claim_truth if self.target_fact else None,
            'unit_type': self.unit_type,
            'scale_factor': self.scale_factor,
            'display_format': self.display_format,
            'confidence_weight': self.confidence_weight,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __str__(self):
        return f"{self.symbol_name} -> {self.semantic_key} ({self.target_fact.fact_code if self.target_fact else 'unmapped'})"


class CodebaseConstant(models.Model):
    """
    Extracted code constant from a repository scan.
    Records symbol name, raw value, normalized value, source file, line number, commit SHA.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    repo = models.ForeignKey(CodebaseRepo, on_delete=models.CASCADE, related_name='constants')
    mapping = models.ForeignKey(CodeSymbolMapping, null=True, blank=True, on_delete=models.SET_NULL, related_name='extracted_constants')
    symbol_name = models.CharField(max_length=255, db_index=True)
    raw_value = models.TextField()
    normalized_value = models.TextField()
    file_path = models.CharField(max_length=512)
    line_number = models.IntegerField(default=1)
    commit_sha = models.CharField(max_length=64, db_index=True)
    confidence = models.FloatField(default=1.0)
    extracted_at = models.DateTimeField(auto_now=True)

    def to_dict(self):
        return {
            'id': str(self.id),
            'repo_id': str(self.repo_id),
            'repo_name': self.repo.repo_name,
            'mapping_id': str(self.mapping_id) if self.mapping_id else None,
            'symbol_name': self.symbol_name,
            'raw_value': self.raw_value,
            'normalized_value': self.normalized_value,
            'file_path': self.file_path,
            'line_number': self.line_number,
            'commit_sha': self.commit_sha,
            'confidence': self.confidence,
            'extracted_at': self.extracted_at.isoformat() if self.extracted_at else None,
        }

    def __str__(self):
        return f"{self.symbol_name} = {self.normalized_value} ({self.file_path}:{self.line_number})"


class ProposedFactChange(models.Model):
    """
    Pending truth change detected from codebase scan.
    NEVER overwrites an existing verified fact directly.
    Requires Admin review; approval creates a new fact version and triggers Module 3.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending Review'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(BrandProfile, on_delete=models.CASCADE, related_name='proposed_fact_changes')
    fact = models.ForeignKey(FactLedger, on_delete=models.CASCADE, related_name='proposed_changes')
    constant = models.ForeignKey(CodebaseConstant, on_delete=models.CASCADE, related_name='proposed_changes')
    old_value = models.TextField()
    new_value = models.TextField()
    code_location = models.CharField(max_length=512)
    commit_sha = models.CharField(max_length=64)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='PENDING', db_index=True)
    valid_until = models.DateField(null=True, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def to_dict(self):
        return {
            'id': str(self.id),
            'profile_id': str(self.profile_id),
            'fact_id': str(self.fact_id),
            'fact_code': self.fact.fact_code,
            'fact_category': self.fact.category,
            'constant_id': str(self.constant_id),
            'symbol_name': self.constant.symbol_name,
            'old_value': self.old_value,
            'new_value': self.new_value,
            'code_location': self.code_location,
            'commit_sha': self.commit_sha,
            'status': self.status,
            'valid_until': self.valid_until.isoformat() if self.valid_until else None,
            'reviewed_by': self.reviewed_by.username if self.reviewed_by else None,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'rejection_reason': self.rejection_reason,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __str__(self):
        return f"Proposed Change for {self.fact.fact_code}: '{self.old_value}' -> '{self.new_value}' ({self.status})"


class SubmissionCitation(models.Model):
    """
    Granular citation linking a submission version to the exact facts, rules,
    and codebase constants it depends upon.
    Used by Module 3 Blast Radius engine to pinpoint stale assets when a fact changes.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name='citations')
    submission_version = models.ForeignKey(SubmissionVersion, null=True, blank=True, on_delete=models.CASCADE, related_name='citations')
    fact = models.ForeignKey(FactLedger, null=True, blank=True, on_delete=models.CASCADE, related_name='citations')
    rule = models.ForeignKey(BrandRule, null=True, blank=True, on_delete=models.CASCADE, related_name='citations')
    codebase_constant = models.ForeignKey(CodebaseConstant, null=True, blank=True, on_delete=models.SET_NULL, related_name='citations')
    cited_claim = models.TextField(blank=True, default='')
    citation_code = models.CharField(max_length=64, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['submission', 'fact'],
                condition=models.Q(fact__isnull=False),
                name='unique_submission_fact_citation'
            ),
            models.UniqueConstraint(
                fields=['submission', 'rule'],
                condition=models.Q(rule__isnull=False),
                name='unique_submission_rule_citation'
            ),
        ]

    def to_dict(self):
        return {
            'id': str(self.id),
            'submission_id': str(self.submission_id),
            'submission_version_id': str(self.submission_version_id) if self.submission_version_id else None,
            'fact_id': str(self.fact_id) if self.fact_id else None,
            'rule_id': str(self.rule_id) if self.rule_id else None,
            'constant_id': str(self.codebase_constant_id) if self.codebase_constant_id else None,
            'cited_claim': self.cited_claim,
            'citation_code': self.citation_code,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __str__(self):
        return f"Citation: {self.submission.title} -> {self.citation_code}"


class BlastRadiusReport(models.Model):
    """
    Historical record of Blast Radius computation triggered on truth change,
    fact expiration, or manual re-audit.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(BrandProfile, on_delete=models.CASCADE, related_name='blast_radius_reports')
    company = models.ForeignKey(Company, null=True, blank=True, on_delete=models.CASCADE, related_name='blast_radius_reports')
    fact = models.ForeignKey(FactLedger, on_delete=models.CASCADE, related_name='blast_radius_reports')
    trigger_reason = models.CharField(max_length=128, default='FACT_CHANGE_APPROVED')
    old_value = models.TextField()
    new_value = models.TextField()
    affected_assets_count = models.IntegerField(default=0)
    channel_breakdown = models.JSONField(default=dict)
    severity = models.CharField(max_length=32, default='MEDIUM')
    estimated_reach = models.IntegerField(default=0)
    affected_owners = models.JSONField(default=list)
    draft_patches = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def to_dict(self):
        return {
            'id': str(self.id),
            'profile_id': str(self.profile_id),
            'fact_id': str(self.fact_id),
            'fact_code': self.fact.fact_code,
            'fact_category': self.fact.category,
            'trigger_reason': self.trigger_reason,
            'old_value': self.old_value,
            'new_value': self.new_value,
            'affected_assets_count': self.affected_assets_count,
            'channel_breakdown': self.channel_breakdown,
            'severity': self.severity,
            'estimated_reach': self.estimated_reach,
            'affected_owners': self.affected_owners,
            'draft_patches': self.draft_patches,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __str__(self):
        return f"Blast Radius for {self.fact.fact_code} ({self.severity}): {self.affected_assets_count} assets"


class InviteToken(models.Model):
    """
    Cryptographically secure invite token created by an Admin for writer registration.
    Valid for up to 7 days, single-use or limited-use, scoped to organization and companies.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=64, unique=True, db_index=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='invites')
    companies = models.ManyToManyField(Company, blank=True, related_name='invites')
    created_by = models.ForeignKey(BrandGuardUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_invites')
    role = models.CharField(max_length=32, choices=BrandGuardUser.ROLE_CHOICES, default='CONTENT_WRITER')
    max_uses = models.IntegerField(default=1)
    uses_count = models.IntegerField(default=0)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @classmethod
    def generate_code(cls):
        return f"bg_inv_{secrets.token_urlsafe(24)}"

    def is_valid(self):
        if timezone.now() > self.expires_at:
            return False, "This invite code has expired (7-day validity limit)."
        if self.max_uses > 0 and self.uses_count >= self.max_uses:
            return False, "This invite code has reached its maximum number of uses."
        if not self.is_active:
            return False, "This invite code has been deactivated."
        return True, "Valid"

    def to_dict(self):
        valid, msg = self.is_valid()
        return {
            'id': str(self.id),
            'code': self.code,
            'organization_id': str(self.organization_id),
            'organization_name': self.organization.name,
            'role': self.role,
            'max_uses': self.max_uses,
            'uses_count': self.uses_count,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_active': self.is_active,
            'is_valid': valid,
            'validity_message': msg,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __str__(self):
        return f"Invite {self.code} ({self.organization.name})"


class EmailVerificationToken(models.Model):
    """
    Expiring single-use token sent to user's email upon registration before first login.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    token = models.CharField(max_length=128, unique=True, db_index=True)
    user = models.ForeignKey(BrandGuardUser, on_delete=models.CASCADE, related_name='verification_tokens')
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    @classmethod
    def generate_token(cls):
        return f"bg_emv_{secrets.token_urlsafe(32)}"

    def is_valid(self):
        if self.is_used:
            return False, "Verification token has already been used."
        if timezone.now() > self.expires_at:
            return False, "Verification token has expired."
        return True, "Valid"

    def __str__(self):
        return f"Verify {self.user.username} ({'used' if self.is_used else 'pending'})"


class PasswordResetToken(models.Model):
    """
    Expiring single-use token for email password reset flows.
    Prevents email discovery by returning generic success across all inputs.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    token = models.CharField(max_length=128, unique=True, db_index=True)
    user = models.ForeignKey(BrandGuardUser, on_delete=models.CASCADE, related_name='password_reset_tokens')
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    @classmethod
    def generate_token(cls):
        return f"bg_rst_{secrets.token_urlsafe(32)}"

    def is_valid(self):
        if self.is_used:
            return False, "Password reset token has already been used."
        if timezone.now() > self.expires_at:
            return False, "Password reset token has expired."
        return True, "Valid"

    def __str__(self):
        return f"Reset {self.user.username} ({'used' if self.is_used else 'pending'})"


class LoginAttemptLog(models.Model):
    """
    Security audit log of login and registration attempts for IP/identifier rate-limiting
    and account lockout protection.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ip_address = models.CharField(max_length=64, db_index=True)
    identifier = models.CharField(max_length=255, db_index=True)
    portal = models.CharField(max_length=32, default='WRITER')
    success = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']

    @classmethod
    def record_attempt(cls, ip_address, identifier, portal, success):
        return cls.objects.create(
            ip_address=ip_address or '127.0.0.1',
            identifier=(identifier or '').lower()[:255],
            portal=portal,
            success=success
        )

    @classmethod
    def is_rate_limited(cls, ip_address, identifier, max_failures=5, window_minutes=15):
        cutoff = timezone.now() - timedelta(minutes=window_minutes)
        # Check IP-level failed attempts
        if ip_address:
            ip_failures = cls.objects.filter(
                ip_address=ip_address,
                success=False,
                created_at__gte=cutoff
            ).count()
            if ip_failures >= max_failures:
                return True, f"Too many failed attempts from your IP. Please try again in {window_minutes} minutes."

        # Check Identifier-level failed attempts
        if identifier:
            id_failures = cls.objects.filter(
                identifier=identifier.lower(),
                success=False,
                created_at__gte=cutoff
            ).count()
            if id_failures >= max_failures:
                return True, f"Too many failed login attempts for this account. Please try again in {window_minutes} minutes."

        return False, ""

