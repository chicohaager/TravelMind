"""Initial schema - baseline migration

Revision ID: 0001
Revises:
Create Date: 2024-12-06

This migration represents the initial database schema.
All existing tables are captured here as the baseline.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users table
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('email', sa.String(length=100), nullable=False),
        sa.Column('hashed_password', sa.String(length=200), nullable=False),
        sa.Column('full_name', sa.String(length=100), nullable=True),
        sa.Column('avatar_url', sa.String(length=500), nullable=True),
        sa.Column('bio', sa.String(length=500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('is_superuser', sa.Boolean(), nullable=True, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ai_salt', sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # Trips table
    op.create_table('trips',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('destination', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('start_date', sa.DateTime(), nullable=True),
        sa.Column('end_date', sa.DateTime(), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('interests', sa.JSON(), nullable=True),
        sa.Column('budget', sa.Float(), nullable=True),
        sa.Column('currency', sa.String(length=3), nullable=True, default='EUR'),
        sa.Column('cover_image', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_trips_id'), 'trips', ['id'], unique=False)
    op.create_index(op.f('ix_trips_owner_id'), 'trips', ['owner_id'], unique=False)

    # Place Lists table
    op.create_table('place_lists',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=100), nullable=False),
        sa.Column('icon', sa.String(length=10), nullable=True, default='📍'),
        sa.Column('color', sa.String(length=7), nullable=True, default='#6366F1'),
        sa.Column('is_collapsed', sa.Boolean(), nullable=True, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('trip_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['trip_id'], ['trips.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_place_lists_id'), 'place_lists', ['id'], unique=False)
    op.create_index(op.f('ix_place_lists_trip_id'), 'place_lists', ['trip_id'], unique=False)

    # Places table
    op.create_table('places',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('address', sa.String(length=500), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=True),
        sa.Column('visit_date', sa.DateTime(), nullable=True),
        sa.Column('visited', sa.Boolean(), nullable=True, default=False),
        sa.Column('website', sa.String(length=500), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('opening_hours', sa.JSON(), nullable=True),
        sa.Column('cost', sa.Float(), nullable=True),
        sa.Column('currency', sa.String(length=3), nullable=True, default='EUR'),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('photos', sa.JSON(), nullable=True),
        sa.Column('image_url', sa.String(length=1000), nullable=True),
        sa.Column('order', sa.Integer(), nullable=True, default=0),
        sa.Column('color', sa.String(length=7), nullable=True, default='#6366F1'),
        sa.Column('icon_type', sa.String(length=50), nullable=True, default='location'),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('external_links', sa.JSON(), nullable=True),
        sa.Column('google_place_id', sa.String(length=200), nullable=True),
        sa.Column('external_rating', sa.Float(), nullable=True),
        sa.Column('review_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('trip_id', sa.Integer(), nullable=False),
        sa.Column('list_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['list_id'], ['place_lists.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['trip_id'], ['trips.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_places_id'), 'places', ['id'], unique=False)
    op.create_index(op.f('ix_places_trip_id'), 'places', ['trip_id'], unique=False)
    op.create_index(op.f('ix_places_list_id'), 'places', ['list_id'], unique=False)

    # Diary Entries table
    op.create_table('diary_entries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('entry_date', sa.DateTime(), nullable=True),
        sa.Column('location_name', sa.String(length=200), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('photos', sa.JSON(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('mood', sa.String(length=50), nullable=True),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('trip_id', sa.Integer(), nullable=False),
        sa.Column('author_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['trip_id'], ['trips.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_diary_entries_id'), 'diary_entries', ['id'], unique=False)
    op.create_index(op.f('ix_diary_entries_trip_id'), 'diary_entries', ['trip_id'], unique=False)
    op.create_index(op.f('ix_diary_entries_author_id'), 'diary_entries', ['author_id'], unique=False)

    # Participants table
    op.create_table('participants',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=100), nullable=True),
        sa.Column('role', sa.String(length=100), nullable=True),
        sa.Column('photo_url', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('trip_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['trip_id'], ['trips.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_participants_id'), 'participants', ['id'], unique=False)
    op.create_index(op.f('ix_participants_trip_id'), 'participants', ['trip_id'], unique=False)

    # Expenses table
    op.create_table('expenses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=True, default='EUR'),
        sa.Column('category', sa.String(length=50), nullable=True, default='other'),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('paid_by', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('receipt_url', sa.String(length=500), nullable=True),
        sa.Column('splits', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('trip_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['paid_by'], ['participants.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['trip_id'], ['trips.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_expenses_id'), 'expenses', ['id'], unique=False)
    op.create_index(op.f('ix_expenses_trip_id'), 'expenses', ['trip_id'], unique=False)

    # Routes table
    op.create_table('routes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('color', sa.String(length=7), nullable=True, default='#6366F1'),
        sa.Column('line_style', sa.String(length=20), nullable=True, default='solid'),
        sa.Column('line_width', sa.Integer(), nullable=True, default=3),
        sa.Column('place_ids', sa.JSON(), nullable=True),
        sa.Column('total_distance', sa.Float(), nullable=True),
        sa.Column('estimated_duration', sa.Integer(), nullable=True),
        sa.Column('transport_mode', sa.String(length=20), nullable=True, default='car'),
        sa.Column('order', sa.Integer(), nullable=True, default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('trip_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['trip_id'], ['trips.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_routes_id'), 'routes', ['id'], unique=False)
    op.create_index(op.f('ix_routes_trip_id'), 'routes', ['trip_id'], unique=False)

    # System Settings table
    op.create_table('system_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('value', sa.Text(), nullable=True),
        sa.Column('value_type', sa.String(length=20), nullable=True, default='string'),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_system_settings_id'), 'system_settings', ['id'], unique=False)
    op.create_index(op.f('ix_system_settings_key'), 'system_settings', ['key'], unique=True)

    # User AI Settings table
    op.create_table('user_ai_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False, default='groq'),
        sa.Column('encrypted_api_key', sa.Text(), nullable=True),
        sa.Column('model_preference', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_ai_settings_id'), 'user_ai_settings', ['id'], unique=False)
    op.create_index(op.f('ix_user_ai_settings_user_id'), 'user_ai_settings', ['user_id'], unique=True)


def downgrade() -> None:
    op.drop_table('user_ai_settings')
    op.drop_table('system_settings')
    op.drop_table('routes')
    op.drop_table('expenses')
    op.drop_table('participants')
    op.drop_table('diary_entries')
    op.drop_table('places')
    op.drop_table('place_lists')
    op.drop_table('trips')
    op.drop_table('users')
