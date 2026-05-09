# app/leads/schemas.py
from marshmallow import Schema, fields, validate
from .models import LeadSource, LeadStatus


class SubmitLeadSchema(Schema):
    """
    Validated when a visitor submits a lead on a listing page.
    No auth required — visitors are not registered users.
    """

    visitor_name = fields.Str(required=True, validate=validate.Length(min=2, max=100))
    visitor_phone = fields.Str(required=True, validate=validate.Length(min=7, max=20))
    message = fields.Str(validate=validate.Length(max=1000), load_default="")
    source = fields.Str(
        validate=validate.OneOf(
            [LeadSource.FORM, LeadSource.WHATSAPP, LeadSource.PHONE]
        ),
        load_default=LeadSource.FORM,
    )


class UpdateLeadStatusSchema(Schema):
    """
    Validated when a broker updates a lead's status.
    Only the status field can be changed.
    """

    status = fields.Str(
        required=True,
        validate=validate.OneOf(
            [LeadStatus.NEW, LeadStatus.CONTACTED, LeadStatus.CLOSED]
        ),
    )
