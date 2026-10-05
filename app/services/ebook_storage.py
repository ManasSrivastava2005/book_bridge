"""Managed PDF files are never exposed through StaticFiles."""
from pathlib import Path
import re
from fastapi import HTTPException

PRIVATE_EBOOK_DIR=Path(__file__).resolve().parents[2]/'private_uploads'/'ebooks'
MANAGED_PATTERN=r'^/digital-resources/files/[a-f0-9]{32}\.pdf$'


def managed(url):
    return bool(url and re.fullmatch(MANAGED_PATTERN,url))


def authorize(resource,user):
    staff=user.role.value in ('librarian','admin')
    if (not resource.is_published or resource.archived_at is not None or not resource.reviewed_by) and not staff:
        raise HTTPException(404,'Digital resource not found')
    if resource.access_type=='library_members' and not staff:
        if not resource.library_id or user.library_id!=resource.library_id:
            raise HTTPException(403,'This PDF is available only to members of its library.')


def validate_managed_metadata(payload):
    if payload.access_type not in ('free','library_members'):
        raise HTTPException(422,'Uploaded PDFs require Free or Library members access.')
    if payload.access_type=='library_members' and not payload.library_id:
        raise HTTPException(422,'Select a library for a members-only PDF.')


def validate_rights(resource):
    if resource.distribution_basis not in ('public_domain','open_license','permission'):
        raise HTTPException(422,'Record a distribution basis before publishing.')
    if not resource.rights_evidence or len(resource.rights_evidence.strip())<10:
        raise HTTPException(422,'Describe the source and evidence permitting distribution (at least 10 characters).')
    if not resource.license_name or not resource.license_name.strip():
        raise HTTPException(422,'Record the license or permission name.')
    if not managed(resource.file_url) and not (resource.file_url or '').startswith('/uploads/'):
        raise HTTPException(422,'Upload an authorized PDF for the curated library. External references remain staff-only.')
    if resource.external_url:
        raise HTTPException(422,'Remove the external content URL before publishing a curated PDF.')


def record_review(resource,staff):
    from datetime import datetime,timezone
    validate_rights(resource)
    resource.reviewed_by=staff.id
    resource.reviewed_at=datetime.now(timezone.utc).replace(tzinfo=None)
