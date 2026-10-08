"""SQLAlchemy models."""

from __future__ import annotations

import enum
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class UserRole(str, enum.Enum):
    provider = "provider"
    subscriber = "subscriber"


class TokenPurpose(str, enum.Enum):
    invite = "invite"
    email_change = "email_change"
    password_reset = "password_reset"


class LeadStatus(str, enum.Enum):
    new = "new"
    converted = "converted"
    rejected = "rejected"


class DeployStatus(str, enum.Enum):
    pending = "pending"
    synced = "synced"
    error = "error"


class TenantPlan(str, enum.Enum):
    free_year = "free_year"
    starter = "starter"
    pro = "pro"


DEFAULT_FREE_YEAR_DAYS = 365


class TicketStatus(str, enum.Enum):
    open = "open"
    waiting_subscriber = "waiting_subscriber"
    waiting_provider = "waiting_provider"
    resolved = "resolved"


class PaymentKind(str, enum.Enum):
    renewal = "renewal"
    add_server = "add_server"
    renewal_and_add_server = "renewal_and_add_server"


class BillingPaymentStatus(str, enum.Enum):
    pending = "pending"
    succeeded = "succeeded"
    canceled = "canceled"
    failed = "failed"


PLATFORM_SETTINGS_ID = 1


class PaymentKind(str, enum.Enum):
    renewal = "renewal"
    add_server = "add_server"
    renewal_and_add_server = "renewal_and_add_server"


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    succeeded = "succeeded"
    canceled = "canceled"
    failed = "failed"


PLATFORM_SETTINGS_ID = 1
DEFAULT_PRICE_PER_SERVER_RUB = 299


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), default="")
    role: Mapped[str] = mapped_column(String(32))
    tenant_pk: Mapped[int | None] = mapped_column(ForeignKey("tenants.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    pending_email: Mapped[str | None] = mapped_column(String(254), nullable=True, index=True)
    token_version: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    tenant: Mapped[Tenant | None] = relationship(back_populates="users")


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(254), index=True)
    telegram: Mapped[str | None] = mapped_column(String(64), nullable=True)
    instance_count: Mapped[int] = mapped_column(Integer, default=1)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default=LeadStatus.new.value)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    subscription_until: Mapped[date] = mapped_column(Date)
    wargm_shop_id: Mapped[str] = mapped_column(String(64), default="")
    wargm_api_key_enc: Mapped[str] = mapped_column(Text, default="")
    wargm_api_base: Mapped[str] = mapped_column(String(256), default="https://api.wargm.ru/v1.1/shop")
    catalog_offers_path: Mapped[str] = mapped_column(String(512), default="")
    catalog_vehicle_profiles_path: Mapped[str] = mapped_column(String(512), default="")
    allowed_egress_ips_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    theme_prefix: Mapped[str | None] = mapped_column(String(128), nullable=True)
    catalog_draft_json: Mapped[str] = mapped_column(Text, default="")
    catalog_has_unpublished: Mapped[bool] = mapped_column(Boolean, default=False)
    catalog_published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    lead_id: Mapped[int | None] = mapped_column(ForeignKey("leads.id"), nullable=True)
    max_servers: Mapped[int] = mapped_column(Integer, default=1)
    plan: Mapped[str] = mapped_column(String(32), default=TenantPlan.free_year.value)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    servers: Mapped[list[GameServer]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    users: Mapped[list[User]] = relationship(back_populates="tenant")
    sync_state: Mapped[TenantSyncState | None] = relationship(
        back_populates="tenant", uselist=False, cascade="all, delete-orphan"
    )
    tickets: Mapped[list[Ticket]] = relationship(back_populates="tenant", cascade="all, delete-orphan")


class GameServer(Base):
    __tablename__ = "servers"
    __table_args__ = (UniqueConstraint("server_id", name="uq_server_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_pk: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    server_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    shop_server_id: Mapped[int] = mapped_column(Integer)
    api_token_enc: Mapped[str] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    catalog_path: Mapped[str] = mapped_column(String(512), default="")

    tenant: Mapped[Tenant] = relationship(back_populates="servers")


class TenantSyncState(Base):
    __tablename__ = "tenant_sync_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_pk: Mapped[int] = mapped_column(ForeignKey("tenants.id"), unique=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    bridge_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    deploy_status: Mapped[str] = mapped_column(String(32), default=DeployStatus.pending.value)

    tenant: Mapped[Tenant] = relationship(back_populates="sync_state")


class InviteToken(Base):
    __tablename__ = "invite_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    purpose: Mapped[str] = mapped_column(String(32), default=TokenPurpose.invite.value, index=True)
    token_hash: Mapped[str] = mapped_column(String(128), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_user_id: Mapped[int] = mapped_column(Integer, index=True)
    action: Mapped[str] = mapped_column(String(64))
    target_type: Mapped[str] = mapped_column(String(64))
    target_id: Mapped[str] = mapped_column(String(128))
    meta_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_pk: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    server_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    subject: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(32), default=TicketStatus.open.value)
    operation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    tenant: Mapped[Tenant] = relationship(back_populates="tickets")
    messages: Mapped[list[TicketMessage]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan"
    )


class TicketMessage(Base):
    __tablename__ = "ticket_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"), index=True)
    author_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    body: Mapped[str] = mapped_column(Text)
    is_provider: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    ticket: Mapped[Ticket] = relationship(back_populates="messages")


class PlatformSettings(Base):
    __tablename__ = "platform_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    price_per_server_rub: Mapped[int] = mapped_column(Integer, default=299)
    billing_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class BillingPayment(Base):
    __tablename__ = "billing_payments"
    __table_args__ = (UniqueConstraint("yookassa_payment_id", name="uq_yookassa_payment_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_pk: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    payment_kind: Mapped[str] = mapped_column(String(32))
    months: Mapped[int] = mapped_column(Integer)
    max_servers_snapshot: Mapped[int] = mapped_column(Integer)
    max_servers_delta: Mapped[int] = mapped_column(Integer, default=0)
    price_per_server_rub: Mapped[int] = mapped_column(Integer)
    amount_kopecks: Mapped[int] = mapped_column(Integer)
    yookassa_payment_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(16), default=BillingPaymentStatus.pending.value)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    tenant: Mapped[Tenant] = relationship()
