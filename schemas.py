from pydantic import BaseModel, model_validator
from typing import Optional, List

# Request payload for /identify
class IdentifyRequest(BaseModel):
    email: Optional[str] = None
    phoneNumber: Optional[str] = None

    @model_validator(mode='before')
    @classmethod
    def check_at_least_one(cls, values):
        """Ensure either email or phoneNumber is provided in the request."""
        # Pydantic v2 mode='before' receives a dict
        email = values.get('email')
        phone = values.get('phoneNumber')
        if not email and not phone:
            raise ValueError('At least one of email or phoneNumber must be provided')
        return values

# The nested contact object in the response
class ContactPayload(BaseModel):
    primaryContactId: int
    emails: List[str]
    phoneNumbers: List[str]
    secondaryContactIds: List[int]

# The top-level response payload
class IdentifyResponse(BaseModel):
    contact: ContactPayload
