from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'remove_class_and_subject_from_assignment'
down_revision = '<твой предыдущий revision id>'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('teacher_position_assignments') as batch_op:
        batch_op.drop_column('class_id')
        batch_op.drop_column('subject_id')

def downgrade():
    with op.batch_alter_table('teacher_position_assignments') as batch_op:
        batch_op.add_column(sa.Column('class_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('subject_id', sa.Integer(), nullable=True))