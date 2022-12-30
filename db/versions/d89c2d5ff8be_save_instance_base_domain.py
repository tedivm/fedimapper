"""save_instance_base_domain

Revision ID: d89c2d5ff8be
Revises: 08e94aac57b6
Create Date: 2022-12-29 21:47:47.778190

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d89c2d5ff8be"
down_revision = "08e94aac57b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("instances", sa.Column("base_domain", sa.String(), nullable=True))
    op.create_index(op.f("ix_instances_base_domain"), "instances", ["base_domain"], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("ix_instances_base_domain"), table_name="instances")
    op.drop_column("instances", "base_domain")
    # ### end Alembic commands ###