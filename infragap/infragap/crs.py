import logging

from shapely.ops import transform
import pyproj

logger = logging.getLogger(__name__)


def detect_crs(longitude, latitude):
    utm_zone = min(int((longitude + 180) / 6) + 1, 60)
    epsg = f"EPSG:{'326' if latitude >= 0 else '327'}{utm_zone:02d}"
    logger.info("UTM zone: %s", epsg)
    return pyproj.Transformer.from_crs("EPSG:4326", epsg, always_xy=True)


def get_length_meters(geom, transformer):
    return transform(transformer.transform, geom).length
