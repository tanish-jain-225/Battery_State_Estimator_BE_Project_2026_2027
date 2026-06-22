// BMS Physical Simulator - Playback Dashboard Logic

document.addEventListener('DOMContentLoaded', () => {
    // Control Elements
    const btnStart = document.getElementById('btn-start');
    const btnPause = document.getElementById('btn-pause');
    const btnStop = document.getElementById('btn-stop');
    const btnReset = document.getElementById('btn-reset');

    const chemSelect = document.getElementById('chem-select');
    const cycleSelect = document.getElementById('cycle-select');
    const agingToggle = document.getElementById('aging-toggle');

    // New Environment and Fault Elements
    const tempSlider = document.getElementById('temp-slider');
    const valAmbientTemp = document.getElementById('val-ambient-temp');
    const faultShortToggle = document.getElementById('fault-short-toggle');
    const faultThermalToggle = document.getElementById('fault-thermal-toggle');
    const faultDropoutToggle = document.getElementById('fault-dropout-toggle');

    // Status Elements
    const genStatus = document.getElementById('gen-status');
    const dbStatus = document.getElementById('db-status');
    const linkBadge = document.getElementById('link-badge');

    // Telemetry Fields
    const valTime = document.getElementById('val-time');
    const valVoltage = document.getElementById('val-voltage');
    const valCurrent = document.getElementById('val-current');
    const valTemp = document.getElementById('val-temp');

    const valSoc = document.getElementById('val-soc');
    const valSoh = document.getElementById('val-soh');
    const barSoc = document.getElementById('bar-soc');
    const barSoh = document.getElementById('bar-soh');

    const valCount = document.getElementById('val-count');

    // REST Request Utility
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
            console.error(`API Error on simulator endpoint ${endpoint}:`, error);
            return null;
        }
    }

    // Refresh UI configurations and states
    async function updateStatus() {
        const res = await apiRequest('/api/status');
        if (!res) {
            // Simulator API offline
            genStatus.querySelector('.dot').className = 'dot pulse-red';
            genStatus.querySelector('.label').textContent = 'Simulator: Disconnected';
            return;
        }

        // Toggle playback button disabled states
        btnStart.disabled = res.sim_running;
        btnPause.disabled = !res.sim_running;
        btnStop.disabled = !res.sim_running;

        // Synchronize select inputs
        chemSelect.value = res.chemistry;
        cycleSelect.value = res.active_cycle;
        agingToggle.checked = res.accelerated_aging;

        // Sync Environment and Fault Inputs
        if (tempSlider && document.activeElement !== tempSlider) {
            tempSlider.value = res.T_ambient;
            if (valAmbientTemp) valAmbientTemp.textContent = res.T_ambient;
        }
        if (faultShortToggle) faultShortToggle.checked = res.fault_short;
        if (faultThermalToggle) faultThermalToggle.checked = res.fault_thermal;
        if (faultDropoutToggle) faultDropoutToggle.checked = res.fault_dropout;

        // Update counts
        valCount.textContent = res.telemetry_count;

        // Sync main generator indicator
        if (res.sim_running) {
            genStatus.querySelector('.dot').className = 'dot pulse-green';
            let cycleStr = res.active_cycle.toUpperCase();
            if (res.accelerated_aging) cycleStr += ' (AGING)';
            if (res.fault_short || res.fault_thermal || res.fault_dropout) cycleStr += ' (FAULT)';
            genStatus.querySelector('.label').textContent = `Simulator: Generating (${cycleStr})`;

            linkBadge.textContent = 'Transmitting';
            linkBadge.className = 'badge green';
        } else {
            if (res.time > 0.0) {
                genStatus.querySelector('.dot').className = 'dot pulse-amber';
                genStatus.querySelector('.label').textContent = 'Simulator: Paused';

                linkBadge.textContent = 'Link Paused';
                linkBadge.className = 'badge amber';
            } else {
                genStatus.querySelector('.dot').className = 'dot pulse-red';
                genStatus.querySelector('.label').textContent = 'Simulator: Idle';

                linkBadge.textContent = 'Idle';
                linkBadge.className = 'badge';
            }
        }

        // Sync MongoDB database indicator
        if (res.mongodb_connected) {
            dbStatus.querySelector('.dot').className = 'dot pulse-green';
            dbStatus.querySelector('.label').textContent = 'MongoDB: Connected';
        } else {
            dbStatus.querySelector('.dot').className = 'dot pulse-red';
            dbStatus.querySelector('.label').textContent = 'MongoDB: Connection Failed';
        }

        // Sync Telemetry numeric displays
        valTime.textContent = Math.round(res.time);
        valVoltage.textContent = res.voltage.toFixed(2);
        valCurrent.textContent = res.current.toFixed(2);
        valTemp.textContent = res.temperature.toFixed(1);

        // Sync Progress wavefronts
        const socPercent = (res.soc * 100.0).toFixed(1);
        const sohPercent = (res.soh * 100.0).toFixed(1);

        valSoc.textContent = socPercent + '%';
        valSoh.textContent = sohPercent + '%';

        if (barSoc) barSoc.style.width = socPercent + '%';
        if (barSoh) barSoh.style.width = sohPercent + '%';
    }

    // Button Click Listeners
    btnStart.addEventListener('click', async () => {
        await apiRequest('/api/control', 'POST', { command: 'start' });
        updateStatus();
    });

    btnPause.addEventListener('click', async () => {
        await apiRequest('/api/control', 'POST', { command: 'pause' });
        updateStatus();
    });

    btnStop.addEventListener('click', async () => {
        await apiRequest('/api/control', 'POST', { command: 'stop' });
        updateStatus();
    });

    btnReset.addEventListener('click', async () => {
        if (confirm('Are you sure you want to reset the simulation? This clears all telemetry stored in MongoDB.')) {
            await apiRequest('/api/control', 'POST', { command: 'reset' });
            updateStatus();
        }
    });

    // Profile Select Listeners
    chemSelect.addEventListener('change', async (e) => {
        await apiRequest('/api/control', 'POST', { chemistry: e.target.value });
        updateStatus();
    });

    cycleSelect.addEventListener('change', async (e) => {
        await apiRequest('/api/control', 'POST', { cycle_type: e.target.value });
        updateStatus();
    });

    agingToggle.addEventListener('change', async (e) => {
        await apiRequest('/api/control', 'POST', { accelerated_aging: e.target.checked });
        updateStatus();
    });

    // Environment & Fault Listeners
    if (tempSlider) {
        tempSlider.addEventListener('input', (e) => {
            if (valAmbientTemp) valAmbientTemp.textContent = e.target.value;
        });
        tempSlider.addEventListener('change', async (e) => {
            await apiRequest('/api/control', 'POST', { T_ambient: parseFloat(e.target.value) });
            updateStatus();
        });
    }

    if (faultShortToggle) {
        faultShortToggle.addEventListener('change', async (e) => {
            await apiRequest('/api/control', 'POST', { fault_short: e.target.checked });
            updateStatus();
        });
    }

    if (faultThermalToggle) {
        faultThermalToggle.addEventListener('change', async (e) => {
            await apiRequest('/api/control', 'POST', { fault_thermal: e.target.checked });
            updateStatus();
        });
    }

    if (faultDropoutToggle) {
        faultDropoutToggle.addEventListener('change', async (e) => {
            await apiRequest('/api/control', 'POST', { fault_dropout: e.target.checked });
            updateStatus();
        });
    }

    // Initialize Status
    updateStatus();

    // Start status polling recursive loop (prevents overlapping fetch stacking)
    async function pollLoop() {
        await updateStatus();
        setTimeout(pollLoop, 1000);
    }
    pollLoop();
});
