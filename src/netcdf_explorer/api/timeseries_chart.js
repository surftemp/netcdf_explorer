class TimeseriesChart {

    static all_charts = [];

    constructor(element_id, csv_url, variable_names) {
        let div = document.getElementById(element_id);
        this.g = new Dygraph(div, csv_url, {
          legend: 'always',
            zoomCallback: (minDate, maxDate, yRange) => {
                this.handle_zoom_event(minDate, maxDate, yRange);
              }
        });
        TimeseriesChart.all_charts.push(this);
    }

    set_zoom(minDate, maxDate) {
        this.disable_zoom_event = true;
        this.g.updateOptions({
          dateWindow: [minDate, maxDate]
        });
        this.disable_zoom_event = false;
    }

    handle_zoom_event(minDate, maxDate, yRange) {
        if (!this.disable_zoom_event) {
            TimeseriesChart.all_charts.forEach((chart) => {
                if (chart !== this) {
                    chart.set_zoom(minDate, maxDate);
                }
            });
        }
    }
}