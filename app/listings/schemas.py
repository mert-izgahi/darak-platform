# app/listings/schemas.py
from marshmallow import Schema, fields, validate
from .models import ListingType, ListingPurpose, Currency, ListingStatus
LISTING_TYPE_VALUES = [value for value, _ in ListingType.CHOICES]
LISTING_PURPOSE_VALUES = [value for value, _ in ListingPurpose.CHOICES]
CURRENCY_VALUES = [value for value, _ in Currency.CHOICES]
LISTING_STATUS_VALUES = [value for value, _ in ListingStatus.CHOICES]


class CreateListingSchema(Schema):
    title = fields.Str(required=True, validate=validate.Length(min=5, max=200))
    description = fields.Str(validate=validate.Length(max=2000), load_default="")

    property_type = fields.Str(
        required=True,
        validate=validate.OneOf(LISTING_TYPE_VALUES),
    )
    purpose = fields.Str(required=True, validate=validate.OneOf(LISTING_PURPOSE_VALUES))

    price = fields.Float(required=True, validate=validate.Range(min=0))
    currency = fields.Str(
        validate=validate.OneOf(CURRENCY_VALUES), load_default=Currency.USD
    )

    city = fields.Str(required=True, validate=validate.Length(min=2, max=100))
    district = fields.Str(validate=validate.Length(max=100), load_default="")

    area_sqm = fields.Float(validate=validate.Range(min=0), load_default=0)
    bedrooms = fields.Int(validate=validate.Range(min=0), load_default=0)
    bathrooms = fields.Int(validate=validate.Range(min=0), load_default=0)
    floor = fields.Int(load_default=0)
    furnished = fields.Bool(load_default=False)


class UpdateListingSchema(Schema):
    """All fields optional — only update what's sent."""

    title = fields.Str(validate=validate.Length(min=5, max=200))
    description = fields.Str(validate=validate.Length(max=2000))
    price = fields.Float(validate=validate.Range(min=0))
    currency = fields.Str(validate=validate.OneOf(CURRENCY_VALUES), load_default=Currency.USD)
    city = fields.Str(validate=validate.Length(min=2, max=100))
    district = fields.Str(validate=validate.Length(max=100))
    area_sqm = fields.Float(validate=validate.Range(min=0))
    bedrooms = fields.Int(validate=validate.Range(min=0))
    bathrooms = fields.Int(validate=validate.Range(min=0))
    floor = fields.Int()
    furnished = fields.Bool()
    status = fields.Str(validate=validate.OneOf(LISTING_STATUS_VALUES))
