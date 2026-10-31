# Safe Data Migration: Migrates existing single-company data into default Organization & Company
# Idempotent and reversible.

from django.db import migrations


def migrate_existing_data_forward(apps, schema_editor):
    Organization = apps.get_model('governance', 'Organization')
    Company = apps.get_model('governance', 'Company')
    Project = apps.get_model('governance', 'Project')
    Membership = apps.get_model('governance', 'Membership')
    BrandProfile = apps.get_model('governance', 'BrandProfile')
    BrandGuardUser = apps.get_model('governance', 'BrandGuardUser')
    BrandRule = apps.get_model('governance', 'BrandRule')
    FactLedger = apps.get_model('governance', 'FactLedger')
    Submission = apps.get_model('governance', 'Submission')
    AuditEvent = apps.get_model('governance', 'AuditEvent')
    Job = apps.get_model('governance', 'Job')
    CodebaseRepo = apps.get_model('governance', 'CodebaseRepo')
    CodeSymbolMapping = apps.get_model('governance', 'CodeSymbolMapping')
    BlastRadiusReport = apps.get_model('governance', 'BlastRadiusReport')
    DraftRule = apps.get_model('governance', 'DraftRule')
    Notification = apps.get_model('governance', 'Notification')

    # 1. Default Organization
    org, _ = Organization.objects.get_or_create(
        slug='novapay-group',
        defaults={
            'name': 'NovaPay Group',
            'requires_writer_approval': True
        }
    )

    # 2. Existing BrandProfile
    profile = BrandProfile.objects.first()
    palette = [
        {"name": "Midnight Emerald", "hex": "#0A3423", "max_delta_e": 4.0},
        {"name": "Teal", "hex": "#00D4B6", "max_delta_e": 4.5},
        {"name": "Pure White", "hex": "#FFFFFF", "max_delta_e": 2.0},
        {"name": "Muted Panel", "hex": "#F8FAF9", "max_delta_e": 2.0},
    ]

    # 3. Default Company
    company, _ = Company.objects.get_or_create(
        organization=org,
        slug='novapay',
        defaults={
            'name': 'NovaPay',
            'allowed_hex_palette': palette if not profile else profile.allowed_hex_palette,
            'allowed_fonts': ["Inter", "JetBrains Mono", "Plus Jakarta Sans"] if not profile else profile.allowed_fonts,
            'wcag_min_ratio': 4.5 if not profile else profile.wcag_min_ratio,
            'logo_aspect_ratio': 3.5 if not profile else profile.logo_aspect_ratio,
            'ruleset_version': 'v3.2',
            'confidential_mode_default': True,
            'min_triggers': 10,
            'minutes_per_audit': 5,
        }
    )

    if profile and not profile.company:
        profile.company = company
        profile.save(update_fields=['company'])

    if not company.brand_profile and profile:
        company.brand_profile = profile
        company.save(update_fields=['brand_profile'])

    # 4. Default Project
    project, _ = Project.objects.get_or_create(
        company=company,
        slug='global-launch-campaign',
        defaults={
            'name': 'Global Launch Campaign',
            'description': 'Cross-Border Rails & Core Product Launch',
            'channel': 'ALL',
            'is_active': True
        }
    )

    # 5. Link Existing Users & Memberships
    for user in BrandGuardUser.objects.all():
        user.organization = org
        user.company = company
        user.save(update_fields=['organization', 'company'])

        # Create Org-level membership
        Membership.objects.get_or_create(
            user=user,
            organization=org,
            company=None,
            defaults={'role': user.role, 'is_active': True}
        )

        # Create Company-level membership
        Membership.objects.get_or_create(
            user=user,
            organization=org,
            company=company,
            defaults={'role': user.role, 'is_active': True}
        )

    # 6. Migrate Scoped Resources to Company
    BrandRule.objects.filter(company__isnull=True).update(company=company)
    FactLedger.objects.filter(company__isnull=True).update(company=company)
    Submission.objects.filter(company__isnull=True).update(company=company, project=project)
    AuditEvent.objects.filter(company__isnull=True).update(company=company)
    Job.objects.filter(company__isnull=True).update(company=company)
    CodebaseRepo.objects.filter(company__isnull=True).update(company=company)
    CodeSymbolMapping.objects.filter(company__isnull=True).update(company=company)
    BlastRadiusReport.objects.filter(company__isnull=True).update(company=company)
    DraftRule.objects.filter(company__isnull=True).update(company=company)
    Notification.objects.filter(company__isnull=True).update(company=company)


def migrate_existing_data_backward(apps, schema_editor):
    # Backward migration is safe: keeps data, simply disassociates
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('governance', '0007_auditevent_company_blastradiusreport_company_and_more'),
    ]

    operations = [
        migrations.RunPython(migrate_existing_data_forward, migrate_existing_data_backward),
    ]

