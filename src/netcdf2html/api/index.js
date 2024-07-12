
var di = null;

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
            console.log("pre:"+this.zoom+","+x+","+y);
            x = Math.round(x/this.zoom);
            y = Math.round(y/this.zoom);
            console.log("post:"+this.zoom+","+x+","+y);
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

let time_index = [];

let current_index = 0;

let layer_opacities = {};

let months_excluded = {};

function update_time_range() {
   let time_range = document.getElementById("time_index");
   if (time_index.length) {
      time_range.value = String(100 * (current_index / (time_index.length - 1)));
   } else {
      time_range.value = "50";
   }
}

function update_filters() {
   current_index = 0;
   time_index = [];
   for(let idx=0; idx<all_time_index.length; idx++) {
      let item = all_time_index[idx];
      let month = Number.parseInt(item.timestamp.slice(5,7));
      if (!(month in months_excluded)) {
         time_index.push(item);
      }
   }
   update_time_range();
   show();
}

function create_month_filter_callback(month) {
   return (evt) => {
      if (!evt.target.checked) {
         months_excluded[month] = true;
      } else {
         delete months_excluded[month];
      }
      update_filters();
   }
}

function create_opacity_callback(for_img, layer_name) {
   return (evt) => {
      layer_opacities[layer_name] = Number.parseFloat(evt.target.value) / 100;
      for_img.style.opacity = layer_opacities[layer_name];
   }
}

function show() {
   let scene_label_elt = document.getElementById("scene_label");

   for(let idx=0; idx<time_index.length; idx++) {
      if (idx === current_index) {
         let image_srcs = time_index[idx].image_srcs;
         for(let layer_name in image_srcs) {
            let img = document.getElementById(layer_name);
            img.src = image_srcs[layer_name];
         }
         let data_srcs = time_index[idx].data_srcs;
         if (di) {
             di.unbind_tooltips();
         }
         di = new DataImage("viridis");
         let zoom_control = document.getElementById("zoom_control");
         let zoom = Number.parseInt(zoom_control.value);
         zoom = Math.sqrt(zoom);
         di.set_zoom(zoom);
         for(let layer_name in data_srcs) {
             di.load(layer_name, data_srcs[layer_name]);
         }
         let idiv = document.getElementById("image_div");
         // pass in img padding+margin as the x and y offsets to binding tooltips
         di.bind_tooltips_to_img(idiv, 6, 6);
      }
   }

   let label = "0/0";
   if (time_index.length) {
      label = "(" + (current_index + 1) + "/" + time_index.length + ") " + time_index[current_index].timestamp;
   }
   scene_label_elt.innerHTML = label;
}

