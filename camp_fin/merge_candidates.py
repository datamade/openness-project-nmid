"""
Copyright (c) 2007 Michael Trier

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

Developer's note:
The get_generic_fields and merge_candidates functions were copied from the
merge_model_instances management command from django-extensions. The code
required a small change to work for us, and I didn't want to introduce a large
dependency for two functions. Permalink to source code:
https://github.com/django-extensions/django-extensions/blob/b7dfee0be0c16ba7fca107380f81fc86b6aaaaa8/django_extensions/management/commands/merge_model_instances.py
"""
import sys

from django.apps import apps
from django.contrib.contenttypes.fields import GenericForeignKey


def get_generic_fields():
    """Return a list of all GenericForeignKeys in all models."""
    generic_fields = []
    for model in apps.get_models():
        for field_name, field in model.__dict__.items():
            if isinstance(field, GenericForeignKey):
                generic_fields.append(field)
    return generic_fields


def merge_candidates(primary_object, alias_objects):
    """
    Merge several model instances into one, the `primary_object`.
    Use this function to merge model objects and migrate all of the related
    fields from the alias objects the primary object.
    """
    generic_fields = get_generic_fields()

    # get related fields
    related_fields = list(
        filter(lambda x: x.is_relation is True, primary_object._meta.get_fields())
    )

    many_to_many_fields = list(filter(lambda x: x.many_to_many is True, related_fields))

    related_fields = list(filter(lambda x: x.many_to_many is False, related_fields))

    # Loop through all alias objects and migrate their references to the
    # primary object
    deleted_objects = []
    deleted_objects_count = 0
    for alias_object in alias_objects:
        # Migrate all foreign key references from alias object to primary
        # object.
        for many_to_many_field in many_to_many_fields:
            alias_varname = many_to_many_field.name
            related_objects = getattr(alias_object, f"{alias_varname}_set")
            for obj in related_objects.all():
                try:
                    # Handle regular M2M relationships.
                    getattr(alias_object, alias_varname).remove(obj)
                    getattr(primary_object, alias_varname).add(obj)
                except AttributeError:
                    # Handle M2M relationships with a 'through' model.
                    # This does not delete the 'through model.
                    # TODO: Allow the user to delete a duplicate 'through' model.
                    through_model = getattr(alias_object, alias_varname).through
                    kwargs = {
                        many_to_many_field.m2m_reverse_field_name(): obj,
                        many_to_many_field.m2m_field_name(): alias_object,
                    }
                    through_model_instances = through_model.objects.filter(**kwargs)
                    for instance in through_model_instances:
                        # Re-attach the through model to the primary_object
                        setattr(
                            instance,
                            many_to_many_field.m2m_field_name(),
                            primary_object,
                        )
                        instance.save()
                        # TODO: Here, try to delete duplicate instances that are
                        # disallowed by a unique_together constraint

        for related_field in related_fields:
            if related_field.one_to_many:
                alias_varname = related_field.get_accessor_name()
                related_objects = getattr(alias_object, alias_varname)
                for obj in related_objects.all():
                    field_name = related_field.field.name
                    setattr(obj, field_name, primary_object)
                    obj.save()
            elif related_field.one_to_one or related_field.many_to_one:
                alias_varname = related_field.name
                related_object = getattr(alias_object, alias_varname)
                primary_related_object = getattr(primary_object, alias_varname)
                if primary_related_object is None:
                    setattr(primary_object, alias_varname, related_object)
                    primary_object.save()
                elif related_field.one_to_one:
                    related_object.delete()

        for field in generic_fields:
            filter_kwargs = {}
            filter_kwargs[field.fk_field] = alias_object._get_pk_val()
            filter_kwargs[field.ct_field] = field.get_content_type(alias_object)
            related_objects = field.model.objects.filter(**filter_kwargs)
            for generic_related_object in related_objects:
                setattr(generic_related_object, field.name, primary_object)
                generic_related_object.save()

        if alias_object.id:
            deleted_objects += [alias_object]
            alias_object.delete()
            deleted_objects_count += 1

    return primary_object, deleted_objects, deleted_objects_count
