"""
Database models for Falsifi - Refutation Bounty Platform
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import enum

db = SQLAlchemy()

class BountyStatus(enum.Enum):
    OPEN = "open"
    CLOSED = "closed"
    EXPIRED = "expired"

class AdjudicationStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    FLAGGED = "flagged"  # AI flagged for human review

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    points = db.Column(db.Integer, default=1000)  # Starting points
    reputation_score = db.Column(db.Float, default=0.0)  # 0-100
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    bounties = db.relationship('Bounty', backref='creator', lazy=True)
    refutations = db.relationship('Refutation', backref='author', lazy=True)
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'points': self.points,
            'reputation_score': round(self.reputation_score, 2),
            'bounties_created': len(self.bounties),
            'refutations_submitted': len(self.refutations)
        }

class Bounty(db.Model):
    __tablename__ = 'bounties'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), default='general')
    bounty_amount = db.Column(db.Integer, nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.Enum(BountyStatus), default=BountyStatus.OPEN)
    auto_adjudicate = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    refutations = db.relationship('Refutation', backref='bounty', lazy=True)
    
    def __repr__(self):
        return f'<Bounty {self.title}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'category': self.category,
            'bounty_amount': self.bounty_amount,
            'creator': self.creator.username if self.creator else None,
            'status': self.status.value,
            'auto_adjudicate': self.auto_adjudicate,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'refutation_count': len(self.refutations),
            'is_open': self.status == BountyStatus.OPEN
        }

class Refutation(db.Model):
    __tablename__ = 'refutations'
    
    id = db.Column(db.Integer, primary_key=True)
    bounty_id = db.Column(db.Integer, db.ForeignKey('bounties.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    sources = db.Column(db.Text, nullable=True)  # JSON string of sources
    bond_amount = db.Column(db.Integer, default=50)
    
    # AI Adjudication
    ai_score = db.Column(db.Float, nullable=True)  # 0-100 quality score
    ai_feedback = db.Column(db.Text, nullable=True)
    adjudication_status = db.Column(db.Enum(AdjudicationStatus), default=AdjudicationStatus.PENDING)
    
    # Creator Rating
    creator_rating = db.Column(db.Integer, nullable=True)  # 1-10
    creator_feedback = db.Column(db.Text, nullable=True)
    
    # Rewards
    reward_earned = db.Column(db.Integer, default=0)
    bond_returned = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Refutation {self.id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'bounty_id': self.bounty_id,
            'author': self.author.username if self.author else None,
            'content': self.content,
            'sources': self.sources,
            'bond_amount': self.bond_amount,
            'ai_score': round(self.ai_score, 2) if self.ai_score else None,
            'ai_feedback': self.ai_feedback,
            'adjudication_status': self.adjudication_status.value,
            'creator_rating': self.creator_rating,
            'creator_feedback': self.creator_feedback,
            'reward_earned': self.reward_earned,
            'bond_returned': self.bond_returned,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class LeaderboardEntry(db.Model):
    """Cached leaderboard entries for performance"""
    __tablename__ = 'leaderboard'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    total_refutations = db.Column(db.Integer, default=0)
    avg_rating = db.Column(db.Float, default=0.0)
    total_earned = db.Column(db.Integer, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='leaderboard_entry', lazy=True)
    
    def to_dict(self):
        return {
            'user_id': self.user_id,
            'username': self.user.username if self.user else None,
            'total_refutations': self.total_refutations,
            'avg_rating': round(self.avg_rating, 2),
            'total_earned': self.total_earned
        }