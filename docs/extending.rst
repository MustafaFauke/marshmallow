.. _extending:
.. module:: marshmallow

Extending Schemas
=================

Pre-processing and Post-processing Methods
------------------------------------------

Data pre-processing and post-processing methods can be registered using the `marshmallow.pre_load <marshmallow.decorators.pre_load>`, `marshmallow.post_load <marshmallow.decorators.post_load>`, `marshmallow.pre_dump <marshmallow.decorators.pre_dump>`, `marshmallow.post_dump <marshmallow.decorators.post_dump>` decorators.


.. code-block:: python

    from marshmallow import Schema, fields, pre_load

    class UserSchema(Schema):
        name = fields.Str()
        slug = fields.Str()

        @pre_load
        def slugify_name(self, in_data):
            in_data['slug'] = in_data['slug'].lower().strip().replace(' ', '-')
            return in_data

    schema = UserSchema()
    result, errors = schema.load({'name': 'Steve', 'slug': 'Steve Loria '})
    result['slug']  # => 'steve-loria'


Passing Raw Data
++++++++++++++++

By default, pre- and post-processing methods receive one object/datum at a time, transparently handling the ``many`` parameter passed to the schema at runtime.

In cases where your pre- and post-processing methods need to receive the raw data passed to the `Schema`, pass ``raw=True`` to the method decorators. The method will receive the raw input data (which may be a single datum or a collection) and the boolean value of ``many``.


Example: Enveloping
+++++++++++++++++++

One common use case is to wrap data in a namespace upon serialization and unwrap the data during deserialization.

.. code-block:: python
    :emphasize-lines: 12,13,17,18

    from marshmallow import Schema, fields, pre_load, post_load, post_dump

    class UserSchema(Schema):
        name = fields.Str()
        email = fields.Email()

        @staticmethod
        def get_envelope_key(many):
            """Helper to get the envelope key."""
            return 'users' if many else 'user'

        @pre_load(raw=True)
        def unwrap_envelope(self, data, many):
            key = self.get_envelope_key(many)
            return data[key]

        @post_dump(raw=True)
        def wrap_with_envelope(self, data, many):
            key = self.get_envelope_key(many)
            return {key: data}

        @post_load
        def make_user(self, data):
            return User(**data)

    user_schema = UserSchema()

    user = User('Mick', email='mick@stones.org')
    user_data = user_schema.dump(user).data
    # {'user': {'email': 'mick@stones.org', 'name': 'Mick'}}

    users = [User('Keith', email='keith@stones.org'),
            User('Charlie', email='charlie@stones.org')]
    users_data = user_schema.dump(users, many=True).data
    # {'users': [{'email': 'keith@stones.org', 'name': 'Keith'},
    #            {'email': 'charlie@stones.org', 'name': 'Charlie'}]}

    user_objs = user_schema.load(users_data, many=True).data
    # [<User(name='Keith Richards')>, <User(name='Charlie Watts')>]

A Note About Invocation Order
-----------------------------

You may register multiple processor methods on a a Schema. Keep in mind, however, that **the invocation order of registered processor methods of the same type is not guaranteed**. If you need to guarantee order of processing steps, you should put them in the same method.


.. code-block:: python

    from marshmallow import Schema, fields, pre_load

    # YES
    class MySchema(Schema):
        field_a = fields.Field()

        @pre_load
        def preprocess(self, data):
            step1_data = self.step1(data)
            step2_data = self.step2(data)
            return step2_data

        def step1(self, data):
            # ...

        # Depends on step1
        def step2(self, data):
            # ...

    # NO
    class MySchema(Schema):
        field_a = fields.Field()

        @pre_load
        def step1(self, data):
            # ...

        # Depends on step1
        @pre_load
        def step2(self, data):
            # ...


Handling Errors
---------------

By default, :meth:`Schema.dump` and :meth:`Schema.load` will return validation errors as a dictionary (unless ``strict`` mode is enabled).

You can register a custom error-handling function for a :class:`Schema` using the :meth:`Schema.error_handler` decorator. The function receives the schema instance, the errors dictionary, and the original object to be serialized.


.. code-block:: python

    import logging
    from marshmallow import Schema, fields

    class AppError(Exception):
        pass

    class UserSchema(Schema):
        email = fields.Email()

    # Log and raise our custom exception when serialization
    # or deserialization fails
    @UserSchema.error_handler
    def handle_errors(schema, errors, obj):
        logging.error(errors)
        raise AppError('An error occurred while serializing {0}'.format(obj))

    invalid = User('Foo Bar', email='invalid-email')
    schema = UserSchema()
    schema.dump(invalid)  # raises AppError
    schema.load({'email': 'invalid-email'})  # raises AppError

.. _schemavalidation:

Schema-level Validation
-----------------------

You can register schema-level validation functions for a :class:`Schema` using the :meth:`Schema.validator` decorator. The function receives the schema instance and the input data
as arguments. Schema-level validation errors will be stored on the ``_schema`` key of the errors dictonary.

