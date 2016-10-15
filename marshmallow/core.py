# -*- coding: utf-8 -*-
from __future__ import absolute_import
import json
from collections import OrderedDict
import copy

from marshmallow import base
from marshmallow.compat import with_metaclass, iteritems


def is_instance_or_subclass(val, class_):
    try:
        return issubclass(val, class_)
    except TypeError:
        return isinstance(val, class_)


def _get_declared_fields(bases, attrs):
    '''Return the declared fields of a class as an OrderedDict.'''
    declared = [(field_name, attrs.pop(field_name))
                for field_name, val in list(iteritems(attrs))
                if is_instance_or_subclass(val, base.Field)]
    # If subclassing another Serializer, inherit its fields
    # Loop in reverse to maintain the correct field order
    for base_class in bases[::-1]:
        if hasattr(base_class, '_base_fields'):
            declared = list(base_class._base_fields.items()) + declared
    return OrderedDict(declared)


class SerializerMeta(type):
    '''Metaclass for the Serializer class. Binds the declared fields to
    a ``_base_fields`` attribute, which is a dictionary mapping attribute
    names to field classes and instances.
    '''

    def __new__(cls, name, bases, attrs):
        attrs['_base_fields'] = _get_declared_fields(bases, attrs)
        return super(SerializerMeta, cls).__new__(cls, name, bases, attrs)


class BaseSerializer(object):
    '''Base serializer class which defines the interface for a serializer.

    :param data: The object, dict, or list to be serialized.
    '''

    def __init__(self, data=None):
        self._data = data
        self.fields = self.get_fields()

    def get_fields(self):
        '''Return the declared fields for the object as an OrderedDict.'''
        base_fields = copy.deepcopy(self._base_fields)
        for field_name, field_obj in iteritems(base_fields):
            if not field_obj.parent:
                field_obj.parent = self
        return base_fields

    @property
    def data(self):
        '''The serialized data as an ``OrderedDict``. Fields are in the order
        in which they are declared.
        '''
        return self.to_data()

    @property
    def json(self):
        '''The data as a JSON string.'''
        return self.to_json()

    def to_data(self, *args, **kwargs):
        return marshal(self._data, self.fields)

    def to_json(self, *args, **kwargs):
        return json.dumps(self.data, *args, **kwargs)



class Serializer(with_metaclass(SerializerMeta, BaseSerializer)):
    '''Base serializer class with which to define custom serializers.

    Example usage:
    ::

        from datetime import datetime
        from marshmallow import Serializer, fields

        class Person(object):
            def __init__(self, name):
                self.name = name
                self.date_born = datetime.now()

        class PersonSerializer(Serializer):
            name = fields.String()
            date_born = fields.DateTime()

        person = Person("Guido van Rossum")
        serialized = PersonSerializer(person)
        serialized.data
        # OrderedDict([('name', u'Guido van Rossum'), ('date_born', 'Sat, 09 Nov 2013 00:10:29 -0000')])
    '''
    pass


def _is_iterable_but_not_string(obj):
    return hasattr(obj, "__iter__") and not hasattr(obj, "strip")


def marshal(data, fields):
    """Takes raw data (in the form of a dict, list, object) and a dict of
    fields to output and filters the data based on those fields.

    :param fields: a dict of whose keys will make up the final serialized
                   response output
    :param data: the actual object(s) from which the fields are taken from

    """
    if _is_iterable_but_not_string(data):
        return [marshal(d, fields) for d in data]
    items = ((k, marshal(data, v) if isinstance(v, dict)
                                  else v.output(k, data))
                                  for k, v in fields.items())
    return OrderedDict(items)