function boot() {

   let next_button = document.getElementById("next_btn");
   let time_range= document.getElementById("time_index");
   let prev_button = document.getElementById("prev_btn");

   let overlay_container = document.getElementById("overlay_container");
   let grid_container = document.getElementById("grid_container");

   let grid_view_button = document.getElementById("grid_view_btn");
   grid_view_button.addEventListener("click", (evt) => {
      overlay_container.style.display = "none";
      grid_container.style.display = "block";
   });

   let overlay_view_button = document.getElementById("overlay_view_btn");
   overlay_view_button.addEventListener("click", (evt) => {
      grid_container.style.display = "none";
      overlay_container.style.display = "block";
   });

   next_button.addEventListener("click", (evt) => {
      if (current_index < time_index.length-1) {
         current_index += 1;
         update_time_range();
         show();
      }
   });

   prev_button.addEventListener("click", (evt) => {
      if (current_index > 0) {
         current_index -= 1;
         update_time_range();
         show();
      }
   });
   time_range.addEventListener("input", (evt) => {
      if (time_index.length) {
         let fraction = Number.parseFloat(evt.target.value) / 100;
         current_index = Math.round(fraction * (time_index.length - 1));
         show();
      }
   });

   update_filters();
   update_time_range();
   show();

   for(let month=1; month<=12; month+=1) {
      let cb_elt = document.getElementById("month"+month);
      if (cb_elt) {
         cb_elt.addEventListener("change", create_month_filter_callback(month));
      }
   }

   layer_list.forEach(layer => {
      let opacity = (layer.name in layer_opacities) ? layer_opacities[layer.name] : 1.0;
      let img = document.getElementById(layer.name);
      img.style.opacity = opacity;
      let r = document.getElementById(layer.opacity_control_id);
      r.value = String(100 * opacity);
      r.addEventListener("input", create_opacity_callback(img, layer.name));
   });

   let show_layers = document.getElementById("show_layers");
   let layer_container = document.getElementById("layer_container");
   show_layers.addEventListener("input", (evt) => {
      let s = "none";
      if (evt.target.checked) {
         s = "block";
      }
      layer_container.style.display = s;
   });

   let show_filters = document.getElementById("show_filters");
   let filter_container = document.getElementById("filter_container");
   if (filter_container) {
      show_filters.addEventListener("input", (evt) => {
         let s = "none";
         if (evt.target.checked) {
            s = "block";
         }
         filter_container.style.display = s;
      });
   }

   let zoom_control = document.getElementById("zoom_control");

   function set_zoom() {
      let zoom = Number.parseInt(zoom_control.value);
      zoom = Math.sqrt(zoom);
      layer_list.forEach(layer => {
         let img = document.getElementById(layer.name);
         img.width = Math.round(zoom*image_width);
         if (di) {
             di.set_zoom(zoom);
         }
      });
   }
   zoom_control.addEventListener("input", (evt) => {
      set_zoom();
   });
   set_zoom();

   let close_all_btn = document.getElementById("close_all_sliders");
   close_all_btn.addEventListener("click", (evt) => {
      layer_list.forEach(layer => {
         layer_opacities[layer.name] = 0.0;
         let img = document.getElementById(layer.name);
         img.style.opacity = 0.0;
         let r = document.getElementById(layer.opacity_control_id);
         r.value = "0";
      });
   });

   const params = new URLSearchParams(window.location.search);
   if (params.has('initial_view')) {
      const initial_view = params.get('initial_view');
      if (initial_view=='overlay') {
         grid_container.style.display = "none";
         overlay_container.style.display = "block";
      }
      if (initial_view=='grid') {
         grid_container.style.display = "block";
         overlay_container.style.display = "none";
      }
   }

   const make_hide_column_callback = (col_id) => {
      return () => {
         document.getElementById(col_id).style.visibility = "collapse";
      }
   }

   layer_list.forEach(layer => {
      let col_id = layer.name+"_col";
      let hide_btn = layer.name+"_hide";
      document.getElementById(hide_btn).addEventListener("click", make_hide_column_callback(col_id));
   });
}


function setup_drag(elt, header_elt, initial_top, initial_left) {
  var startx, starty, dx, dy;

  elt.style.top = initial_top+"px";
  elt.style.left = initial_left+"px";

  var top = initial_top;
  var left = initial_left;

  header_elt.onmousedown = start_drag;

  function start_drag(e) {
    e.preventDefault();
    startx = e.clientX;
    starty = e.clientY;
    document.onmouseup = close_drag;
    document.onmousemove = move_drag;
  }

  function move_drag(e) {
    e.preventDefault();

    dx = startx - e.clientX;
    dy = starty - e.clientY;
    startx = e.clientX;
    starty = e.clientY;

    top = top - dy;
    left = left - dx;

    elt.style.top = top + "px";
    elt.style.left = left + "px";
  }

  function close_drag() {
    document.onmouseup = null;
    document.onmousemove = null;
  }
}

window.addEventListener("load", (ect) => {
   boot();
   setup_drag(document.getElementById("layer_container"),document.getElementById("layer_container_header"), 400, 400);
   let filter_container = document.getElementById("filter_container");
   if (filter_container) {
      setup_drag(filter_container,document.getElementById("filter_container_header"), 200, 400);
   }
});
