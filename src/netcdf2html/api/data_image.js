class DataImage {

    constructor(cmap) {
        this.cmap = cmap;
        this.height = null;
        this.width = null;
        this.data_layers = {};
        this.layer_options = {};
        this.ele = null;
        this.listener = null;
        this.zoom = 1;
    }

    async load(layer_name, data_source) {
        let from_url = data_source.url;
        let options = data_source.options;
        let fetched = await fetch(from_url);
        let blob = await fetched.blob();
        const ds = new DecompressionStream("gzip");
        const decompressedStream = blob.stream().pipeThrough(ds);
        let r = await new Response(decompressedStream).arrayBuffer();
        let dv = new DataView(r);
        this.height = dv.getInt32(0, true);
        this.width = dv.getInt32(4, true);

        let pos = 8;
        let data = [];
        for (let y = 0; y < this.height; y++) {
            let row = [];
            for (let x = 0; x < this.width; x++) {
                let v = dv.getFloat32(pos, true /* littleEndian */);
                row.push(v);
                pos += 4;
            }
            data.push(row);
        }
        this.data_layers[layer_name] = data;
        this.layer_options[layer_name] = options;
    }

    get_height() {
        return this.height;
    }

    get_width() {
        return this.width;
    }

    get_value(layer_name, y, x) {
        return this.data_layers[layer_name][y][x];
    }

    get_legend_url(cmap_name, vmin, vmax, height, width) {
        const canvas = document.createElement("canvas");
        const ctx = canvas.getContext("2d");
        ctx.canvas.width = width;
        ctx.canvas.height = height;

        for(let x=0; x<width; x++) {
            let v = vmin + ((x+0.5)/(width))*(vmax-vmin);
            for(let y=0; y<height; y++) {
                let rgb = this.cmap.get_rgb(cmap_name,vmin,vmax,v);
                ctx.fillStyle="rgb("+255*rgb[0]+","+255*rgb[1]+","+255*rgb[2]+")";
                ctx.fillRect(x,y,1,1);
            }
        }
        return canvas.toDataURL("image/png");
    }

    get_image_url(layer_name, cmap_name, vmin, vmax) {
        const canvas = document.createElement("canvas");
        const ctx = canvas.getContext("2d");
        ctx.canvas.width = this.width;
        ctx.canvas.height = this.height;
        let data = this.data_layers[layer_name];
        for(let y=0; y<this.height; y++) {
            for(let x=0; x<this.width; x++) {
                let v = data[y][x];
                let rgb = this.cmap.get_rgb(cmap_name,vmin,vmax,v);
                ctx.fillStyle="rgb("+255*rgb[0]+","+255*rgb[1]+","+255*rgb[2]+")";
                ctx.fillRect(x,y,1,1);
            }
        }
        return canvas.toDataURL("image/png");
    }

    set_zoom(zoom) {
        console.log("set_zoom:"+zoom);
        this.zoom = zoom;
    }

    unbind_tooltips() {
        if (this.mouseover_listener) {
            this.ele.removeEventListener("mousemove",this.mouseover_listener);
        }
        this.mouseover_listener = null;
        if (this.mouseout_listener) {
            this.ele.removeEventListener("mouseout",this.mouseout_listener);
        }
        this.mouseout_listener = null;
    }

    bind_tooltips_to_img(img_ele, offset_x, offset_y) {
        this.ele = img_ele;
        this.mouseover_listener = (e) => {
            var rect = e.target.getBoundingClientRect();
            var x = Math.floor(e.clientX - rect.left) - offset_x;
            var y = Math.floor(e.clientY - rect.top) - offset_y;
            x = Math.round(x/this.zoom);
            y = Math.round(y/this.zoom);
            if (x < 0) {
                x = 0;
            }
            if (y < 0) {
                y = 0;
            }
            if (x >= this.width) {
                x = this.width-1;
            }
            if (y >= this.height) {
                y = this.height - 1;
            }
            let s = "";
            for(var layer_name in this.data_layers) {
                let v = this.get_value(layer_name, y, x);
                let label = "{value}";
                let fixed = 2;
                if (layer_name in this.layer_options) {
                    let options = this.layer_options[layer_name];
                    if ("label" in options) {
                        label = this.layer_options[layer_name].label;
                    }
                    if ("fixed" in options) {
                        fixed = options.fixed;
                    }
                }

                if (!isNaN(v)) {
                    v = v.toFixed(fixed);
                } else {
                    v = "(missing)";
                }
                s += "<p>"+ label.replace("{value}",v) + "</p>";
            }
            let tooltip = document.getElementById("tooltip");
            tooltip.innerHTML = s;
            tooltip.style.position = "absolute";
            tooltip.style.left = (e.clientX-10)+"px";
            tooltip.style.top = (e.clientY+40)+"px";
            tooltip.style.display = "block";
        };
        img_ele.addEventListener("mousemove",this.mouseover_listener);
        this.mouseout_listener = (e) => {
            let tooltip = document.getElementById("tooltip");
            tooltip.style.display = "none";
        }
        img_ele.addEventListener("mouseout",this.mouseout_listener);
    }
}