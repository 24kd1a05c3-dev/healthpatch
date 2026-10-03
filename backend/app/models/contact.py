from datetime import date
from typing import Annotated

import phonenumbers
from pydantic import AfterValidator, BaseModel, EmailStr, Field, field_validator


def normalize_phone(value: str | None) -> str | None:
    if not value or not value.strip():
        return None
    try:
        number = phonenumbers.parse(value.strip(), 'IN')
    except phonenumbers.NumberParseException as exc:
        raise ValueError('Enter a valid phone number with country and area code') from exc
    if not phonenumbers.is_valid_number(number) or number.extension:
        raise ValueError('Enter a valid phone number without an extension')
    return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)


PhoneNumber = Annotated[str, Field(max_length=40), AfterValidator(normalize_phone)]


class ContactFields(BaseModel):
    address: str | None = Field(default=None, max_length=500)
    additional_phones: list[PhoneNumber] = Field(default_factory=list, max_length=5)
    emergency_contact_relationship: str | None = Field(default=None, max_length=60)
    emergency_contact_email: EmailStr | None = None


class ContactValidation(ContactFields):
    @field_validator('phone', 'emergency_contact_phone', mode='before', check_fields=False)
    @classmethod
    def phone_number(cls, value):
        return normalize_phone(value)

    @field_validator('date_of_birth', check_fields=False)
    @classmethod
    def birth_date(cls, value):
        if not value:
            return None
        parsed = date.fromisoformat(value)
        if parsed > date.today():
            raise ValueError('Date of birth cannot be in the future')
        return parsed.isoformat()

    @field_validator('full_name', check_fields=False)
    @classmethod
    def name(cls, value):
        if value is None or not value.strip():
            raise ValueError('Name cannot be empty')
        return value.strip()
