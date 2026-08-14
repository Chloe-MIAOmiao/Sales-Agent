from pathlib import Path

from fastapi.templating import Jinja2Templates
from jinja2 import pass_context

from app.config import BASE_DIR
from app.i18n import DEFAULT_LANG, SUPPORTED, get_lang, t as _t

templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))


@pass_context
def t(context, key, lang=None):
    lang = lang or context.get("lang", DEFAULT_LANG)
    return _t(key, lang)


templates.env.filters["t"] = t
templates.env.globals["t"] = t

_original = templates.TemplateResponse


def template_response(request, name, context=None, **kw):
    context = dict(context or {})
    context.setdefault("lang", get_lang(request))
    context.setdefault("SUPPORTED", SUPPORTED)
    return _original(request, name, context, **kw)


templates.TemplateResponse = template_response
