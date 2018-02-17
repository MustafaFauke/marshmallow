
.. _upgrading:


Upgrading to Newer Releases
===========================

Upgrading to 2.0
++++++++++++++++

Deserializing empty values, ``allow_none``, and ``allow_blank``
***************************************************************

Two new parameters were added to the field classes: ``allow_none`` and ``allow_blank``.

In 2.0, validation/deserialization of `None` is consistent across fields. If ``allow_none`` equals `False` (the default), validation fails when the field's value is `None`. If ``allow_none`` equals `True`, `None` is considered valid, and the field deserialized to `None`.


.. code-block:: python

    from marshmallow import fields

    # In 1.0, deserialization of None was inconsistent
    fields.Int().deserialize(None)  # 0
    fields.Str().deserialize(None)  # ''
    fields.DateTime().deserialize(None)  # error: Could not deserialize None to a datetime.


    # In 2.0, validation/deserialization of None is consistent
    fields.Int().deserialize(None)  # error: Field may not be null.
    fields.Str().deserialize(None)  # error: Field may not be null.
    fields.DateTime().deserialize(None)  # error: Field may not be null.

    # allow_none makes None a valid value
    fields.Int(allow_none=True).deserialize(None)  # None

Similarly, the ``allow_blank`` parameter determines whether the empty string is valid input for string fields.


.. code-block:: python

    from marshmallow import fields

    fields.Str().deserialize('')  # error: Field may not be blank.
    fields.Str(allow_blank=True).deserialize('')  # ''

Error Format when ``many=True``
*******************************

When validating a collection (i.e. when calling ``load`` or ``dump`` with ``many=True``), the errors dictionary will be keyed on the indices of invalid items.

.. code-block:: python

    from marshmallow import Schema, fields

    class BandMemberSchema(Schema):
        name = fields.String(required=True)
        email = fields.Email()

    user_data = [
        {'email': 'mick@stones.com', 'name': 'Mick'},
        {'email': 'invalid', 'name': 'Invalid'},  # invalid email
        {'email': 'keith@stones.com', 'name': 'Keith'},
        {'email': 'charlie@stones.com'},  # missing "name"
    ]

    result = BandMemberSchema(many=True).load(user_data)

    # 1.0
    result.errors
    # {'email': ['"invalid" is not a valid email address.'],
    #  'name': ['Missing data for required field.']}

    # 2.0
    result.errors
    # {1: {'email': ['"invalid" is not a valid email address.']},
    #  3: {'name': ['Missing data for required field.']}}

You can still get the pre-2.0 behavior by setting the ``index_errors`` *class Meta* option to `False`.

Use ``ValidationError`` instead of ``MarshallingError`` and ``UnmarshallingError``
**********************************************************************************

The :exc:`MarshallingError` and :exc:`UnmarshallingError` exceptions are deprecated in favor of a single :exc:`ValidationError <marshmallow.exceptions.ValidationError>`. Users who have written custom fields or are using ``strict`` mode will need to change their code accordingly.

Custom Fields
-------------

Custom fields should raise :exc:`ValidationError <marshmallow.exceptions.ValidationError>` in their `_deserialize` and `_serialize` methods when a validation error occurs.

.. code-block:: python
    :emphasize-lines: 17

    from marshmallow import fields, ValidationError
    from marshmallow.exceptions import UnmarshallingError

    # In 1.0, an UnmarshallingError was raised
    class PasswordField(fields.Field):

        def _deserialize(self, val):
            if not len(val) >= 6:
                raise UnmarshallingError('Password to short.')
            return val

    # In 2.0, an UnmarshallingError is raised
    class PasswordField(fields.Field):

        def _deserialize(self, val):
            if not len(val) >= 6:
                raise ValidationError('Password to short.')
            return val

Handle ``ValidationError`` in strict mode
-----------------------------------------

When using `strict` mode, you should handle `ValidationErrors` when calling `Schema.dump` and `Schema.load`.

.. code-block:: python
    :emphasize-lines: 14

    from marshmallow import exceptions as exc

    schema = BandMemberSchema(strict=True)

    # 1.0
    try:
        schema.load({'email': 'invalid-email'})
    except exc.UnmarshallingError as err:
        # ...

    # 2.0
    try:
        schema.load({'email': 'invalid-email'})
    except exc.ValidationError as err:
        # ...


Accessing error messages in strict mode
***************************************

In 2.0, `strict` mode was improved so that you can access all error messages for a schema (rather than failing early) by accessing a `ValidationError's` ``messages`` attribute.

.. code-block:: python
    :emphasize-lines: 6

    schema = BandMemberSchema(strict=True)

    try:
        result = schema.load({'email': 'invalid'})
    except ValidationMessage as err:
        print(err.messages)
    # {
    #     'email': ['"invalid" is not a valid email address.'],
    #     'name': ['Missing data for required field.']
    # }



Use ``OneOf`` instead of ``fields.Select``
******************************************

