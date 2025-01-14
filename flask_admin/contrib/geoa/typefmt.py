from flask_admin.contrib.sqla.typefmt import DEFAULT_FORMATTERS as BASE_FORMATTERS
from markupsafe import Markup
from wtforms.widgets import html_params
from geoalchemy2.shape import to_shape
from geoalchemy2.elements import WKBElement
from sqlalchemy import func


def geom_formatter(view, value):
    params = html_params(**{
        "data-role": "leaflet",
        "disabled": "disabled",
        "data-width": 100,
        "data-height": 70,
        "data-geometry-type": to_shape(value).geom_type,
        "data-zoom": 15,
        "data-tile-layer-url": view.tile_layer_url,
        "data-tile-layer-attribution": view.tile_layer_attribution
    })

    if value.srid == -1:
        value.srid = 4326

    geojson = view.session.query(view.model).with_entities(func.ST_AsGeoJSON(value)).scalar()
    return Markup(f'<textarea {params}>{geojson}</textarea>')


DEFAULT_FORMATTERS = BASE_FORMATTERS.copy()
DEFAULT_FORMATTERS[WKBElement] = geom_formatter
