
// manage the HTML comprising grid and overlay views
// bind the controls in the views

class HtmlView {

    constructor() {
        this.scenes = {};
        this.index = [];
        this.current_index = 0;
        this.layer_opacities = {};
        this.months_excluded = {};
        this.labels = null;
        this.di = null; // the dataimage used in the overlay view

        // locate overlay controls and other elements
        this.time_range = document.getElementById("time_index");
        this.zoom_control = document.getElementById("zoom_control");
        this.info_content = document.getElementById("info_content"); // optional, may be undefined
        this.show_layers = document.getElementById("show_layers");
        this.layer_container = document.getElementById("layer_container");
        this.next_button = document.getElementById("next_btn");
        this.prev_button = document.getElementById("prev_btn");
        this.close_all_btn = document.getElementById("close_all_sliders");
        this.show_filters = document.getElementById("show_filters");
        this.filter_container = document.getElementById("filter_container");
        this.scene_label_elt = document.getElementById("scene_label");
        this.show_labels = document.getElementById("show_labels");
        this.labels_container = document.getElementById("labels_container");

        this.show_info = document.getElementById("show_info");
        this.info_container = document.getElementById("info_container");

        this.overlay_container = document.getElementById("overlay_container");
        this.grid_container = document.getElementById("grid_container");

        this.grid_view_button = document.getElementById("grid_view_btn");
        this.overlay_view_button = document.getElementById("overlay_view_btn");

        this.grid_label_controls = {}; // label_group => [label_value => label_control]
        this.overlay_label_controls = {}; // label_group => label_value => label_control

        this.download_labels_btn = document.getElementById("download_labels_btn"); // optional, may be undefined

        // record which services are available from the server (by default, none)
        this.services = {};
    }

    async load() {
        // load data files: scenes.json and (optionally) labels.json
        // this needs to be called before init
        let r = await fetch("scenes.json");
        this.scenes = await r.json();

        if (this.download_labels_btn) {
            try {
                r = await fetch("labels.json");
                this.labels = await r.json();
            } catch (e) {
                console.log("No labels could be loaded")
            }
        }

        // initially, include all scenes in the index
        this.index = [];
        for (let idx = 0; idx < this.scenes.index.length; idx++) {
            this.index.push(this.scenes.index[idx]);
        }

        // test to see what services are available (if any)
        try {
            r = await fetch("service_info/services.json");
            this.services = await r.json();
        } catch(e) {

        }
    }

    get_label_control_id(label_group, label_value, index) {
        // obtain the expected id for a label control
        let control_id = "radio_"+label_group+"_"+label_value;
        if (index !== null) {
            control_id += "_" + index;
        }
        return control_id;
    }

    create_overlay_label_control_callback(label_group, label) {
        // create a callback to be called when a label is updated by an overlay label control
        return async () => {
            let index = this.index[this.current_index].pos;
            this.labels.values[label_group][index] = label;
            this.grid_label_controls[label_group][index][label].checked = true;
            await this.notify_label_update(label_group, index, label);
        }
    }

    create_grid_label_control_callback(label_group, label, i) {
        // create a callback to be called when a label is updated by a grid label control
        return async () => {
            this.labels.values[label_group][i] = label;
            if (i === this.current_index) {
                this.overlay_label_controls[label_group][label].checked = true;
            }
            await this.notify_label_update(label_group, i, label);
        }
    }

    async notify_label_update(label_group, i, label) {
        // notify the server (if this service is supported) of the label update
        if ("labels" in this.services) {
            await fetch("/label/"+label_group+"/"+i+"/"+label, { "method":"POST"});
        }
    }

    create_open_callback(index) {
        // create a callback to open a particular scene in the overlay view
        return (evt) => {
            this.current_index = index;
            this.grid_container.style.display = "none";
            this.overlay_container.style.display = "block";
            this.update_time_range();
            this.show();
        }
    }

