"""Pydantic API schemas."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from shop_claim_portal.models import TenantPlan
from shop_claim_portal.services.validation import (
    strip_control_chars,
    validate_email_no_crlf,
    validate_invite_token,
    validate_server_id,
    validate_tenant_slug,
    contains_forbidden_secret,
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LeadCreate(StrictModel):
    project_name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    telegram: str | None = Field(default=None, max_length=64)
    instance_count: int = Field(default=1, ge=1, le=50)
    comment: str | None = Field(default=None, max_length=2000)
    website: str | None = Field(default=None, max_length=200)  # honeypot

    @field_validator("email")
    @classmethod
    def email_no_crlf(cls, v: str) -> str:
        return validate_email_no_crlf(str(v))

    @field_validator("project_name", "telegram", "comment")
    @classmethod
    def strip_fields(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return strip_control_chars(v, allow_newline=(v is not None and len(v) > 100))


class LeadOut(BaseModel):
    id: int
    project_name: str
    email: str
    telegram: str | None
    instance_count: int
    comment: str | None
    status: str
    created_at: datetime


class LoginRequest(StrictModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def email_norm(cls, v: str) -> str:
        return validate_email_no_crlf(str(v))


class SetPasswordRequest(StrictModel):
    code: str = Field(min_length=32, max_length=128)
    password: str = Field(min_length=10, max_length=128)

    @field_validator("code")
    @classmethod
    def code_fmt(cls, v: str) -> str:
        return validate_invite_token(v)


class ChangePasswordRequest(StrictModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=10, max_length=128)


class ChangeEmailRequest(StrictModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_email: EmailStr

    @field_validator("new_email")
    @classmethod
    def email_norm(cls, v: str) -> str:
        return validate_email_no_crlf(str(v))


class ConfirmEmailChangeRequest(StrictModel):
    code: str = Field(min_length=32, max_length=128)

    @field_validator("code")
    @classmethod
    def code_fmt(cls, v: str) -> str:
        return validate_invite_token(v)


class ChangeEmailResponse(BaseModel):
    status: str
    email: str
    pending_email: str
    email_sent: bool


class ConfirmEmailChangeResponse(BaseModel):
    status: str
    email: str


class ForgotPasswordRequest(StrictModel):
    email: EmailStr
    website: str | None = Field(default=None, max_length=200)  # honeypot

    @field_validator("email")
    @classmethod
    def email_norm(cls, v: str) -> str:
        return validate_email_no_crlf(str(v))


class ResetPasswordRequest(StrictModel):
    code: str = Field(min_length=32, max_length=128)
    password: str = Field(min_length=10, max_length=128)

    @field_validator("code")
    @classmethod
    def code_fmt(cls, v: str) -> str:
        return validate_invite_token(v)


class StepUpPassword(StrictModel):
    current_password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    id: int
    email: str
    role: str
    tenant_id: str | None
    is_active: bool
    pending_email: str | None = None


class TenantCreate(StrictModel):
    tenant_id: str
    subscription_until: date | None = None
    plan: Literal["free_year", "starter", "pro"] | None = None
    wargm_shop_id: str = Field(default="", max_length=64)
    wargm_api_key: str = Field(default="", max_length=256)
    wargm_api_base: str = Field(default="https://api.wargm.ru/v1.1/shop", max_length=256)
    catalog_offers_path: str | None = None
    catalog_vehicle_profiles_path: str | None = None
    theme_prefix: str | None = Field(default=None, max_length=128)
    lead_id: int | None = None
    subscriber_email: EmailStr | None = None
    max_servers: int | None = Field(default=None, ge=1, le=50)

    @field_validator("tenant_id")
    @classmethod
    def slug(cls, v: str) -> str:
        return validate_tenant_slug(v)


class TenantUpdate(StrictModel):
    enabled: bool | None = None
    subscription_until: date | None = None
    plan: Literal["free_year", "starter", "pro"] | None = None
    wargm_shop_id: str | None = Field(default=None, max_length=64)
    wargm_api_key: str | None = Field(default=None, max_length=256)
    theme_prefix: str | None = Field(default=None, max_length=128)
    max_servers: int | None = Field(default=None, ge=1, le=50)


class WargmCredentialsIn(StepUpPassword):
    wargm_shop_id: str = Field(min_length=1, max_length=64)
    wargm_api_key: str = Field(min_length=1, max_length=256)


class ServerUpdate(StrictModel):
    shop_server_id: int | None = Field(default=None, ge=1)
    enabled: bool | None = None


class TenantUserOut(BaseModel):
    id: int
    email: str
    is_active: bool
    has_password: bool


class ServerCreate(StrictModel):
    server_id: str = Field(min_length=3, max_length=64)
    shop_server_id: int = Field(ge=1)
    catalog_path: str | None = Field(default=None, max_length=512)
    enabled: bool = True

    @field_validator("server_id")
    @classmethod
    def server_id_slug(cls, v: str) -> str:
        return validate_server_id(v)


class ServerOut(BaseModel):
    server_id: str
    shop_server_id: int
    api_token_masked: str
    enabled: bool
    catalog_path: str


class ServerCreatedOut(ServerOut):
    api_token_plain: str | None = None


class SubscriptionOut(BaseModel):
    tenant_id: str
    enabled: bool
    subscription_until: date
    active: bool
    deploy_status: str | None
    bridge_url: str
    max_servers: int
    server_count: int
    wargm_configured: bool
    plan: str
    days_remaining: int
    price_per_server_rub: int
    billing_enabled: bool
    checkout_available: bool
    monthly_fee_rub: int
    tier: str
    network3_rub: int
    unlimited_rub: int
    next_add_target_max: int | None = None
    next_add_monthly_fee_rub: int | None = None


class PricingOut(BaseModel):
    price_per_server_rub: int
    network3_rub: int
    unlimited_rub: int
    billing_enabled: bool
    checkout_available: bool


class BillingCheckoutIn(StrictModel):
    payment_kind: Literal["renewal", "add_server", "renewal_and_add_server"]
    months: Literal[1, 3, 12]


class BillingCheckoutOut(BaseModel):
    confirmation_url: str
    payment_id: str


class BillingReconcileIn(StrictModel):
    payment_id: str | None = Field(default=None, max_length=36)


class BillingReconcileOut(BaseModel):
    status: str
    applied: bool


class BillingReduceLimitIn(StrictModel):
    max_servers: int = Field(ge=1, le=50)


class BillingReduceLimitOut(BaseModel):
    max_servers: int


class BillingSettingsOut(BaseModel):
    price_per_server_rub: int
    billing_enabled: bool
    yookassa_configured: bool


class BillingSettingsUpdate(StrictModel):
    price_per_server_rub: int | None = Field(default=None, ge=1, le=999_999)
    billing_enabled: bool | None = None


class BillingExtendIn(StrictModel):
    days: Literal[30, 365]
    reason: str | None = Field(default=None, max_length=500)


class BillingPaymentOut(BaseModel):
    id: str
    payment_kind: str
    months: int
    amount_rub: int
    price_per_server_rub: int
    status: str
    created_at: datetime
    paid_at: datetime | None
    yookassa_payment_id: str | None = None


class TicketCreate(StrictModel):
    subject: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=3, max_length=8000)
    server_id: str | None = Field(default=None, max_length=64)
    operation_id: str | None = Field(default=None, max_length=64)

    @field_validator("body")
    @classmethod
    def no_secrets(cls, v: str) -> str:
        if contains_forbidden_secret(v):
            raise ValueError("Do not include api_token or full config in ticket")
        return v


class TicketMessageCreate(StrictModel):
    body: str = Field(min_length=1, max_length=8000)

    @field_validator("body")
    @classmethod
    def no_secrets(cls, v: str) -> str:
        if contains_forbidden_secret(v):
            raise ValueError("Do not include secrets in message")
        return v


class TicketOut(BaseModel):
    id: int
    subject: str
    status: str
    server_id: str | None
    operation_id: str | None
    created_at: datetime
    updated_at: datetime


class TicketDetailOut(TicketOut):
    messages: list["TicketMessageOut"]


class TicketMessageOut(BaseModel):
    id: int
    body: str
    is_provider: bool
    created_at: datetime


class TicketStatusUpdate(StrictModel):
    status: Literal["open", "waiting_subscriber", "waiting_provider", "resolved"]


class BridgeSyncRequest(StrictModel):
    restart_bridge: bool = False


class BridgeSyncResult(BaseModel):
    dry_run: bool
    changed: bool
    tenant_count: int
    bridge_hash: str
    message: str
    backup: str | None = None


class TenantOut(BaseModel):
    id: int
    tenant_id: str
    enabled: bool
    subscription_until: date
    plan: str
    wargm_shop_id: str
    catalog_offers_path: str
    theme_prefix: str | None
    deploy_status: str | None
    server_count: int
    max_servers: int
    wargm_configured: bool


class TenantDetailOut(TenantOut):
    servers: list[ServerOut]
    users: list[TenantUserOut]


class CatalogItemIn(BaseModel):
    class_: str = Field(alias="class")
    qty: int = Field(default=1, ge=1, le=999)
    attachments: list[str] = Field(default_factory=list, max_length=20)

    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class CatalogOfferIn(BaseModel):
    type: Literal["container", "vehicle"] = "container"
    name: str = Field(min_length=1, max_length=200)
    container: str | None = Field(default=None, max_length=128)
    items: list[CatalogItemIn] | None = None
    shop_server_ids: list[int] | None = None
    wargm_server_ids: list[int] | None = None  # legacy YAML alias
    class_: str | None = Field(default=None, alias="class", max_length=128)
    spawn: dict[str, float | int] | None = None
    give_key: bool | None = None  # legacy, stripped on save

    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class CatalogPublishIn(StrictModel):
    expected_published_at: datetime | None = None
    current_password: str | None = Field(default=None, max_length=128)


class CatalogImportWargmIn(StrictModel):
    offer_ids: list[str] = Field(min_length=1, max_length=50)
    current_password: str | None = Field(default=None, max_length=128)


class VehicleProfileIn(StrictModel):
    spawn_attachments: list[str] = Field(default_factory=list, max_length=30)
    cargo_items: list[dict[str, Any]] = Field(default_factory=list, max_length=30)
    fluids: dict[str, Any] | None = None


class CatalogOut(BaseModel):
    offers: dict[str, Any]
    vehicle_profiles: dict[str, Any]
    has_unpublished_changes: bool
    catalog_published_at: datetime | None


class CatalogMetaOut(BaseModel):
    has_unpublished_changes: bool
    catalog_published_at: datetime | None
    offers_path: str
    vehicle_profiles_path: str
    published_offer_count: int
    merged_offer_count: int


class CatalogPublishOut(BaseModel):
    status: str
    offer_count: int
    reloaded: int
    catalog_published_at: datetime


class CatalogImportResultOut(BaseModel):
    imported: list[str]
    skipped: list[str]
    errors: list[dict[str, str]]
    warnings: list[dict[str, str]]


class ModArtifactOut(BaseModel):
    id: str
    name: str
    description: str
    kind: str
    required: bool
    download_url: str
    download_available: bool
    workshop_url: str | None = None
    filename: str | None = None
    size_bytes: int | None = None


class ModsManifestOut(BaseModel):
    version: str
    updated_at: str
    status_page_url: str | None = None
    artifacts: list[ModArtifactOut]
