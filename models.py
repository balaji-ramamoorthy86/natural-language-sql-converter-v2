from app import db
from datetime import datetime
from sqlalchemy import text

class QueryHistory(db.Model):
    """Model to store query conversion history"""
    
    __tablename__ = 'query_history'
    
    id = db.Column(db.Integer, primary_key=True)
    natural_language = db.Column(db.Text, nullable=False)
    generated_sql = db.Column(db.Text, nullable=False)
    optimized_sql = db.Column(db.Text)
    is_valid = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<QueryHistory {self.id}: {self.natural_language[:50]}...>'

class DatabaseSchema(db.Model):
    """Model to store database schema information"""
    
    __tablename__ = 'database_schemas'
    
    id = db.Column(db.Integer, primary_key=True)
    schema_name = db.Column(db.String(255), nullable=False)
    table_name = db.Column(db.String(255), nullable=False)
    column_name = db.Column(db.String(255), nullable=False)
    data_type = db.Column(db.String(100))
    is_nullable = db.Column(db.Boolean, default=True)
    is_primary_key = db.Column(db.Boolean, default=False)
    is_foreign_key = db.Column(db.Boolean, default=False)
    referenced_table = db.Column(db.String(255))
    referenced_column = db.Column(db.String(255))
    column_description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Composite unique constraint to prevent duplicate schema+table+column combinations
    __table_args__ = (
        db.UniqueConstraint('schema_name', 'table_name', 'column_name', name='uq_schema_table_column'),
    )
    
    def __repr__(self):
        return f'<DatabaseSchema {self.schema_name}.{self.table_name}.{self.column_name}>'

class UserFeedback(db.Model):
    """Model to store user feedback on generated queries"""
    
    __tablename__ = 'user_feedback'
    
    id = db.Column(db.Integer, primary_key=True)
    query_history_id = db.Column(db.Integer, db.ForeignKey('query_history.id'), nullable=False)
    rating = db.Column(db.Integer)  # 1-5 rating
    feedback_text = db.Column(db.Text)
    is_helpful = db.Column(db.Boolean)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    query_history = db.relationship('QueryHistory', backref=db.backref('feedback', lazy=True))
    
    def __repr__(self):
        return f'<UserFeedback {self.id}: Rating {self.rating}>'
