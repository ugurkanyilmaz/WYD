"""initial

Revision ID: 0001
Revises: 
Create Date: 2025-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('users',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('username', sa.String(150), nullable=False),
        sa.Column('name', sa.String(150), nullable=False),
        sa.Column('surname', sa.String(150), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('phone_number', sa.String(50), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('display_name', sa.String(255), nullable=True),
        sa.Column('avatar_url', sa.String(255), nullable=True),
        sa.Column('blocked', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now())
    )
    op.create_index('ix_users_username', 'users', ['username'], unique=True)
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_phone_number', 'users', ['phone_number'], unique=True)
    op.create_table('posts',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('author_id', sa.Integer, sa.ForeignKey('users.id')),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now())
    )
    op.create_table('comments',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('post_id', sa.Integer, sa.ForeignKey('posts.id')),
        sa.Column('author_id', sa.Integer, sa.ForeignKey('users.id')),
        sa.Column('parent_id', sa.Integer, sa.ForeignKey('comments.id')),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now())
    )
    op.create_table('friend_requests',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('from_user', sa.Integer, sa.ForeignKey('users.id')),
        sa.Column('to_user', sa.Integer, sa.ForeignKey('users.id')),
        sa.Column('status', sa.String(50), nullable=True)
    )
    op.create_table('notifications',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id')),
        sa.Column('payload', sa.Text(), nullable=False),
        sa.Column('read', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now())
    )

def downgrade():
    op.drop_table('notifications')
    op.drop_table('friend_requests')
    op.drop_table('comments')
    op.drop_table('posts')
    op.drop_table('users')
