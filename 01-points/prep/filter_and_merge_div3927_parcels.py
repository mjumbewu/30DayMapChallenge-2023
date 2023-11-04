"""
Parcels from PWD Stormwater Billing Parcels on OpenDataPhilly
https://opendataphilly.org/datasets/pwd-stormwater-billing-parcels/

Divisions from Political Ward Divisions on OpenDataPhilly
https://opendataphilly.org/datasets/political-ward-divisions/

Division properties used:
- DIVISION_NUM (four-digit ward/division pair)
"""

import contextlib
import json
import pathlib
import requests
import shapely
import shapely.geometry
import time

divnum = '3927'
BoundingBox = tuple[float, float, float, float]


def bounds_intersect(b1: BoundingBox, b2: BoundingBox) -> bool:
    min_x1, min_y1, max_x1, max_y1 = b1
    min_x2, min_y2, max_x2, max_y2 = b2

    return (
        min_x1 <= max_x2 and
        min_x2 <= max_x1 and
        min_y1 <= max_y2 and
        min_y2 <= max_y1
    )


@contextlib.contextmanager
def timer():
    t1 = time.perf_counter()
    t2 = None
    yield lambda: (t2 or time.perf_counter()) - t1
    t2 = time.perf_counter()


def main():
    print('Downloading division data...')
    divisions_url = 'https://data-phl.opendata.arcgis.com/datasets/160a3665943d4864806d7b1399029a04_0.geojson'
    response = requests.get(divisions_url)
    divisions_data = response.json()

    # Load the geometry for the given division number
    print(f'Loading the geometry for division {divnum}...')

    with timer() as get_elapsed_time:
        for feature in divisions_data['features']:
            if feature['properties']['DIVISION_NUM'] == divnum:
                break
        else:
            raise Exception(f'Division {divnum} not found.')

        division_geom = shapely.geometry.shape(feature['geometry'])
        division_bbox = division_geom.bounds

    print(f'Took {get_elapsed_time():0.2f} seconds')
    print()

    print('Downloading parcel data...')
    parcels_url = 'https://opendata.arcgis.com/datasets/84baed491de44f539889f2af178ad85c_0.geojson'
    response = requests.get(parcels_url)
    parcels_data = response.json()

    # Load the parcels within the division
    print(f'Loading the parcels within division {divnum}...')

    with timer() as get_elapsed_time:
        # The following loop could probably be sped up using the RTree library
        # (https://github.com/Toblerity/rtree), but as it is, it only takes 17
        # seconds on my computer (23 seconds without the bounding box checks
        # first), and only needs to be run once. Not a high priority to
        # optimize.

        parcel_geoms: list[shapely.Geometry] = []
        for feature in parcels_data['features']:
            try:
                parcel_geom = shapely.geometry.shape(feature['geometry'])
                parcel_bbox = parcel_geom.bounds

            # The FeatureCollection may contain features that are null (None),
            # so we may get an AttributeError when trying to convert to a
            # geometry.
            except AttributeError:
                continue

            if (
                bounds_intersect(division_bbox, parcel_bbox) and
                division_geom.contains(parcel_geom)
            ):
                parcel_geoms.append(parcel_geom)

    print(f'Took {get_elapsed_time():0.2f} seconds')
    print()

    print('Outputting new composit parcel file...')
    composite_parcel_geom = shapely.union_all(parcel_geoms)
    data_folder = pathlib.Path(__file__).parent.parent / 'data'

    with (data_folder / 'div3927-footprints.geojson').open('w') as outfile:
        composite_parcel_data = shapely.geometry.mapping(composite_parcel_geom)
        json.dump(composite_parcel_data, outfile)


if __name__ == '__main__':
    main()
