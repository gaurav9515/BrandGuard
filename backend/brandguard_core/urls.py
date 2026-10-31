from django.contrib import admin
from django.urls import path, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
import governance.views as gov_views

urlpatterns = [
    # Production Health & Readiness Endpoints (Phase R4)
    path('healthz', gov_views.healthz_view, name='healthz'),
    path('healthz/', gov_views.healthz_view, name='healthz_slash'),
    path('readyz', gov_views.readyz_view, name='readyz'),
    path('readyz/', gov_views.readyz_view, name='readyz_slash'),
    path('api/healthz/', gov_views.healthz_view, name='api_healthz'),
    path('api/readyz/', gov_views.readyz_view, name='api_readyz'),

    # Root Health Check & API Directory
    path('', gov_views.root_api_status_view, name='root_status'),
    path('api/health/', gov_views.root_api_status_view, name='api_health'),

    # Authentication
    path('api/auth/login/', gov_views.auth_login_view, name='auth_login'),
    path('api/auth/login/admin/', gov_views.auth_admin_login_view, name='auth_admin_login'),
    path('api/auth/register/admin/', gov_views.auth_register_admin_view, name='auth_register_admin'),
    path('api/auth/register/writer/', gov_views.auth_register_writer_view, name='auth_register_writer'),
    path('api/auth/verify-email/', gov_views.auth_verify_email_view, name='auth_verify_email'),
    path('api/auth/password-reset/request/', gov_views.auth_password_reset_request_view, name='auth_password_reset_request'),
    path('api/auth/password-reset/confirm/', gov_views.auth_password_reset_confirm_view, name='auth_password_reset_confirm'),
    path('api/auth/me/', gov_views.auth_me_view, name='auth_me'),
    path('api/auth/logout/', gov_views.auth_logout_view, name='auth_logout'),
    path('api/auth/users/', gov_views.auth_users_view, name='auth_users'),
    path('api/invites/', gov_views.invites_list_create_view, name='invites_list_create'),
    path('api/invites/validate/', gov_views.invite_validate_view, name='invite_validate'),
    path('api/members/pending/', gov_views.members_pending_list_view, name='members_pending_list'),
    path('api/members/<int:user_id>/approve/', gov_views.member_approve_view, name='member_approve'),
    path('api/members/<int:user_id>/reject/', gov_views.member_reject_view, name='member_reject'),
    path('api/members/<int:user_id>/deactivate/', gov_views.member_deactivate_view, name='member_deactivate'),
    path('api/notifications/', gov_views.notifications_list_view, name='notifications_list'),

    # Multi-tenant Companies and Projects (Phase R2)
    path('api/companies/', gov_views.companies_list_create_view, name='companies_list_create'),
    path('api/companies/<uuid:company_id>/', gov_views.company_detail_view, name='company_detail'),
    path('api/companies/<uuid:company_id>/archive/', gov_views.company_detail_view, name='company_archive'),
    path('api/companies/<uuid:company_id>/projects/', gov_views.company_projects_view, name='company_projects'),

    # Existing and profile routes
    path('api/brand-profile/', gov_views.brand_profile_view, name='brand_profile'),
    path('api/brand-profile/add-rule/', gov_views.add_rule_view, name='add_rule'),
    path('api/brand-profile/safe-prompt/', gov_views.brand_safe_prompt_view, name='safe_prompt'),
    path('api/brand-profile/facts/<uuid:fact_id>/expire-or-update/', gov_views.expire_or_update_fact_view, name='expire_or_update_fact'),
    path('api/facts/', gov_views.facts_list_create_view, name='facts_list_create'),
    path('api/facts/<uuid:fact_id>/blast-radius/', gov_views.fact_blast_radius_view, name='fact_blast_radius'),
    path('api/facts/<uuid:fact_id>/apply-patches/', gov_views.fact_apply_patches_view, name='fact_apply_patches'),
    path('api/facts/<uuid:fact_id>/bulk-re-audit/', gov_views.fact_bulk_re_audit_view, name='fact_bulk_re_audit'),
    path('api/facts/<uuid:fact_id>/expire-or-update/', gov_views.expire_or_update_fact_view, name='fact_expire_or_update'),
    path('api/submissions/', gov_views.submissions_list_view, name='submissions_list'),
    path('api/submissions/audit/', gov_views.audit_submission_view, name='audit_submission'),
    path('api/submissions/live-lint/', gov_views.live_lint_view, name='submissions_live_lint'),
    path('api/submissions/verify-stamp/', gov_views.verify_stamp_view, name='verify_stamp'),
    path('api/submissions/<uuid:sub_id>/', gov_views.submission_detail_view, name='submission_detail'),
    path('api/submissions/<uuid:sub_id>/approve/', gov_views.approve_submission_view, name='approve_submission'),
    path('api/findings/<uuid:finding_id>/resolve/', gov_views.resolve_finding_view, name='resolve_finding'),
    path('api/telemetry/', gov_views.telemetry_view, name='telemetry'),
    path('api/telemetry/export-csv/', gov_views.telemetry_export_csv_view, name='telemetry_export_csv'),
    path('api/telemetry/export-pdf/', gov_views.telemetry_export_pdf_view, name='telemetry_export_pdf'),
    path('api/telemetry/writer-summary/', gov_views.writer_telemetry_summary_view, name='telemetry_writer_summary'),
    path('api/jobs/<uuid:job_id>/', gov_views.job_status_view, name='job_status'),
    path('api/exceptions/', gov_views.exception_requests_view, name='exception_requests'),
    path('api/exceptions/<str:exception_id>/', gov_views.exception_detail_view, name='exception_detail'),
    path('api/exceptions/<str:exception_id>/decide/', gov_views.exception_decision_view, name='exception_decide'),
    path('api/exceptions/<str:exception_id>/decision/', gov_views.exception_decision_view, name='exception_decision'),
    # Phase 2: Rule Registry, Drafts, Scraper, Playground, and Versioning
    path('api/rules/', gov_views.rules_list_create_view, name='rules_list_create'),
    path('api/rules/upload/', gov_views.rules_upload_view, name='rules_upload'),
    path('api/rules/scrape/', gov_views.rules_scrape_view, name='rules_scrape'),
    path('api/rules/drafts/', gov_views.draft_rules_list_view, name='draft_rules_list'),
    path('api/rules/drafts/approve/', gov_views.draft_rules_approve_view, name='draft_rules_approve'),
    path('api/rules/playground/', gov_views.rule_playground_view, name='rule_playground'),
    path('api/rules/<str:rule_code>/', gov_views.rule_detail_view, name='rule_detail'),
    path('api/rules/<str:rule_code>/versions/', gov_views.rule_versions_view, name='rule_versions'),
    path('api/rules/<str:rule_code>/rollback/', gov_views.rule_rollback_view, name='rule_rollback'),
    path('api/submissions/<uuid:sub_id>/export-pdf/', gov_views.export_submission_pdf_view, name='export_submission_pdf'),
    path('api/notifications/integrations/', gov_views.notification_integrations_view, name='notification_integrations'),
    path('api/notifications/test-webhook/', gov_views.test_notification_webhook_view, name='test_notification_webhook'),
    path('api/users/', gov_views.users_management_view, name='users_management'),
    # Module 2: Codebase-to-Claim Ground-Truth Verifier
    path('api/codebase/repos/', gov_views.codebase_repos_view, name='codebase_repos'),
    path('api/codebase/repos/<uuid:repo_id>/', gov_views.codebase_repo_detail_view, name='codebase_repo_detail'),
    path('api/codebase/repos/<uuid:repo_id>/scan/', gov_views.codebase_repo_scan_view, name='codebase_repo_scan'),
    path('api/codebase/repos/<uuid:repo_id>/constants/', gov_views.codebase_constants_view, name='codebase_constants'),
    path('api/codebase/mappings/', gov_views.codebase_mappings_view, name='codebase_mappings'),
    path('api/codebase/mappings/<uuid:mapping_id>/', gov_views.codebase_mapping_detail_view, name='codebase_mapping_detail'),
    path('api/codebase/proposed-changes/', gov_views.codebase_proposed_changes_view, name='codebase_proposed_changes'),
    path('api/codebase/proposed-changes/<uuid:change_id>/review/', gov_views.codebase_review_proposed_change_view, name='codebase_review_proposed_change'),
    path('api/webhooks/github/', gov_views.github_webhook_view, name='github_webhook'),
    path('api/realtime/stream/', gov_views.realtime_event_stream_view, name='realtime_event_stream'),

    # Global Search API across Rules, Facts, Submissions, and Navigation
    path('api/search/', gov_views.global_search_view, name='global_search'),

    # Phase R3: Visual Test Lab & Accuracy Calibration
    path('api/visual-test-lab/run/', gov_views.visual_test_lab_run_view, name='visual_test_lab_run'),
    path('api/visual-test-lab/report/', gov_views.visual_test_lab_report_view, name='visual_test_lab_report'),
    path('api/visual-test-lab/low-confidence/', gov_views.visual_test_lab_low_confidence_view, name='visual_test_lab_low_confidence'),
    path('api/samples/', gov_views.samples_catalog_view, name='samples_catalog'),

    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    re_path(r'^samples/(?P<path>.*)$', serve, {'document_root': settings.BASE_DIR / 'fixtures' / 'images'}),
]
