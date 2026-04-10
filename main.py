import os
import json
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

district_df = pd.read_csv(os.path.join(BASE_DIR, "district_data.csv"))
stations_df = pd.read_csv(os.path.join(BASE_DIR, "stations.csv"))

with open(os.path.join(BASE_DIR, "almaty.geo.json"), "r", encoding="utf-8") as f:
    geojson_data = json.load(f)

stations_df["latitude"] = pd.to_numeric(stations_df["latitude"], errors="coerce")
stations_df["longitude"] = pd.to_numeric(stations_df["longitude"], errors="coerce")
stations_df = stations_df.dropna(subset=["latitude", "longitude"])

district_name_map = {
    "Almaly": "Алмалинский район",
    "Medeu": "Медеуский район",
    "Bostandyk": "Бостандыкский район",
    "Bostandyq": "Бостандыкский район",
    "Alatau": "Алатауский район",
    "Auezov": "Ауэзовский район",
    "Turksib": "Турксибский район",
    "Nauryzbay": "Наурызбайский район",
    "Zhetysu": "Жетысуский район"
}

reverse_map = {
    "Алмалинский район": "Almaly",
    "Медеуский район": "Medeu",
    "Бостандыкский район": "Bostandyk",
    "Алатауский район": "Alatau",
    "Ауэзовский район": "Auezov",
    "Турксибский район": "Turksib",
    "Наурызбайский район": "Nauryzbay",
    "Жетысуский район": "Zhetysu"
}

for feature in geojson_data.get("features", []):
    props = feature.setdefault("properties", {})
    if "district" not in props or not props["district"]:
        ru_name = props.get("nameRu")
        if ru_name:
            props["district"] = ru_name

district_info = {}
for _, row in district_df.iterrows():
    en_name = str(row["district"]).strip()
    ru_name = district_name_map.get(en_name, en_name)
    district_info[ru_name] = {
        "district_ru": ru_name,
        "district_en": en_name,
        "pollution": int(row["pollution"]) if pd.notna(row["pollution"]) else None,
        "population": int(row["population"]) if pd.notna(row["population"]) else None,
        "schools": int(row["schools"]) if "schools" in row and pd.notna(row["schools"]) else None,
        "hospitals": int(row["hospitals"]) if "hospitals" in row and pd.notna(row["hospitals"]) else None,
        "infrastructure": int(row["infrastructure"]) if "infrastructure" in row and pd.notna(row["infrastructure"]) else None
    }

station_groups = {}
for _, row in stations_df.iterrows():
    en_name = str(row["district"]).strip()
    ru_name = district_name_map.get(en_name, en_name)

    if ru_name not in station_groups:
        station_groups[ru_name] = []

    station_groups[ru_name].append({
        "station_name": str(row["station_name"]),
        "latitude": float(row["latitude"]),
        "longitude": float(row["longitude"]),
        "type": str(row["type"]),
        "district_ru": ru_name,
        "district_en": en_name
    })

geojson_js = json.dumps(geojson_data, ensure_ascii=False)
district_info_js = json.dumps(district_info, ensure_ascii=False)
station_groups_js = json.dumps(station_groups, ensure_ascii=False)

