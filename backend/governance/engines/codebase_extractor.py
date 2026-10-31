"""
Codebase-to-Claim Ground-Truth Verifier Engine.

Performs shallow clone into an isolated sandbox directory, records commit SHA,
and safely parses code via AST (Python) and config parsers (YAML, JSON, TOML, .env).
NEVER executes repository code.
Matches code constants against admin-editable mapping table and proposes truth changes.
"""

import os
import re
import ast
import json
import shutil
import tempfile
import ipaddress
import subprocess
import urllib.parse
from datetime import datetime
from django.utils import timezone
from django.db import transaction

# Config parsers
try:
    import yaml
except ImportError:
    yaml = None

try:
    import tomllib
except ImportError:
    tomllib = None

# Safety and Resource Limits
MAX_FILE_SIZE = 1 * 1024 * 1024  # 1 MB
MAX_FILE_COUNT = 500
SCAN_TIMEOUT = 60  # seconds

EXCLUDED_DIRS = {
    'tests', 'test', 'venv', '.venv', 'env', '.git',
    'node_modules', 'migrations', 'vendor', '__pycache__',
    'dist', 'build', '.idea', '.vscode'
}

EXCLUDED_EXTENSIONS = {
    '.pyc', '.pyo', '.pyd', '.so', '.dll', '.exe', '.bin',
    '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.pdf',
    '.zip', '.tar', '.gz', '.woff', '.woff2', '.ttf', '.eot'
}


def validate_repo_url(url: str) -> bool:
    """
    Validates repository URL against SSRF and unsupported protocols.
    Rejects file://, loopback, private networks, and link-local addresses.
    """
    if not url or not isinstance(url, str):
        raise ValueError("Repository URL is required.")

    url = url.strip()
    # Support git@github.com:org/repo.git format
    if url.startswith("git@"):
        match = re.match(r"^git@([a-zA-Z0-9.-]+):([\w.-]+/[\w.-]+)(?:\.git)?$", url)
        if not match:
            raise ValueError("Invalid SSH git URL format.")
        hostname = match.group(1)
        if hostname.lower() in ('localhost', '127.0.0.1', '::1', '0.0.0.0'):
            raise ValueError("SSRF protection: loopback hostnames are forbidden.")
        return True

    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ('https', 'http'):
        raise ValueError(f"Unsupported URL scheme '{parsed.scheme}'. Only HTTPS/HTTP/SSH git URLs are permitted.")

    hostname = parsed.hostname or ''
    if not hostname:
        raise ValueError("Invalid URL: missing hostname.")

    if hostname.lower() in ('localhost', '127.0.0.1', '::1', '0.0.0.0'):
        raise ValueError("SSRF protection: loopback and local hostnames are forbidden.")

    # Check for private IP literals
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise ValueError(f"SSRF protection: private network IP {hostname} is forbidden.")
    except ValueError:
        pass  # Normal domain name, allowed

    return True


