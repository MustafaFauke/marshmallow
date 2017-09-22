# -*- coding: utf-8 -*-
import pytest

from marshmallow import validate, ValidationError

def test_invalid_email():
    invalid1 = "user@example"
    with pytest.raises(ValidationError):
        validate.email(invalid1)
    invalid2 = "example.com"
    with pytest.raises(ValidationError):
        validate.email(invalid2)
    invalid3 = "user"
    with pytest.raises(ValidationError):
        validate.email(invalid3)
