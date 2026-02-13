from shapely.ops import transform
import pyproj


def detect_crs(file_longitude, file_latitude):
    utm_zone = min(int((file_longitude + 180) / 6) + 1, 60)
    if file_latitude < 0:
        project_crs = f"EPSG:327{utm_zone:02d}"
    else:
        project_crs = f"EPSG:326{utm_zone:02d}"
    print(f"Your UTM Zone is {project_crs}")
    transformer = pyproj.Transformer.from_crs("EPSG:4326", project_crs, always_xy=True)
    return transformer


def get_length_meters(geom, transformer):
    projected = transform(transformer.transform, geom)
    return projected.length
