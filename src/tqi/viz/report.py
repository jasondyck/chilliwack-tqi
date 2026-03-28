"""Assemble HTML report from all analysis outputs."""

import json
from pathlib import Path

import numpy as np
from jinja2 import Template

from tqi.config import OUTPUT_DIR, WALKSCORE_RANGES
from tqi.scoring.tqi import TQIResult, DetailedAnalysis

REPORT_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chilliwack Transit Quality Index</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;700&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet">
    <script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
    <script>
      tailwind.config = {
        theme: {
          extend: {
            colors: {
              primary: "#3b82f6",
              success: "#10b981",
              warning: "#f59e0b",
              danger: "#ef4444",
              info: "#8b5cf6",
              slate: {
                50: "#f8fafc", 100: "#f1f5f9", 200: "#e2e8f0",
                400: "#94a3b8", 500: "#64748b", 600: "#475569",
                800: "#1e293b", 900: "#0f172a", 950: "#020617",
              }
            },
            fontFamily: {
              "headline": ["Inter", "sans-serif"],
              "body": ["Inter", "sans-serif"],
              "label": ["Space Grotesk", "sans-serif"]
            },
            borderRadius: {"DEFAULT": "0.5rem", "lg": "1rem", "xl": "1.5rem", "full": "9999px"},
          },
        },
      }
    </script>
    <script>
      const CHART_DATA = {{ chart_data_json }};
      document.addEventListener('DOMContentLoaded', () => {
        Chart.defaults.font.family = "'Inter', sans-serif";
        Chart.defaults.font.size = 12;
        Chart.defaults.color = '#64748b';
        Chart.defaults.plugins.legend.display = false;
        Chart.defaults.plugins.tooltip.backgroundColor = '#1e293b';
        Chart.defaults.plugins.tooltip.titleFont = { weight: '600' };
        Chart.defaults.plugins.tooltip.cornerRadius = 8;
        Chart.defaults.plugins.tooltip.padding = 10;
        Chart.defaults.elements.bar.borderRadius = 4;
        Chart.defaults.elements.line.tension = 0.3;
        Chart.defaults.scale.grid = { color: '#e2e8f0' };

        // Time-of-day profile
        if (CHART_DATA.time_profile) {
          new Chart(document.getElementById('chart-time-profile'), {
            type: 'line',
            data: {
              labels: CHART_DATA.time_profile.labels,
              datasets: [{
                data: CHART_DATA.time_profile.values,
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59,130,246,0.08)',
                fill: true,
                pointRadius: 2,
                pointHoverRadius: 6,
                pointBackgroundColor: '#3b82f6',
                borderWidth: 2.5,
              }]
            },
            options: {
              responsive: true, maintainAspectRatio: false,
              plugins: { tooltip: { callbacks: { label: ctx => `TQI: ${ctx.parsed.y.toFixed(2)}` }}},
              scales: {
                y: { beginAtZero: true, title: { display: true, text: 'TQI Score' }},
                x: { ticks: { maxTicksLimit: 16 }}
              },
              interaction: { intersect: false, mode: 'index' }
            }
          });
        }

        // Score breakdown
        if (CHART_DATA.scores) {
          new Chart(document.getElementById('chart-scores'), {
            type: 'bar',
            data: {
              labels: ['Coverage', 'Speed', 'Overall TQI'],
              datasets: [{
                data: [CHART_DATA.scores.coverage, CHART_DATA.scores.speed, CHART_DATA.scores.tqi],
                backgroundColor: ['#3b82f6', '#10b981', '#f59e0b'],
                borderRadius: 6,
                barPercentage: 0.6,
              }]
            },
            options: {
              indexAxis: 'y', responsive: true, maintainAspectRatio: false,
              scales: { x: { max: 100, title: { display: true, text: 'Score (0-100)' }}},
              plugins: { tooltip: { callbacks: { label: ctx => ctx.parsed.x.toFixed(1) + ' / 100' }}}
            }
          });
        }

        // TSR distribution (doughnut)
        if (CHART_DATA.tsr) {
          new Chart(document.getElementById('chart-tsr'), {
            type: 'doughnut',
            data: {
              labels: ['Slower than walking (<5 km/h)', 'Marginal (5-10 km/h)', 'Useful (10-20 km/h)', 'Competitive (20+ km/h)'],
              datasets: [{
                data: [CHART_DATA.tsr.slower, CHART_DATA.tsr.band_5_10, CHART_DATA.tsr.band_10_20, CHART_DATA.tsr.band_20_plus],
                backgroundColor: ['#ef4444', '#f59e0b', '#10b981', '#059669'],
                borderWidth: 2, borderColor: '#ffffff',
              }]
            },
            options: {
              responsive: true, maintainAspectRatio: false,
              cutout: '55%',
              plugins: {
                legend: { display: true, position: 'bottom', labels: { padding: 16, usePointStyle: true, pointStyle: 'circle' }},
                tooltip: { callbacks: { label: ctx => `${ctx.label}: ${ctx.parsed.toFixed(1)}%` }}
              }
            }
          });
        }

        // Travel time percentiles
        if (CHART_DATA.travel_time) {
          new Chart(document.getElementById('chart-travel-time'), {
            type: 'bar',
            data: {
              labels: CHART_DATA.travel_time.labels,
              datasets: [{
                data: CHART_DATA.travel_time.values,
                backgroundColor: CHART_DATA.travel_time.values.map((v, i, a) => {
                  const t = i / (a.length - 1);
                  return `rgba(${Math.round(16 + 223*t)}, ${Math.round(185 - 120*t)}, ${Math.round(129 - 60*t)}, 0.85)`;
                }),
                borderRadius: 6, barPercentage: 0.65,
              }]
            },
            options: {
              responsive: true, maintainAspectRatio: false,
              scales: { y: { beginAtZero: true, title: { display: true, text: 'Minutes' }}},
              plugins: { tooltip: { callbacks: { label: ctx => ctx.parsed.y.toFixed(0) + ' min' }}}
            }
          });
        }

        // Reliability histogram
        if (CHART_DATA.reliability) {
          new Chart(document.getElementById('chart-reliability'), {
            type: 'bar',
            data: {
              labels: CHART_DATA.reliability.labels,
              datasets: [{
                data: CHART_DATA.reliability.counts,
                backgroundColor: CHART_DATA.reliability.counts.map((_, i, a) => {
                  const t = i / a.length;
                  return `rgba(${Math.round(99 + 40*t)}, ${Math.round(102 - 40*t)}, ${Math.round(241 - 50*t)}, 0.75)`;
                }),
                borderRadius: 2, barPercentage: 1.0, categoryPercentage: 0.95,
              }]
            },
            options: {
              responsive: true, maintainAspectRatio: false,
              scales: {
                y: { title: { display: true, text: 'Grid Points' }},
                x: { title: { display: true, text: 'Coefficient of Variation' }, ticks: { maxTicksLimit: 10 }}
              }
            }
          });
        }

        // PTAL distribution
        if (CHART_DATA.ptal) {
          new Chart(document.getElementById('chart-ptal'), {
            type: 'bar',
            data: {
              labels: CHART_DATA.ptal.labels,
              datasets: [{
                data: CHART_DATA.ptal.counts,
                backgroundColor: ['#ef4444','#f97316','#f59e0b','#eab308','#84cc16','#10b981','#059669','#047857'],
                borderRadius: 6, barPercentage: 0.7,
              }]
            },
            options: {
              responsive: true, maintainAspectRatio: false,
              scales: { y: { title: { display: true, text: 'Grid Points' }}},
              plugins: {
                legend: { display: false },
                tooltip: { callbacks: { label: ctx => `${ctx.parsed.y.toLocaleString()} points` }}
              }
            }
          });
        }
      });
    </script>
    <style>
        .material-symbols-outlined {
            font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
            vertical-align: middle;
        }
        .tabular-nums { font-variant-numeric: tabular-nums; }
        @media (max-width: 639px) {
            .map-frame { height: 300px !important; }
            table th, table td { padding-left: 0.75rem !important; padding-right: 0.75rem !important; font-size: 0.8rem !important; }
            table th { font-size: 0.65rem !important; }
        }
        @media print {
            .map-frame { height: 400px !important; }
            body { print-color-adjust: exact; -webkit-print-color-adjust: exact; }
        }
    </style>
