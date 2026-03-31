"""001 — Core tables

Revision ID: 001_core_tables
Revises: None
Create Date: 2026-03-26
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET

revision: str = "001_core_tables"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── restaurants ───
    op.create_table(
        "restaurants",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("admin_id", sa.String(12), unique=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("subscription_tier", sa.String(20), nullable=False, server_default="free"),
        sa.Column("timezone", sa.String(50), nullable=False, server_default="Asia/Kolkata"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("password_hash", sa.Text, nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("email_verified", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("email_verification_token", sa.String(128), nullable=True),
        sa.Column("email_verification_expires", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refresh_token_hash", sa.Text, nullable=True),
        sa.Column("refresh_token_expires", sa.DateTime(timezone=True), nullable=True),
    )

    # ─── customer_sessions (must come before tables for FK) ───
    op.create_table(
        "customer_sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("table_id", UUID(as_uuid=True), nullable=False),
        sa.Column("restaurant_id", UUID(as_uuid=True), sa.ForeignKey("restaurants.id"), nullable=False),
        sa.Column("session_token", sa.String(128), unique=True, nullable=False),
        sa.Column("is_table_owner", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("device_fingerprint", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("invalidated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ─── tables ───
    op.create_table(
        "tables",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("restaurant_id", UUID(as_uuid=True), sa.ForeignKey("restaurants.id"), nullable=False),
        sa.Column("table_number", sa.SmallInteger, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="available"),
        sa.Column("owner_session_id", UUID(as_uuid=True), sa.ForeignKey("customer_sessions.id"), nullable=True),
        sa.Column("merged_into_table_id", UUID(as_uuid=True), sa.ForeignKey("tables.id"), nullable=True),
        sa.Column("is_expandable", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("qr_code_token", sa.String(128), unique=True, nullable=False),
        sa.Column("qr_code_url", sa.Text, nullable=False),
        sa.Column("max_capacity", sa.SmallInteger, nullable=False, server_default="4"),
        sa.Column("last_cleaned_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("restaurant_id", "table_number", name="uq_restaurant_table_number"),
    )

    # Add FK from customer_sessions.table_id → tables.id (deferred due to circular ref)
    op.create_foreign_key("fk_session_table", "customer_sessions", "tables", ["table_id"], ["id"])

    # ─── menu_items ───
    op.create_table(
        "menu_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("restaurant_id", UUID(as_uuid=True), sa.ForeignKey("restaurants.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("cuisine", sa.String(100), nullable=True),
        sa.Column("dietary_type", sa.String(30), nullable=False),
        sa.Column("is_daily_special", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_weekly_special", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_available", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("image_url", sa.Text, nullable=True),
        sa.Column("prep_time_minutes", sa.SmallInteger, nullable=False, server_default="15"),
    )

    # ─── orders ───
    op.create_table(
        "orders",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("restaurant_id", UUID(as_uuid=True), sa.ForeignKey("restaurants.id"), nullable=False),
        sa.Column("table_id", UUID(as_uuid=True), sa.ForeignKey("tables.id"), nullable=False),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("customer_sessions.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("special_requests", sa.Text, nullable=True),
        sa.Column("total_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("tax_amount", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("is_finalized", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("barcode_token", sa.String(128), unique=True, nullable=True),
        sa.Column("placed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ─── order_items ───
    op.create_table(
        "order_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", UUID(as_uuid=True), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("menu_item_id", UUID(as_uuid=True), sa.ForeignKey("menu_items.id"), nullable=False),
        sa.Column("quantity", sa.SmallInteger, nullable=False),
        sa.Column("unit_price_at_order", sa.Numeric(10, 2), nullable=False),
        sa.Column("item_notes", sa.Text, nullable=True),
    )

    # ─── audit_log ───
    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("restaurant_id", UUID(as_uuid=True), sa.ForeignKey("restaurants.id"), nullable=True),
        sa.Column("actor_type", sa.String(20), nullable=False),
        sa.Column("actor_id", sa.Text, nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=True),
        sa.Column("resource_id", UUID(as_uuid=True), nullable=True),
        sa.Column("ip_address", INET, nullable=True),
        sa.Column("metadata_json", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # ─── tax_configurations ───
    op.create_table(
        "tax_configurations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("restaurant_id", UUID(as_uuid=True), sa.ForeignKey("restaurants.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("rate_percent", sa.Numeric(5, 2), nullable=False),
        sa.Column("applies_to", sa.String(20), nullable=False, server_default="all"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # ─── staff ───
    op.create_table(
        "staff",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("restaurant_id", UUID(as_uuid=True), sa.ForeignKey("restaurants.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("pin_hash", sa.Text, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ─── Performance indexes ───
    op.create_index("ix_orders_restaurant_status", "orders", ["restaurant_id", "status"])
    op.create_index("ix_orders_placed_at", "orders", ["placed_at"])
    op.create_index("ix_menu_items_restaurant", "menu_items", ["restaurant_id", "is_deleted"])
    op.create_index("ix_customer_sessions_token", "customer_sessions", ["session_token"])
    op.create_index("ix_tables_qr_token", "tables", ["qr_code_token"])
    op.create_index("ix_audit_log_restaurant", "audit_log", ["restaurant_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_log_restaurant")
    op.drop_index("ix_tables_qr_token")
    op.drop_index("ix_customer_sessions_token")
    op.drop_index("ix_menu_items_restaurant")
    op.drop_index("ix_orders_placed_at")
    op.drop_index("ix_orders_restaurant_status")
    op.drop_table("staff")
    op.drop_table("tax_configurations")
    op.drop_table("audit_log")
    op.drop_table("order_items")
    op.drop_table("orders")
    op.drop_table("menu_items")
    op.drop_constraint("fk_session_table", "customer_sessions", type_="foreignkey")
    op.drop_table("tables")
    op.drop_table("customer_sessions")
    op.drop_table("restaurants")
