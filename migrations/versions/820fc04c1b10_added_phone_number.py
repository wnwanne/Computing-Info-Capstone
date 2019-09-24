"""added phone number

Revision ID: 820fc04c1b10
Revises: c50167abe5b4
Create Date: 2019-09-19 15:47:00.593359

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '820fc04c1b10'
down_revision = 'c50167abe5b4'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('phone_number', sa.String(length=64), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users', 'phone_number')
    # ### end Alembic commands ###
