"""New base serializer class to handle full serialization of model objects."""
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

from django.core.serializers import base


class Serializer(base.Serializer):
    """Serializer for Django models inspired by Ruby on Rails serializer.

    """

    def __init__(self, *args, **kwargs):
        """Declare instance attributes."""
        self.options = None
        self.stream = None
        self.fields = None
        self.excludes = None
        self.relations = None
        self.extras = None
        self.use_natural_keys = None
        self.use_choices = None
        super(Serializer, self).__init__(*args, **kwargs)

    def serialize(self, queryset, **options):
        """Serialize a queryset with the following options allowed:
            fields - list of fields to be serialized. If not provided then all
                fields are serialized.
            excludes - list of fields to be excluded. Overrides ``fields``.
            relations - list of related fields to be fully serialized.
            choices - use choices instead of the value associated
            extras - list of attributes and methods to include.
                Methods cannot take arguments.
        """
        self.options = options
        self.stream = options.pop("stream", StringIO())
        self.fields = options.pop("fields", [])
        self.excludes = options.pop("excludes", [])
        self.relations = options.pop("relations", [])
        self.extras = options.pop("extras", [])
        self.use_choices = options.pop("choices", False)
        self.use_natural_keys = options.pop("use_natural_keys", False)

        already_processed = []
        self.start_serialization()
        for obj in queryset:
            self.start_object(obj)
            # Use the concrete parent class' _meta instead of the object's _meta
            # This is to avoid local_fields problems for proxy models. Refs #17717.
            concrete_class = obj._meta.proxy_for_model or obj.__class__
            for field in concrete_class._meta.local_fields:
                attname = field.attname
                already_processed.append(attname)
                if field.serialize:
                    if field.rel is None:
                        if attname not in self.excludes:
                            if not self.fields or attname in self.fields:
                                self.handle_field(obj, field)
                    else:
                        if attname[:-3] not in self.excludes:
                            if not self.fields or attname[:-3] in self.fields:
                                self.handle_fk_field(obj, field)
            for field in concrete_class._meta.many_to_many:
                already_processed.append(field.attname)
                if field.serialize:
                    if field.attname not in self.excludes:
                        if not self.fields or field.attname in self.fields:
                            self.handle_m2m_field(obj, field)
            for fname in self.relations:
                if fname in already_processed:
                    continue
                try:
                    field = getattr(obj, fname)
                except:
                    continue
                # optional back-referenced models appear as None field
                if field is None:
                    continue
                field._priv_name = fname
                if (field.__module__ + '.' + field.__class__.__name__
                    == "django.db.models.fields.related.RelatedManager"):
                    if len(field.get_query_set()) == 0:
                        continue
                    self.handle_m2m_field(obj, field)
                else:
                    self.handle_fk_field(obj, field)

            for extra in self.extras:
                self.handle_extra_field(obj, extra)
            self.end_object(obj)
        self.end_serialization()
        return self.getvalue()

    def handle_extra_field(self, obj, extra):
        """Called to handle 'extras' field serialization."""
        raise NotImplementedError