.. code-block:: python

    from marshmallow import Schema, fields, ValidationError

    class NumberSchema(Schema):
        field_a = fields.Integer()
        field_b = fields.Integer()

    @NumberSchema.validator
    def validate_numbers(schema, input_data):
        if input_data['field_b'] >= input_data['field_a']:
            raise ValidationError('field_a must be greater than field_b')

    schema = NumberSchema()
    result, errors = schema.load({'field_a': 2, 'field_b': 1})
    errors['_schema'] # => ["field_a must be greater than field_b"]


Validating Raw Input Data
+++++++++++++++++++++++++

Normally, unspecified field names are ignored by the validator. If you would like access to the raw input (e.g. to fail validation if an unknown field name is sent), an optional third argument will contain the raw input data.

.. code-block:: python

    @NumberSchema.validator
    def check_unknown_fields(schema, input_data, raw_data):
        for k in raw_data:
            if k not in schema.fields:
                raise ValidationError('Unknown field name')

    schema = NumberSchema()
    result, errors = schema.load({'field_c': 0})
    errors['_schema'] # => ["Unknown field name"]


Storing Errors on Specific Fields
+++++++++++++++++++++++++++++++++

If you want to store schema-level validation errors on a specific field, you can pass a field name (or multiple field names) to the :exc:`ValidationError <marshmallow.exceptions.ValidationError>`.

.. code-block:: python

    @NumberSchema.validator
    def validate_numbers(schema, input_data):
        if input_data['field_b'] >= input_data['field_a']:
            # Store error on field_a
            raise ValidationError('field_a must be greater than field_b', 'field_a')

    schema = NumberSchema()
    result, errors = schema.load({'field_a': 2, 'field_b': 1})
    errors['field_a'] # => ["field_a must be greater than field_b"]

Overriding how attributes are accessed
--------------------------------------

By default, marshmallow uses the `utils.get_value` function to pull attributes from various types of objects for serialization. This will work for *most* use cases.

However, if you want to specify how values are accessed from an object, you can use the :meth:`Schema.accessor` decorator.

.. code-block:: python

    class UserDictSchema(Schema):
        name = fields.Str()
        email = fields.Email()

    # If we know we're only serializing dictionaries, we can
    # override the accessor function
    @UserDictSchema.accessor
    def get_from_dict(schema, key, obj, default=None):
        return obj.get(key, default)


Handler Functions as Class Members
----------------------------------

You can register a Schema's error handler, validators, and accessor as optional class members. This might be useful for defining an abstract `Schema` class.

.. code-block:: python

    class BaseSchema(Schema):
        __error_handler__ = handle_errors  # A function
        __validators__ = [validate_schema]  # List of functions
        __accessor__ = get_from_dict  # A function


Custom "class Meta" Options
---------------------------

``class Meta`` options are a way to configure and modify a :class:`Schema's <Schema>` behavior. See the :class:`API docs <Schema.Meta>` for a listing of available options.

You can add custom ``class Meta`` options by subclassing :class:`SchemaOpts`.

Example: Enveloping, Revisited
++++++++++++++++++++++++++++++

Let's build upon the example above for adding an envelope to serialized output. This time, we will allow the envelope key to be customizable with ``class Meta`` options.

::

    # Example outputs
    {
        'user': {
            'name': 'Keith',
            'email': 'keith@stones.com'
        }
    }
    # List output
    {
        'users': [{'name': 'Keith'}, {'name': 'Mick'}]
    }


First, we'll add our namespace configuration to a custom options class.

.. code-block:: python
    :emphasize-lines: 3

    from marshmallow import Schema, SchemaOpts

    class NamespaceOpts(SchemaOpts):
        """Same as the default class Meta options, but adds "name" and
        "plural_name" options for enveloping.
        """
        def __init__(self, meta):
            SchemaOpts.__init__(self, meta)
            self.name = getattr(meta, 'name', None)
            self.plural_name = getattr(meta, 'plural_name', self.name)


Then we create a custom :class:`Schema` that uses our options class.

.. code-block:: python
    :emphasize-lines: 1,2

    class NamespacedSchema(Schema):
        OPTIONS_CLASS = NamespaceOpts

        @pre_load(raw=True)
        def unwrap_envelope(self, data, many):
            key = self.opts.plural_name if many else self.opts.name
            return {key: data}

        @post_dump(raw=True)
        def wrap_with_envelope(self, data, many):
            key = self.opts.plural_name if many else self.opts.name
            return {key: data}


Our application schemas can now inherit from our custom schema class.

.. code-block:: python
    :emphasize-lines: 1,6,7

    class UserSchema(NamespacedSchema):
        name = fields.String()
        email = fields.Email()

        class Meta:
            name = 'user'
            plural_name = 'users'

    ser = UserSchema()
    user = User('Keith', email='keith@stones.com')
    result = ser.dump(user)
    result.data  # {"user": {"name": "Keith", "email": "keith@stones.com"}}

