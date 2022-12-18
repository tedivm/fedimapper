"""historical_stats

Revision ID: 04c441968ceb
Revises: a2631f842ebb
Create Date: 2022-12-17 21:47:01.268863

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '04c441968ceb'
down_revision = 'a2631f842ebb'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('instance_stats',
    sa.Column('host', sa.String(), nullable=False),
    sa.Column('ingest_time', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('user_count', sa.Integer(), nullable=True),
    sa.Column('status_count', sa.Integer(), nullable=True),
    sa.Column('domain_count', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('host', 'ingest_time')
    )
    op.add_column('instances', sa.Column('current_user_count', sa.Integer(), nullable=True))
    op.add_column('instances', sa.Column('current_status_count', sa.Integer(), nullable=True))
    op.add_column('instances', sa.Column('current_domain_count', sa.Integer(), nullable=True))
    op.drop_column('instances', 'domain_count')
    op.drop_column('instances', 'user_count')
    op.drop_column('instances', 'status_count')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('instances', sa.Column('status_count', sa.INTEGER(), nullable=True))
    op.add_column('instances', sa.Column('user_count', sa.INTEGER(), nullable=True))
    op.add_column('instances', sa.Column('domain_count', sa.INTEGER(), nullable=True))
    op.drop_column('instances', 'current_domain_count')
    op.drop_column('instances', 'current_status_count')
    op.drop_column('instances', 'current_user_count')
    op.drop_table('instance_stats')
    # ### end Alembic commands ###