    init() {
        // initialise the view, to be called once load has completed
        // bind to the controls in this page

        const params = new URLSearchParams(window.location.search);

        this.grid_view_button.addEventListener("click", (evt) => {
            this.overlay_container.style.display = "none";
            this.grid_container.style.display = "block";
        });

        this.overlay_view_button.addEventListener("click", (evt) => {
            this.grid_container.style.display = "none";
            this.overlay_container.style.display = "block";
        });

        this.next_button.addEventListener("click", (evt) => {
            if (this.current_index < this.index.length - 1) {
                this.current_index += 1;
                this.update_time_range();
                this.show();
            }
        });

        this.prev_button.addEventListener("click", (evt) => {
            if (this.current_index > 0) {
                this.current_index -= 1;
                this.update_time_range();
                this.show();
            }
        });

        this.time_range.addEventListener("input", (evt) => {
            if (this.index.length) {
                let fraction = Number.parseFloat(evt.target.value) / 100;
                this.current_index = Math.round(fraction * (this.index.length - 1));
                this.show();
            }
        });

        if (params.has('index')) {
            this.current_index = Number.parseInt(params.get('index'));
        }

        for (let month = 1; month <= 12; month += 1) {
            let cb_elt = document.getElementById("month" + month);
            if (cb_elt) {
                cb_elt.addEventListener("change", this.create_month_filter_callback(month));
            }
        }

        this.scenes.layers.forEach(layer => {
            let opacity = (layer.name in this.layer_opacities) ? this.layer_opacities[layer.name] : 1.0;
            let img = document.getElementById(layer.name);
            img.style.opacity = opacity;
            let r = document.getElementById(layer.name+"_opacity");
            r.value = String(100 * opacity);
            r.addEventListener("input", this.create_opacity_callback(img, layer.name));
        });

        if (this.layer_container && this.show_layers) {
            this.show_layers.addEventListener("input", (evt) => {
                let s = "none";
                if (evt.target.checked) {
                    s = "block";
                }
                this.layer_container.style.display = s;
            });
        }

        if (this.filter_container && this.show_filters) {
            this.show_filters.addEventListener("input", (evt) => {
                let s = "none";
                if (evt.target.checked) {
                    s = "block";
                }
                this.filter_container.style.display = s;
            });
        }

        if (this.info_container && this.show_info) {
            this.show_info.addEventListener("input", (evt) => {
                let s = "none";
                if (evt.target.checked) {
                    s = "block";
                }
                this.info_container.style.display = s;
            });
        }

        if (this.labels_container && this.show_labels) {
            this.show_labels.addEventListener("input", (evt) => {
                let s = "none";
                if (evt.target.checked) {
                    s = "block";
                }
                this.labels_container.style.display = s;
            });
        }

        this.zoom_control.addEventListener("input", (evt) => {
            this.set_zoom();
        });
        this.set_zoom();

        this.close_all_btn.addEventListener("click", (evt) => {
            this.scenes.layers.forEach(layer => {
                this.layer_opacities[layer.name] = 0.0;
                let img = document.getElementById(layer.name);
                img.style.opacity = 0.0;
                let r = document.getElementById(layer.name+"_opacity");
                r.value = "0";
            });
        });

        // work out whether to start in grid or overlay view
        let view = "grid";
        if (params.has('view')) {
            view = params.get('view');
        }

        if (view === 'overlay') {
            grid_container.style.display = "none";
            overlay_container.style.display = "block";
        }

        if (view === 'grid') {
            grid_container.style.display = "block";
            overlay_container.style.display = "none";
        }

        const make_hide_column_callback = (col_id) => {
            return () => {
                document.getElementById(col_id).style.visibility = "collapse";
            }
        }

        this.scenes.layers.forEach(layer => {
            let col_id = layer.name + "_col";
            let hide_btn = layer.name + "_hide";
            document.getElementById(hide_btn).addEventListener("click", make_hide_column_callback(col_id));
        });

        this.download_labels_btn.addEventListener("click", evt => {
            var uri = "data:text/plain;base64," + btoa(JSON.stringify(this.labels));
            this.download_labels_btn.setAttribute("href", uri);
        });

        for (let i = 0; i < this.scenes.index.length; i++) {
            let open_btn_id = "open_" + i + "_btn";
            let btn = document.getElementById(open_btn_id);
            btn.addEventListener("click", this.create_open_callback(i));
        }

        if (this.labels) {
            // get the label controls, and clear them
            for(let label_group in this.labels.schema) {
                this.overlay_label_controls[label_group] = {};
                for (let label_idx in this.labels.schema[label_group]) {
                    let label_value = this.labels.schema[label_group][label_idx];
                    let control_id = this.get_label_control_id(label_group, label_value, null);
                    console.log(control_id);
                    let control = document.getElementById(control_id);
                    control.checked = false;
                    this.overlay_label_controls[label_group][label_value] = control;
                }

                this.grid_label_controls[label_group] = [];
                for (let i = 0; i < this.labels.values[label_group].length; i++) {
                    let label_controls = {};
                    for(let label_idx in this.labels.schema[label_group]) {
                        let label_value = this.labels.schema[label_group][label_idx];
                        let control = document.getElementById(this.get_label_control_id(label_group,label_value,i));
                        control.checked = false;
                        label_controls[label_value] = control;
                    }
                    this.grid_label_controls[label_group].push(label_controls);
                }
            }

            // set the values on the controls
            for(let label_group in this.labels.values) {
                let values = this.labels.values[label_group];

                for (let i = 0; i < values.length; i++) {
                    let value = values[i];
                    if (value) {
                        this.grid_label_controls[label_group][i][value].checked = true;

                        if (i === this.current_index) {
                            this.overlay_label_controls[label_group][value].checked = true;
                        }
                    }
                }
            }

            // bind the label controls
            for(let label_group in this.overlay_label_controls) {
                for(let label in this.overlay_label_controls[label_group]) {
                    this.overlay_label_controls[label_group][label].addEventListener("click",
                        this.create_overlay_label_control_callback(label_group, label));
                }
                let grid_controls = this.grid_label_controls[label_group];
                for(let i=0; i<grid_controls.length; i++) {
                    let controls = grid_controls[i];
                    for(let label in controls) {
                        controls[label].addEventListener("click",this.create_grid_label_control_callback(label_group, label, i));
                    }
                }
            }
        }

        this.update_filters();
        this.update_time_range();
        this.show();
    }

