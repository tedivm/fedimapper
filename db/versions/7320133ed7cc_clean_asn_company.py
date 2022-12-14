"""clean_asn_company

Revision ID: 7320133ed7cc
Revises: 4cecd778ad0b
Create Date: 2023-01-07 12:42:27.625258

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "7320133ed7cc"
down_revision = "4cecd778ad0b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("asn", sa.Column("company", sa.String(), nullable=True))
    op.create_index(op.f("ix_asn_company"), "asn", ["company"], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("ix_asn_company"), table_name="asn")
    op.drop_column("asn", "company")
    # ### end Alembic commands ###
