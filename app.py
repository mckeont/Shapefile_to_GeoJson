import os
import zipfile
import tempfile
from flask import Flask, request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename
import geopandas as gpd

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'

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

    # Try to process the shapefile and return the GeoJSON
    try:
        geojson = process_shapefile(filepath)
        return jsonify(geojson)
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
            return {'error': 'No .shp file found'}

        # Print out the shapefile path for debugging (you can remove this in production)
        print(f"Shapefile path: {shp_path}")

        # Load the shapefile into a GeoDataFrame
        try:
            gdf = gpd.read_file(shp_path)
            # Print the GeoDataFrame for debugging (you can remove this in production)
            print(gdf)
        except Exception as e:
            print(f"Error loading shapefile: {e}")  # Replace print with logging in production
            return {'error': str(e)}

        # Convert to GeoJSON
        try:
            geojson = gdf.to_json()
            # Print the GeoJSON for debugging (you can remove this in production)
            print(geojson)
            return geojson
        except Exception as e:
            print(f"Error converting to GeoJSON: {e}")  # Replace print with logging in production
            return {'error': str(e)}

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    # Serve files from the upload directory
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