    set_zoom() {
        // update the overlay zoom
        let zoom = Number.parseInt(zoom_control.value);
        zoom = Math.sqrt(zoom);
        this.scenes.layers.forEach(layer => {
            let img = document.getElementById(layer.name);
            img.width = Math.round(zoom * image_width);
        });
        if (this.di) {
            this.di.set_zoom(zoom);
        }
    }

    update_time_range() {
        // called from the overlay view on initialisation or after filters are updated or after the current index is updated
        // update the time range slider to reflect the current index
        if (this.index.length) {
            this.time_range.value = String(100 * (this.current_index / (this.index.length - 1)));
        } else {
            this.time_range.value = "50";
        }
    }

    update_filters() {
        // called from the overlay view after filters are updated
        // rebuild the main index based on the new filter settings
        this.current_index = 0;
        this.index = [];
        for (let idx = 0; idx < this.scenes.index.length; idx++) {
            let item = this.scenes.index[idx];
            let month = Number.parseInt(item.timestamp.slice(5, 7));
            if (!(month in this.months_excluded)) {
                this.index.push(item);
            }
        }
    }

    create_month_filter_callback(month) {
        // create a callback for when a month filter checkbox is checked/unchecked
        return (evt) => {
            if (!evt.target.checked) {
                this.months_excluded[month] = true;
            } else {
                delete this.months_excluded[month];
            }
            this.update_filters();
            this.update_time_range();
            this.show();
        }
    }