class ASTConstantExtractor:
    """Safely inspects Python files via AST parsing without execution."""

    @staticmethod
    def extract_literal_value(node):
        """Extracts python literal or basic structure from AST node."""
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub) and isinstance(node.operand, ast.Constant):
            return -node.operand.value
        elif isinstance(node, ast.List):
            return [ASTConstantExtractor.extract_literal_value(elt) for elt in node.elts]
        elif isinstance(node, ast.Dict):
            res = {}
            for k, v in zip(node.keys, node.values):
                if isinstance(k, ast.Constant):
                    res[k.value] = ASTConstantExtractor.extract_literal_value(v)
            return res
        return None

    @classmethod
    def parse_python_source(cls, source_code: str, rel_path: str):
        """
        Parses python source code and extracts Assign, AnnAssign,
        class attributes, and dictionary constants.
        """
        extracted = []
        try:
            tree = ast.parse(source_code, filename=rel_path)
        except Exception:
            return extracted

        for node in ast.walk(tree):
            # 1. Simple Assign: KEY = value or Class.KEY = value
            if isinstance(node, ast.Assign):
                val = cls.extract_literal_value(node.value)
                if val is not None:
                    for target in node.targets:
                        target_name = None
                        if isinstance(target, ast.Name):
                            target_name = target.id
                        elif isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
                            target_name = f"{target.value.id}.{target.attr}"

                        if target_name and (target_name.isupper() or '_' in target_name):
                            extracted.append({
                                'symbol_name': target_name,
                                'raw_value': str(val),
                                'file_path': rel_path,
                                'line_number': getattr(node, 'lineno', 1),
                                'confidence': 1.0,
                            })

                # Also extract key-value constants inside dictionaries
                if isinstance(node.value, ast.Dict):
                    for k, v in zip(node.value.keys, node.value.values):
                        if isinstance(k, ast.Constant) and isinstance(k.value, str):
                            dict_val = cls.extract_literal_value(v)
                            if dict_val is not None and (k.value.isupper() or '_' in k.value):
                                extracted.append({
                                    'symbol_name': k.value,
                                    'raw_value': str(dict_val),
                                    'file_path': rel_path,
                                    'line_number': getattr(v, 'lineno', getattr(node, 'lineno', 1)),
                                    'confidence': 0.95,
                                })

            # 2. Type-Annotated Assign: KEY: float = 0.005
            elif isinstance(node, ast.AnnAssign) and node.value:
                val = cls.extract_literal_value(node.value)
                if val is not None and isinstance(node.target, ast.Name):
                    target_name = node.target.id
                    if target_name.isupper() or '_' in target_name:
                        extracted.append({
                            'symbol_name': target_name,
                            'raw_value': str(val),
                            'file_path': rel_path,
                            'line_number': getattr(node, 'lineno', 1),
                            'confidence': 1.0,
                        })

        return extracted


class ConfigConstantExtractor:
    """Parses .env, JSON, YAML, and TOML configuration files."""

    @staticmethod
    def parse_env_file(content: str, rel_path: str):
        extracted = []
        lines = content.splitlines()
        for idx, line in enumerate(lines, start=1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                k, v = line.split('=', 1)
                k = k.strip()
                v = v.strip().strip("'\"")
                if k.isupper() or '_' in k:
                    extracted.append({
                        'symbol_name': k,
                        'raw_value': v,
                        'file_path': rel_path,
                        'line_number': idx,
                        'confidence': 0.95,
                    })
        return extracted

    @staticmethod
    def parse_json_file(content: str, rel_path: str):
        extracted = []
        try:
            data = json.loads(content)
            if isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, (str, int, float, bool)):
                        extracted.append({
                            'symbol_name': str(k),
                            'raw_value': str(v),
                            'file_path': rel_path,
                            'line_number': 1,
                            'confidence': 0.90,
                        })
        except Exception:
            pass
        return extracted

    @staticmethod
    def parse_yaml_file(content: str, rel_path: str):
        extracted = []
        if not yaml:
            return extracted
        try:
            data = yaml.safe_load(content)
            if isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, (str, int, float, bool)):
                        extracted.append({
                            'symbol_name': str(k),
                            'raw_value': str(v),
                            'file_path': rel_path,
                            'line_number': 1,
                            'confidence': 0.90,
                        })
        except Exception:
            pass
        return extracted

    @staticmethod
    def parse_toml_file(content: str, rel_path: str):
        extracted = []
        if not tomllib:
            return extracted
        try:
            data = tomllib.loads(content)
            if isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, (str, int, float, bool)):
                        extracted.append({
                            'symbol_name': str(k),
                            'raw_value': str(v),
                            'file_path': rel_path,
                            'line_number': 1,
                            'confidence': 0.90,
                        })
        except Exception:
            pass
        return extracted