html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Almaty District Monitor</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.css"/>
    <style>
        html, body {{
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
            font-family: Arial, sans-serif;
            background: #f5f7fb;
        }}

        #app {{
            display: flex;
            width: 100%;
            height: 100%;
        }}

        #map {{
            flex: 1;
            height: 100%;
        }}

        #sidebar {{
            width: 340px;
            background: #ffffff;
            box-shadow: -4px 0 16px rgba(0,0,0,0.08);
            padding: 22px 20px;
            box-sizing: border-box;
            overflow-y: auto;
            z-index: 1000;
        }}

        .title {{
            font-size: 24px;
            font-weight: 700;
            margin-bottom: 10px;
            color: #111827;
        }}

        .subtitle {{
            font-size: 14px;
            color: #6b7280;
            margin-bottom: 18px;
        }}

        .card {{
            background: #f8fafc;
            border: 1px solid #e5e7eb;
            border-radius: 16px;
            padding: 16px;
            margin-bottom: 16px;
        }}

        .district-name {{
            font-size: 20px;
            font-weight: 700;
            margin-bottom: 12px;
            color: #111827;
        }}

        .metric {{
            margin-bottom: 10px;
            font-size: 15px;
            color: #1f2937;
        }}

        .metric b {{
            color: #111827;
        }}

        .stations-title {{
            font-size: 16px;
            font-weight: 700;
            margin: 18px 0 10px;
            color: #111827;
        }}

        .station-item {{
            border-bottom: 1px solid #e5e7eb;
            padding: 10px 0;
            font-size: 14px;
            color: #374151;
        }}

        .station-item:last-child {{
            border-bottom: none;
        }}

        .legend {{
            margin-top: 18px;
            font-size: 14px;
            color: #374151;
        }}

        .legend-row {{
            display: flex;
            align-items: center;
            margin-bottom: 8px;
        }}

        .dot {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 10px;
        }}

        .leaflet-tooltip {{
            font-size: 13px;
            padding: 6px 10px;
            border-radius: 8px;
        }}

        .hint {{
            font-size: 14px;
            color: #6b7280;
            line-height: 1.6;
        }}

        .top-btn {{
            margin-top: 10px;
            background: #2563eb;
            color: white;
            border: none;
            border-radius: 10px;
            padding: 10px 14px;
            font-size: 14px;
            cursor: pointer;
        }}

        .top-btn:hover {{
            background: #1d4ed8;
        }}
    </style>
</head>
<body>
<div id="app">
    <div id="map"></div>
    <div id="sidebar">
        <div class="title">Almaty District Monitor</div>
        <div class="subtitle">Интерактивная карта районов и станций</div>

        <div class="card" id="info-card">
            <div class="district-name">Алматы</div>
            <div class="hint">
                Нажми на район на карте.<br>
                Справа покажутся данные района, а на карте останутся только его станции.
            </div>
            <button class="top-btn" onclick="resetView()">Сбросить выбор</button>
        </div>

        <div class="card">
            <div class="stations-title">Легенда</div>
            <div class="legend">
                <div class="legend-row"><span class="dot" style="background:red;"></span>Metro</div>
                <div class="legend-row"><span class="dot" style="background:green;"></span>Air Station</div>
                <div class="legend-row"><span class="dot" style="background:#2563eb;"></span>Выбранный район</div>
            </div>
        </div>

        <div class="card">
            <div class="stations-title">Станции</div>
            <div id="station-list" class="hint">Выбери район</div>
        </div>
    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
const geojsonData = {geojson_js};
const districtInfo = {district_info_js};
const stationGroups = {station_groups_js};

const map = L.map('map', {{
    zoomControl: true
}}).setView([43.2389, 76.8897], 11);

L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors'
}}).addTo(map);

let currentMarkers = [];
let selectedLayer = null;
let allDistrictLayers = [];

function getDefaultStyle() {{
    return {{
        color: '#1f2937',
        weight: 2,
        opacity: 1,
        fillColor: '#93c5fd',
        fillOpacity: 0.12
    }};
}}

function getHighlightStyle() {{
    return {{
        color: '#2563eb',
        weight: 4,
        opacity: 1,
        fillColor: '#60a5fa',
        fillOpacity: 0.22
    }};
}}

function clearMarkers() {{
    for (let i = 0; i < currentMarkers.length; i++) {{
        map.removeLayer(currentMarkers[i]);
    }}
    currentMarkers = [];
}}

function showMarkersForDistrict(districtRu) {{
    clearMarkers();

    const stations = stationGroups[districtRu] || [];
    let bounds = [];

    for (let i = 0; i < stations.length; i++) {{
        const s = stations[i];
        const color = String(s.type).toLowerCase() === 'metro' ? 'red' : 'green';

        const marker = L.circleMarker([s.latitude, s.longitude], {{
            radius: 8,
            color: color,
            fillColor: color,
            fillOpacity: 0.95,
            opacity: 1,
            weight: 2
        }}).bindPopup(
            `<b>${{s.station_name}}</b><br>Type: ${{s.type}}<br>District: ${{s.district_ru}}`
        );

        marker.addTo(map);
        currentMarkers.push(marker);
        bounds.push([s.latitude, s.longitude]);
    }}

    return bounds;
}}

