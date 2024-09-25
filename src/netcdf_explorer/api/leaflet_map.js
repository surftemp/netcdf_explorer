

class LeafletMap {

    constructor(element_id, mouseover_callback, zoom_event_callback) {

        this.mouseover_callback = mouseover_callback;
        this.zoom_event_callback = zoom_event_callback;
        this.opacities = {};

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
                [-1,1],
                [-1,1]
            ]
        };

        this.map = L.map(element_id, mapOptions);

        this.map.on('mousemove', async (e) => {
            let lat = e.latlng.lat;
            let lon = e.latlng.lng;

            if (lat >= -1 && lat <= 1 && lon >= -1 && lon <= 1) {
                await this.mouseover_callback((lat+1)/2,(lon+1)/2);
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


    add_image_layer(layer_name, url) {
        console.log("Add image layer: "+layer_name+" => " + url);
        if (!(layer_name in this.opacities)) {
            this.opacities[layer_name] = 1.0;
        }
        if (layer_name in this.layers) {
            this.layers[layer_name].setUrl(url);
        } else {
            var corner1 = L.latLng(-1, -1);
            var corner2 = L.latLng(1, 1);
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