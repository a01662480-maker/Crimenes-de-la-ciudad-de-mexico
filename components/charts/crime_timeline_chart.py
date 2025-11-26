"""
crime_timeline_chart.py - Crime Timeline Line Chart

Renders an animated D3.js line chart showing crime trends over time.
Includes an interactive dual-handle date range slider for filtering.
"""

import json


def render_crime_timeline_chart(data, mode='single'):
    """
    Render an animated D3.js crime timeline line chart.
    
    Args:
        data: List of dictionaries with crime data
              For 'single' mode: [{'date': 'YYYY-MM-DD', 'value': int, 'label': str}, ...]
              For 'breakdown' mode: [{'date': 'YYYY-MM-DD', 'value': int, 'category': str}, ...]
        mode: 'single' for total crimes, 'breakdown' for violent/non-violent split
    
    Returns:
        HTML string containing the D3.js visualization with interactive date range slider
    """
    
    chart_data_json = json.dumps(data)
    
    # Use triple quotes and avoid f-string for the HTML template to prevent escaping issues
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://d3js.org/d3.v7.min.js"></script>
        <style>
            body {
                margin: 0;
                padding: 20px;
                background: #f5f5f5;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            }
            .chart-container {
                background: white;
                border-radius: 12px;
                padding: 15px;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                margin-bottom: 10px;
                border: 1px solid #e0e0e0;
            }
            #chart {
                width: 100%;
                height: 350px;
            }
            .slider-container-wrapper {
                background: white;
                border-radius: 12px;
                padding: 12px 15px;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                border: 1px solid #e0e0e0;
            }
            .slider-container {
                display: flex;
                align-items: center;
                gap: 15px;
            }
            .slider-label {
                color: #333;
                font-size: 13px;
                font-weight: 600;
            }
            .range-slider-wrapper {
                flex: 1;
                position: relative;
                height: 40px;
            }
            .range-slider-track {
                position: absolute;
                width: 100%;
                height: 8px;
                background: #ddd;
                border-radius: 4px;
                top: 16px;
            }
            .range-slider-range {
                position: absolute;
                height: 8px;
                background: #0066CC;
                border-radius: 4px;
                top: 16px;
            }
            input[type="range"] {
                position: absolute;
                width: 100%;
                height: 8px;
                background: transparent;
                outline: none;
                -webkit-appearance: none;
                appearance: none;
                cursor: pointer;
                pointer-events: none;
                top: 16px;
            }
            input[type="range"]::-webkit-slider-thumb {
                -webkit-appearance: none;
                appearance: none;
                width: 20px;
                height: 20px;
                border-radius: 50%;
                background: #0066CC;
                cursor: pointer;
                border: 3px solid white;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
                pointer-events: auto;
                position: relative;
                z-index: 4;
            }
            input[type="range"]::-moz-range-thumb {
                width: 20px;
                height: 20px;
                border-radius: 50%;
                background: #0066CC;
                cursor: pointer;
                border: 3px solid white;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
                pointer-events: auto;
                position: relative;
                z-index: 4;
            }
            input[type="range"]::-webkit-slider-runnable-track {
                width: 100%;
                height: 8px;
                background: transparent;
                border-radius: 4px;
            }
            input[type="range"]::-moz-range-track {
                width: 100%;
                height: 8px;
                background: transparent;
                border-radius: 4px;
            }
            #minSlider {
                z-index: 3;
            }
            #maxSlider {
                z-index: 3;
            }
            .value-display {
                color: #555;
                font-size: 12px;
                min-width: 90px;
                text-align: center;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                font-weight: 500;
            }
            .date-range-display {
                display: flex;
                justify-content: space-between;
                margin-top: 8px;
                font-size: 11px;
                color: #888;
            }
            .line {
                fill: none;
                stroke-width: 3;
            }
            .dot {
                stroke: white;
                stroke-width: 2;
            }
            .grid line {
                stroke: #d0d0d0;
                stroke-dasharray: 2,2;
            }
            .grid path {
                stroke-width: 0;
            }
            .axis text {
                fill: #333;
                font-size: 12px;
            }
            .axis path,
            .axis line {
                stroke: #999;
            }
            /* Year label styling - bigger and bolder */
            .year-label {
                font-size: 14px !important;
                font-weight: 700 !important;
                fill: #0066CC !important;
            }
            .legend {
                font-size: 14px;
                fill: #000;
                font-weight: 600;
            }
            .legend-item {
                cursor: default;
            }
            .legend-color {
                width: 20px;
                height: 3px;
            }
            .tooltip {
                position: absolute;
                background: rgba(0, 0, 0, 0.9);
                color: white;
                padding: 10px;
                border-radius: 5px;
                pointer-events: none;
                font-size: 12px;
                opacity: 0;
                transition: opacity 0.2s;
                border: 1px solid rgba(255, 255, 255, 0.2);
                z-index: 1000;
            }
        </style>
    </head>
    <body>
        <div class="chart-container">
            <div id="chart"></div>
        </div>
        <div class="slider-container-wrapper">
            <div class="slider-container">
                <span class="slider-label">Rango de Fechas:</span>
                <div class="range-slider-wrapper">
                    <div class="range-slider-track"></div>
                    <div class="range-slider-range" id="rangeHighlight"></div>
                    <input type="range" id="minSlider" min="0" max="100" value="0" step="1">
                    <input type="range" id="maxSlider" min="0" max="100" value="100" step="1">
                </div>
                <div style="display: flex; gap: 10px; align-items: center;">
                    <span class="value-display" id="minValue">Inicio</span>
                    <span style="color: #999;">→</span>
                    <span class="value-display" id="maxValue">Fin</span>
                </div>
            </div>
        </div>
        <div class="tooltip" id="tooltip"></div>
        <script>
            // Spanish locale for D3.js date formatting
            const esLocale = {
                "dateTime": "%A, %e de %B de %Y, %X",
                "date": "%d/%m/%Y",
                "time": "%H:%M:%S",
                "periods": ["AM", "PM"],
                "days": ["domingo", "lunes", "martes", "miércoles", "jueves", "viernes", "sábado"],
                "shortDays": ["dom", "lun", "mar", "mié", "jue", "vie", "sáb"],
                "months": ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"],
                "shortMonths": ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
            };
            
            const formatTime = d3.timeFormatLocale(esLocale);
            const formatMonth = formatTime.format("%b %Y");
            const formatMonthFull = formatTime.format("%B %Y");
            
            const data = DATA_PLACEHOLDER;
            const mode = 'MODE_PLACEHOLDER';
            
            // Set up dimensions
            const margin = {top: 30, right: 30, bottom: 60, left: 60};
            const width = document.getElementById('chart').clientWidth - margin.left - margin.right;
            const height = 350 - margin.top - margin.bottom;
            
            // Create SVG
            const svg = d3.select("#chart")
                .append("svg")
                .attr("width", width + margin.left + margin.right)
                .attr("height", height + margin.top + margin.bottom)
                .append("g")
                .attr("transform", `translate(${margin.left},${margin.top})`);
            
            // Parse dates
            const parseDate = d3.timeParse("%Y-%m-%d");
            
            // Helper function to format x-axis with year labels
            function customXAxisFormat(date) {
                const month = date.getMonth();
                if (month === 0) {
                    // January - show year below
                    return formatMonth(date).replace(/\s(\d{4})/, '\\n$1');
                } else {
                    // Other months - just show month and year on same line
                    return formatMonth(date);
                }
            }
            
            // Helper function to style year labels after axis is created
            function styleYearLabels(axisGroup) {
                axisGroup.selectAll(".tick text")
                    .each(function() {
                        const text = d3.select(this);
                        const content = text.text();
                        
                        // Check if this tick has a year (January ticks)
                        if (content.includes('\\n')) {
                            const parts = content.split('\\n');
                            text.text(''); // Clear existing text
                            
                            // Add month on first line
                            text.append('tspan')
                                .attr('x', 0)
                                .attr('dy', 0)
                                .text(parts[0]);
                            
                            // Add year on second line with styling
                            text.append('tspan')
                                .attr('x', 0)
                                .attr('dy', '1.2em')
                                .attr('class', 'year-label')
                                .text(parts[1]);
                        }
                    });
            }
            
            if (mode === 'single') {
                data.forEach(d => {
                    d.date = parseDate(d.date);
                    d.value = +d.value;
                });
                
                // Sort data by date
                data.sort((a, b) => a.date - b.date);
                
                // Store original data for filtering
                const originalData = [...data];
                const allDates = data.map(d => d.date);
                
                // Set up scales with full data initially
                const x = d3.scaleTime()
                    .domain(d3.extent(allDates))
                    .range([0, width]);
                
                const maxValue = d3.max(data, d => d.value);
                const minValue = d3.min(data, d => d.value);
                const padding = (maxValue - minValue) * 0.1;
                const y = d3.scaleLinear()
                    .domain([Math.max(0, minValue - padding), maxValue + padding])
                    .range([height, 0]);
                
                // Setup range sliders for X-axis (time)
                const minSlider = document.getElementById('minSlider');
                const maxSlider = document.getElementById('maxSlider');
                const minValueDisplay = document.getElementById('minValue');
                const maxValueDisplay = document.getElementById('maxValue');
                
                minSlider.max = data.length - 1;
                maxSlider.max = data.length - 1;
                maxSlider.value = data.length - 1;
                
                const dateExtent = d3.extent(allDates);
                minValueDisplay.textContent = formatMonth(dateExtent[0]);
                maxValueDisplay.textContent = formatMonth(dateExtent[1]);
                
                // Function to update the range highlight
                function updateRangeHighlight() {
                    const minIdx = +minSlider.value;
                    const maxIdx = +maxSlider.value;
                    const rangeHighlight = document.getElementById('rangeHighlight');
                    
                    const minPercent = (minIdx / (data.length - 1)) * 100;
                    const maxPercent = (maxIdx / (data.length - 1)) * 100;
                    
                    rangeHighlight.style.left = minPercent + '%';
                    rangeHighlight.style.width = (maxPercent - minPercent) + '%';
                }
                
                updateRangeHighlight();
                
                // Function to update chart based on X-axis range
                function updateXAxis() {
                    const minIdx = +minSlider.value;
                    const maxIdx = +maxSlider.value;
                    
                    // Ensure min is less than max
                    if (minIdx >= maxIdx) {
                        if (this === minSlider) {
                            minSlider.value = Math.max(0, maxIdx - 1);
                        } else {
                            maxSlider.value = Math.min(originalData.length - 1, minIdx + 1);
                        }
                        return;
                    }
                    
                    // Filter data based on date indices (X-axis filtering)
                    const filteredData = originalData.slice(minIdx, maxIdx + 1);
                    
                    // Update display labels
                    minValueDisplay.textContent = formatMonth(filteredData[0].date);
                    maxValueDisplay.textContent = formatMonth(filteredData[filteredData.length - 1].date);
                    
                    // Update X-axis domain (time range)
                    x.domain(d3.extent(filteredData, d => d.date));
                    
                    // Update Y-axis domain to fit filtered data with padding
                    const filteredMaxValue = d3.max(filteredData, d => d.value);
                    const filteredMinValue = d3.min(filteredData, d => d.value);
                    const filteredPadding = (filteredMaxValue - filteredMinValue) * 0.1;
                    y.domain([Math.max(0, filteredMinValue - filteredPadding), filteredMaxValue + filteredPadding]);
                    
                    // Update line
                    svg.selectAll(".line")
                        .datum(filteredData)
                        .transition()
                        .duration(500)
                        .attr("d", line);
                    
                    // Remove old dots
                    svg.selectAll(".dot").remove();
                    
                    // Add new dots
                    svg.selectAll(".dot")
                        .data(filteredData)
                        .enter()
                        .append("circle")
                        .attr("class", "dot")
                        .attr("cx", d => x(d.date))
                        .attr("cy", d => y(d.value))
                        .attr("r", 5)
                        .attr("fill", "#0066CC")
                        .on("mouseover", function(event, d) {
                            tooltip.style("opacity", 1)
                                .html(`<strong>${formatMonthFull(d.date)}</strong><br>Delitos: ${d.value.toLocaleString()}`);
                        })
                        .on("mousemove", function(event) {
                            tooltip.style("left", (event.pageX + 10) + "px")
                                .style("top", (event.pageY - 10) + "px");
                        })
                        .on("mouseout", function() {
                            tooltip.style("opacity", 0);
                        });
                    
                    // Update x-axis with custom formatting
                    const xAxisGroup = svg.select(".x-axis")
                        .transition()
                        .duration(500)
                        .call(d3.axisBottom(x).ticks(8).tickFormat(customXAxisFormat));
                    
                    // Style year labels after transition
                    setTimeout(() => styleYearLabels(svg.select(".x-axis")), 500);
                    
                    svg.select(".y-axis")
                        .transition()
                        .duration(500)
                        .call(d3.axisLeft(y).tickFormat(d => d.toLocaleString()));
                    
                    svg.select(".grid")
                        .transition()
                        .duration(500)
                        .call(d3.axisLeft(y)
                            .tickSize(-width)
                            .tickFormat(""));
                    
                    updateRangeHighlight();
                }
                
                minSlider.addEventListener('input', updateXAxis);
                maxSlider.addEventListener('input', updateXAxis);
                
                // Add grid
                svg.append("g")
                    .attr("class", "grid")
                    .attr("opacity", 0.2)
                    .call(d3.axisLeft(y)
                        .tickSize(-width)
                        .tickFormat(""));
                
                // Add x-axis with custom formatting
                const xAxis = svg.append("g")
                    .attr("class", "x-axis")
                    .attr("transform", `translate(0,${height})`)
                    .call(d3.axisBottom(x).ticks(8).tickFormat(customXAxisFormat));
                
                // Style year labels
                styleYearLabels(xAxis);
                
                svg.append("g")
                    .attr("class", "y-axis")
                    .call(d3.axisLeft(y).tickFormat(d => d.toLocaleString()));
                
                // Define line with less curve (catmullRom with alpha=0.5 for moderate smoothing)
                const line = d3.line()
                    .x(d => x(d.date))
                    .y(d => y(d.value))
                    .curve(d3.curveCatmullRom.alpha(0.5));
                
                // Add line with animation
                const path = svg.append("path")
                    .datum(data)
                    .attr("class", "line")
                    .attr("stroke", "#0066CC")
                    .attr("d", line);
                
                const totalLength = path.node().getTotalLength();
                
                path
                    .attr("stroke-dasharray", totalLength + " " + totalLength)
                    .attr("stroke-dashoffset", totalLength)
                    .transition()
                    .duration(2000)
                    .ease(d3.easeLinear)
                    .attr("stroke-dashoffset", 0);
                
                // Add dots with delayed animation
                const tooltip = d3.select("#tooltip");
                
                svg.selectAll(".dot")
                    .data(data)
                    .enter()
                    .append("circle")
                    .attr("class", "dot")
                    .attr("cx", d => x(d.date))
                    .attr("cy", d => y(d.value))
                    .attr("r", 0)
                    .attr("fill", "#0066CC")
                    .transition()
                    .delay((d, i) => i * (2000 / data.length))
                    .duration(300)
                    .attr("r", 5);
                
                // Add tooltip after animation
                setTimeout(() => {
                    svg.selectAll(".dot")
                        .on("mouseover", function(event, d) {
                            tooltip.style("opacity", 1)
                                .html(`<strong>${formatMonthFull(d.date)}</strong><br>Delitos: ${d.value.toLocaleString()}`);
                        })
                        .on("mousemove", function(event) {
                            tooltip.style("left", (event.pageX + 10) + "px")
                                .style("top", (event.pageY - 10) + "px");
                        })
                        .on("mouseout", function() {
                            tooltip.style("opacity", 0);
                        });
                }, 2500);
                
            } else {
                // Breakdown mode - similar structure, just add the breakdown code here
                // (keeping it shorter for now, but same pattern)
                data.forEach(d => {
                    d.date = parseDate(d.date);
                    d.value = +d.value;
                });
                
                data.sort((a, b) => a.date - b.date);
                
                const dataByCategory = d3.group(data, d => d.category);
                
                const allDates = data.map(d => d.date);
                const x = d3.scaleTime()
                    .domain(d3.extent(allDates))
                    .range([0, width]);
                
                const maxValue = d3.max(data, d => d.value);
                const minValue = d3.min(data, d => d.value);
                const padding = (maxValue - minValue) * 0.1;
                const y = d3.scaleLinear()
                    .domain([Math.max(0, minValue - padding), maxValue + padding])
                    .range([height, 0]);
                
                const originalData = [...data];
                
                const minSlider = document.getElementById('minSlider');
                const maxSlider = document.getElementById('maxSlider');
                const minValueDisplay = document.getElementById('minValue');
                const maxValueDisplay = document.getElementById('maxValue');
                
                const uniqueDates = [...new Set(data.map(d => d.date.getTime()))].sort().map(t => new Date(t));
                
                minSlider.max = uniqueDates.length - 1;
                maxSlider.max = uniqueDates.length - 1;
                maxSlider.value = uniqueDates.length - 1;
                
                const dateExtent = d3.extent(allDates);
                minValueDisplay.textContent = formatMonth(dateExtent[0]);
                maxValueDisplay.textContent = formatMonth(dateExtent[1]);
                
                function updateRangeHighlight() {
                    const minIdx = +minSlider.value;
                    const maxIdx = +maxSlider.value;
                    const rangeHighlight = document.getElementById('rangeHighlight');
                    
                    const minPercent = (minIdx / (uniqueDates.length - 1)) * 100;
                    const maxPercent = (maxIdx / (uniqueDates.length - 1)) * 100;
                    
                    rangeHighlight.style.left = minPercent + '%';
                    rangeHighlight.style.width = (maxPercent - minPercent) + '%';
                }
                
                updateRangeHighlight();
                
                function updateXAxis() {
                    const minIdx = +minSlider.value;
                    const maxIdx = +maxSlider.value;
                    
                    if (minIdx >= maxIdx) {
                        if (this === minSlider) {
                            minSlider.value = Math.max(0, maxIdx - 1);
                        } else {
                            maxSlider.value = Math.min(uniqueDates.length - 1, minIdx + 1);
                        }
                        return;
                    }
                    
                    const minDate = uniqueDates[minIdx];
                    const maxDate = uniqueDates[maxIdx];
                    
                    const filteredData = originalData.filter(d => 
                        d.date >= minDate && d.date <= maxDate
                    );
                    
                    minValueDisplay.textContent = formatMonth(minDate);
                    maxValueDisplay.textContent = formatMonth(maxDate);
                    
                    x.domain([minDate, maxDate]);
                    
                    const filteredMaxValue = d3.max(filteredData, d => d.value);
                    const filteredMinValue = d3.min(filteredData, d => d.value);
                    const filteredPadding = (filteredMaxValue - filteredMinValue) * 0.1;
                    y.domain([Math.max(0, filteredMinValue - filteredPadding), filteredMaxValue + filteredPadding]);
                    
                    const filteredByCategory = d3.group(filteredData, d => d.category);
                    
                    filteredByCategory.forEach((values, category) => {
                        svg.selectAll(`.line-${category}`)
                            .datum(values)
                            .transition()
                            .duration(500)
                            .attr("d", line);
                    });
                    
                    svg.selectAll(".dot").remove();
                    
                    filteredByCategory.forEach((values, category) => {
                        svg.selectAll(`.dot-${category}`)
                            .data(values)
                            .enter()
                            .append("circle")
                            .attr("class", `dot dot-${category}`)
                            .attr("cx", d => x(d.date))
                            .attr("cy", d => y(d.value))
                            .attr("r", 5)
                            .attr("fill", colors[category])
                            .on("mouseover", function(event, d) {
                                const categoryLabel = d.category === 'violent' ? 'Violentos' : 'No Violentos';
                                tooltip.style("opacity", 1)
                                    .html(`<strong>${formatMonthFull(d.date)}</strong><br>${categoryLabel}: ${d.value.toLocaleString()}`);
                            })
                            .on("mousemove", function(event) {
                                tooltip.style("left", (event.pageX + 10) + "px")
                                    .style("top", (event.pageY - 10) + "px");
                            })
                            .on("mouseout", function() {
                                tooltip.style("opacity", 0);
                            });
                    });
                    
                    const xAxisGroup = svg.select(".x-axis")
                        .transition()
                        .duration(500)
                        .call(d3.axisBottom(x).ticks(8).tickFormat(customXAxisFormat));
                    
                    setTimeout(() => styleYearLabels(svg.select(".x-axis")), 500);
                    
                    svg.select(".y-axis")
                        .transition()
                        .duration(500)
                        .call(d3.axisLeft(y).tickFormat(d => d.toLocaleString()));
                    
                    svg.select(".grid")
                        .transition()
                        .duration(500)
                        .call(d3.axisLeft(y)
                            .tickSize(-width)
                            .tickFormat(""));
                    
                    updateRangeHighlight();
                }
                
                minSlider.addEventListener('input', updateXAxis);
                maxSlider.addEventListener('input', updateXAxis);
                
                svg.append("g")
                    .attr("class", "grid")
                    .attr("opacity", 0.2)
                    .call(d3.axisLeft(y)
                        .tickSize(-width)
                        .tickFormat(""));
                
                const xAxis = svg.append("g")
                    .attr("class", "x-axis")
                    .attr("transform", `translate(0,${height})`)
                    .call(d3.axisBottom(x).ticks(8).tickFormat(customXAxisFormat));
                
                styleYearLabels(xAxis);
                
                svg.append("g")
                    .attr("class", "y-axis")
                    .call(d3.axisLeft(y).tickFormat(d => d.toLocaleString()));
                
                const colors = {
                    'violent': '#0066CC',
                    'non_violent': '#4ECDC4'
                };
                
                const line = d3.line()
                    .x(d => x(d.date))
                    .y(d => y(d.value))
                    .curve(d3.curveCatmullRom.alpha(0.5));
                
                dataByCategory.forEach((values, category) => {
                    const path = svg.append("path")
                        .datum(values)
                        .attr("class", `line line-${category}`)
                        .attr("data-category", category)
                        .attr("stroke", colors[category])
                        .attr("d", line);
                    
                    const totalLength = path.node().getTotalLength();
                    
                    path
                        .attr("stroke-dasharray", totalLength + " " + totalLength)
                        .attr("stroke-dashoffset", totalLength)
                        .transition()
                        .duration(2000)
                        .ease(d3.easeLinear)
                        .attr("stroke-dashoffset", 0);
                    
                    svg.selectAll(`.dot-${category}`)
                        .data(values)
                        .enter()
                        .append("circle")
                        .attr("class", `dot dot-${category}`)
                        .attr("cx", d => x(d.date))
                        .attr("cy", d => y(d.value))
                        .attr("r", 0)
                        .attr("fill", colors[category])
                        .transition()
                        .delay((d, i) => i * (2000 / values.length))
                        .duration(300)
                        .attr("r", 5);
                });
                
                const legendData = [
                    {label: 'Violentos', color: '#0066CC'},
                    {label: 'No Violentos', color: '#4ECDC4'}
                ];
                
                const legend = svg.append("g")
                    .attr("class", "legend-group")
                    .attr("transform", `translate(${width - 140}, 10)`);
                
                legendData.forEach((item, i) => {
                    const legendItem = legend.append("g")
                        .attr("class", "legend-item")
                        .attr("transform", `translate(0, ${i * 25})`)
                        .attr("opacity", 0);
                    
                    legendItem.append("line")
                        .attr("x1", 0)
                        .attr("x2", 25)
                        .attr("y1", 0)
                        .attr("y2", 0)
                        .attr("stroke", item.color)
                        .attr("stroke-width", 3);
                    
                    legendItem.append("text")
                        .attr("x", 35)
                        .attr("y", 5)
                        .attr("class", "legend")
                        .text(item.label);
                    
                    legendItem.transition()
                        .delay(2000 + i * 200)
                        .duration(500)
                        .attr("opacity", 1);
                });
                
                const tooltip = d3.select("#tooltip");
                
                setTimeout(() => {
                    svg.selectAll(".dot")
                        .on("mouseover", function(event, d) {
                            const categoryLabel = d.category === 'violent' ? 'Violentos' : 'No Violentos';
                            tooltip.style("opacity", 1)
                                .html(`<strong>${formatMonthFull(d.date)}</strong><br>${categoryLabel}: ${d.value.toLocaleString()}`);
                        })
                        .on("mousemove", function(event) {
                            tooltip.style("left", (event.pageX + 10) + "px")
                                .style("top", (event.pageY - 10) + "px");
                        })
                        .on("mouseout", function() {
                            tooltip.style("opacity", 0);
                        });
                }, 2500);
            }
        </script>
    </body>
    </html>
    """
    
    # Replace placeholders with actual data
    html_template = html_template.replace('DATA_PLACEHOLDER', chart_data_json)
    html_template = html_template.replace('MODE_PLACEHOLDER', mode)
    
    return html_template