import geopandas as gpd
import osmnx
import pathlib

data_folder = pathlib.Path(__file__).parent.parent / 'data'

divnum = '3927'

print('Downloading division data...')
divisions_url = 'https://data-phl.opendata.arcgis.com/datasets/160a3665943d4864806d7b1399029a04_0.geojson'
divisions_gdf = gpd.read_file(divisions_url)\
    .query(f'DIVISION_NUM == "{divnum}"')

# Reproject to PA state plane and buffer by a couple meters; without the
# buffer, we end up missing some of the bordering roads. With the buffer we end
# up with little stumps on the ends of some of the streets after clipping, but
# it's an acceptable tradeoff.
divisions_gdf = divisions_gdf.to_crs(32129)
divisions_gdf.geometry = divisions_gdf.geometry.buffer(2)
divisions_gdf = divisions_gdf.to_crs(4326)

# Get the division geometry
division_geom = divisions_gdf.geometry.iloc[0]

# Read roads from OSM
print('Downloading roads from OpenStreetMap...')
osm_features = osmnx\
    .features_from_polygon(division_geom, {'highway': True})\
    .clip(division_geom)

# Drop the "nodes" column, as it's a list and OGR will have problems with it.
osm_features = osm_features.drop('nodes', axis=1)

osm_features.to_file(data_folder / 'div3927-roads.geojson')