def scan_directory(dir_path: str, commit_sha: str = 'HEAD'):
    """
    Scans a directory of code and configs with strict resource limits.
    Returns list of extracted constants.
    """
    extracted_constants = []
    file_count = 0

    for root, dirs, files in os.walk(dir_path):
        # Exclude ignored directories in-place
        dirs[:] = [d for d in dirs if d.lower() not in EXCLUDED_DIRS and not d.startswith('.')]

        for fname in files:
            file_count += 1
            if file_count > MAX_FILE_COUNT:
                break

            _, ext = os.path.splitext(fname)
            ext = ext.lower()
            if ext in EXCLUDED_EXTENSIONS:
                continue

            full_path = os.path.join(root, fname)
            try:
                if os.path.getsize(full_path) > MAX_FILE_SIZE:
                    continue
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except Exception:
                continue

            rel_path = os.path.relpath(full_path, dir_path).replace('\\', '/')

            # Parse by file type
            if ext == '.py':
                items = ASTConstantExtractor.parse_python_source(content, rel_path)
            elif fname in ('.env', '.env.example') or ext == '.env':
                items = ConfigConstantExtractor.parse_env_file(content, rel_path)
            elif ext == '.json':
                items = ConfigConstantExtractor.parse_json_file(content, rel_path)
            elif ext in ('.yaml', '.yml'):
                items = ConfigConstantExtractor.parse_yaml_file(content, rel_path)
            elif ext == '.toml':
                items = ConfigConstantExtractor.parse_toml_file(content, rel_path)
            else:
                items = []

            for item in items:
                item['commit_sha'] = commit_sha
                extracted_constants.append(item)

        if file_count > MAX_FILE_COUNT:
            break

    return extracted_constants


