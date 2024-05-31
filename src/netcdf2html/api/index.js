
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
      cb_elt.addEventListener("change", create_month_filter_callback(month));
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
   show_filters.addEventListener("input", (evt) => {
      let s = "none";
      if (evt.target.checked) {
         s = "block";
      }
      filter_container.style.display = s;
   });


   let zoom_control = document.getElementById("zoom_control");

   function set_zoom() {
      let zoom = Number.parseInt(zoom_control.value);
      layer_list.forEach(layer => {
         let img = document.getElementById(layer.name);
         img.width = Math.round(Math.sqrt(zoom)*image_width);
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
}

function setup_drag(elt, header_elt) {
  var startx, starty, dx, dy;

  var top = elt.offsetTop;
  var left = elt.offsetLeft;

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
   setup_drag(document.getElementById("layer_container"),document.getElementById("layer_container_header"));
   setup_drag(document.getElementById("filter_container"),document.getElementById("filter_container_header"));
});
