import mongoengine

from flask_admin._compat import string_types, as_unicode, iteritems
from flask_admin.model.ajax import AjaxModelLoader, DEFAULT_PAGE_SIZE


class QueryAjaxModelLoader(AjaxModelLoader):
    def __init__(self, name, model, **options):
        """
            Constructor.

            :param fields:
                Fields to run query against
        """
        super(QueryAjaxModelLoader, self).__init__(name, options)

        self.model = model
        self.fields = options.get('fields')

        self._cached_fields = self._process_fields()

        if not self.fields:
            raise ValueError(
                f'AJAX loading requires `fields` to be specified for {model}.{self.name}'
            )

    def _process_fields(self):
        remote_fields = []

        for field in self.fields:
            if isinstance(field, string_types):
                attr = getattr(self.model, field, None)

                if not attr:
                    raise ValueError(f'{self.model}.{field} does not exist.')

                remote_fields.append(attr)
            else:
                remote_fields.append(field)

        return remote_fields

    def format(self, model):
        return (as_unicode(model.pk), as_unicode(model)) if model else None

    def get_one(self, pk):
        return self.model.objects.filter(pk=pk).first()

    def get_list(self, term, offset=0, limit=DEFAULT_PAGE_SIZE):
        query = self.model.objects

        if len(term) > 0:
            criteria = None

            for field in self._cached_fields:
                flt = {f'{field.name}__icontains': term}

                if not criteria:
                    criteria = mongoengine.Q(**flt)
                else:
                    criteria |= mongoengine.Q(**flt)

            query = query.filter(criteria)

        if offset:
            query = query.skip(offset)

        return query.limit(limit).all()


def create_ajax_loader(model, name, field_name, opts):
    prop = getattr(model, field_name, None)

    if prop is None:
        raise ValueError(f'Model {model} does not have field {field_name}.')

    ftype = type(prop).__name__

    if ftype in ['ListField', 'SortedListField']:
        prop = prop.field
        ftype = type(prop).__name__

    if ftype != 'ReferenceField':
        raise ValueError(f'Dont know how to convert {ftype} type for AJAX loader')

    remote_model = prop.document_type
    return QueryAjaxModelLoader(name, remote_model, **opts)


def process_ajax_references(references, view):
    def make_name(base, name):
        return f'{base}-{name}'.lower() if base else as_unicode(name).lower()

    def handle_field(field, subdoc, base):
        ftype = type(field).__name__

        if ftype in ['ListField', 'SortedListField']:
            if child_doc := getattr(subdoc, '_form_subdocuments', {}).get(None):
                handle_field(field.field, child_doc, base)
        elif ftype == 'EmbeddedDocumentField':
            result = {}

            ajax_refs = getattr(subdoc, 'form_ajax_refs', {})

            for field_name, opts in iteritems(ajax_refs):
                child_name = make_name(base, field_name)

                if isinstance(opts, dict):
                    loader = create_ajax_loader(field.document_type_obj, child_name, field_name, opts)
                else:
                    loader = opts

                result[field_name] = loader
                references[child_name] = loader

            subdoc._form_ajax_refs = result

            if child_doc := getattr(subdoc, '_form_subdocuments', None):
                handle_subdoc(field.document_type_obj, subdoc, base)
        else:
            raise ValueError(f'Failed to process subdocument field {field}')

    def handle_subdoc(model, subdoc, base):
        documents = getattr(subdoc, '_form_subdocuments', {})

        for name, doc in iteritems(documents):
            field = getattr(model, name, None)

            if not field:
                raise ValueError(f'Invalid subdocument field {model}.{name}')

            handle_field(field, doc, make_name(base, name))

    handle_subdoc(view.model, view, '')

    return references
