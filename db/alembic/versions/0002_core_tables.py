"""create keywords, mentions, sentiment_results, alert_rules, alerts, reports

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── keywords ──
    op.create_table(
        "keywords",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("keyword", sa.String(200), nullable=False),
        sa.Column("sources", postgresql.ARRAY(sa.Text()), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("alert_threshold", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("idx_keywords_org", "keywords", ["org_id"])

    # ── mentions ──
    op.create_table(
        "mentions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("keyword_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("author", sa.String(200), nullable=True),
        sa.Column("published_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("scraped_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("upvotes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("comment_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("language", sa.String(10), nullable=False, server_default="en"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["keyword_id"], ["keywords.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("source_url", name="uq_mentions_source_url"),
    )
    op.create_index("idx_mentions_keyword_scraped", "mentions", ["keyword_id", sa.text("scraped_at DESC")])
    op.create_index("idx_mentions_org_scraped", "mentions", ["org_id", sa.text("scraped_at DESC")])
    op.create_index("idx_mentions_published", "mentions", [sa.text("published_at DESC")])

    # ── sentiment_results ──
    op.create_table(
        "sentiment_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("mention_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sentiment", sa.Enum("positive", "negative", "neutral", name="sentiment_enum"), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("positive_score", sa.Float(), nullable=False),
        sa.Column("negative_score", sa.Float(), nullable=False),
        sa.Column("neutral_score", sa.Float(), nullable=False),
        sa.Column("keywords", postgresql.ARRAY(sa.Text()), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("entities", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("model_version", sa.String(50), nullable=False),
        sa.Column("analyzed_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["mention_id"], ["mentions.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("mention_id", name="uq_sentiment_mention_id"),
    )
    op.create_index("idx_sentiment_mention", "sentiment_results", ["mention_id"])

    # ── alert_rules ──
    op.create_table(
        "alert_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("keyword_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("condition", postgresql.JSONB(), nullable=False),
        sa.Column("channels", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["keyword_id"], ["keywords.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
    )

    # ── alerts ──
    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("keyword", sa.String(200), nullable=False),
        sa.Column("trigger_reason", sa.Text(), nullable=False),
        sa.Column("mention_count", sa.Integer(), nullable=False),
        sa.Column("channel", sa.Enum("email", "websocket", "push", name="alert_channel_enum"), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("triggered_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rule_id"], ["alert_rules.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_alerts_org_triggered", "alerts", ["org_id", sa.text("triggered_at DESC")])

    # ── reports ──
    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.Enum("pdf", "csv", name="report_type_enum"), nullable=False),
        sa.Column(
            "status",
            sa.Enum("queued", "processing", "done", "failed", name="report_status_enum"),
            nullable=False,
            server_default="queued",
        ),
        sa.Column("filters", postgresql.JSONB(), nullable=False),
        sa.Column("s3_key", sa.Text(), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_reports_org", "reports", ["org_id"])


def downgrade() -> None:
    op.drop_table("reports")
    op.drop_table("alerts")
    op.drop_table("alert_rules")
    op.drop_table("sentiment_results")
    op.drop_table("mentions")
    op.drop_table("keywords")
    for enum_name in ("report_status_enum", "report_type_enum", "alert_channel_enum", "sentiment_enum"):
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
