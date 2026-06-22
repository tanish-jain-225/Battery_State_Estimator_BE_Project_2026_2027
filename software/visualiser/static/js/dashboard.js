// Battery State Estimator Dashboard Control & Visualization Script

document.addEventListener('DOMContentLoaded', () => {
    // UI Elements
    const mismatchSelect = document.getElementById('mismatch-select');
    const quantizeSelect = document.getElementById('quantize-select');

    // Simulator Control Center Elements
    const btnStart = document.getElementById('btn-start');
    const btnPause = document.getElementById('btn-pause');
    const btnStop = document.getElementById('btn-stop');
    const btnReset = document.getElementById('btn-reset');

    const chemSelect = document.getElementById('chem-select');
    const cycleSelect = document.getElementById('cycle-select');
    const agingToggle = document.getElementById('aging-toggle');
    const tempSlider = document.getElementById('temp-slider');
    const valAmbientTemp = document.getElementById('val-ambient-temp');

    const faultShortToggle = document.getElementById('fault-short-toggle');
    const faultThermalToggle = document.getElementById('fault-thermal-toggle');
    const faultDropoutToggle = document.getElementById('fault-dropout-toggle');
    
    const simBadge = document.getElementById('sim-status-badge');
    const simPortBadge = document.getElementById('sim-port-badge');
    const dbBadge = document.getElementById('db-status-badge');
    const modelBadge = document.getElementById('model-status-badge');
    const mlWarningBanner = document.getElementById('ml-warning-banner');
    
    const valVoltage = document.getElementById('val-voltage');
    const valCurrent = document.getElementById('val-current');
    const valTemp = document.getElementById('val-temp');
    const valTime = document.getElementById('val-time');
    
    const valEkfSoc = document.getElementById('val-ekf-soc');
    const valEsnSoc = document.getElementById('val-esn-soc');
    const valEkfSoh = document.getElementById('val-ekf-soh');
    const valEsnSoh = document.getElementById('val-esn-soh');

    // Advanced Estimations selectors
    const valEkfSoe = document.getElementById('val-ekf-soe');
    const valEsnSoe = document.getElementById('val-esn-soe');
    const valEnergyRem = document.getElementById('val-energy-rem');
    const valSopDischarge = document.getElementById('val-sop-discharge');
    const valSopCharge = document.getElementById('val-sop-charge');
    const valSopCurrents = document.getElementById('val-sop-currents');
    const valEkfRul = document.getElementById('val-ekf-rul');
    const valEsnRul = document.getElementById('val-esn-rul');
    const valRulStatus = document.getElementById('val-rul-status');

    // Large top summary fields
    const valTrueSocLarge = document.getElementById('val-true-soc-large');
    const valTrueSohLarge = document.getElementById('val-true-soh-large');
    
    // Diagnostics Elements
    const diagEnvTemp = document.getElementById('diag-env-temp');
    const diagHealthRing = document.getElementById('diag-health-ring');
    const diagStatusTitle = document.getElementById('diag-status-title');
    const diagStatusDesc = document.getElementById('diag-status-desc');
    const alarmSensor = document.getElementById('alarm-sensor');
    const alarmShort = document.getElementById('alarm-short');
    const alarmThermal = document.getElementById('alarm-thermal');

    const valEkfSocError = document.getElementById('val-ekf-soc-error');
    const valEsnSocError = document.getElementById('val-esn-soc-error');
    const valEkfSohError = document.getElementById('val-ekf-soh-error');
    const valEsnSohError = document.getElementById('val-esn-soh-error');

    // Chart Handles
    let chartSOC, chartSOH;

    // Telemetry History and Inspection States
    let telemetryHistory = [];
    let isLocked = false;
    let lockedIndex = -1;
    let isScrubbing = false;
    let scrubbedIndex = -1;

    // Configuration Settings
    let graphSliceLimit = 120;

    // Badge Elements
    const readoutModeBadge = document.getElementById('readout-mode-badge');
    const readoutModeLabel = document.getElementById('readout-mode-label');
    const btnResumeLive = document.getElementById('btn-resume-live');

    function updateBadge() {
        if (!readoutModeBadge || !readoutModeLabel) return;
        
        if (isLocked && lockedIndex !== -1 && telemetryHistory[lockedIndex]) {
            const t = Math.round(telemetryHistory[lockedIndex].time);
            readoutModeLabel.textContent = `Historical: Locked (t = ${t}s)`;
            readoutModeBadge.style.display = 'flex';
            readoutModeBadge.style.background = 'var(--accent-blue-lt)';
            readoutModeBadge.style.borderColor = 'rgba(29, 78, 216, 0.4)';
            if (btnResumeLive) btnResumeLive.style.display = 'inline-block';
        } else if (isScrubbing && scrubbedIndex !== -1 && telemetryHistory[scrubbedIndex]) {
            const t = Math.round(telemetryHistory[scrubbedIndex].time);
            readoutModeLabel.textContent = `Historical: Scrubbing (t = ${t}s)`;
            readoutModeBadge.style.display = 'flex';
            readoutModeBadge.style.background = 'rgba(241, 245, 249, 0.9)';
            readoutModeBadge.style.borderColor = 'var(--border-light)';
            if (btnResumeLive) btnResumeLive.style.display = 'inline-block';
        } else {
            readoutModeBadge.style.display = 'none';
        }
    }

    function handleChartHover(index, chart) {
        const graphDataLength = Math.min(telemetryHistory.length, graphSliceLimit);
        const actualIndex = telemetryHistory.length - graphDataLength + index;

        if (actualIndex < 0 || actualIndex >= telemetryHistory.length) return;
        isScrubbing = true;
        scrubbedIndex = actualIndex;
        
        const otherChart = (chart === chartSOC) ? chartSOH : chartSOC;
        if (otherChart && otherChart.data && otherChart.data.datasets && otherChart.data.datasets.length > 0 && otherChart.data.datasets[0].data) {
            const otherDataLength = otherChart.data.datasets[0].data.length;
            if (index >= 0 && index < otherDataLength) {
                const activeElements = otherChart.data.datasets.map((ds, dsIdx) => ({
                    datasetIndex: dsIdx,
                    index: index
                }));
                otherChart.setActiveElements(activeElements);
                otherChart.update();
            }
        }

        updateNumericalReadouts(telemetryHistory[actualIndex]);
        updateBadge();
    }

    function handleChartHoverEnd(chart) {
        isScrubbing = false;
        scrubbedIndex = -1;

        const otherChart = (chart === chartSOC) ? chartSOH : chartSOC;
        if (otherChart && otherChart.data && otherChart.data.datasets && otherChart.data.datasets.length > 0) {
            otherChart.setActiveElements([]);
            otherChart.update();
        }

        if (isLocked && lockedIndex !== -1) {
            updateNumericalReadouts(telemetryHistory[lockedIndex]);
        } else if (telemetryHistory.length > 0) {
            updateNumericalReadouts(telemetryHistory[telemetryHistory.length - 1]);
        }
        updateBadge();
    }

    function handleChartClick(index) {
        const graphDataLength = Math.min(telemetryHistory.length, graphSliceLimit);
        const actualIndex = telemetryHistory.length - graphDataLength + index;

        if (actualIndex < 0 || actualIndex >= telemetryHistory.length) return;
        isLocked = true;
        lockedIndex = actualIndex;
        updateNumericalReadouts(telemetryHistory[actualIndex]);
        updateBadge();
    }

    function handleChartClickOutside() {
        resumeLiveMode();
    }

    function resumeLiveMode() {
        isLocked = false;
        lockedIndex = -1;
        isScrubbing = false;
        scrubbedIndex = -1;
        
        if (chartSOC && chartSOC.data && chartSOC.data.datasets && chartSOC.data.datasets.length > 0) {
            chartSOC.setActiveElements([]);
            chartSOC.update();
        }
        if (chartSOH && chartSOH.data && chartSOH.data.datasets && chartSOH.data.datasets.length > 0) {
            chartSOH.setActiveElements([]);
            chartSOH.update();
        }

        if (telemetryHistory.length > 0) {
            updateNumericalReadouts(telemetryHistory[telemetryHistory.length - 1]);
        } else {
            updateNumericalReadouts(null);
        }
        updateBadge();
    }

    // Charts Configuration Options — Premium Light Mode
    const CHART_COLORS = {
        gridLine:   'rgba(226, 232, 240, 0.75)',    // Slate 200
        tickLabel:  '#64748b',                      // Slate 500
        axisLabel:  '#334155',                      // Slate 700
        emerald:    '#10b981',                      // True ground truth
        amber:      '#b45309',                      // EKF traditional (Dark Amber)
        blue:       '#1d4ed8',                      // ESN SOC (Royal Blue)
        violet:     '#6d28d9',                      // ESN SOH (Purple)
    };

    // Helper to build gradient fills for area charts
    function getFadedGradient(ctx, hexColor) {
        const gradient = ctx.createLinearGradient(0, 0, 0, 180);
        const r = parseInt(hexColor.slice(1, 3), 16);
        const g = parseInt(hexColor.slice(3, 5), 16);
        const b = parseInt(hexColor.slice(5, 7), 16);
        gradient.addColorStop(0, `rgba(${r}, ${g}, ${b}, 0.08)`);
        gradient.addColorStop(1, `rgba(${r}, ${g}, ${b}, 0.0)`);
        return gradient;
    }

    const commonChartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 0 },
        interaction: {
            mode: 'index',
            intersect: false
        },
        onHover: (event, activeElements, chart) => {
            if (chart && chart.canvas) {
                chart.canvas.style.cursor = (activeElements && activeElements.length > 0) ? 'pointer' : 'default';
            }
            if (activeElements && activeElements.length > 0) {
                const index = activeElements[0].index;
                handleChartHover(index, chart);
            } else {
                handleChartHoverEnd(chart);
            }
        },
        onClick: (event, activeElements, chart) => {
            if (activeElements && activeElements.length > 0) {
                const index = activeElements[0].index;
                handleChartClick(index);
            } else {
                handleChartClickOutside();
            }
        },
        plugins: {
            legend: {
                display: true,
                labels: {
                    color: CHART_COLORS.tickLabel,
                    font: { family: 'Inter', size: 10, weight: '600' },
                    boxWidth: 10,
                    boxHeight: 3,
                    padding: 10
                }
            }
        },
        scales: {
            x: {
                type: 'linear',
                title: {
                    display: true, text: 'Time (s)',
                    color: CHART_COLORS.axisLabel,
                    font: { family: 'Inter', size: 10, weight: '600' }
                },
                grid: { color: CHART_COLORS.gridLine, lineWidth: 1 },
                ticks: { color: CHART_COLORS.tickLabel, font: { family: 'Inter', size: 9 } },
                border: { color: '#e2e8f0' }
            },
            y: {
                grid: { color: CHART_COLORS.gridLine, lineWidth: 1 },
                ticks: { color: CHART_COLORS.tickLabel, font: { family: 'Inter', size: 9 } },
                border: { color: '#e2e8f0' }
            }
        }
    };

    // Initialize Chart.js Instances
    function initCharts() {
        // 1. SOC Chart (True vs. EKF vs. ESN)
        const ctxSOC = document.getElementById('chart-soc').getContext('2d');
        const gradientSOC = getFadedGradient(ctxSOC, CHART_COLORS.emerald);
        
        chartSOC = new Chart(ctxSOC, {
            type: 'line',
            data: {
                datasets: [
                    {
                        label: 'True SOC (Reference)',
                        data: [],
                        borderColor: CHART_COLORS.emerald,
                        backgroundColor: gradientSOC,
                        borderWidth: 2.5,
                        fill: true,
                        pointRadius: 2.5,
                        pointHoverRadius: 6,
                        pointHitRadius: 10,
                        tension: 0.3
                    },
                    {
                        label: 'EKF + CC Estimation',
                        data: [],
                        borderColor: CHART_COLORS.amber,
                        borderWidth: 1.8,
                        borderDash: [4, 4],
                        fill: false,
                        pointRadius: 2.5,
                        pointHoverRadius: 6,
                        pointHitRadius: 10,
                        tension: 0.3
                    },
                    {
                        label: 'ESN (Reservoir ML)',
                        data: [],
                        borderColor: CHART_COLORS.blue,
                        borderWidth: 1.8,
                        fill: false,
                        pointRadius: 2.5,
                        pointHoverRadius: 6,
                        pointHitRadius: 10,
                        tension: 0.3
                    }
                ]
            },
            options: {
                ...commonChartOptions,
                scales: {
                    ...commonChartOptions.scales,
                    y: {
                        ...commonChartOptions.scales.y,
                        min: 0, max: 1.05,
                        title: { display: true, text: 'SOC Ratio', color: CHART_COLORS.axisLabel, font: { family: 'Inter', size: 10 } }
                    }
                }
            }
        });

        // 2. SOH Chart (True vs. EKF vs. ESN)
        const ctxSOH = document.getElementById('chart-soh').getContext('2d');
        const gradientSOH = getFadedGradient(ctxSOH, CHART_COLORS.emerald);

        chartSOH = new Chart(ctxSOH, {
            type: 'line',
            data: {
                datasets: [
                    {
                        label: 'True SOH (Reference)',
                        data: [],
                        borderColor: CHART_COLORS.emerald,
                        backgroundColor: gradientSOH,
                        borderWidth: 2.5,
                        fill: true,
                        pointRadius: 2.5,
                        pointHoverRadius: 6,
                        pointHitRadius: 10,
                        tension: 0.3
                    },
                    {
                        label: 'EKF Resistance tracker',
                        data: [],
                        borderColor: CHART_COLORS.amber,
                        borderWidth: 1.8,
                        borderDash: [4, 4],
                        fill: false,
                        pointRadius: 2.5,
                        pointHoverRadius: 6,
                        pointHitRadius: 10,
                        tension: 0.3
                    },
                    {
                        label: 'ESN (Reservoir ML)',
                        data: [],
                        borderColor: CHART_COLORS.violet,
                        borderWidth: 1.8,
                        fill: false,
                        pointRadius: 2.5,
                        pointHoverRadius: 6,
                        pointHitRadius: 10,
                        tension: 0.3
                    }
                ]
            },
            options: {
                ...commonChartOptions,
                scales: {
                    ...commonChartOptions.scales,
                    y: {
                        ...commonChartOptions.scales.y,
                        min: 0.0, max: 1.05,
                        title: { display: true, text: 'SOH Ratio', color: CHART_COLORS.axisLabel, font: { family: 'Inter', size: 10 } }
                    }
                }
            }
        });


    }

    // Server API calls helper
    async function apiRequest(endpoint, method = 'GET', body = null) {
        try {
            const options = {
                method,
                headers: { 'Content-Type': 'application/json' }
            };
            if (body) options.body = JSON.stringify(body);
            const response = await fetch(endpoint, options);
            return await response.json();
        } catch (error) {
            console.error(`API Error on ${endpoint}:`, error);
            return null;
        }
    }

    // ── CSS-class helpers for the diagnostics panel ─────────────
    const RING_CLASSES = ['diag-ring-nominal', 'diag-ring-warning', 'diag-ring-critical'];

    function setAlarmBadge(el, isActive, activeClass) {
        if (!el) return;
        if (isActive) {
            el.classList.add(activeClass);
        } else {
            el.classList.remove(activeClass);
        }
    }

    function setHealthRing(ringEl, titleEl, descEl, ringClass, iconHtml, titleText, descText) {
        RING_CLASSES.forEach(c => ringEl.classList.remove(c));
        ringEl.classList.add(ringClass);
        ringEl.innerHTML = iconHtml;
        titleEl.textContent = titleText;
        descEl.textContent = descText;
    }

    // Refresh status and configuration parameters
    async function refreshStatus() {
        const status = await apiRequest('/api/status');
        if (!status) return;

        if (status.graph_slice_limit !== undefined) {
            graphSliceLimit = status.graph_slice_limit;
        }

        mismatchSelect.value = status.ekf_mismatch !== undefined ? Number(status.ekf_mismatch).toFixed(1) : "1.0";
        quantizeSelect.value = status.quantize_mode || "float32";

        // Update Ambient Temp status badge
        if (diagEnvTemp && status.T_ambient !== undefined) {
            diagEnvTemp.textContent = status.T_ambient.toFixed(1) + '°C Ambient';
        }

        // Update Simulator badge
        if (status.sim_running) {
            simBadge.querySelector('.dot').className = 'dot pulse-green';
            let labelText = "Simulator: " + status.active_cycle.toUpperCase();
            if (status.accelerated_aging) labelText += " (AGING)";
            if (status.fault_short || status.fault_thermal || status.fault_dropout) labelText += " (FAULT)";
            simBadge.querySelector('.label').textContent = labelText;
        } else {
            simBadge.querySelector('.dot').className = 'dot pulse-red';
            simBadge.querySelector('.label').textContent = 'Simulator: Idle';
        }

        // Update Port 8000/simulator service badge
        if (simPortBadge) {
            if (status.simulator_port_online) {
                simPortBadge.querySelector('.dot').className = 'dot pulse-green';
                simPortBadge.querySelector('.label').textContent = 'Sim Service: Online';
            } else {
                simPortBadge.querySelector('.dot').className = 'dot pulse-red';
                simPortBadge.querySelector('.label').textContent = 'Sim Service: Offline';
            }
        }

        // Update DB badge
        if (status.mongodb_connected) {
            dbBadge.querySelector('.dot').className = 'dot pulse-green';
            dbBadge.querySelector('.label').textContent = 'MongoDB: Connected';
        } else {
            dbBadge.querySelector('.dot').className = 'dot pulse-amber';
            dbBadge.querySelector('.label').textContent = 'MongoDB: In-Memory';
        }

        // Update ESN model badge
        if (status.model_loaded) {
            modelBadge.querySelector('.dot').className = 'dot pulse-green';
            modelBadge.querySelector('.label').textContent = 'ESN Model: Active';
            mlWarningBanner.classList.add('hidden');
        } else {
            modelBadge.querySelector('.dot').className = 'dot pulse-red';
            modelBadge.querySelector('.label').textContent = 'ESN Model: Missing';
            mlWarningBanner.classList.remove('hidden');
        }

        // Update Chemistry badge in header
        const chemBadgeLabel = document.getElementById('val-chem-badge');
        if (chemBadgeLabel && status.chemistry) {
            const chemMap = {
                'li_ion': 'Generic Li-ion',
                'nmc': 'Li-ion NMC',
                'lfp': 'LiFePO₄ LFP',
                'lead_acid': 'Lead-Acid'
            };
            const chemName = chemMap[status.chemistry] || status.chemistry.toUpperCase();
            chemBadgeLabel.textContent = 'Chemistry: ' + chemName;
        }

        // Update Simulator Control Center states
        if (btnStart) btnStart.disabled = status.sim_running;
        if (btnPause) btnPause.disabled = !status.sim_running;
        if (btnStop) btnStop.disabled = !status.sim_running;

        if (chemSelect) chemSelect.value = status.chemistry;
        if (cycleSelect) cycleSelect.value = status.active_cycle;
        if (agingToggle) agingToggle.checked = status.accelerated_aging;

        if (tempSlider && document.activeElement !== tempSlider) {
            tempSlider.value = status.T_ambient;
            if (valAmbientTemp) valAmbientTemp.textContent = status.T_ambient;
        }

        if (faultShortToggle) faultShortToggle.checked = status.fault_short;
        if (faultThermalToggle) faultThermalToggle.checked = status.fault_thermal;
        if (faultDropoutToggle) faultDropoutToggle.checked = status.fault_dropout;

        // Update loaded ESN model registry RMSE details in Sidebar
        const valModelSocRmse = document.getElementById('val-model-soc-rmse');
        const valModelSohRmse = document.getElementById('val-model-soh-rmse');
        if (valModelSocRmse) {
            valModelSocRmse.textContent = (status.soc_rmse !== null && status.soc_rmse !== undefined) ? status.soc_rmse.toFixed(6) : '--';
        }
        if (valModelSohRmse) {
            valModelSohRmse.textContent = (status.soh_rmse !== null && status.soh_rmse !== undefined) ? status.soh_rmse.toFixed(6) : '--';
        }

        // Update Sidebar elements with live status values
        const valSimPort = document.getElementById('val-sim-port');
        const valSimRunning = document.getElementById('val-sim-running');
        const valSimChemistry = document.getElementById('val-sim-chemistry');
        const valSimCycle = document.getElementById('val-sim-cycle');
        const valSimAmbient = document.getElementById('val-sim-ambient');
        const valSimAging = document.getElementById('val-sim-aging');

        const statusInjectedShort = document.getElementById('status-injected-short');
        const statusInjectedThermal = document.getElementById('status-injected-thermal');
        const statusInjectedDropout = document.getElementById('status-injected-dropout');

        if (valSimPort) {
            if (status.simulator_port_online) {
                valSimPort.textContent = 'Online';
                valSimPort.className = 'font-blue';
            } else {
                valSimPort.textContent = 'Offline';
                valSimPort.className = 'text-rose';
            }
        }

        if (valSimRunning) {
            if (status.sim_running) {
                valSimRunning.textContent = 'Running';
                valSimRunning.className = 'font-blue';
            } else {
                valSimRunning.textContent = 'Idle';
                valSimRunning.className = 'text-rose';
            }
        }

        if (valSimChemistry && status.chemistry) {
            const chemMap = {
                'li_ion': 'Generic Li-ion',
                'nmc': 'Li-ion NMC',
                'lfp': 'LiFePO₄ LFP',
                'lead_acid': 'Lead-Acid'
            };
            const chemName = chemMap[status.chemistry] || status.chemistry.toUpperCase();
            valSimChemistry.textContent = chemName;
        }

        if (valSimCycle && status.active_cycle) {
            valSimCycle.textContent = status.active_cycle.toUpperCase();
        }

        if (valSimAmbient && status.T_ambient !== undefined) {
            valSimAmbient.textContent = status.T_ambient.toFixed(1) + '°C';
        }

        if (valSimAging) {
            valSimAging.textContent = status.accelerated_aging ? 'Active' : 'Off';
            valSimAging.className = status.accelerated_aging ? 'font-blue' : '';
        }

        if (statusInjectedShort) {
            statusInjectedShort.style.color = status.fault_short ? 'var(--accent-rose)' : 'var(--text-muted)';
            statusInjectedShort.style.fontWeight = status.fault_short ? '600' : 'normal';
        }
        if (statusInjectedThermal) {
            statusInjectedThermal.style.color = status.fault_thermal ? 'var(--accent-rose)' : 'var(--text-muted)';
            statusInjectedThermal.style.fontWeight = status.fault_thermal ? '600' : 'normal';
        }
        if (statusInjectedDropout) {
            statusInjectedDropout.style.color = status.fault_dropout ? 'var(--accent-rose)' : 'var(--text-muted)';
            statusInjectedDropout.style.fontWeight = status.fault_dropout ? '600' : 'normal';
        }
    }

    // Helper to render numerical readouts
    function updateNumericalReadouts(latest) {
        if (latest) {
            valVoltage.textContent = latest.voltage.toFixed(2);
            valCurrent.textContent = latest.current.toFixed(2);
            valTemp.textContent = latest.temperature.toFixed(1);
            valTime.textContent = Math.round(latest.time);
            
            valEkfSoc.textContent = (latest.ekf_soc * 100.0).toFixed(1) + '%';
            valEsnSoc.textContent = (latest.esn_soc * 100.0).toFixed(1) + '%';
            valEkfSoh.textContent = (latest.ekf_soh * 100.0).toFixed(1) + '%';
            valEsnSoh.textContent = (latest.esn_soh * 100.0).toFixed(1) + '%';

            // Compute absolute errors
            const trueSoc = latest.true_soc !== undefined ? latest.true_soc : latest.cc_soc;
            const trueSoh = latest.true_soh !== undefined ? latest.true_soh : latest.trad_soh;
            const ekfSocErr = Math.abs(trueSoc - latest.ekf_soc);
            const esnSocErr = Math.abs(trueSoc - latest.esn_soc);
            const ekfSohErr = Math.abs(trueSoh - latest.ekf_soh);
            const esnSohErr = Math.abs(trueSoh - latest.esn_soh);

            if (valEkfSocError) valEkfSocError.textContent = (ekfSocErr * 100.0).toFixed(2) + '%';
            if (valEsnSocError) valEsnSocError.textContent = (esnSocErr * 100.0).toFixed(2) + '%';
            if (valEkfSohError) valEkfSohError.textContent = (ekfSohErr * 100.0).toFixed(2) + '%';
            if (valEsnSohError) valEsnSohError.textContent = (esnSohErr * 100.0).toFixed(2) + '%';

            // Update Advanced Estimations values
            if (valEkfSoe) valEkfSoe.textContent = (latest.ekf_soe * 100.0).toFixed(1);
            if (valEsnSoe) valEsnSoe.textContent = latest.esn_soe !== undefined ? (latest.esn_soe * 100.0).toFixed(1) + '%' : '--%';
            if (valEnergyRem) valEnergyRem.textContent = latest.energy_remaining_wh !== undefined ? latest.energy_remaining_wh.toFixed(1) + ' Wh' : '-- Wh';
            
            if (valSopDischarge) valSopDischarge.textContent = latest.sop_discharge_pwr !== undefined ? Math.round(latest.sop_discharge_pwr) : '--';
            if (valSopCharge) valSopCharge.textContent = latest.sop_charge_pwr !== undefined ? Math.round(latest.sop_charge_pwr) + ' W' : '-- W';
            if (valSopCurrents) {
                const disCurr = latest.sop_discharge_curr !== undefined ? latest.sop_discharge_curr.toFixed(1) : '--';
                const chgCurr = latest.sop_charge_curr !== undefined ? latest.sop_charge_curr.toFixed(1) : '--';
                valSopCurrents.textContent = `${disCurr} A / ${chgCurr} A`;
            }
            
            if (valEkfRul) valEkfRul.textContent = latest.ekf_rul_cycles !== undefined ? Math.round(latest.ekf_rul_cycles) : '--';
            if (valEsnRul) valEsnRul.textContent = latest.esn_rul_cycles !== undefined ? Math.round(latest.esn_rul_cycles) + ' cyc' : '-- cyc';
            
            if (valRulStatus && latest.ekf_soh !== undefined) {
                const soh = latest.ekf_soh;
                let status = 'Excellent';
                let color = '#10b981';
                if (soh <= 0.8) {
                    status = 'Replace (EOL)';
                    color = '#be123c';
                } else if (soh <= 0.85) {
                    status = 'Fair';
                    color = '#b45309';
                } else if (soh <= 0.9) {
                    status = 'Good';
                    color = '#1d4ed8';
                }
                valRulStatus.textContent = status;
                valRulStatus.style.color = color;
            }

            // Top battery cell status values
            const trueSocVal = latest.true_soc !== undefined ? latest.true_soc : latest.cc_soc;
            const trueSohVal = latest.true_soh !== undefined ? latest.true_soh : latest.trad_soh;
            
            valTrueSocLarge.textContent = (trueSocVal * 100.0).toFixed(1) + '%';
            valTrueSohLarge.textContent = (trueSohVal * 100.0).toFixed(1) + '%';

            // Diagnostics and faults evaluation
            const faults = latest.faults || [];
            const hasSensor = faults.includes('sensor_dropout');
            const hasShort  = faults.includes('internal_short');
            const hasThermal = faults.includes('thermal_runaway');

            // Toggle alarm badge classes (CSS handles all visual states)
            setAlarmBadge(alarmSensor,  hasSensor,  'alarm-active-sensor');
            setAlarmBadge(alarmShort,   hasShort,   'alarm-active-short');
            setAlarmBadge(alarmThermal, hasThermal, 'alarm-active-thermal');

            // Update main health ring and status text
            if (diagHealthRing && diagStatusTitle && diagStatusDesc) {
                if (hasThermal || hasSensor) {
                    let desc = '';
                    if (hasSensor)   desc += 'BMS sensor connection lost (voltage flatlined). ';
                    if (hasThermal)  desc += 'Extreme cell temperature runaway detected! ';
                    if (hasShort)    desc += 'Internal micro-short circuit leakage detected. ';
                    setHealthRing(diagHealthRing, diagStatusTitle, diagStatusDesc,
                        'diag-ring-critical', '<i class="fa-solid fa-triangle-exclamation"></i>',
                        'System Status: Critical Alert', desc);
                } else if (hasShort) {
                    setHealthRing(diagHealthRing, diagStatusTitle, diagStatusDesc,
                        'diag-ring-warning', '<i class="fa-solid fa-circle-exclamation"></i>',
                        'System Status: Warning Anomaly', 'Internal micro-short circuit leakage detected.');
                } else {
                    setHealthRing(diagHealthRing, diagStatusTitle, diagStatusDesc,
                        'diag-ring-nominal', '<i class="fa-solid fa-check"></i>',
                        'System Status: Nominal', 'All estimators running normally. No active fault anomalies.');
                }
            }
        } else {
            valVoltage.textContent = '0.00';
            valCurrent.textContent = '0.00';
            valTemp.textContent = '0.0';
            valTime.textContent = '0';

            valEkfSoc.textContent = '--%';
            valEsnSoc.textContent = '--%';
            valEkfSoh.textContent = '--%';
            valEsnSoh.textContent = '--%';

            if (valEkfSocError) valEkfSocError.textContent = '--%';
            if (valEsnSocError) valEsnSocError.textContent = '--%';
            if (valEkfSohError) valEkfSohError.textContent = '--%';
            if (valEsnSohError) valEsnSohError.textContent = '--%';

            if (valEkfSoe) valEkfSoe.textContent = '--';
            if (valEsnSoe) valEsnSoe.textContent = '--%';
            if (valEnergyRem) valEnergyRem.textContent = '-- Wh';
            if (valSopDischarge) valSopDischarge.textContent = '--';
            if (valSopCharge) valSopCharge.textContent = '-- W';
            if (valSopCurrents) valSopCurrents.textContent = '-- A / -- A';
            if (valEkfRul) valEkfRul.textContent = '--';
            if (valEsnRul) valEsnRul.textContent = '-- cyc';
            if (valRulStatus) {
                valRulStatus.textContent = 'Good';
                valRulStatus.style.color = '#10b981';
            }

            valTrueSocLarge.textContent = '--%';
            valTrueSohLarge.textContent = '--%';

            setAlarmBadge(alarmSensor,  false, 'alarm-active-sensor');
            setAlarmBadge(alarmShort,   false, 'alarm-active-short');
            setAlarmBadge(alarmThermal, false, 'alarm-active-thermal');

            if (diagHealthRing && diagStatusTitle && diagStatusDesc) {
                setHealthRing(diagHealthRing, diagStatusTitle, diagStatusDesc,
                    'diag-ring-nominal', '<i class="fa-solid fa-check"></i>',
                    'System Status: Nominal', 'All estimators running normally. No active fault anomalies.');
            }
        }
    }

    // Refresh telemetry and plot data
    async function refreshTelemetry() {
        const telemetry = await apiRequest('/api/telemetry');
        if (!telemetry || !telemetry.data) return;

        telemetryHistory = telemetry.data;
        const data = telemetryHistory;
        
        // Handle database reset or truncation safety
        if (data.length === 0) {
            isLocked = false;
            lockedIndex = -1;
            isScrubbing = false;
            scrubbedIndex = -1;
            updateBadge();
        } else if (isLocked && lockedIndex >= data.length) {
            isLocked = false;
            lockedIndex = -1;
            updateBadge();
        }
        
        // Update numerical readouts only if we are in Live Mode (not locked, not scrubbing)
        if (!isLocked && !isScrubbing) {
            if (data.length > 0) {
                updateNumericalReadouts(data[data.length - 1]);
            } else {
                updateNumericalReadouts(null);
            }
        }

        // Limit the graphs to the latest rolling slice to avoid clutter
        const graphData = data.slice(-graphSliceLimit);

        // Scale X-axis bounds to cover the full graph width
        if (graphData.length > 0) {
            const minTime = graphData[0].time;
            const maxTime = graphData[graphData.length - 1].time;
            
            chartSOC.options.scales.x.min = minTime;
            chartSOC.options.scales.x.max = maxTime;
            
            chartSOH.options.scales.x.min = minTime;
            chartSOH.options.scales.x.max = maxTime;
        } else {
            delete chartSOC.options.scales.x.min;
            delete chartSOC.options.scales.x.max;
            delete chartSOH.options.scales.x.min;
            delete chartSOH.options.scales.x.max;
        }

        // Map data arrays for graphs
        const socTrueData = graphData.map(r => ({ x: r.time, y: r.true_soc !== undefined ? r.true_soc : r.cc_soc }));
        const socEkfData = graphData.map(r => ({ x: r.time, y: r.ekf_soc }));
        const socEsnData = graphData.map(r => ({ x: r.time, y: r.esn_soc }));
        
        const sohTrueData = graphData.map(r => ({ x: r.time, y: r.true_soh !== undefined ? r.true_soh : r.trad_soh }));
        const sohEkfData = graphData.map(r => ({ x: r.time, y: r.ekf_soh }));
        const sohEsnData = graphData.map(r => ({ x: r.time, y: r.esn_soh }));

        // Update graph datasets
        chartSOC.data.datasets[0].data = socTrueData;
        chartSOC.data.datasets[1].data = socEkfData;
        chartSOC.data.datasets[2].data = socEsnData;
        chartSOC.update();

        chartSOH.data.datasets[0].data = sohTrueData;
        chartSOH.data.datasets[1].data = sohEkfData;
        chartSOH.data.datasets[2].data = sohEsnData;
        chartSOH.update();
    }

    if (btnResumeLive) {
        btnResumeLive.addEventListener('click', (e) => {
            e.stopPropagation();
            resumeLiveMode();
        });
    }

    mismatchSelect.addEventListener('change', async (e) => {
        resumeLiveMode();
        await apiRequest('/api/control', 'POST', { ekf_mismatch: parseFloat(e.target.value) });
        refreshStatus();
        refreshTelemetry();
    });

    quantizeSelect.addEventListener('change', async (e) => {
        resumeLiveMode();
        await apiRequest('/api/control', 'POST', { quantize_mode: e.target.value });
        refreshStatus();
        refreshTelemetry();
    });

    // Playback control button listeners
    if (btnStart) {
        btnStart.addEventListener('click', async () => {
            resumeLiveMode();
            await apiRequest('/api/control', 'POST', { command: 'start' });
            refreshStatus();
            refreshTelemetry();
        });
    }
    if (btnPause) {
        btnPause.addEventListener('click', async () => {
            resumeLiveMode();
            await apiRequest('/api/control', 'POST', { command: 'pause' });
            refreshStatus();
            refreshTelemetry();
        });
    }
    if (btnStop) {
        btnStop.addEventListener('click', async () => {
            resumeLiveMode();
            await apiRequest('/api/control', 'POST', { command: 'stop' });
            refreshStatus();
            refreshTelemetry();
        });
    }
    if (btnReset) {
        btnReset.addEventListener('click', async () => {
            if (confirm('Reset simulator and purge all historical database records?')) {
                resumeLiveMode();
                await apiRequest('/api/control', 'POST', { command: 'reset' });
                refreshStatus();
                refreshTelemetry();
            }
        });
    }

    // Config selects & toggle listeners
    if (chemSelect) {
        chemSelect.addEventListener('change', async (e) => {
            resumeLiveMode();
            await apiRequest('/api/control', 'POST', { chemistry: e.target.value });
            refreshStatus();
            refreshTelemetry();
        });
    }
    if (cycleSelect) {
        cycleSelect.addEventListener('change', async (e) => {
            resumeLiveMode();
            await apiRequest('/api/control', 'POST', { cycle_type: e.target.value });
            refreshStatus();
            refreshTelemetry();
        });
    }
    if (agingToggle) {
        agingToggle.addEventListener('change', async (e) => {
            resumeLiveMode();
            await apiRequest('/api/control', 'POST', { accelerated_aging: e.target.checked });
            refreshStatus();
            refreshTelemetry();
        });
    }

    // Environment & fault toggle listeners
    if (tempSlider) {
        tempSlider.addEventListener('input', (e) => {
            if (valAmbientTemp) valAmbientTemp.textContent = e.target.value;
        });
        tempSlider.addEventListener('change', async (e) => {
            resumeLiveMode();
            await apiRequest('/api/control', 'POST', { T_ambient: parseFloat(e.target.value) });
            refreshStatus();
            refreshTelemetry();
        });
    }
    if (faultShortToggle) {
        faultShortToggle.addEventListener('change', async (e) => {
            resumeLiveMode();
            await apiRequest('/api/control', 'POST', { fault_short: e.target.checked });
            refreshStatus();
            refreshTelemetry();
        });
    }
    if (faultThermalToggle) {
        faultThermalToggle.addEventListener('change', async (e) => {
            resumeLiveMode();
            await apiRequest('/api/control', 'POST', { fault_thermal: e.target.checked });
            refreshStatus();
            refreshTelemetry();
        });
    }
    if (faultDropoutToggle) {
        faultDropoutToggle.addEventListener('change', async (e) => {
            resumeLiveMode();
            await apiRequest('/api/control', 'POST', { fault_dropout: e.target.checked });
            refreshStatus();
            refreshTelemetry();
        });
    }



    // ──────────────── ESN Model Retraining Bindings ────────────────
    const btnRetrain = document.getElementById('btn-retrain');
    const consoleEl = document.getElementById('train-console');
    let isTraining = false;

    async function pollTrainingStatus() {
        const res = await apiRequest('/api/train/status');
        if (!res) return;

        if (res.status === 'running') {
            isTraining = true;
            if (btnRetrain) {
                btnRetrain.disabled = true;
                btnRetrain.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Training…';
            }
            if (consoleEl) {
                consoleEl.textContent = res.logs;
                consoleEl.scrollTop = consoleEl.scrollHeight;
            }
            setTimeout(pollTrainingStatus, 1500);
        } else {
            if (isTraining) {
                isTraining = false;
                if (btnRetrain) {
                    btnRetrain.disabled = false;
                    btnRetrain.innerHTML = '<i class="fa-solid fa-arrows-spin"></i> Retrain ESN Weights';
                }
                refreshStatus();
                refreshTelemetry();
            }
            if (consoleEl && res.status !== 'idle') {
                consoleEl.textContent = res.logs;
                consoleEl.scrollTop = consoleEl.scrollHeight;
            }
            if (res.status === 'completed') {
                document.getElementById('val-model-soc-rmse').textContent = res.soc_rmse.toFixed(6);
                document.getElementById('val-model-soh-rmse').textContent = res.soh_rmse.toFixed(6);
            } else if (res.status === 'failed') {
                document.getElementById('val-model-soc-rmse').textContent = 'ERROR';
                document.getElementById('val-model-soh-rmse').textContent = 'ERROR';
            }
        }
    }

    if (btnRetrain) {
        btnRetrain.addEventListener('click', async () => {
            if (confirm('Launch Echo State Network model retraining? This process runs in the background.')) {
                btnRetrain.disabled = true;
                btnRetrain.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Starting…';
                const res = await apiRequest('/api/train', 'POST');
                if (res && (res.status === 'started' || res.status === 'running')) {
                    pollTrainingStatus();
                } else {
                    btnRetrain.disabled = false;
                    btnRetrain.innerHTML = '<i class="fa-solid fa-arrows-spin"></i> Retrain ESN Weights';
                }
            }
        });
    }

    // Run Initialization
    initCharts();
    refreshStatus();
    refreshTelemetry();
    pollTrainingStatus();

    // Start Polling loops using recursive setTimeout to prevent request stacking
    async function statusPoll() {
        await refreshStatus();
        setTimeout(statusPoll, 1500);
    }

    async function telemetryPoll() {
        await refreshTelemetry();
        setTimeout(telemetryPoll, 1000);
    }

    statusPoll();
    telemetryPoll();
});
