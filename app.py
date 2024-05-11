import os
import zipfile
import tempfile
from flask import Flask, request, jsonify, render_template, send_from_directory, url_for
from werkzeug.utils import secure_filename
import geopandas as gpd
from pyproj import Transformer

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'

# Ensure the upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    # Render the file upload form
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])


def upload():
    # Handle file upload
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    # Securely save the uploaded file
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    # Try to process the shapefile and save the GeoJSON
    try:
        geojson_filename = process_shapefile(filepath)
        geojson_url = url_for('uploaded_file', filename=geojson_filename, _external=True)
        return jsonify({'url': geojson_url, 'filename': filename})  # Include filename in the response

    except Exception as e:
        app.logger.error(f"Failed to process shapefile: {e}")
        return jsonify({'error': str(e)}), 500

def process_shapefile(zip_path):
    with tempfile.TemporaryDirectory() as temp_dir:
        # Extract the ZIP file into the temporary directory
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        # Find the .shp file
        shp_path = None
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.endswith('.shp'):
                    shp_path = os.path.join(root, file)
                    break
            if shp_path:
                break

        if shp_path is None:
            raise Exception('No .shp file found in the uploaded ZIP.')

        # Load the shapefile into a GeoDataFrame
        gdf = gpd.read_file(shp_path)

        # Transform the coordinate system to WGS 84
        if gdf.crs is not None:
            gdf = gdf.to_crs(epsg=4326)  # Transform all coordinates to EPSG:4326
        else:
            transformer = Transformer.from_crs("EPSG:2272", "EPSG:4326", always_xy=True)
            gdf['geometry'] = gdf['geometry'].apply(lambda geom: transform(transformer.transform, geom))

        # Convert to GeoJSON
        geojson = gdf.to_json()

        # Save GeoJSON to a file
        geojson_filename = os.path.splitext(os.path.basename(zip_path))[0] + '.geojson'
        geojson_filepath = os.path.join(app.config['UPLOAD_FOLDER'], geojson_filename)
        with open(geojson_filepath, 'w') as f:
            f.write(geojson)

        return geojson_filename

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    # Serve files from the upload directory
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)



if __name__ == '__main__':
    app.run(debug=True)