    create_opacity_callback(for_img, layer_name) {
        // create a callback for changes to an overlay view opacity slider
        return (evt) => {
            this.layer_opacities[layer_name] = Number.parseFloat(evt.target.value) / 100;
            for_img.style.opacity = this.layer_opacities[layer_name];
        }
    }

    populate_info(info_content, info) {
        // populate a table with scene information, in the overlay view
        let tbl = document.createElement("table");
        for (let key in info) {
            let tr = document.createElement("tr");
            let tc0 = document.createElement("td");
            let tc1 = document.createElement("td");
            tc0.innerHTML = key;
            tc1.innerHTML = info[key];
            tr.appendChild(tc0);
            tr.appendChild(tc1);
            tbl.appendChild(tr);
        }
        info_content.innerHTML = "";
        info_content.appendChild(tbl);
    }

    show() {
        // called in the overlay view to show the currently selected scene
        for (let idx = 0; idx < this.index.length; idx++) {
            if (idx === this.current_index) {
                let image_srcs = this.index[idx].image_srcs;

                let label_specs = this.index[idx].label_specs;

                for (let layer_name in image_srcs) {
                    let img = document.getElementById(layer_name);
                    img.src = image_srcs[layer_name];
                }
                let data_srcs = this.index[idx].data_srcs;
                if (this.di) {
                    this.di.unbind_tooltips();
                }
                this.di = new DataImage("viridis");

                let zoom = Number.parseInt(this.zoom_control.value);
                zoom = Math.sqrt(zoom);
                this.di.set_zoom(zoom);
                for (let layer_name in data_srcs) {
                    this.di.load(layer_name, data_srcs[layer_name]);
                }
                let idiv = document.getElementById("image_div");
                // pass in img padding+margin as the x and y offsets to binding tooltips
                this.di.bind_tooltips_to_img(idiv, 6, 6);

                if (this.info_content) {
                    let info = this.index[idx].info;
                    this.populate_info(this.info_content, info);
                }

                if (this.labels) {
                    let pos = this.index[idx].pos;
                    for (let label_group in this.labels.values) {
                        let label = this.labels.values[label_group][pos];
                        if (label) {
                            this.overlay_label_controls[label_group][label].checked = true;
                        } else {
                            // if there is no label value, uncheck all the controls
                            for(let label_value in this.overlay_label_controls[label_group]) {
                                this.overlay_label_controls[label_group][label_value].checked = false;
                            }
                        }
                    }
                }
            }
        }

        let overlay_label = "0/0";
        if (this.index.length) {
            overlay_label = "(" + (this.current_index + 1) + "/" + this.index.length + ") " + this.index[this.current_index].timestamp;
        }
        this.scene_label_elt.innerHTML = overlay_label;
    }

    setup_drag(elt, header_elt, initial_top, initial_left) {
        // set up draggable behaviour on an element
        var startx, starty, dx, dy;

        elt.style.top = initial_top + "px";
        elt.style.left = initial_left + "px";

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
}

window.addEventListener("load", async (ect) => {
   let hv = new HtmlView();
   await hv.load();
   hv.init();
   hv.setup_drag(document.getElementById("layer_container"),document.getElementById("layer_container_header"), 400, 400);
   let filter_container = document.getElementById("filter_container");
   if (filter_container) {
      hv.setup_drag(filter_container,document.getElementById("filter_container_header"), 200, 400);
   }
   let info_container = document.getElementById("info_container");
   if (info_container) {
       hv.setup_drag(info_container,document.getElementById("info_container_header"), 50, 400);
   }
   let labels_container = document.getElementById("labels_container");
   if (labels_container) {
       hv.setup_drag(labels_container,document.getElementById("labels_container_header"), 50, 400);
   }
});
