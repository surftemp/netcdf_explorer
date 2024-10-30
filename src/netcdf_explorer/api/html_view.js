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

        this.base_url = window.location.origin + window.location.pathname

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

        this.show_data = document.getElementById("show_data");
        this.data_container = document.getElementById("data_container");

        this.show_info = document.getElementById("show_info");
        this.info_container = document.getElementById("info_container");

        this.overlay_container = document.getElementById("overlay_container");
        this.grid_container = document.getElementById("grid_container");
        this.timeseries_container = document.getElementById("timeseries_container");
        this.terrain_container = document.getElementById("terrain_container");

        this.grid_view_button = document.getElementById("grid_view_btn");
        this.grid_view_button2 = document.getElementById("grid_view_btn2");
        this.timeseries_view_button = document.getElementById("timeseries_view_btn");
        this.overlay_view_button = document.getElementById("overlay_view_btn");

        this.terrain_view_button = document.getElementById("terrain_view_btn");
        this.exit_terrain_view_button = document.getElementById("exit_terrain_view");
        this.terrain_zoom = document.getElementById("terrain_zoom");
        this.terrain_zoom_value = document.getElementById("terrain_zoom_value");

        this.grid_label_controls = {}; // label_group => [label_value => label_control]
        this.overlay_label_controls = {}; // label_group => label_value => label_control

        this.download_labels_btn = document.getElementById("download_labels_btn"); // optional, may be undefined

        // record which services are available from the server (by default, none)
        this.services = {};

        // record custom min/max/cmaps selected in overlay view for data layers only
        this.data_layers = {};

        // for each layer_group, record the current activate layer
        this.layer_group_active_layers = {};

        // record the last image url viewed in overlay mode for each layer
        this.overlay_urls = {};

        this.lm = null;

        this.timeseries_charts = null;

        if (!this.grid_container) {
            if (this.timeseries_container) {
                this.timeseries_container.style.display = "block";
                this.load_timeseries().then(() => {
                });
            }
        }

        this.tv = null; // populated with a TerrainView object when in "terrain view" mode
        if (this.terrain_zoom) {
            this.terrain_zoom_value.innerHTML = this.terrain_zoom.value;
            this.terrain_zoom.addEventListener("change", (evt) => {
                if (this.terrain_zoom_value) {
                    this.terrain_zoom_value.innerHTML = this.terrain_zoom.value;
                }
                this.tv.set_terrain_zoom(Number.parseFloat(this.terrain_zoom.value));
            });
            this.terrain_zoom.addEventListener("input", (evt) => {
                if (this.terrain_zoom_value) {
                    this.terrain_zoom_value.innerHTML = this.terrain_zoom.value;
                }
            });
        }
    }

    handle_map_mouseover(y_frac, x_frac) {
        let data_content = document.getElementById("data_content");
        if (data_content) {
            let html = "<p>No Data</p>";
            if (this.di && y_frac !== null && x_frac !== null) {
                html = this.di.get_popup_html(y_frac, x_frac)
            }
            data_content.innerHTML = html;
        }
    }

    async load_timeseries() {
        if (this.timeseries_charts === null) {
            this.timeseries_charts = {};
            let r = await fetch("timeseries.json");
            let timeseries = await r.json();
            if (timeseries) {
                timeseries.forEach(o => {
                    let name = o["name"];
                    let csv_url = o["csv_url"];
                    let spec = o["spec"];
                    let div_id = o["div_id"];
                    let chart = new TimeseriesChart(div_id, csv_url, spec);
                    this.timeseries_charts[name] = chart;
                });
            }
        }
    }

    async load() {
        // load data files: scenes.json and (optionally) labels.json
        // this needs to be called before init
        let r = await fetch("scenes.json");
        this.scenes = await r.json();

        if (this.overlay_container) {
            this.lm = new LeafletMap('map', this.scenes.data_height, this.scenes.data_width,
                async (y_frac, x_frac) => {
                    this.handle_map_mouseover(y_frac, x_frac);
                },
                async (zoom) => {
                    this.set_zoom(zoom);
                }
            );

            this.zoom = 1;
            this.handle_map_mouseover(null, null);
        }

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
            this.scenes.index[idx].original_index = idx + 1;
            this.index.push(this.scenes.index[idx]);
        }

        // test to see what services are available (if any)
        try {
            r = await fetch("service_info/services.json");
            this.services = await r.json();
        } catch (e) {

        }
    }

    get_label_control_id(label_group, label_value, index) {
        // obtain the expected id for a label control
        let control_id = "radio_" + label_group + "_" + label_value;
        if (index !== null) {
            control_id += "_" + index;
        }
        return control_id;
    }

    create_overlay_label_control_callback(label_group, label) {
        // create a callback to be called when a label is updated by an overlay label control
        return async () => {
            if (this.index.length == 0) {
                return; // all scenes filtered out, perhaps
            }
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

    create_custom_cmap_callback(layer_name, select_control, min_control, max_control) {
        // create a callback to be called when a cmap is changed in the overlay view
        let cb = async (evt) => {
            let new_min = Number.parseFloat(min_control.value);
            let new_max = Number.parseFloat(max_control.value);
            let new_cmap = select_control.value;
            this.data_layers[layer_name] = {"cmap": new_cmap, "vmin": new_min, "vmax": new_max}
            await cmap.load(new_cmap);
            this.update_data_layer(layer_name);
        }
        select_control.addEventListener("change", cb);
        min_control.addEventListener("input", cb);
        max_control.addEventListener("input", cb);
    }

    async notify_label_update(label_group, i, label) {
        // notify the server (if this service is supported) of the label update
        if ("labels" in this.services) {
            await fetch("/label/" + label_group + "/" + i + "/" + label, {"method": "POST"});
        }
    }

    create_open_callback(index) {
        // create a callback to open a particular scene in the overlay view
        return async (evt) => {
            this.current_index = index;
            this.grid_container.style.display = "none";
            this.overlay_container.style.display = "block";
            this.update_time_range();
            await this.show();
        }
    }

    get_layer_group(layer_name) {
        for(let group in this.scenes.layer_groups) {
            if (this.scenes.layer_groups[group].includes(layer_name)) {
                return group;
            }
        }
        return "";
    }

    async init() {
        // initialise the view, to be called once load has completed
        // bind to the controls in this page


        if (this.grid_view_button) {
            this.grid_view_button.addEventListener("click", (evt) => {
                this.show_container(this.grid_container);
                history.pushState({}, null, this.base_url);
            });
        }

        if (this.grid_view_button2) {
            this.grid_view_button2.addEventListener("click", (evt) => {
                this.show_container(this.grid_container);
                history.pushState({}, null, this.base_url);
            });
        }

        if (this.overlay_view_button) {
            this.overlay_view_button.addEventListener("click", (evt) => {
                this.show_container(this.overlay_container);
            });
        }

        if (this.timeseries_view_button) {
            this.timeseries_view_button.addEventListener("click", async (evt) => {
                history.pushState({}, null, this.base_url);
                this.show_container(null);
                if (this.timeseries_container) {
                    this.timeseries_container.style.display = "block";
                    await this.load_timeseries();
                }
            });
        }

        if (this.next_button) {
            this.next_button.addEventListener("click", async (evt) => {
                if (this.current_index < this.index.length - 1) {
                    this.current_index += 1;
                    this.update_time_range();
                    await this.show();
                }
            });
        }

        if (this.prev_button) {
            this.prev_button.addEventListener("click", async (evt) => {
                if (this.current_index > 0) {
                    this.current_index -= 1;
                    this.update_time_range();
                    await this.show();
                }
            });
        }

        if (this.time_range) {
            this.time_range.addEventListener("input", async (evt) => {
                if (this.index.length) {
                    let fraction = Number.parseFloat(evt.target.value) / 100;
                    this.current_index = Math.round(fraction * (this.index.length - 1));
                    await this.show();
                }
            });
        }

        for (let month = 1; month <= 12; month += 1) {
            let cb_elt = document.getElementById("month" + month);
            if (cb_elt) {
                cb_elt.addEventListener("change", this.create_month_filter_callback(month));
            }
        }

        this.scenes.layers.forEach(layer => {
            let group = this.get_layer_group(layer.name);
            this.layer_opacities[layer.name] = 1;
            if (group && group in this.layer_group_active_layers) {
                // hide layers that are grouped if they are not the first layer in their group
                this.lm.set_layer_opacity(layer.name, 0);
            } else {
                this.lm.set_layer_opacity(layer.name, 1);
                this.layer_group_active_layers[group] = layer.name;
            }
            let r = document.getElementById(layer.name + "_opacity");
            if (r) {
                r.value = "100";
                r.addEventListener("input", this.create_opacity_callback(layer.name));
            }
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

        if (this.data_container && this.show_data) {
            this.show_data.addEventListener("input", (evt) => {
                let s = "none";
                if (evt.target.checked) {
                    s = "block";
                }
                this.data_container.style.display = s;
            });
        }

        if (this.close_all_btn) {
            this.close_all_btn.addEventListener("click", (evt) => {
                this.scenes.layers.forEach(layer => {
                    this.layer_opacities[layer.name] = 0.0;
                    this.lm.set_layer_opacity(layer.name, 0.0);
                    let r = document.getElementById(layer.name + "_opacity");
                    r.value = "0";
                });
            });
        }

        const make_hide_column_callback = (col_id) => {
            return (evt) => {
                document.getElementById(col_id).style.visibility = "collapse";
            }
        }

        const make_group_select_column_callback = (layer_name) => {
            return (evt) => {
                this.show_group_column(evt.target.value);
                this.show_group_row(evt.target.value);
            }
        }

        const make_group_select_row_callback = (layer_name) => {
            return (evt) => {
                this.show_group_column(evt.target.value);
                this.show_group_row(evt.target.value);
            }
        }

        this.scenes.layers.forEach(layer => {
            let col_id = layer.name + "_col";
            let hide_btn_id = layer.name + "_hide";
            let hide_btn = document.getElementById(hide_btn_id);
            if (hide_btn) {
                hide_btn.addEventListener("click", make_hide_column_callback(col_id));
                let group_name = this.get_layer_group(layer.name);
                if (group_name) {
                    let group_select_id = layer.name + "_group_select";
                    let group_select = document.getElementById(group_select_id);
                    if (group_select) {
                        group_select.addEventListener("input", make_group_select_column_callback(layer.name));
                    }

                    let group_select_row_id = layer.name + "_group_select_row";
                    let group_select_row = document.getElementById(group_select_row_id);
                    if (group_select_row) {
                        group_select_row.addEventListener("input", make_group_select_row_callback(layer.name));
                    }
                }
            }
        });

        // initialise layer groups to show the first layer
        let groups_initialised = {};
        this.scenes.layers.forEach(layer => {
            let group_name = this.get_layer_group(layer.name);
            if (group_name) {
                if (!(group_name in groups_initialised)) {
                    this.show_group_row(layer.name);
                    this.show_group_column(layer.name);
                    groups_initialised[layer.name] = true;
                }
            }
        });

        if (this.download_labels_btn) {
            this.download_labels_btn.addEventListener("click", evt => {
                var uri = "data:text/plain;base64," + btoa(JSON.stringify(this.labels));
                this.download_labels_btn.setAttribute("href", uri);
            });
        }

        for (let i = 0; i < this.scenes.index.length; i++) {
            let open_btn_id = "open_" + i + "_btn";
            let btn = document.getElementById(open_btn_id);
            btn.addEventListener("click", this.create_open_callback(i));
        }

        if (this.labels) {
            // get the label controls, and clear them
            for (let label_group in this.labels.schema) {
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
                    for (let label_idx in this.labels.schema[label_group]) {
                        let label_value = this.labels.schema[label_group][label_idx];
                        let control = document.getElementById(this.get_label_control_id(label_group, label_value, i));
                        control.checked = false;
                        label_controls[label_value] = control;
                    }
                    this.grid_label_controls[label_group].push(label_controls);
                }
            }

            // set the values on the controls
            for (let label_group in this.labels.values) {
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
            for (let label_group in this.overlay_label_controls) {
                for (let label in this.overlay_label_controls[label_group]) {
                    this.overlay_label_controls[label_group][label].addEventListener("click",
                        this.create_overlay_label_control_callback(label_group, label));
                }
                let grid_controls = this.grid_label_controls[label_group];
                for (let i = 0; i < grid_controls.length; i++) {
                    let controls = grid_controls[i];
                    for (let label in controls) {
                        controls[label].addEventListener("click", this.create_grid_label_control_callback(label_group, label, i));
                    }
                }
            }
        }

        for (let layer_idx in this.scenes.layers) {
            let layer = this.scenes.layers[layer_idx];
            if (layer.has_data) {
                let min_control = document.getElementById(layer.name + "_min_input");
                let max_control = document.getElementById(layer.name + "_max_input");
                let select_control = document.getElementById(layer.name + "_camp_selector");
                if (min_control && max_control && select_control) {
                    this.create_custom_cmap_callback(layer.name, select_control, min_control, max_control);
                }
            }
        }

        if (this.terrain_view_button) {
            this.terrain_view_button.addEventListener("click", async () => {
                await this.open_terrain_view();
            });
        }

        if (this.exit_terrain_view_button) {
            this.exit_terrain_view_button.addEventListener("click", () => {
                this.close_terrain_view();
            });
        }

        this.update_filters();

        // by default open the grid container if it exists
        if (this.grid_container) {
            const params = new URLSearchParams(window.location.search);
            if (params.has('index')) {
                this.current_index = Number.parseInt(params.get('index'))-1;
                if (this.current_index < 0) {
                    this.current_index = 0;
                }
                if (this.current_index >= this.index.length) {
                    this.current_index = this.index.length-1;
                }
                this.show_container(this.overlay_container);
            } else {
                this.show_container(this.grid_container);
            }
        } else if (this.timeseries_container) {
            // otherwise open the timeseries container
            this.show_container(this.timeseries_container);
        }

        if (this.time_range) {
            this.update_time_range();
        }

        await this.show();
    }

    show_group_column(layer_name) {
        let group_name = this.get_layer_group(layer_name);
        if (group_name) {
            let grouped_layers = this.scenes.layer_groups[group_name];
            for (let idx = 0; idx < grouped_layers.length; idx += 1) {
                let grouped_layer_name = grouped_layers[idx];
                let col_id = grouped_layer_name + "_col";
                if (grouped_layer_name === layer_name) {
                    document.getElementById(col_id).style.visibility = "visible";
                } else {
                    document.getElementById(col_id).style.visibility = "collapse";
                }
                let group_select_id = grouped_layer_name + "_group_select";
                document.getElementById(group_select_id).value = layer_name;
            }
        }
    }

    show_group_row(layer_name) {
        let group_name = this.get_layer_group(layer_name);
        if (group_name) {
            let grouped_layers = this.scenes.layer_groups[group_name];
            for (let idx=0; idx<grouped_layers.length; idx+=1) {
                let grouped_layer_name = grouped_layers[idx];
                let group_select_row_id = layer_name + "_group_select_row";
                let target_group_select_id = grouped_layer_name + "_group_select_row";
                let overlay_row_id = grouped_layer_name + "_overlay_row";
                if (grouped_layer_name === layer_name) {
                    document.getElementById(overlay_row_id).style.display = "table-row";
                    this.lm.set_layer_opacity(layer_name, this.layer_opacities[layer_name]);
                } else {
                    document.getElementById(overlay_row_id).style.display = "none";

                    this.lm.set_layer_opacity(grouped_layer_name, 0);
                }
                document.getElementById(group_select_row_id).value = layer_name;
            }
            this.layer_group_active_layers[group_name] = layer_name;
        }
    }

    show_container(target_container) {
        let containers = [this.grid_container, this.timeseries_container, this.overlay_container, this.terrain_container];
        containers.forEach(container => {
            if (container && container !== target_container) {
                container.style.display = "none";
            }
        });
        containers.forEach(container => {
            if (container && container === target_container) {
                container.style.display = "block";
            }
        });
    }

    set_zoom(zoom) {
        // update the overlay zoom
        this.zoom = zoom;
        this.scenes.layers.forEach(layer => {
            if (layer.wms_url) {
                let wms_url = layer.wms_url.replace("{WIDTH}", "" + this.zoom * image_width).replace("{HEIGHT}", "" + this.zoom * image_width)
                    .replace("{XMIN}", "" + this.scenes.index[this.current_index].x_min)
                    .replace("{YMIN}", "" + this.scenes.index[this.current_index].y_min)
                    .replace("{XMAX}", "" + this.scenes.index[this.current_index].x_max)
                    .replace("{YMAX}", "" + this.scenes.index[this.current_index].y_max);
                this.lm.add_image_layer(layer.name, wms_url);
            }
        });
    }

    update_time_range() {
        // called from the overlay view on initialisation or after filters are updated or after the current index is updated
        // update the time range slider to reflect the current index
        if (this.index.length) {
            this.time_range.value = String(100 * (this.current_index / (this.index.length - 1)));
            let original_index = this.index[this.current_index].original_index;
            history.pushState({}, null, this.base_url+"?index="+original_index);
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
        return async (evt) => {
            if (!evt.target.checked) {
                this.months_excluded[month] = true;
            } else {
                delete this.months_excluded[month];
            }
            this.update_filters();
            this.update_time_range();
            await this.show();
        }
    }

    create_opacity_callback(layer_name) {
        // create a callback for changes to an overlay view opacity slider
        return (evt) => {
            let opacity = Number.parseFloat(evt.target.value) / 100;
            this.layer_opacities[layer_name] = opacity;
            this.lm.set_layer_opacity(layer_name, opacity);
            let group_name = this.get_layer_group(layer_name);
            if (group_name) {
                // this layer belongs to a group
                // apply the same opacity to all layers in the same group
                let grouped_layers = this.scenes.layer_groups[group_name];
                grouped_layers.forEach((group_layer_name) => {
                    if (layer_name !== group_layer_name) {
                        this.layer_opacities[group_layer_name] = opacity;
                        this.lm.set_layer_opacity(layer_name, opacity);
                        let r = document.getElementById(group_layer_name + "_opacity");
                        if (r) {
                            r.value = evt.target.value;
                        }
                    }
                });
            }
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

    update_data_layer(layer_name) {
        let dl = this.data_layers[layer_name];
        let lurl = this.di.get_legend_url(dl.cmap, dl.vmin, dl.vmax, 20, 200);
        let img_id = layer_name + "_legend_img";
        document.getElementById(img_id).src = lurl;
        this.update_image(layer_name);
    }

    update_image(layer_name) {
        let image_srcs = this.index[this.current_index].image_srcs;
        let url = "";
        if (layer_name in this.data_layers) {
            let dl = this.data_layers[layer_name];
            url = this.di.get_image_url(layer_name, dl.cmap, dl.vmin, dl.vmax);
        } else {
            url = image_srcs[layer_name];
        }
        this.lm.add_image_layer(layer_name, url);
        return url;
    }

    async show() {
        // called in the overlay view to show the currently selected scene

        if (this.index.length == 0) {
            // nothing to show, hide the imagery
            this.lm.clear_layers();
            let overlay_label = "0/0";
            this.scene_label_elt.innerHTML = overlay_label;
            if (this.terrain_view_button) {
                this.terrain_view_button.disabled = true;
            }
            return;
        } else {
            if (this.terrain_view_button) {
                this.terrain_view_button.disabled = false;
            }
        }

        this.di = new DataImage("viridis");
        let data_srcs = this.index[this.current_index].data_srcs;
        for (let layer_name in data_srcs) {
            this.di.register_layer(layer_name);
            await this.di.load(layer_name, data_srcs[layer_name]);
        }

        this.overlay_urls = {};

        let label_specs = this.index[this.current_index].label_specs;

        for (let idx = this.scenes.layers.length - 1; idx >= 0; idx = idx - 1) {
            let layer_name = this.scenes.layers[idx].name;
            let image_url = this.update_image(layer_name);
            this.overlay_urls[layer_name] = image_url;
        }


        if (this.info_content) {
            let info = this.index[this.current_index].info;
            this.populate_info(this.info_content, info);
        }

        if (this.labels) {
            let pos = this.index[this.current_index].pos;
            for (let label_group in this.labels.values) {
                let label = this.labels.values[label_group][pos];
                if (label) {
                    this.overlay_label_controls[label_group][label].checked = true;
                } else {
                    // if there is no label value, uncheck all the controls
                    for (let label_value in this.overlay_label_controls[label_group]) {
                        this.overlay_label_controls[label_group][label_value].checked = false;
                    }
                }
            }
        }

        if (this.scene_label_elt) {
            let overlay_label = "0/0";
            if (this.index.length) {
                overlay_label = "(" + (this.current_index + 1) + "/" + this.index.length + ") " + this.index[this.current_index].timestamp;
            }
            this.scene_label_elt.innerHTML = overlay_label;
        }
    }

    async get_overlay_combined_image() {
        let image_urls = [];
        for (let idx = this.scenes.layers.length - 1; idx >= 0; idx = idx - 1) {
            let layer_name = this.scenes.layers[idx].name;
            let image_url = this.overlay_urls[layer_name];
            let group = this.get_layer_group(layer_name);
            if (group && this.layer_group_active_layers[group] !== layer_name) {
                continue;
            }
            let opacity = this.layer_opacities[layer_name];
            image_urls.push([image_url,opacity]);
        }

        function make_image_fetcher(url) {
            return new Promise(resolve => {
                let img = new Image();
                img.onload = () => {
                    resolve(img);
                }
                img.src = url;
            });
        }

        let cnv = new OffscreenCanvas(this.di.get_width(), this.di.get_height());
        let ctx = cnv.getContext("2d");
        for(let idx=0; idx<image_urls.length; idx++) {
            let url = image_urls[idx][0]
            let opacity = image_urls[idx][1];
            let p = make_image_fetcher(url);
            let img = await p;
            ctx.globalAlpha = opacity;
            ctx.drawImage(img, 0, 0);
            ctx.globalAlpha = 1.0;
        }
        let blob = await cnv.convertToBlob({"type":"image/png"});
        return URL.createObjectURL(blob);
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

    async open_terrain_view() {
        this.show_container(this.terrain_container);
        let elevation_band = this.scenes["terrain_view"]["elevation_band"];
        let image_url = await this.get_overlay_combined_image();
        let zoom = 1;
        if (this.terrain_zoom) {
            zoom = Number.parseFloat(this.terrain_zoom.value);
        }
        this.tv = new TerrainView(this.di, elevation_band, image_url, zoom);
        this.tv.open();
    }

    close_terrain_view() {
        this.tv.close();
        this.tv = null;
        this.show_container(this.overlay_container);
    }
}

window.addEventListener("load", async (ect) => {
    let hv = new HtmlView();
    await hv.load();
    hv.init();
    let layer_container = document.getElementById("layer_container");
    if (layer_container) {
        hv.setup_drag(layer_container, document.getElementById("layer_container_header"), 400, 400);
    }
    let filter_container = document.getElementById("filter_container");
    if (filter_container) {
        hv.setup_drag(filter_container, document.getElementById("filter_container_header"), 100, 400);
    }
    let info_container = document.getElementById("info_container");
    if (info_container) {
        hv.setup_drag(info_container, document.getElementById("info_container_header"), 200, 400);
    }
    let labels_container = document.getElementById("labels_container");
    if (labels_container) {
        hv.setup_drag(labels_container, document.getElementById("labels_container_header"), 300, 400);
    }
    let data_container = document.getElementById("data_container");
    if (data_container) {
        hv.setup_drag(data_container, document.getElementById("data_container_header"), 400, 400);
    }
});
