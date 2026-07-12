from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from database import engine, Base, get_db
import models
import schemas
from models import Contact, LinkPrecedence

from contextlib import asynccontextmanager
from fastapi.responses import JSONResponse

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables in the database (if they don't exist)
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title="Identity Reconciliation API", lifespan=lifespan)

# BONUS POINT: Misdirect potential threats with misleading error responses
@app.exception_handler(Exception)
async def covert_exception_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"error": "Signal transmission disrupted. Identity cannot be verified at this time."},
    )

@app.post("/identify", response_model=schemas.IdentifyResponse, status_code=status.HTTP_200_OK)
def identify_contact(request: schemas.IdentifyRequest, db: Session = Depends(get_db)):
    """
    Identifies a contact based on email or phone number.
    Reconciles identity by creating new contacts, linking them, or merging primary contacts.
    """
    req_email = request.email
    req_phone = request.phoneNumber

    # 1. Search for existing contacts matching either email or phone
    conditions = []
    if req_email:
        conditions.append(Contact.email == req_email)
    if req_phone:
        conditions.append(Contact.phoneNumber == req_phone)
    
    matches = db.query(Contact).filter(or_(*conditions)).all()

    # Scenario A: No matches found -> Create a new primary contact
    if not matches:
        new_contact = Contact(
            email=req_email,
            phoneNumber=req_phone,
            linkPrecedence=LinkPrecedence.primary
        )
        db.add(new_contact)
        db.commit()
        db.refresh(new_contact)
        
        return create_response_payload([new_contact], new_contact)

    # Scenario B: Matches found -> Reconcile identities
    
    # 2. Find all primary contact IDs associated with the matches.
    # Due to the star schema design, a match is either a primary itself,
    # or a secondary pointing directly to its primary.
    primary_ids = set()
    for match in matches:
        if match.linkPrecedence == LinkPrecedence.primary:
            primary_ids.add(match.id)
        else:
            if match.linkedId is not None:
                primary_ids.add(match.linkedId)
            
    # Load all unique primary contacts involved, sorted by creation date
    primaries = db.query(Contact).filter(Contact.id.in_(primary_ids)).order_by(Contact.createdAt.asc()).all()
    
    if not primaries:
        # Edge case safeguard (should theoretically never happen if data is consistent)
        raise HTTPException(status_code=500, detail="Database integrity error: missing primary contacts.")
        
    # The oldest primary contact becomes the root identity
    oldest_primary = primaries[0]
    
    # 3. Merge overlapping primaries (The "Hardest Part")
    # If a request linked two previously separate identities, we convert the newer primaries into secondaries.
    if len(primaries) > 1:
        for i in range(1, len(primaries)):
            newer_primary = primaries[i]
            # Convert newer primary to secondary
            newer_primary.linkPrecedence = LinkPrecedence.secondary
            newer_primary.linkedId = oldest_primary.id
            db.add(newer_primary)
            
            # Re-link any secondaries that were pointing to the newer primary
            db.query(Contact).filter(Contact.linkedId == newer_primary.id).update(
                {"linkedId": oldest_primary.id}, synchronize_session=False
            )
        db.commit() # Save the merge changes
        
    # 4. Fetch the fully consolidated cluster of contacts
    # This includes the oldest primary and ALL its secondaries
    cluster_contacts = db.query(Contact).filter(
        or_(Contact.id == oldest_primary.id, Contact.linkedId == oldest_primary.id)
    ).order_by(Contact.createdAt.asc()).all()
    
    # Extract known emails and phones in the cluster
    cluster_emails = {c.email for c in cluster_contacts if c.email}
    cluster_phones = {c.phoneNumber for c in cluster_contacts if c.phoneNumber}
    
    # Check if the incoming request introduces new information
    has_new_email = req_email and req_email not in cluster_emails
    has_new_phone = req_phone and req_phone not in cluster_phones
    
    # 5. Create a new secondary contact if there is new information
    if has_new_email or has_new_phone:
        new_secondary = Contact(
            email=req_email,
            phoneNumber=req_phone,
            linkedId=oldest_primary.id,
            linkPrecedence=LinkPrecedence.secondary
        )
        db.add(new_secondary)
        db.commit()
        db.refresh(new_secondary)
        
        # Add the newly created secondary to our cluster list for building the response
        cluster_contacts.append(new_secondary)

    # 6. Construct and return the final payload
    return create_response_payload(cluster_contacts, oldest_primary)


def create_response_payload(cluster_contacts: list[Contact], primary_contact: Contact):
    """
    Helper function to format the consolidated contact data into the expected JSON response.
    """
    emails_list = []
    phones_list = []
    secondary_ids = []
    
    # Ensure primary's email/phone are first in the list
    if primary_contact.email:
        emails_list.append(primary_contact.email)
    if primary_contact.phoneNumber:
        phones_list.append(primary_contact.phoneNumber)
        
    for contact in cluster_contacts:
        if contact.id != primary_contact.id:
            secondary_ids.append(contact.id)
            
        if contact.email and contact.email not in emails_list:
            emails_list.append(contact.email)
            
        if contact.phoneNumber and contact.phoneNumber not in phones_list:
            phones_list.append(contact.phoneNumber)
            
    return schemas.IdentifyResponse(
        contact=schemas.ContactPayload(
            primaryContactId=primary_contact.id,
            emails=emails_list,
            phoneNumbers=phones_list,
            secondaryContactIds=secondary_ids
        )
    )
