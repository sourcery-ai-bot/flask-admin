from wtforms import form, __version__ as wtforms_version
from wtforms.fields.core import UnboundField
from flask_admin.babel import Translations

from .fields import *  # noqa: F403,F401
from .widgets import *  # noqa: F403,F401
from .upload import *  # noqa: F403,F401


class BaseForm(form.Form):
    _translations = Translations()

    def __init__(self, formdata=None, obj=None, prefix=u'', **kwargs):
        self._obj = obj

        super(BaseForm, self).__init__(formdata=formdata, obj=obj, prefix=prefix, **kwargs)

    def _get_translations(self):
        return self._translations


class FormOpts(object):
    __slots__ = ['widget_args', 'form_rules']

    def __init__(self, widget_args=None, form_rules=None):
        self.widget_args = widget_args or {}
        self.form_rules = form_rules


def recreate_field(unbound):
    """
        Create new instance of the unbound field, resetting wtforms creation counter.

        :param unbound:
            UnboundField instance
    """
    if not isinstance(unbound, UnboundField):
        raise ValueError(
            f'recreate_field expects UnboundField instance, {type(unbound)} was passed.'
        )


    return unbound.field_class(*unbound.args, **unbound.kwargs)


if int(wtforms_version[0]) > 1:
    # only WTForms 2+ has built-in CSRF functionality
    from os import urandom
    from flask import session, current_app
    from wtforms.csrf.session import SessionCSRF
    from flask_admin._compat import text_type

    class SecureForm(BaseForm):
        """
            BaseForm with CSRF token generation and validation support.

            Requires WTForms 2+
        """
        class Meta:
            csrf = True
            csrf_class = SessionCSRF
            _csrf_secret = urandom(24)

            @property
            def csrf_secret(self):
                secret = current_app.secret_key or self._csrf_secret
                if isinstance(secret, text_type):
                    secret = secret.encode('utf-8')
                return secret

            @property
            def csrf_context(self):
                return session
else:
    class SecureForm(BaseForm):
        def __init__(self, *args, **kwargs):
            raise Exception("SecureForm requires WTForms 2+")
