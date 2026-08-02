"""Add chat_messages table

Revision ID: 0002_add_chat_messages
Revises: 0001_initial_migration
Create Date: 2026-08-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0002_add_chat_messages"
down_revision: Union[str, None] = "0001_initial_migration"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("skill_used", sa.String(length=50), nullable=True),
        sa.Column("artifact_type", sa.String(length=20), nullable=True),
        sa.Column("artifact_content", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["chat_sessions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_chat_messages_session_id"),
        "chat_messages",
        ["session_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_chat_messages_session_id"), table_name="chat_messages"
    )
    op.drop_table("chat_messages")