The `fields.Select` field is deprecated in favor of the newly-added `OneOf` validator.

.. code-block:: python

    from marshmallow import fields
    from marshmallow.validate import OneOf

    # 1.0
    fields.Select(['red', 'blue'])

    # 2.0
    fields.Str(validate=OneOf(['red', 'blue']))


Upgrading to 1.2
++++++++++++++++

.. module:: marshmallow.fields

Validators
**********

Validators were rewritten as class-based callables, making them easier to use when declaring fields.

.. code-block:: python

    from marshmallow import fields

    # 1.2
    from marshmallow.validate import Range

    age = fields.Int(validate=[Range(min=0, max=999)])

    # Pre-1.2
    from marshmallow.validate import ranging

    age = fields.Int(validate=[lambda val: ranging(val, min=0, max=999)])


The validator functions from 1.1 are deprecated and will be removed in 2.0.

Deserializing the Empty String
******************************


In version 1.2, deserialization of the empty string (``''``) with `DateTime`, `Date`, `Time`, or `TimeDelta` fields results in consistent error messages, regardless of whether or not `python-dateutil` is installed.

.. code-block:: python

    from marshmallow import fields

    fields.Date().deserialize('')
    # UnmarshallingError: Could not deserialize '' to a date object.


Decimal
*******

The `Decimal` field was added to support serialization/deserialization of `decimal.Decimal` numbers. You should use this field when dealing with numbers where precision is critical. The `Fixed`, `Price`, and `Arbitrary` fields are deprecated in favor the `Decimal` field.


Upgrading to 1.0
++++++++++++++++

.. module:: marshmallow

Version 1.0 marks the first major release of marshmallow. Many big changes were made from the pre-1.0 releases in order to provide a cleaner API, support object deserialization, and improve field validation.

Perhaps the largest change is in how objects get serialized. Serialization occurs by invoking the :meth:`Schema.dump` method rather than passing the object to the constructor.  Because only configuration options (e.g. the ``many``, ``strict``, and ``only`` parameters) are passed to the constructor, you can more easily reuse serializer instances.  The :meth:`dump <Schema.dump>` method also forms a nice symmetry with the :meth:`Schema.load` method, which is used for deserialization.

.. code-block:: python

    from marshmallow import Schema, fields

    class UserSchema(Schema):
        email = fields.Email()
        name = fields.String()

    user= User(email='monty@python.org', name='Monty Python')

    # 1.0
    serializer = UserSchema()
    data, errors = serializer.dump(user)
    # OR
    result = serializer.dump(user)
    result.data  # => serialized result
    result.errors  # => errors

    # Pre-1.0
    serialized = UserSchema(user)
    data = serialized.data
    errors = serialized.errors

.. note::

    Some crucial parts of the pre-1.0 API have been retained to ease the transition. You can still pass an object to a `Schema` constructor and access the `Schema.data` and `Schema.errors` properties. The `is_valid` method, however, has been completely removed. It is recommended that you migrate to the new API to prevent future releases from breaking your code.

.. module:: marshmallow.fields

The Fields interface was also reworked in 1.0 to make it easier to define custom fields with their own serialization and deserialization behavior. Custom fields now implement :meth:`Field._serialize` and :meth:`Field._deserialize`.

.. code-block:: python

    from marshmallow import fields, MarshallingError

    class PasswordField(fields.Field):
        def _serialize(self, value, attr, obj):
            if not value or len(value) < 6:
                raise MarshallingError('Password must be greater than 6 characters.')
            return str(value).strip()

        # Similarly, you can override the _deserialize method

Another major change in 1.0 is that multiple validation errors can be stored for a single field. The ``errors`` dictionary returned by :meth:`Schema.dump` and :meth:`Schema.load` is a list of error messages keyed by field name.


.. code-block:: python

    from marshmallow import Schema, fields, ValidationError

    def must_have_number(val):
        if not any(ch.isdigit() for ch in val):
            raise ValidationError('Value must have an number.')

    def validate_length(val):
        if len(val) < 8:
            raise ValidationError('Value must have 8 or more characters.')

    class ValidatingSchema(Schema):
        password = fields.String(validate=[must_have_number, validate_length])

    result, errors = ValidatingSchema().load({'password': 'secure'})
    print(errors)
    # {'password': ['Value must have an number.',
    #               'Value must have 8 or more characters.']}

Other notable changes:

- Serialized output is no longer an `OrderedDict` by default. You must explicitly set the `ordered` class Meta option to `True` .
- :class:`Serializer` has been renamed to :class:`Schema`, but you can still import `marshmallow.Serializer` (which is aliased to :class:`Schema`).
- ``datetime`` objects serialize to ISO8601-formatted strings by default (instead of RFC821 format).
- The ``fields.validated`` decorator was removed, as it is no longer necessary given the new Fields interface.
- `Schema.factory` class method was removed.

.. seealso::

    See the :ref:`Changelog <changelog>` for a  more complete listing of added features, bugfixes and breaking changes.
