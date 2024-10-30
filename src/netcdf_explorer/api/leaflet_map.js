

class LeafletMap {

    constructor(element_id, data_height, data_width, mouseover_callback, zoom_event_callback) {

        this.mouseover_callback = mouseover_callback;
        this.zoom_event_callback = zoom_event_callback;
        this.opacities = {};

        this.min_lat = -1;
        this.max_lat = 1;
        this.min_lon = -(data_width/data_height);
        this.max_lon = (data_width/data_height);

        // Initialize the map.
        const mapOptions = {
            minZoom: 9,
            maxZoom: 20,
            zoomSnap: 0.5,
            zoomDelta: 0.5,
            wheelPxPerZoomLevel: 500,
            center: [1,-1], // why?
            zoom: 9,
            bounds: [
                [this.min_lat,this.min_lon],
                [this.max_lat,this.max_lon]
            ]
        };

        this.map = L.map(element_id, mapOptions);

        this.map.on('mousemove', async (e) => {
            let lat = e.latlng.lat;
            let lon = e.latlng.lng;

            if (lat >= this.min_lat && lat <= this.max_lat && lon >= this.min_lon && lon <= this.max_lon) {
                await this.mouseover_callback((lat+this.max_lat)/(this.max_lat-this.min_lat),(lon+this.max_lon)/(this.max_lon-this.min_lon));
            } else {
                await this.mouseover_callback(null, null);
            }
        });

        this.map.on('mouseout', async (e) => {
            await this.mouseover_callback(null, null);
        });

        this.map.on('zoom', async (e) => {
            this.zoom_event_callback(this.map.getZoom()-8);
        });

        this.layers = {};
    }

    clear_layers() {
        for(let layer_name in this.layers) {
            this.map.removeLayer(this.layers[layer_name]);
        }
        this.layers = {};
    }

    add_image_layer(layer_name, url) {
        console.log("Add image layer: "+layer_name+" => " + url);
        if (!(layer_name in this.opacities)) {
            this.opacities[layer_name] = 1.0;
        }
        if (layer_name in this.layers) {
            this.layers[layer_name].setUrl(url);
        } else {
            var corner1 = L.latLng(this.min_lat, this.min_lon);
            var corner2 = L.latLng(this.max_lat, this.max_lon);
            let bounds = L.latLngBounds(corner1, corner2);
            this.layers[layer_name] = L.imageOverlay(url, bounds, {opacity: this.opacities[layer_name]}).addTo(this.map);
        }
    }

    set_layer_opacity(layer_name, opacity) {
        console.log("Set layer opacity: "+layer_name+" => " + opacity);
        this.opacities[layer_name] = opacity;
        if (layer_name in this.layers) {
            this.layers[layer_name].setOpacity(opacity);
        }
    }
}