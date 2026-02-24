class TimeseriesChart {

    static all_charts = [];

    constructor(element_id, csv_url, spec) {
        this.type = spec.type || "timeseries";
        let div = document.getElementById(element_id);
        let options = {
            legend: 'always',
            /* showRangeSelector: true, */
            connectSeparatedPoints: true,
            zoomCallback: (minDate, maxDate, yRange) => {
                if (spec.type !== "seasonal") {
                    this.handle_zoom_event(minDate, maxDate, yRange, this.type);
                }
            }
        }
        this.g = new Dygraph(div, csv_url, options);
        TimeseriesChart.all_charts.push(this);
    }

    set_zoom(minDate, maxDate) {
        this.disable_zoom_event = true;
        this.g.updateOptions({
          dateWindow: [minDate, maxDate]
        });
        this.disable_zoom_event = false;
    }

    handle_zoom_event(minDate, maxDate, yRange, type) {
        if (!this.disable_zoom_event) {
            TimeseriesChart.all_charts.forEach((chart) => {
                if (chart !== this && chart.type === type) {
                    chart.set_zoom(minDate, maxDate);
                }
            });
        }
    }
}