</head>
<body class="bg-slate-50 font-body text-slate-600 antialiased">

<div class="max-w-7xl mx-auto px-4 py-6 sm:px-6 sm:py-10 lg:px-12 space-y-8 sm:space-y-10">

    <!-- ============================================================ -->
    <!-- HERO SECTION                                                  -->
    <!-- ============================================================ -->
    <section class="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <!-- Main Score Card -->
        <div class="lg:col-span-8 bg-white p-5 sm:p-8 rounded-xl border border-slate-200 shadow-sm relative overflow-hidden flex flex-col justify-between min-h-[260px] sm:min-h-[340px]">
            <div class="absolute top-0 right-0 w-64 h-64 bg-warning/5 rounded-full -translate-y-1/2 translate-x-1/2 blur-3xl"></div>
            <div>
                <nav class="flex items-center gap-2 text-slate-400 mb-4 font-label uppercase tracking-widest text-[0.7rem]">
                    <span>British Columbia</span>
                    <span class="material-symbols-outlined text-xs">chevron_right</span>
                    <span class="text-slate-600">Fraser Valley</span>
                </nav>
                <h1 class="text-2xl sm:text-4xl md:text-5xl font-extrabold text-slate-900 font-headline tracking-tight mb-2">
                    Chilliwack Transit Quality Index
                </h1>
                <p class="text-slate-500 max-w-xl">
                    Measuring how well public transit connects the city &mdash; scored 0 to 100 using established transit planning metrics.
                </p>
            </div>
            <div class="mt-6 sm:mt-8">
                <span class="font-label uppercase text-[0.78rem] tracking-wider text-warning font-bold block mb-1">Current Score</span>
                <div class="flex items-baseline gap-2 flex-wrap">
                    <span class="text-5xl sm:text-7xl md:text-8xl font-black font-headline text-slate-900 tracking-tighter tabular-nums">{{ "%.1f"|format(tqi) }}</span>
                    <span class="text-xl sm:text-3xl font-bold text-slate-400 tabular-nums">/ 100</span>
                </div>
                <div class="mt-3 flex items-center gap-3 flex-wrap">
                    {% if da %}
                    <div class="flex items-center gap-2 px-3 py-1 bg-warning/10 text-warning rounded-full text-xs font-bold">
                        <span class="material-symbols-outlined text-sm">info</span>
                        <span>{{ da.walkscore_category }}</span>
                    </div>
                    {% endif %}
                    <div class="h-2 w-32 sm:w-48 bg-slate-100 rounded-full overflow-hidden">
                        <div class="h-full bg-warning rounded-full" style="width: {{ tqi }}%"></div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Heatmap Preview -->
        <div class="lg:col-span-4 bg-slate-900 rounded-xl overflow-hidden relative border border-slate-800 shadow-xl min-h-[200px] sm:min-h-[340px]">
            <iframe src="heatmap.html" class="w-full h-full absolute inset-0 border-none opacity-80"></iframe>
            <div class="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/20 to-transparent p-6 flex flex-col justify-end pointer-events-none">
                <div class="flex justify-between items-end">
                    <div>
                        <h3 class="text-white font-bold font-headline">Service Heatmap</h3>
                        <p class="text-slate-400 text-xs">Per-location transit connectivity</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- Score Cards Grid -->
        <div class="lg:col-span-12 grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-6">
            <!-- Overall TQI -->
            <div class="bg-white p-6 rounded-xl border border-slate-200 shadow-sm group hover:border-warning transition-all">
                <div class="flex justify-between items-start mb-4">
                    <div class="p-2 bg-warning/10 text-warning rounded-lg">
                        <span class="material-symbols-outlined">star</span>
                    </div>
                    <span class="text-[10px] font-bold text-slate-400 font-label">COMPOSITE</span>
                </div>
                <h4 class="font-label uppercase text-[0.78rem] font-medium text-slate-500 mb-1 tracking-wider">Overall TQI</h4>
                <div class="flex items-baseline gap-2">
                    <span class="text-2xl sm:text-4xl font-extrabold font-headline text-slate-900 tabular-nums tracking-tight">{{ "%.1f"|format(tqi) }}</span>
                </div>
                <p class="text-xs text-slate-400 mt-2">50% coverage + 50% speed</p>
            </div>
            <!-- Coverage -->
            <div class="bg-white p-6 rounded-xl border border-slate-200 shadow-sm group hover:border-primary transition-all">
                <div class="flex justify-between items-start mb-4">
                    <div class="p-2 bg-primary/10 text-primary rounded-lg">
                        <span class="material-symbols-outlined">location_on</span>
                    </div>
                    <span class="text-[10px] font-bold text-slate-400 font-label">GEOSPATIAL</span>
                </div>
                <h4 class="font-label uppercase text-[0.78rem] font-medium text-slate-500 mb-1 tracking-wider">Coverage</h4>
                <div class="flex items-baseline gap-2">
                    <span class="text-2xl sm:text-4xl font-extrabold font-headline text-slate-900 tabular-nums tracking-tight">{{ "%.1f"|format(coverage) }}</span>
                </div>
                <p class="text-xs text-slate-400 mt-2">OD pair reachability score</p>
            </div>
            <!-- Speed -->
            <div class="bg-white p-6 rounded-xl border border-slate-200 shadow-sm group hover:border-success transition-all">
                <div class="flex justify-between items-start mb-4">
                    <div class="p-2 bg-success/10 text-success rounded-lg">
                        <span class="material-symbols-outlined">speed</span>
                    </div>
                    <span class="text-[10px] font-bold text-slate-400 font-label">AVG KM/H</span>
                </div>
                <h4 class="font-label uppercase text-[0.78rem] font-medium text-slate-500 mb-1 tracking-wider">Speed</h4>
                <div class="flex items-baseline gap-2">
                    <span class="text-2xl sm:text-4xl font-extrabold font-headline text-slate-900 tabular-nums tracking-tight">{{ "%.1f"|format(speed) }}</span>
                </div>
                <p class="text-xs text-slate-400 mt-2">Effective door-to-door speed</p>
            </div>
            <!-- Reliability -->
            <div class="bg-white p-6 rounded-xl border border-slate-200 shadow-sm group hover:border-info transition-all">
                <div class="flex justify-between items-start mb-4">
                    <div class="p-2 bg-info/10 text-info rounded-lg">
                        <span class="material-symbols-outlined">schedule</span>
                    </div>
                    <span class="text-[10px] font-bold text-slate-400 font-label">VARIANCE</span>
                </div>
                <h4 class="font-label uppercase text-[0.78rem] font-medium text-slate-500 mb-1 tracking-wider">Reliability (CV)</h4>
                <div class="flex items-baseline gap-2">
                    <span class="text-2xl sm:text-4xl font-extrabold font-headline text-slate-900 tabular-nums tracking-tight">{{ "%.2f"|format(reliability_cv) }}</span>
                </div>
                <p class="text-xs text-slate-400 mt-2">Lower is more consistent</p>
            </div>
        </div>
    </section>

    {% if da %}
    <!-- ============================================================ -->
    <!-- KEY FINDINGS                                                  -->
    <!-- ============================================================ -->
    <section>
        <div class="flex items-center gap-4 mb-6">
            <h2 class="font-headline font-bold text-xl text-slate-900">Key Findings</h2>
            <div class="h-px flex-1 bg-slate-200"></div>
        </div>
        <div class="bg-white rounded-xl shadow-sm border border-slate-200 border-l-[6px] border-l-primary p-5 sm:p-8 lg:p-10">
            <div class="flex items-start gap-4 mb-6">
                <span class="material-symbols-outlined text-primary text-3xl">lightbulb</span>
                <h3 class="font-headline font-bold text-2xl text-slate-900 tracking-tight">Analysis Narrative</h3>
            </div>
            <div class="space-y-4 text-slate-600 leading-relaxed max-w-4xl">
                {% for para in da.narrative %}
                <p class="text-[0.93rem]">{{ para }}</p>
                {% endfor %}
            </div>
        </div>
    </section>
    {% endif %}

    <!-- ============================================================ -->
    <!-- SCORE BREAKDOWN                                               -->
    <!-- ============================================================ -->
    <section>
        <div class="flex items-center gap-4 mb-6">
            <h2 class="font-headline font-bold text-xl text-slate-900">Score Breakdown</h2>
            <div class="h-px flex-1 bg-slate-200"></div>
        </div>
        <div class="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
            <div class="h-48"><canvas id="chart-scores"></canvas></div>
        </div>
    </section>

    {% if da %}
    <!-- ============================================================ -->
    <!-- WALK SCORE CLASSIFICATION                                     -->
    <!-- ============================================================ -->
    <section>
        <div class="flex items-center gap-4 mb-6">
            <h2 class="font-headline font-bold text-xl text-slate-900">Walk Score Transit Score Classification</h2>
            <div class="h-px flex-1 bg-slate-200"></div>
        </div>
        <p class="text-slate-500 mb-4 text-sm">The TQI maps to the Walk Score Transit Score scale, a widely-used 0&ndash;100 index of transit accessibility.</p>
        <div class="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <table class="w-full text-left border-collapse">
                <thead>
                    <tr class="bg-slate-50">
                        <th class="px-6 py-4 font-label text-[0.78rem] uppercase tracking-wider text-slate-500 font-semibold">Score</th>
                        <th class="px-6 py-4 font-label text-[0.78rem] uppercase tracking-wider text-slate-500 font-semibold">Category</th>
                        <th class="px-6 py-4 font-label text-[0.78rem] uppercase tracking-wider text-slate-500 font-semibold">Meaning</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-slate-100">
                    {% for low, high, name, desc in walkscore_ranges %}
                    <tr class="{% if tqi >= low and tqi <= high %}bg-warning/5 font-semibold{% endif %} hover:bg-slate-50 transition-colors">
                        <td class="px-6 py-3 tabular-nums {% if tqi >= low and tqi <= high %}text-warning font-extrabold{% else %}text-slate-700{% endif %}">{{ low }}&ndash;{{ high }}</td>
                        <td class="px-6 py-3 {% if tqi >= low and tqi <= high %}text-slate-900 font-bold{% else %}text-slate-700{% endif %}">{{ name }}</td>
                        <td class="px-6 py-3 text-slate-500">{{ desc }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        <p class="text-xs text-slate-400 italic mt-2">Source: Walk Score Transit Score Methodology (walkscore.com)</p>
    </section>

    <!-- ============================================================ -->
    <!-- ROUTE-LEVEL SERVICE QUALITY (TCQSM)                          -->
    <!-- ============================================================ -->
    {% if da.route_los %}
    <section>
        <div class="flex items-center gap-4 mb-6">
            <h2 class="font-headline font-bold text-xl text-slate-900">Route-Level Service Quality (TCQSM)</h2>
            <div class="h-px flex-1 bg-slate-200"></div>
        </div>
        <p class="text-slate-500 mb-6 text-sm">Each route graded per the Transit Capacity and Quality of Service Manual (TCRP Report 165) based on median headway.</p>

        <div class="grid grid-cols-1 lg:grid-cols-4 gap-6">
            <!-- Route LOS Bars (HTML) -->
            <div class="lg:col-span-3 bg-white border border-slate-200 rounded-xl shadow-sm p-6 overflow-hidden">
                <div class="flex items-center justify-between mb-8">
                    <div>
                        <h3 class="text-lg font-bold text-slate-900 font-headline">Headway by Route</h3>
                        <p class="text-sm text-slate-500">Median headway in minutes</p>
                    </div>
                    <span class="text-[10px] font-label text-slate-400 uppercase tracking-widest">Scale: 0&ndash;80 min</span>
                </div>
                <div class="space-y-4">
                    {% for r in da.route_los %}
                    <div class="flex items-center group">
                        <div class="w-24 sm:w-40 pr-2 sm:pr-4 text-right shrink-0">
                            <p class="text-sm font-bold text-slate-800 leading-tight">Route {{ r.route_name }}</p>
                            <p class="text-[10px] text-slate-400 uppercase tracking-tighter truncate">{{ r.route_long_name }}</p>
                        </div>
                        <div class="flex-1 relative h-8 bg-slate-50 rounded-r-lg overflow-hidden flex items-center">
                            {% set bar_pct = [r.median_headway_min, 80] | min / 80 * 100 %}
                            {% if r.los_grade in ['A', 'B'] %}
                                {% set bar_color = 'bg-emerald-500' %}
                            {% elif r.los_grade == 'C' %}
                                {% set bar_color = 'bg-lime-500' %}
                            {% elif r.los_grade == 'D' %}
                                {% set bar_color = 'bg-amber-500' %}
                            {% elif r.los_grade == 'E' %}
                                {% set bar_color = 'bg-orange-500' %}
                            {% else %}
                                {% set bar_color = 'bg-rose-600' %}
                            {% endif %}
                            <div class="h-full {{ bar_color }}/80 group-hover:{{ bar_color }} transition-all duration-500" style="width: {{ "%.1f"|format(bar_pct) }}%"></div>
                            <div class="ml-2 flex items-center gap-2 shrink-0">
                                <span class="tabular-nums font-extrabold text-slate-900">{{ "%.0f"|format(r.median_headway_min) }}</span>
                                <span class="px-2 py-0.5 rounded-full {{ bar_color }} text-[10px] text-white font-bold">LOS {{ r.los_grade }}</span>
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>

            <!-- LOS Legend -->
            <div class="flex flex-col gap-6">
                {% if da.system_los_summary %}
                <div class="bg-white border border-slate-200 rounded-xl shadow-sm p-6">
                    <p class="font-label text-[10px] uppercase tracking-widest text-slate-500 mb-1">Overall System LOS</p>
                    <div class="flex items-baseline gap-2">
                        <span class="text-3xl sm:text-4xl font-extrabold text-slate-900 font-headline">{{ da.system_los_summary.best_grade }}</span>
                        <span class="text-sm font-medium text-orange-500">Best route grade ({{ da.system_los_summary.worst_grade }} worst)</span>
                    </div>
                    <div class="mt-4 pt-4 border-t border-slate-100">
                        <div class="flex justify-between text-xs mb-1">
                            <span class="text-slate-500">Avg. Headway</span>
                            <span class="font-bold text-slate-900">{{ "%.1f"|format(da.system_los_summary.median_system_headway_min) }} min</span>
                        </div>
                        <div class="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
                            <div class="h-full bg-orange-500 rounded-full" style="width: {{ [da.system_los_summary.median_system_headway_min / 80 * 100, 100] | min }}%"></div>
                        </div>
                    </div>
                </div>
                {% endif %}
                <div class="bg-slate-900 text-white rounded-xl shadow-sm overflow-hidden flex-1">
                    <div class="p-5 border-b border-slate-800">
                        <h3 class="font-bold text-sm">LOS Reference</h3>
                        <p class="text-[10px] text-slate-400 font-label uppercase tracking-wider">TCQSM Standards</p>
                    </div>
                    <table class="w-full text-left border-collapse">
                        <tbody class="text-[11px]">
                            <tr class="border-b border-slate-800 hover:bg-slate-800/50 transition-colors">
                                <td class="p-3 font-bold text-emerald-500">A</td>
                                <td class="p-3">&lt;10 min</td>
                                <td class="p-3 text-slate-400">High Frequency</td>
                            </tr>
                            <tr class="border-b border-slate-800 hover:bg-slate-800/50 transition-colors">
                                <td class="p-3 font-bold text-emerald-400">B</td>
                                <td class="p-3">10&ndash;14 min</td>
                                <td class="p-3 text-slate-400">Frequent</td>
                            </tr>
                            <tr class="border-b border-slate-800 hover:bg-slate-800/50 transition-colors">
                                <td class="p-3 font-bold text-lime-400">C</td>
                                <td class="p-3">15&ndash;20 min</td>
                                <td class="p-3 text-slate-400">Standard Urban</td>
                            </tr>
                            <tr class="border-b border-slate-800 hover:bg-slate-800/50 transition-colors">
                                <td class="p-3 font-bold text-amber-500">D</td>
                                <td class="p-3">21&ndash;30 min</td>
                                <td class="p-3 text-slate-400">Basic Service</td>
                            </tr>
                            <tr class="border-b border-slate-800 hover:bg-slate-800/50 transition-colors">
                                <td class="p-3 font-bold text-orange-500">E</td>
                                <td class="p-3">31&ndash;60 min</td>
                                <td class="p-3 text-slate-400">Low Frequency</td>
                            </tr>
                            <tr class="hover:bg-slate-800/50 transition-colors">
                                <td class="p-3 font-bold text-rose-500">F</td>
                                <td class="p-3">&gt;60 min</td>
                                <td class="p-3 text-slate-400">Poor Service</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        <p class="text-xs text-slate-400 italic mt-2">Source: TCRP Report 165, Transit Capacity and Quality of Service Manual, 3rd Edition (Transportation Research Board)</p>
    </section>
    {% endif %}

    <!-- ============================================================ -->
    <!-- PTAL                                                          -->
    <!-- ============================================================ -->
    {% if da and da.ptal_distribution %}
    <section>
        <div class="flex items-center gap-4 mb-6">
            <h2 class="font-headline font-bold text-xl text-slate-900">Public Transport Accessibility Level (PTAL)</h2>
            <div class="h-px flex-1 bg-slate-200"></div>
        </div>
        <p class="text-slate-500 mb-4 text-sm">Each grid point scored using the Transport for London PTAL methodology, which measures the density of transit service accessible on foot based on walk time to stops, service frequency, and route availability.</p>
        <div class="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
            <div class="h-72"><canvas id="chart-ptal"></canvas></div>
        </div>
        <p class="text-xs text-slate-400 italic mt-2">Source: Transport for London PTAL methodology (originally Hammersmith &amp; Fulham, 1992; now TfL standard, adopted internationally)</p>
    </section>
    {% endif %}

    <!-- ============================================================ -->
    <!-- COVERAGE ANALYSIS                                             -->
    <!-- ============================================================ -->
    <section>
        <div class="flex items-center gap-4 mb-6">
            <h2 class="font-headline font-bold text-xl text-slate-900">Coverage Analysis</h2>
            <div class="h-px flex-1 bg-slate-200"></div>
        </div>
        <p class="text-slate-500 mb-4 text-sm">Transit coverage within Chilliwack's municipal boundary (800m walk-to-stop threshold).</p>
        <div class="grid grid-cols-2 md:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-6">
            <div class="bg-white border border-slate-200 p-4 sm:p-6 rounded-xl shadow-sm">
                <div class="mb-3">
                    <span class="text-2xl sm:text-4xl font-extrabold text-slate-900 tabular-nums tracking-tighter">{{ "{:,}".format(da.n_grid_points) }}</span>
                </div>
                <span class="font-label uppercase text-[0.78rem] tracking-widest text-slate-500 font-medium">Grid points analyzed (250m spacing)</span>
            </div>
            <div class="bg-white border border-slate-200 p-6 rounded-xl shadow-sm">
                <div class="mb-3">
                    <span class="text-2xl sm:text-4xl font-extrabold text-slate-900 tabular-nums tracking-tighter">{{ "{:,}".format(da.n_stops) }}</span>
                </div>
                <span class="font-label uppercase text-[0.78rem] tracking-widest text-slate-500 font-medium">Transit stops in network</span>
            </div>
            <div class="bg-white border border-slate-200 p-6 rounded-xl shadow-sm border-l-4 border-l-danger">
                <div class="mb-3">
                    <span class="text-2xl sm:text-4xl font-extrabold text-danger tabular-nums tracking-tighter">{{ "%.0f"|format(da.transit_desert_pct) }}%</span>
                </div>
                <span class="font-label uppercase text-[0.78rem] tracking-widest text-slate-500 font-medium">Transit deserts (no stop within 800m)</span>
            </div>
            <div class="bg-white border border-slate-200 p-6 rounded-xl shadow-sm">
                <div class="mb-3">
                    <span class="text-2xl sm:text-4xl font-extrabold text-slate-900 tabular-nums tracking-tighter">{{ "{:,}".format(da.n_origins_with_service) }}</span>
                </div>
                <span class="font-label uppercase text-[0.78rem] tracking-widest text-slate-500 font-medium">Locations with any transit access</span>
            </div>
            <div class="bg-white border border-slate-200 p-6 rounded-xl shadow-sm border-l-4 border-l-warning">
                <div class="mb-3">
                    <span class="text-2xl sm:text-4xl font-extrabold text-warning tabular-nums tracking-tighter">{{ "%.1f"|format(da.reachability_rate_pct) }}%</span>
                </div>
                <span class="font-label uppercase text-[0.78rem] tracking-widest text-slate-500 font-medium">OD pairs reachable within 90 min</span>
            </div>
            <div class="bg-white border border-slate-200 p-6 rounded-xl shadow-sm">
                <div class="mb-3">
                    <span class="text-2xl sm:text-4xl font-extrabold text-slate-900 tabular-nums tracking-tighter">{{ "%.0f"|format(da.max_origin_reachability_pct) }}%</span>
                </div>
                <span class="font-label uppercase text-[0.78rem] tracking-widest text-slate-500 font-medium">Best single-location reachability</span>
            </div>
        </div>
    </section>

    <!-- ============================================================ -->
    <!-- SPEED ANALYSIS                                                -->
    <!-- ============================================================ -->
    <section>
        <div class="flex items-center gap-4 mb-6">
            <h2 class="font-headline font-bold text-xl text-slate-900">Speed Analysis</h2>
            <div class="h-px flex-1 bg-slate-200"></div>
        </div>
        <p class="text-slate-500 mb-4 text-sm">Effective door-to-door transit speed compared to walking (5 km/h) and driving (~40 km/h).</p>
        <div class="bg-white rounded-xl border border-slate-200 shadow-sm p-6 mb-6">
            <div class="h-72"><canvas id="chart-tsr"></canvas></div>
        </div>
        <div class="grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-6 mb-6">
            <div class="bg-white border border-slate-200 p-4 sm:p-6 rounded-xl shadow-sm {% if da.mean_tsr < 5 %}border-l-4 border-l-danger{% elif da.mean_tsr < 10 %}border-l-4 border-l-warning{% else %}border-l-4 border-l-success{% endif %}">
                <div class="mb-3">
                    <span class="text-2xl sm:text-4xl font-extrabold tabular-nums tracking-tighter {% if da.mean_tsr < 5 %}text-danger{% elif da.mean_tsr < 10 %}text-warning{% else %}text-success{% endif %}">{{ "%.1f"|format(da.mean_tsr) }}</span>
                    <span class="text-sm text-slate-400 ml-1">km/h</span>
                </div>
                <span class="font-label uppercase text-[0.78rem] tracking-widest text-slate-500 font-medium">Mean effective speed (TSR)</span>
            </div>
            <div class="bg-white border border-slate-200 p-6 rounded-xl shadow-sm">
                <div class="mb-3">
                    <span class="text-2xl sm:text-4xl font-extrabold text-slate-900 tabular-nums tracking-tighter">{{ "%.1f"|format(da.median_tsr) }}</span>
                    <span class="text-sm text-slate-400 ml-1">km/h</span>
                </div>
                <span class="font-label uppercase text-[0.78rem] tracking-widest text-slate-500 font-medium">Median effective speed</span>
            </div>
            <div class="bg-white border border-slate-200 p-6 rounded-xl shadow-sm border-l-4 border-l-danger">
                <div class="mb-3">
                    <span class="text-2xl sm:text-4xl font-extrabold text-danger tabular-nums tracking-tighter">{{ "%.0f"|format(da.tsr_slower_than_walking_pct) }}%</span>
                </div>
                <span class="font-label uppercase text-[0.78rem] tracking-widest text-slate-500 font-medium">Trips slower than walking</span>
            </div>
            <div class="bg-white border border-slate-200 p-6 rounded-xl shadow-sm">
                <div class="mb-3">
                    <span class="text-2xl sm:text-4xl font-extrabold text-slate-900 tabular-nums tracking-tighter">{{ "%.0f"|format(da.mean_travel_time_min) }}</span>
                    <span class="text-sm text-slate-400 ml-1">min</span>
                </div>
                <span class="font-label uppercase text-[0.78rem] tracking-widest text-slate-500 font-medium">Mean trip duration (reachable)</span>
            </div>
        </div>
        <div class="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
            <h3 class="text-lg font-bold text-slate-900 font-headline mb-4">Travel Time Distribution</h3>
            <div class="h-64"><canvas id="chart-travel-time"></canvas></div>
        </div>
    </section>
    {% endif %}

    <!-- ============================================================ -->
    <!-- TIME-OF-DAY PROFILE                                           -->
    <!-- ============================================================ -->
    <section>
        <div class="flex items-center gap-4 mb-6">
            <h2 class="font-headline font-bold text-xl text-slate-900">Time-of-Day Profile</h2>
            <div class="h-px flex-1 bg-slate-200"></div>
        </div>
        <p class="text-slate-500 mb-4 text-sm">How transit quality varies throughout the day (6:00 AM &ndash; 10:00 PM).</p>
        <div class="bg-white rounded-xl border border-slate-200 shadow-sm p-6 mb-6">
            <div class="h-64"><canvas id="chart-time-profile"></canvas></div>
        </div>
        {% if da %}
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-6">
            <div class="bg-white border border-slate-200 p-6 rounded-xl shadow-sm border-l-4 border-l-success">
                <div class="flex items-center gap-3 mb-2">
                    <span class="material-symbols-outlined text-success">trending_up</span>
                    <span class="font-label uppercase text-[0.78rem] tracking-widest text-slate-500 font-medium">Peak time slot</span>
                </div>
                <span class="text-2xl font-extrabold text-slate-900">{{ da.peak_slot }}</span>
                <p class="text-xs text-slate-400 mt-1">TQI {{ "%.1f"|format(da.peak_tqi) }}</p>
            </div>
            <div class="bg-white border border-slate-200 p-6 rounded-xl shadow-sm border-l-4 border-l-danger">
                <div class="flex items-center gap-3 mb-2">
                    <span class="material-symbols-outlined text-danger">trending_down</span>
                    <span class="font-label uppercase text-[0.78rem] tracking-widest text-slate-500 font-medium">Lowest time slot</span>
                </div>
                <span class="text-2xl font-extrabold text-slate-900">{{ da.lowest_slot }}</span>
                <p class="text-xs text-slate-400 mt-1">TQI {{ "%.1f"|format(da.lowest_tqi) }}</p>
            </div>
        </div>
        {% endif %}
    </section>

    <!-- ============================================================ -->
    <!-- SPATIAL HEAT MAP (full)                                       -->
    <!-- ============================================================ -->
    <section>
        <div class="flex items-center gap-4 mb-6">
            <h2 class="font-headline font-bold text-xl text-slate-900">Spatial Heat Map</h2>
            <div class="h-px flex-1 bg-slate-200"></div>
        </div>
        <p class="text-slate-500 mb-4 text-sm">Per-location transit connectivity within city limits. Toggle stop markers with the layer control.</p>
        <div class="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <iframe src="heatmap.html" class="w-full border-none map-frame" style="height:350px" onload="if(window.innerWidth>=640)this.style.height='560px'"></iframe>
        </div>
    </section>

    {% if da and da.top_origins %}
    <!-- Best-Connected Locations -->
    <section>
        <div class="flex items-center gap-4 mb-6">
            <h3 class="font-headline font-bold text-lg text-slate-900">Best-Connected Locations</h3>
            <div class="h-px flex-1 bg-slate-200"></div>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {% for loc in da.top_origins %}
            <div class="bg-white border border-slate-200 rounded-xl p-4 shadow-sm flex justify-between items-center">
                <span class="text-sm text-slate-700 tabular-nums">{{ "%.4f"|format(loc.lat) }}, {{ "%.4f"|format(loc.lon) }}</span>
                <span class="text-sm font-extrabold text-primary tabular-nums">{{ "%.1f"|format(loc.reachability_pct) }}%</span>
            </div>
            {% endfor %}
        </div>
    </section>
    {% endif %}

    <!-- ============================================================ -->
    <!-- ISOCHRONE MAPS                                                -->
    <!-- ============================================================ -->
    <section>
        <div class="flex items-center gap-4 mb-6">
            <h2 class="font-headline font-bold text-xl text-slate-900">Isochrone Maps &mdash; Downtown Exchange</h2>
            <div class="h-px flex-1 bg-slate-200"></div>
        </div>
        <p class="text-slate-500 mb-6 text-sm">From the Chilliwack Downtown Exchange, here is everywhere reachable by transit within 15/30/45/60/90 minutes. Walking-only trips are excluded &mdash; only trips where transit is faster than walking are shown.</p>
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div class="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
                <div class="p-4 border-b border-slate-100 flex items-center gap-3">
                    <span class="px-2 py-1 bg-primary text-white text-[10px] font-bold rounded">MORNING PEAK</span>
                    <h3 class="font-bold text-slate-900">AM Peak (8:00 AM)</h3>
                </div>
                <iframe src="isochrone_0800_AM_Peak.html" class="w-full border-none map-frame" style="height:300px" onload="if(window.innerWidth>=640)this.style.height='450px'"></iframe>
            </div>
            <div class="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
                <div class="p-4 border-b border-slate-100 flex items-center gap-3">
                    <span class="px-2 py-1 bg-info text-white text-[10px] font-bold rounded">MIDDAY BASE</span>
                    <h3 class="font-bold text-slate-900">Midday (12:00 PM)</h3>
                </div>
                <iframe src="isochrone_1200_Midday.html" class="w-full border-none map-frame" style="height:300px" onload="if(window.innerWidth>=640)this.style.height='450px'"></iframe>
            </div>
        </div>
    </section>

    <!-- ============================================================ -->
    <!-- ACCESS TO ESSENTIAL SERVICES                                  -->
    <!-- ============================================================ -->
    {% if amenities %}
    <section>
        <div class="flex items-center gap-4 mb-6">
            <h2 class="font-headline font-bold text-xl text-slate-900">Access to Essential Services</h2>
            <div class="h-px flex-1 bg-slate-200"></div>
        </div>
        <p class="text-slate-500 mb-4 text-sm">What percentage of city locations can reach key destinations by transit (faster than walking).</p>
        <div class="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div class="overflow-x-auto">
                <table class="w-full text-left border-collapse">
                    <thead>
                        <tr class="bg-slate-50">
                            <th class="px-6 py-4 font-label text-[0.78rem] uppercase tracking-wider text-slate-500 font-semibold">Destination</th>
                            <th class="px-6 py-4 font-label text-[0.78rem] uppercase tracking-wider text-slate-500 font-semibold">Category</th>
                            <th class="px-6 py-4 font-label text-[0.78rem] uppercase tracking-wider text-slate-500 font-semibold">Within 30 min</th>
                            <th class="px-6 py-4 font-label text-[0.78rem] uppercase tracking-wider text-slate-500 font-semibold">Within 45 min</th>
                            <th class="px-6 py-4 font-label text-[0.78rem] uppercase tracking-wider text-slate-500 font-semibold">Within 60 min</th>
                            <th class="px-6 py-4 font-label text-[0.78rem] uppercase tracking-wider text-slate-500 font-semibold">Median Time</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-100">
                        {% for a in amenities %}
                        <tr class="{% if loop.index is odd %}{% else %}bg-slate-50/50{% endif %} hover:bg-slate-50 transition-colors">
                            <td class="px-6 py-4 font-bold text-slate-900">{{ a.name }}</td>
                            <td class="px-6 py-4 text-slate-400 font-medium">{{ a.category }}</td>
                            <td class="px-6 py-4 tabular-nums font-extrabold {% if a.pct_within_30min < 5 %}text-danger{% elif a.pct_within_30min < 10 %}text-amber-500{% else %}text-success{% endif %}">{{ "%.1f"|format(a.pct_within_30min) }}%</td>
                            <td class="px-6 py-4 tabular-nums font-extrabold {% if a.pct_within_45min < 8 %}text-amber-500{% else %}text-success{% endif %}">{{ "%.1f"|format(a.pct_within_45min) }}%</td>
                            <td class="px-6 py-4 tabular-nums font-extrabold {% if a.pct_within_60min < 10 %}text-amber-500{% else %}text-success{% endif %}">{{ "%.1f"|format(a.pct_within_60min) }}%</td>
                            <td class="px-6 py-4 tabular-nums text-slate-700">{% if a.median_travel_time %}{{ "%.0f"|format(a.median_travel_time) }} min{% else %}&mdash;{% endif %}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </section>
    {% endif %}

    <!-- ============================================================ -->
    <!-- EQUITY OVERLAY                                                -->
    <!-- ============================================================ -->
    {% if has_equity %}
    <section>
        <div class="flex items-center gap-4 mb-6">
            <h2 class="font-headline font-bold text-xl text-slate-900">Equity Overlay</h2>
            <div class="h-px flex-1 bg-slate-200"></div>
        </div>
        <p class="text-slate-500 mb-4 text-sm">Transit quality cross-referenced with census income data by Dissemination Area.</p>
        <div class="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <iframe src="equity_map.html" class="w-full border-none map-frame" style="height:350px" onload="if(window.innerWidth>=640)this.style.height='560px'"></iframe>
        </div>
        {% if tqi_income_corr is not none %}
        <div class="mt-4 bg-white border border-slate-200 rounded-xl shadow-sm p-6 inline-flex items-center gap-4">
            <span class="material-symbols-outlined text-info text-2xl">analytics</span>
            <div>
                <span class="font-label uppercase text-[0.78rem] tracking-widest text-slate-500 font-medium block">TQI&ndash;Income Correlation (Pearson r)</span>
                <span class="text-2xl font-extrabold text-slate-900 tabular-nums">{{ "%.3f"|format(tqi_income_corr) }}</span>
            </div>
        </div>
        {% endif %}
    </section>
    {% endif %}

    <!-- ============================================================ -->
    <!-- TEMPORAL RELIABILITY                                          -->
    <!-- ============================================================ -->
    <section>
        <div class="flex items-center gap-4 mb-6">
            <h2 class="font-headline font-bold text-xl text-slate-900">Temporal Reliability</h2>
            <div class="h-px flex-1 bg-slate-200"></div>
        </div>
        <p class="text-slate-500 mb-4 text-sm">Distribution of travel time variability (coefficient of variation) across grid points.</p>
        <div class="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
            <div class="h-64"><canvas id="chart-reliability"></canvas></div>
        </div>
    </section>

    <!-- ============================================================ -->
    <!-- METHODOLOGY                                                   -->
    <!-- ============================================================ -->
    <section>
        <div class="flex items-center gap-4 mb-6">
            <h2 class="font-headline font-bold text-xl text-slate-900">Methodology</h2>
            <div class="h-px flex-1 bg-slate-200"></div>
        </div>
        <div class="bg-white rounded-xl shadow-sm border border-slate-200 border-l-[6px] border-l-primary p-8 lg:p-10 space-y-4">
            <div class="flex items-start gap-4 mb-4">
                <span class="material-symbols-outlined text-primary text-2xl">science</span>
                <h3 class="font-headline font-bold text-xl text-slate-900">How this score is computed</h3>
            </div>
            <p class="text-[0.93rem] text-slate-600 leading-relaxed">The TQI analyzes every origin-destination pair across a {{ "{:,}".format(da.n_grid_points) if da else "" }}-point grid covering Chilliwack's municipal boundary at 250m spacing. For each pair, at each of 64 departure times (every 15 minutes from 6 AM to 10 PM on a typical Wednesday), the RAPTOR algorithm finds the fastest transit trip including walking to/from stops, wait time, in-vehicle time, and up to 2 transfers.</p>
            <p class="text-[0.93rem] text-slate-600 leading-relaxed">The <strong class="text-slate-800">Transit Speed Ratio (TSR)</strong> measures effective door-to-door speed: straight-line distance divided by total transit time. The <strong class="text-slate-800">Coverage Score</strong> (0&ndash;100) is the fraction of OD pairs reachable at all. The <strong class="text-slate-800">Speed Score</strong> (0&ndash;100) normalizes mean TSR between walking speed (5 km/h = 0) and driving speed (40 km/h = 100). The <strong class="text-slate-800">TQI</strong> is 50% coverage + 50% speed.</p>
            <p class="text-[0.93rem] text-slate-600 leading-relaxed">Parameters: max walk to stop 800m, max transfer walk 400m, max trip 90 min, max 2 transfers, walk speed 5 km/h. Data: BC Transit GTFS (Operator 13, Fraser Valley Region), filtered to Chilliwack routes. Municipal boundary: City of Chilliwack Open Data.</p>
        </div>
    </section>

    <!-- ============================================================ -->
    <!-- STANDARDS & SOURCES                                           -->
    <!-- ============================================================ -->
    <section>
        <div class="flex items-center gap-4 mb-6">
            <h2 class="font-headline font-bold text-xl text-slate-900">Standards &amp; Sources</h2>
            <div class="h-px flex-1 bg-slate-200"></div>
        </div>
        <div class="bg-white rounded-xl shadow-sm border border-slate-200 border-l-[6px] border-l-info p-8 lg:p-10 space-y-4">
            <div class="flex items-start gap-4 mb-4">
                <span class="material-symbols-outlined text-info text-2xl">menu_book</span>
                <h3 class="font-headline font-bold text-xl text-slate-900">Established frameworks referenced in this report</h3>
            </div>
            <p class="text-[0.93rem] text-slate-600 leading-relaxed"><strong class="text-slate-800">Walk Score Transit Score</strong> &mdash; 0&ndash;100 transit accessibility scale developed by Walk Score (Redfin). Uses GTFS data to measure transit service quality. Categories: Minimal Transit (0&ndash;24), Some Transit (25&ndash;49), Good Transit (50&ndash;69), Excellent Transit (70&ndash;89), Rider's Paradise (90&ndash;100). <em class="text-slate-400">walkscore.com/transit-score-methodology.shtml</em></p>
            <p class="text-[0.93rem] text-slate-600 leading-relaxed"><strong class="text-slate-800">TCQSM Level of Service</strong> &mdash; Transit Capacity and Quality of Service Manual, 3rd Edition (TCRP Report 165, Transportation Research Board, 2013). Grades transit routes A&ndash;F based on service frequency, with LOS C (15&ndash;20 min headway) as the maximum desirable wait and LOS D+ as unattractive to choice riders.</p>
            <p class="text-[0.93rem] text-slate-600 leading-relaxed"><strong class="text-slate-800">PTAL</strong> &mdash; Public Transport Accessibility Level. Developed by London Borough of Hammersmith &amp; Fulham (1992), adopted as standard by Transport for London. Measures accessibility based on walk time to stops and service frequency using Equivalent Doorstep Frequency (EDF). Grades 1a (extremely poor) to 6b (excellent). Used internationally in London, Australia, India, and Greater Manchester.</p>
            <p class="text-[0.93rem] text-slate-600 leading-relaxed"><strong class="text-slate-800">RAPTOR Algorithm</strong> &mdash; Delling, D., Pajor, T., &amp; Werneck, R. (2012). "Round-Based Public Transit Routing." ALENEX. The routing engine used to compute transit travel times.</p>
        </div>
    </section>

    <!-- ============================================================ -->
    <!-- FOOTER                                                        -->
    <!-- ============================================================ -->
    <footer class="border-t border-slate-200 pt-8 pb-4">
        <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 bg-primary rounded-lg flex items-center justify-center text-white">
                    <span class="material-symbols-outlined">directions_bus</span>
                </div>
                <div>
                    <p class="font-headline font-bold text-slate-900 text-sm">Chilliwack Transit Quality Index</p>
                    <p class="text-xs text-slate-400">v0.1.0</p>
                </div>
            </div>
            <p class="text-xs text-slate-400 max-w-lg">Generated using Walk Score, TCQSM, and PTAL established frameworks applied to BC Transit GTFS data. This report is for informational and planning purposes.</p>
        </div>
    </footer>

</div>
</body>
</html>"""


def _build_chart_data(result: TQIResult, detailed: DetailedAnalysis | None) -> dict:
    """Build JSON-serializable chart data for Chart.js."""
    data = {}

    # Time-of-day profile
    data["time_profile"] = {
        "labels": [tp[0] for tp in result.time_profile],
        "values": [round(tp[1], 3) for tp in result.time_profile],
    }

    # Score breakdown
    data["scores"] = {
        "coverage": round(result.coverage_score, 2),
        "speed": round(result.speed_score, 2),
        "tqi": round(result.tqi, 2),
    }

    # Reliability histogram
    valid_cv = [v for v in result.reliability_per_origin if v > 0]
    if valid_cv:
        counts, edges = np.histogram(valid_cv, bins=25)
        data["reliability"] = {
            "labels": [f"{edges[i]:.2f}" for i in range(len(counts))],
            "counts": counts.tolist(),
        }

    if detailed:
        # TSR distribution
        data["tsr"] = {
            "slower": round(detailed.tsr_slower_than_walking_pct, 1),
            "band_5_10": round(detailed.tsr_5_to_10_pct, 1),
            "band_10_20": round(detailed.tsr_10_to_20_pct, 1),
            "band_20_plus": round(detailed.tsr_20_plus_pct, 1),
        }

        # Travel time percentiles
        if detailed.travel_time_percentiles:
            pcts = sorted(detailed.travel_time_percentiles.keys())
            data["travel_time"] = {
                "labels": [f"P{p}" for p in pcts],
                "values": [round(detailed.travel_time_percentiles[p], 1) for p in pcts],
            }

        # PTAL distribution
        if detailed.ptal_distribution:
            grades = ["1a", "1b", "2", "3", "4", "5", "6a", "6b"]
            data["ptal"] = {
                "labels": grades,
                "counts": [detailed.ptal_distribution.get(g, 0) for g in grades],
            }

    return data


def generate_report(
    result: TQIResult,
    output_dir: Path = OUTPUT_DIR,
    has_equity: bool = False,
    tqi_income_corr: float | None = None,
    detailed: DetailedAnalysis | None = None,
    amenity_results: list[dict] | None = None,
) -> Path:
    """Generate the HTML report with interactive Chart.js charts."""
    output_dir.mkdir(parents=True, exist_ok=True)

    chart_data = _build_chart_data(result, detailed)

    template = Template(REPORT_TEMPLATE)
    html = template.render(
        tqi=result.tqi,
        coverage=result.coverage_score,
        speed=result.speed_score,
        reliability_cv=result.reliability_mean_cv,
        chart_data_json=json.dumps(chart_data),
        has_equity=has_equity,
        tqi_income_corr=tqi_income_corr,
        da=detailed,
        walkscore_ranges=WALKSCORE_RANGES,
        amenities=amenity_results,
    )

    report_path = output_dir / "report.html"
    report_path.write_text(html)
    print(f"Report written to {report_path}")
    return report_path
