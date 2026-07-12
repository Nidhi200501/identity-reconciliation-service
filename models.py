from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum
from datetime import datetime
from database import Base

# Enum to restrict linkPrecedence values
class LinkPrecedence(str, enum.Enum):
    primary = "primary"
    secondary = "secondary"

# The Contact model mapped to the 'contacts' table
class Contact(Base):
    __tablename__ = "contacts"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Optional contact details
    phoneNumber = Column(String, nullable=True, index=True)
    email = Column(String, nullable=True, index=True)
    
    # Self-referential foreign key linking to the primary contact
    linkedId = Column(Integer, ForeignKey("contacts.id"), nullable=True, index=True)
    
    # Indicates if this is the main identity or an alias
    linkPrecedence = Column(SQLEnum(LinkPrecedence), default=LinkPrecedence.primary)
    
    # Timestamps
    createdAt = Column(DateTime, default=datetime.utcnow)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deletedAt = Column(DateTime, nullable=True)

    # Note: We don't strictly need bidirectional relationships for this specific logic,
    # but we define linkedContact for potential future use or ORM convenience.
    linkedContact = relationship("Contact", remote_side=[id], backref="linked_secondaries")
