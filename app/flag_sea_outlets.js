const Database = require('better-sqlite3');
const https = require('https');
const path = require('path');

const dbPath = path.join(__dirname, 'data', 'outlets.db');
const db = new Database(dbPath);

try {
  db.exec('ALTER TABLE outlets ADD COLUMN in_sea INTEGER DEFAULT 0');
} catch (e) {
  // column already exists
}

// Ray-casting algorithm for point in polygon
function pointInPolygon(point, vs) {
    let x = point[0], y = point[1];
    let inside = false;
    for (let i = 0, j = vs.length - 1; i < vs.length; j = i++) {
        let xi = vs[i][0], yi = vs[i][1];
        let xj = vs[j][0], yj = vs[j][1];
        let intersect = ((yi > y) != (yj > y))
            && (x < (xj - xi) * (y - yi) / (yj - yi) + xi);
        if (intersect) inside = !inside;
    }
    return inside;
}

console.log("Downloading Sri Lanka GeoJSON...");
https.get('https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson', (res) => {
    let data = '';
    res.on('data', chunk => { data += chunk; });
    res.on('end', () => {
        const geo = JSON.parse(data);
        const sl = geo.features.find(f => f.properties.ISO_A3 === 'LKA' || f.properties.ADMIN === 'Sri Lanka' || f.properties.name === 'Sri Lanka');
        if (!sl) { console.error("Sri Lanka not found in GeoJSON!"); return; }
        const polygons = sl.geometry.type === 'MultiPolygon' ? sl.geometry.coordinates : [sl.geometry.coordinates];
        
        const outlets = db.prepare('SELECT outlet_id, longitude, latitude FROM outlets').all();
        let seaOutlets = [];
        
        console.log("Checking outlets against coastline...");
        for (let row of outlets) {
            let inLand = false;
            for (let poly of polygons) {
                // poly[0] is the outer ring
                if (pointInPolygon([row.longitude, row.latitude], poly[0])) {
                    inLand = true;
                    break;
                }
            }
            if (!inLand) {
                seaOutlets.push(row.outlet_id);
            }
        }
        
        console.log(`Found ${seaOutlets.length} outlets in the sea.`);
        
        // Reset all first
        db.prepare('UPDATE outlets SET in_sea = 0').run();
        
        if (seaOutlets.length > 0) {
            const stmt = db.prepare('UPDATE outlets SET in_sea = 1 WHERE outlet_id = ?');
            const updateMany = db.transaction((ids) => {
                for (const id of ids) stmt.run(id);
            });
            updateMany(seaOutlets);
            console.log('Database updated successfully.');
        }
        db.close();
    });
}).on('error', (e) => {
    console.error(e);
});