function updatePanel(districtRu) {{
    const data = districtInfo[districtRu];
    const panel = document.getElementById('info-card');
    const stationList = document.getElementById('station-list');

    if (!data) {{
        panel.innerHTML = `
            <div class="district-name">Нет данных</div>
            <div class="hint">Для этого района нет данных в district_data.csv</div>
            <button class="top-btn" onclick="resetView()">Сбросить выбор</button>
        `;
        stationList.innerHTML = 'Нет станций';
        return;
    }}

    panel.innerHTML = `
        <div class="district-name">${{data.district_ru}}</div>
        <div class="metric"><b>Pollution:</b> ${{data.pollution}}</div>
        <div class="metric"><b>Population:</b> ${{data.population}}</div>
        <div class="metric"><b>Schools:</b> ${{data.schools}}</div>
        <div class="metric"><b>Hospitals:</b> ${{data.hospitals}}</div>
        <div class="metric"><b>Infrastructure:</b> ${{data.infrastructure}}</div>
        <button class="top-btn" onclick="resetView()">Сбросить выбор</button>
    `;

    const stations = stationGroups[districtRu] || [];
    if (stations.length === 0) {{
        stationList.innerHTML = 'Нет станций';
    }} else {{
        stationList.innerHTML = stations.map(s => `
            <div class="station-item">
                <b>${{s.station_name}}</b><br>
                Type: ${{s.type}}
            </div>
        `).join('');
    }}
}}

function resetDistrictStyles() {{
    for (let i = 0; i < allDistrictLayers.length; i++) {{
        allDistrictLayers[i].setStyle(getDefaultStyle());
    }}
    selectedLayer = null;
}}

function resetView() {{
    resetDistrictStyles();
    clearMarkers();

    document.getElementById('info-card').innerHTML = `
        <div class="district-name">Алматы</div>
        <div class="hint">
            Нажми на район на карте.<br>
            Справа покажутся данные района, а на карте останутся только его станции.
        </div>
        <button class="top-btn" onclick="resetView()">Сбросить выбор</button>
    `;
    document.getElementById('station-list').innerHTML = 'Выбери район';

    map.setView([43.2389, 76.8897], 11);
}}

const districtLayer = L.geoJSON(geojsonData, {{
    style: function(feature) {{
        return getDefaultStyle();
    }},
    onEachFeature: function(feature, layer) {{
        allDistrictLayers.push(layer);

        const districtRu = feature.properties?.district || feature.properties?.nameRu || feature.properties?.name || 'Unknown';
        const districtLabel = feature.properties?.nameRu || feature.properties?.district || feature.properties?.name || 'Unknown';

        layer.bindTooltip(districtLabel, {{
            sticky: false
        }});

        layer.on('mouseover', function() {{
            if (selectedLayer !== layer) {{
                layer.setStyle({{
                    color: '#2563eb',
                    weight: 3,
                    fillColor: '#93c5fd',
                    fillOpacity: 0.18
                }});
            }}
        }});

        layer.on('mouseout', function() {{
            if (selectedLayer !== layer) {{
                layer.setStyle(getDefaultStyle());
            }}
        }});

        layer.on('click', function() {{
            resetDistrictStyles();
            selectedLayer = layer;
            layer.setStyle(getHighlightStyle());

            updatePanel(districtRu);

            const markerBounds = showMarkersForDistrict(districtRu);

            if (typeof layer.getBounds === 'function') {{
                map.fitBounds(layer.getBounds(), {{padding: [20, 20]}});
            }} else if (markerBounds.length > 0) {{
                map.fitBounds(markerBounds, {{padding: [20, 20]}});
            }}
        }});
    }}
}}).addTo(map);
</script>
</body>
</html>
"""

output_path = os.path.join(BASE_DIR, "final_map.html")
with open(output_path, "w", encoding="utf-8") as f:
    f.write(html)


print(output_path)
