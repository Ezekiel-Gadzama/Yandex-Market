"""Add buyer_id to Order and Client models

Revision ID: add_buyer_id_columns
Revises: 
Create Date: 2026-02-08 21:40:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_buyer_id_columns'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add buyer_id column to orders table (if it doesn't exist)
    from sqlalchemy import inspect
    from sqlalchemy.engine import reflection
    
    # Check if columns already exist before adding them
    bind = op.get_bind()
    inspector = inspect(bind)
    
    # Get existing columns
    orders_columns = [col['name'] for col in inspector.get_columns('orders')]
    clients_columns = [col['name'] for col in inspector.get_columns('clients')]
    
    # Add buyer_id to orders if it doesn't exist
    if 'buyer_id' not in orders_columns:
        op.add_column('orders', sa.Column('buyer_id', sa.String(), nullable=True))
    
    # Create index for orders.buyer_id if it doesn't exist
    orders_indexes = [idx['name'] for idx in inspector.get_indexes('orders')]
    if 'ix_orders_buyer_id' not in orders_indexes:
        op.create_index(op.f('ix_orders_buyer_id'), 'orders', ['buyer_id'], unique=False)
    
    # Add buyer_id to clients if it doesn't exist
    if 'buyer_id' not in clients_columns:
        op.add_column('clients', sa.Column('buyer_id', sa.String(), nullable=True))
    
    # Create index for clients.buyer_id if it doesn't exist
    clients_indexes = [idx['name'] for idx in inspector.get_indexes('clients')]
    if 'ix_clients_buyer_id' not in clients_indexes:
        op.create_index(op.f('ix_clients_buyer_id'), 'clients', ['buyer_id'], unique=True)


def downgrade() -> None:
    # Remove buyer_id column from clients table
    op.drop_index(op.f('ix_clients_buyer_id'), table_name='clients')
    op.drop_column('clients', 'buyer_id')
    
    # Remove buyer_id column from orders table
    op.drop_index(op.f('ix_orders_buyer_id'), table_name='orders')
    op.drop_column('orders', 'buyer_id')
