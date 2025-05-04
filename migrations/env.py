from alembic import op
import sqlalchemy as sa

def upgrade():
    # Проверяем, существует ли таблица teacher_position_assignments
    if not op.get_context().dialect.has_table(op.get_bind(), 'teacher_position_assignments'):
        op.create_table(
            'teacher_position_assignments',
            sa.Column('assignment_id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('teacher_id', sa.Integer(), nullable=True),
            sa.Column('position_id', sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(['teacher_id'], ['teachers.teacher_id'], ),
            sa.ForeignKeyConstraint(['position_id'], ['teacher_positions.position_id'], ),
            sa.PrimaryKeyConstraint('assignment_id')
        )
    else:
        # Если таблица существует, проверяем наличие столбца assignment_id
        if not op.get_context().dialect.has_column(op.get_bind(), 'teacher_position_assignments', 'assignment_id'):
            with op.batch_alter_table('teacher_position_assignments') as batch_op:
                batch_op.add_column(sa.Column('assignment_id', sa.Integer(), autoincrement=True, nullable=False))
                # Если нужно, обновите первичный ключ
                batch_op.drop_constraint('primary', type_='primary')
                batch_op.create_primary_key('pk_teacher_position_assignments', ['assignment_id'])

    # Создаём таблицу assignment_class_links
    op.create_table(
        'assignment_class_links',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('assignment_id', sa.Integer(), nullable=True),
        sa.Column('class_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['assignment_id'], ['teacher_position_assignments.assignment_id'], ),
        sa.ForeignKeyConstraint(['class_id'], ['classes.class_id'], ),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade():
    op.drop_table('assignment_class_links')
    # Если добавляли столбец assignment_id, удаляем его
    if op.get_context().dialect.has_column(op.get_bind(), 'teacher_position_assignments', 'assignment_id'):
        with op.batch_alter_table('teacher_position_assignments') as batch_op:
            batch_op.drop_column('assignment_id')
            # Восстанавливаем старый первичный ключ, если нужно
            # batch_op.create_primary_key('primary', ['старый_ключ'])