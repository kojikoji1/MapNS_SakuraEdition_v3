from flask import Flask, request, render_template, redirect, url_for, send_from_directory, session
import os, csv
from PIL import Image
import exifread

app = Flask(__name__)
app.secret_key = 'secret_key_for_session'
app.config['UPLOAD_FOLDER'] = 'uploads'
DATA_FILE = 'data/sakura_posts.csv'

def get_gps_and_date(file_path):
    with open(file_path, 'rb') as f:
        tags = exifread.process_file(f)
    try:
        lat = tags['GPS GPSLatitude']
        lon = tags['GPS GPSLongitude']
        lat_ref = tags['GPS GPSLatitudeRef'].values
        lon_ref = tags['GPS GPSLongitudeRef'].values
        date = tags.get('EXIF DateTimeOriginal', None)
        def conv(val):
            d, m, s = [float(x.num) / float(x.den) for x in val.values]
            return d + m / 60 + s / 3600
        latitude = conv(lat)
        longitude = conv(lon)
        if lat_ref != 'N':
            latitude = -latitude
        if lon_ref != 'E':
            longitude = -longitude
        return latitude, longitude, str(date)
    except:
        return None, None, None

@app.route('/', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        session['name'] = name
        return redirect(url_for('map_view'))
    return render_template('register.html')

@app.route('/map', methods=['GET', 'POST'])
def map_view():
    name = session.get('name')
    message = None
    if not name:
        return redirect(url_for('register'))

    if request.method == 'POST':
        if 'delete' in request.form:
            filename = request.form['delete']
            input_name = request.form.get('confirm_name')
            rows = []
            removed = False
            if os.path.exists(DATA_FILE):
                with open(DATA_FILE, newline='', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    for row in reader:
                        if row[1] == filename and row[0] == input_name:
                            removed = True
                            if os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], filename)):
                                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                        else:
                            rows.append(row)
                with open(DATA_FILE, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerows(rows)
                if not removed:
                    message = "名前が一致しません。削除できませんでした。"
                return redirect(url_for('map_view'))

        file = request.files.get('photo')
        comment = request.form.get('comment')
        if file:
            filename = file.filename
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)
            lat, lon, date = get_gps_and_date(save_path)
            if lat and lon:
                with open(DATA_FILE, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow([name, filename, comment, lat, lon, date])
                return redirect(url_for('map_view'))
            else:
                message = "※ 位置情報がありませんでした。"

    markers = []
    contributors = set()
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 6:
                    contributors.add(row[0])
                    if row[3] and row[4]:
                        markers.append({
                            'filename': row[1],
                            'comment': row[2],
                            'lat': float(row[3]),
                            'lon': float(row[4]),
                            'date': row[5]
                        })
    return render_template('map_view.html', markers=markers, name=name, contributors=sorted(contributors), message=message)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