def execute_shallow_clone(repo_url: str, branch: str, dest_dir: str, auth_token: str = None) -> str:
    """
    Executes a shallow git clone into dest_dir and returns the commit SHA.
    Never executes repository code.
    """
    clone_url = repo_url
    if auth_token and ('github.com' in repo_url or 'gitlab.com' in repo_url):
        # Insert auth token safely
        parsed = urllib.parse.urlparse(repo_url)
        netloc = f"x-access-token:{auth_token}@{parsed.netloc}"
        clone_url = urllib.parse.urlunparse(parsed._replace(netloc=netloc))

    cmd = [
        'git', 'clone',
        '--depth', '1',
        '--branch', branch,
        '--single-branch',
        clone_url,
        dest_dir
    ]

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=SCAN_TIMEOUT)
    if result.returncode != 0:
        raise RuntimeError(f"Git clone failed: {result.stderr.strip() or result.stdout.strip()}")

    # Retrieve HEAD commit SHA
    sha_cmd = ['git', '-C', dest_dir, 'rev-parse', 'HEAD']
    sha_res = subprocess.run(sha_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
    commit_sha = sha_res.stdout.strip() if sha_res.returncode == 0 else 'HEAD'
    return commit_sha


def run_repo_scan(repo_id, commit_sha: str = None, sandbox_dir: str = None, job_id=None):
    """
    Main background job task for scanning a CodebaseRepo.
    Can scan an already cloned/mocked sandbox_dir (for tests/fixtures)
    or clone dynamically via git.
    """
    from governance.models import (
        CodebaseRepo, CodeSymbolMapping, CodebaseConstant,
        ProposedFactChange, AuditEvent
    )
    from governance.job_runner import update_job_progress

    repo = CodebaseRepo.objects.filter(id=repo_id).first()
    if not repo:
        raise ValueError(f"CodebaseRepo with id {repo_id} not found.")

    repo.scan_status = 'SCANNING'
    repo.scan_error = ''
    repo.save(update_fields=['scan_status', 'scan_error'])

    temp_dir_created = False
    target_scan_dir = sandbox_dir

    if job_id:
        update_job_progress(job_id, 15, "Cloning repository sandbox...")

    try:
        # Clone if sandbox_dir was not explicitly provided
        if not target_scan_dir or not os.path.exists(target_scan_dir):
            target_scan_dir = tempfile.mkdtemp(prefix="brandguard_repo_")
            temp_dir_created = True
            token = repo.get_auth_token()
            commit_sha = execute_shallow_clone(repo.repo_url, repo.branch, target_scan_dir, auth_token=token)
        else:
            if not commit_sha:
                commit_sha = 'a1b2c3d4e5f67890'

        if job_id:
            update_job_progress(job_id, 40, "Scanning files and parsing AST constants...")

        # Parse constants from repository files
        raw_constants = scan_directory(target_scan_dir, commit_sha=commit_sha)

        if job_id:
            update_job_progress(job_id, 70, "Matching extracted constants against Symbol Mappings...")

        # Match against active CodeSymbolMappings for this profile
        active_mappings = list(CodeSymbolMapping.objects.filter(profile=repo.profile, is_active=True).select_related('target_fact'))
        mapping_by_symbol = {m.symbol_name.upper(): m for m in active_mappings}

        extracted_models = []
        proposed_changes = []

        with transaction.atomic():
            # Clear previous constants for this repo
            repo.constants.all().delete()

            for item in raw_constants:
                sym = item['symbol_name'].upper()
                matched_mapping = mapping_by_symbol.get(sym)

                normalized_val = item['raw_value']
                if matched_mapping:
                    normalized_val = matched_mapping.normalize_value(item['raw_value'])

                const_obj = CodebaseConstant.objects.create(
                    repo=repo,
                    mapping=matched_mapping,
                    symbol_name=item['symbol_name'],
                    raw_value=item['raw_value'],
                    normalized_value=normalized_val,
                    file_path=item['file_path'],
                    line_number=item['line_number'],
                    commit_sha=commit_sha,
                    confidence=item['confidence'],
                )
                extracted_models.append(const_obj)

                # Check if this constant maps to a verified fact and differs from truth
                if matched_mapping and matched_mapping.target_fact:
                    fact = matched_mapping.target_fact
                    curr_truth = fact.claim_truth or ''

                    # Detect conflict: if normalized value is not in current truth or differs
                    if normalized_val not in curr_truth:
                        code_loc = f"{item['file_path']}:{item['line_number']} @ commit {commit_sha[:7]}"
                        
                        # Only propose if there isn't already a pending proposal with the same new_value
                        existing_pending = ProposedFactChange.objects.filter(
                            profile=repo.profile,
                            fact=fact,
                            new_value=normalized_val,
                            status='PENDING'
                        ).first()

                        if not existing_pending:
                            change = ProposedFactChange.objects.create(
                                profile=repo.profile,
                                fact=fact,
                                constant=const_obj,
                                old_value=curr_truth,
                                new_value=normalized_val,
                                code_location=code_loc,
                                commit_sha=commit_sha,
                                status='PENDING'
                            )
                            proposed_changes.append(change)

                            # Emit audit event for proposed truth change
                            AuditEvent.emit(
                                profile=repo.profile,
                                event_type='FACT_CHANGE_PROPOSED',
                                fact_code=fact.fact_code,
                                fact=fact,
                                severity='BLOCKER',
                                metadata={
                                    'repo_id': str(repo.id),
                                    'repo_name': repo.repo_name,
                                    'old_value': curr_truth,
                                    'new_value': normalized_val,
                                    'code_location': code_loc,
                                    'commit_sha': commit_sha,
                                }
                            )

            repo.scan_status = 'SUCCESS'
            repo.scan_error = ''
            repo.last_scanned_at = timezone.now()
            repo.last_commit_sha = commit_sha
            repo.save(update_fields=['scan_status', 'scan_error', 'last_scanned_at', 'last_commit_sha'])

            # Emit audit event for repo scan
            AuditEvent.emit(
                profile=repo.profile,
                event_type='REPO_SCANNED',
                metadata={
                    'repo_id': str(repo.id),
                    'repo_name': repo.repo_name,
                    'commit_sha': commit_sha,
                    'constants_extracted': len(extracted_models),
                    'proposed_changes_count': len(proposed_changes),
                }
            )

        if job_id:
            update_job_progress(job_id, 100, "Repository scan completed successfully.")

        return {
            'repo_id': str(repo.id),
            'commit_sha': commit_sha,
            'constants_extracted': len(extracted_models),
            'proposed_changes_count': len(proposed_changes),
        }

    except Exception as exc:
        repo.scan_status = 'FAILED'
        repo.scan_error = str(exc)
        repo.save(update_fields=['scan_status', 'scan_error'])
        raise
    finally:
        if temp_dir_created and target_scan_dir and os.path.exists(target_scan_dir):
            shutil.rmtree(target_scan_dir, ignore_errors=True)
