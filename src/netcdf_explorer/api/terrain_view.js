class TerrainView {

    constructor(data_image, elevation_band, image_url, terrain_zoom) {
        this.data_image = data_image;
        this.elevation_band = elevation_band;
        this.image_url = image_url;
        this.canvas = null;
        this.scene = null;
        this.engine = null;
        this.terrain_zoom = terrain_zoom;
    }

    set_terrain_zoom(terrain_zoom) {
        this.terrain_zoom = terrain_zoom;
        this.close();
        this.open();
    }

    open() {
        this.canvas = document.getElementById("render_canvas");
        this.engine = new BABYLON.Engine(this.canvas, true);
        var createScene = () => {
            // prepare the data

            var mapSubX = this.data_image.get_width();
            var mapSubZ = this.data_image.get_height();

            var mapData = new Float32Array(mapSubX * mapSubZ * 3);

            var paths = [];
            let min_y = null;
            let max_y = null;
            // x/z scale is 25m per pixel
            // allow the y scale to zoom the terrain
            let y_scale = 25 / this.terrain_zoom;
            for (var l = 0; l < mapSubZ; l++) {
                var path = [];
                for (var w = 0; w < mapSubX; w++) {
                    var x = (w - mapSubX * 0.5) * 2.0;
                    var z = (l - mapSubZ * 0.5) * 2.0;
                    var y = this.data_image.get_data(this.elevation_band, w, mapSubZ-(l+1)) / y_scale;
                    if (min_y === null || min_y > y) {
                        min_y = y;
                    }

                    if (max_y === null || max_y < y) {
                        max_y = y;
                    }

                    mapData[3 *(l * mapSubX + w)] = x;
                    mapData[3 * (l * mapSubX + w) + 1] = y;
                    mapData[3 * (l * mapSubX + w) + 2] = z;

                    path.push(new BABYLON.Vector3(x, y, z));
                }
                paths.push(path);
            }

            // normalise elevation to start at 0
            for (var l = 0; l < mapSubZ; l++) {
                for (var w = 0; w < mapSubX; w++) {
                    mapData[3 * (l * mapSubX + w) + 1] -= min_y;
                }
            }

            var scene = new BABYLON.Scene(this.engine);
            var camera = new BABYLON.ArcRotateCamera("camera1",  0, 0, 0, BABYLON.Vector3.Zero(), scene);
            // position the camera to the south, looking north initially
            camera.setPosition(new BABYLON.Vector3(0.0, 2*(max_y-min_y), -2*this.data_image.get_height()));
            camera.attachControl(this.canvas, true);

            var light = new BABYLON.HemisphericLight("light1", new BABYLON.Vector3(0.0, 2*(max_y-min_y), 0.0), scene);
            light.intensity = 0.75;
            light.specular = BABYLON.Color3.Black();

            var map = BABYLON.MeshBuilder.CreateRibbon("m", {pathArray: paths, sideOrientation: 2}, scene);
            map.position.y = -1.0;
            var mapMaterial = new BABYLON.StandardMaterial("mm", scene);
            mapMaterial.diffuseTexture = new BABYLON.Texture(this.image_url, scene,  undefined, undefined, BABYLON.Texture.NEAREST_SAMPLINGMODE);

            map.material = mapMaterial;

            return scene;
        }
        this.scene = createScene();

        this.engine.runRenderLoop(() => {
            this.scene.render();
        });

        window.addEventListener("resize", () => {
            this.engine.resize();
        });
    }

    close() {
        this.scene.dispose();
        this.engine.dispose();
        this.canvas = null;
        this.scene = null;
        this.engine = null;
    }
}