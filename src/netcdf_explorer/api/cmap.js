
class CMap {

    constructor(base_url) {
        this.cmaps = {};
        this.base_url = base_url;
    }

    async load(name) {
        if (name in this.cmaps) {
            return true;
        }

        let url = this.base_url+"/"+name+".json";
        let fetched = await fetch(url);
        let m = await fetched.json();
        this.cmaps[name] = m;
    }

    get_rgb(name,vmin,vmax,v) {
        if (v === null || v === undefined || isNaN(v)) {
            return null;
        }
        let lookup_v = (v - vmin) / (vmax-vmin);
        let cols = this.cmaps[name];
        let ncols = cols.length;
        let index = Math.floor(lookup_v*ncols);
        if (index < 0) {
            index = 0;
        }
        if (index >= ncols) {
            index = ncols-1;
        }
        return cols[index];
    }
}
