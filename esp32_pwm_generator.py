"""
MicroPython ESP32 - Generador de Señales PWM con Interfaz Web
Características:
- Conexión WiFi a "x1" con contraseña "88888888"
- Frecuencia: 1Hz a 1MHz (pin GPIO12/D12)
- Control de frecuencia y ciclo de trabajo
- Generador de barrido de frecuencia
- Generador de ruido
- Tabla de valores personalizados
- Interfaz web moderna con AJAX en tiempo real
"""

import network
import socket
import time
import json
import random
import urllib.parse
from machine import Pin, PWM

# ==================== CONFIGURACIÓN WIFI ====================
WIFI_SSID = "x1"
WIFI_PASSWORD = "88888888"

# ==================== CONFIGURACIÓN PWM ====================
PWM_PIN = 12  # GPIO12 (D12 en algunas placas)
MIN_FREQ = 1      # 1 Hz
MAX_FREQ = 1000000  # 1 MHz

# ==================== ESTADO GLOBAL ====================
pwm = None
current_mode = "manual"  # manual, sweep, noise, table
current_freq = 1000
current_duty = 50

# Configuración de barrido
sweep_config = {
    "start_freq": 100,
    "end_freq": 10000,
    "step": 100,
    "duty": 50,
    "delay_ms": 100
}

# Configuración de ruido
noise_config = {
    "min_freq": 100,
    "max_freq": 10000,
    "min_duty": 10,
    "max_duty": 90
}

# Tabla de valores
value_table = [
    {"freq": 1000, "duty": 50},
    {"freq": 2000, "duty": 60},
    {"freq": 3000, "duty": 70}
]
table_index = 0
table_start_time = 0

# Variables de estado para barrido
sweep_current_freq = 0
sweep_direction = 1
sweep_last_update = 0

# Variables de estado para ruido
noise_last_update = 0

# ==================== INICIALIZACIÓN WIFI ====================
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    if not wlan.isconnected():
        print(f'Conectando a {WIFI_SSID}...')
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        
        timeout = 30
        while not wlan.isconnected() and timeout > 0:
            time.sleep(1)
            timeout -= 1
            print(f'Esperando conexión... {timeout}s')
    
    if wlan.isconnected():
        ip = wlan.ifconfig()[0]
        print(f'Conectado! IP: {ip}')
        return ip
    else:
        print('Error al conectar')
        return None

# ==================== INICIALIZACIÓN PWM ====================
def init_pwm():
    global pwm
    pin = Pin(PWM_PIN)
    pwm = PWM(pin)
    pwm.freq(MIN_FREQ)
    pwm.duty_u16(32768)  # 50% duty cycle (0-65535)

def set_pwm(freq, duty):
    global current_freq, current_duty
    
    # Limitar frecuencia
    freq = max(MIN_FREQ, min(MAX_FREQ, int(freq)))
    duty = max(0, min(100, int(duty)))
    
    current_freq = freq
    current_duty = duty
    
    if pwm:
        pwm.freq(freq)
        # duty_u16 va de 0 a 65535
        duty_value = int((duty / 100) * 65535)
        pwm.duty_u16(duty_value)

# ==================== GENERADOR DE BARRIDO ====================
def update_sweep():
    global sweep_current_freq, sweep_direction, sweep_last_update
    
    current_time = time.ticks_ms()
    
    if time.ticks_diff(current_time, sweep_last_update) >= sweep_config["delay_ms"]:
        sweep_last_update = current_time
        
        if sweep_direction == 1:
            sweep_current_freq += sweep_config["step"]
            if sweep_current_freq >= sweep_config["end_freq"]:
                sweep_current_freq = sweep_config["end_freq"]
                sweep_direction = -1
        else:
            sweep_current_freq -= sweep_config["step"]
            if sweep_current_freq <= sweep_config["start_freq"]:
                sweep_current_freq = sweep_config["start_freq"]
                sweep_direction = 1
        
        set_pwm(sweep_current_freq, sweep_config["duty"])
    
    return sweep_current_freq, sweep_config["duty"]

# ==================== GENERADOR DE RUIDO ====================
def update_noise():
    global noise_last_update
    
    current_time = time.ticks_ms()
    
    # Actualizar cada 10ms aproximadamente
    if time.ticks_diff(current_time, noise_last_update) >= 10:
        noise_last_update = current_time
        
        freq = random.randint(noise_config["min_freq"], noise_config["max_freq"])
        duty = random.randint(noise_config["min_duty"], noise_config["max_duty"])
        set_pwm(freq, duty)
    
    return current_freq, current_duty

# ==================== TABLA DE VALORES ====================
def update_table():
    global table_index, table_start_time
    
    if len(value_table) == 0:
        return current_freq, current_duty
    
    current_time = time.ticks_ms()
    
    # Cambiar valor cada 500ms
    if time.ticks_diff(current_time, table_start_time) >= 500:
        table_start_time = current_time
        entry = value_table[table_index]
        set_pwm(entry["freq"], entry["duty"])
        table_index = (table_index + 1) % len(value_table)
    
    return current_freq, current_duty

# ==================== PÁGINA WEB ====================
def get_web_page():
    return '''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ESP32 PWM Generator</title>
    <style>
        :root {
            --bg-primary: #1a1a2e;
            --bg-secondary: #16213e;
            --bg-card: #0f3460;
            --text-primary: #eaeaea;
            --text-secondary: #a0a0a0;
            --accent: #e94560;
            --accent-hover: #ff6b6b;
            --success: #4ecca3;
            --border: #2a2a4a;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, var(--bg-primary) 0%, var(--bg-secondary) 100%);
            color: var(--text-primary);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        header {
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background: var(--bg-card);
            border-radius: 15px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        }
        
        h1 {
            font-size: 2em;
            margin-bottom: 10px;
            background: linear-gradient(90deg, var(--accent), var(--success));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .status-bar {
            display: flex;
            justify-content: center;
            gap: 30px;
            flex-wrap: wrap;
            margin-top: 15px;
        }
        
        .status-item {
            background: var(--bg-primary);
            padding: 10px 20px;
            border-radius: 8px;
            border: 1px solid var(--border);
        }
        
        .status-label {
            font-size: 0.85em;
            color: var(--text-secondary);
        }
        
        .status-value {
            font-size: 1.3em;
            font-weight: bold;
            color: var(--success);
        }
        
        .mode-selector {
            display: flex;
            justify-content: center;
            gap: 10px;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }
        
        .mode-btn {
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            background: var(--bg-card);
            color: var(--text-primary);
            cursor: pointer;
            transition: all 0.3s ease;
            border: 2px solid transparent;
            font-size: 0.95em;
        }
        
        .mode-btn:hover {
            background: var(--bg-primary);
            transform: translateY(-2px);
        }
        
        .mode-btn.active {
            border-color: var(--accent);
            background: var(--bg-primary);
            box-shadow: 0 0 15px rgba(233, 69, 96, 0.3);
        }
        
        .card {
            background: var(--bg-card);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 20px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
            border: 1px solid var(--border);
        }
        
        .card-title {
            font-size: 1.2em;
            margin-bottom: 20px;
            color: var(--accent);
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .control-group {
            margin-bottom: 25px;
        }
        
        .control-label {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        
        .control-name {
            font-size: 0.95em;
            color: var(--text-secondary);
        }
        
        .control-value {
            background: var(--bg-primary);
            padding: 5px 15px;
            border-radius: 5px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            border: 1px solid var(--border);
        }
        
        input[type="range"] {
            width: 100%;
            height: 8px;
            border-radius: 4px;
            background: var(--bg-primary);
            outline: none;
            -webkit-appearance: none;
        }
        
        input[type="range"]::-webkit-slider-thumb {
            -webkit-appearance: none;
            width: 20px;
            height: 20px;
            border-radius: 50%;
            background: var(--accent);
            cursor: pointer;
            transition: all 0.2s ease;
        }
        
        input[type="range"]::-webkit-slider-thumb:hover {
            background: var(--accent-hover);
            transform: scale(1.1);
        }
        
        input[type="number"] {
            background: var(--bg-primary);
            border: 1px solid var(--border);
            color: var(--text-primary);
            padding: 8px 12px;
            border-radius: 5px;
            width: 120px;
            font-family: 'Courier New', monospace;
        }
        
        input[type="number"]:focus {
            outline: none;
            border-color: var(--accent);
        }
        
        .input-row {
            display: flex;
            gap: 15px;
            align-items: center;
            flex-wrap: wrap;
        }
        
        .hidden {
            display: none;
        }
        
        .grid-2 {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }
        
        .table-container {
            max-height: 300px;
            overflow-y: auto;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
        }
        
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }
        
        th {
            background: var(--bg-primary);
            color: var(--accent);
            position: sticky;
            top: 0;
        }
        
        tr:hover {
            background: var(--bg-primary);
        }
        
        .btn-small {
            padding: 5px 10px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.8em;
            transition: all 0.2s ease;
        }
        
        .btn-add {
            background: var(--success);
            color: var(--bg-primary);
        }
        
        .btn-delete {
            background: var(--accent);
            color: white;
        }
        
        .btn-small:hover {
            transform: scale(1.05);
        }
        
        .form-row {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
            align-items: center;
            flex-wrap: wrap;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .live-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            background: var(--success);
            border-radius: 50%;
            animation: pulse 2s infinite;
            margin-right: 8px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🎛️ ESP32 PWM Generator</h1>
            <p style="color: var(--text-secondary);">Generador de señales de precisión</p>
            <div class="status-bar">
                <div class="status-item">
                    <div class="status-label"><span class="live-indicator"></span>Frecuencia Actual</div>
                    <div class="status-value" id="liveFreq">-- Hz</div>
                </div>
                <div class="status-item">
                    <div class="status-label">Ciclo de Trabajo</div>
                    <div class="status-value" id="liveDuty">-- %</div>
                </div>
                <div class="status-item">
                    <div class="status-label">Modo</div>
                    <div class="status-value" id="liveMode">Manual</div>
                </div>
            </div>
        </header>
        
        <div class="mode-selector">
            <button class="mode-btn active" onclick="setMode('manual')">📊 Manual</button>
            <button class="mode-btn" onclick="setMode('sweep')">🔄 Barrido</button>
            <button class="mode-btn" onclick="setMode('noise')">⚡ Ruido</button>
            <button class="mode-btn" onclick="setMode('table')">📋 Tabla</button>
        </div>
        
        <!-- MODO MANUAL -->
        <div id="manualPanel" class="card">
            <h2 class="card-title">📊 Control Manual</h2>
            <div class="control-group">
                <div class="control-label">
                    <span class="control-name">Frecuencia (Hz)</span>
                    <input type="number" id="freqInput" value="1000" min="1" max="1000000" onchange="updateFromInput()">
                </div>
                <input type="range" id="freqSlider" min="0" max="100" value="50" oninput="updateFreq()">
            </div>
            <div class="control-group">
                <div class="control-label">
                    <span class="control-name">Ciclo de Trabajo (%)</span>
                    <input type="number" id="dutyInput" value="50" min="0" max="100" onchange="updateFromInput()">
                </div>
                <input type="range" id="dutySlider" min="0" max="100" value="50" oninput="updateDuty()">
            </div>
        </div>
        
        <!-- MODO BARRIDO -->
        <div id="sweepPanel" class="card hidden">
            <h2 class="card-title">🔄 Generador de Barrido</h2>
            <div class="grid-2">
                <div class="control-group">
                    <div class="control-label">
                        <span class="control-name">Frecuencia Inicial (Hz)</span>
                        <input type="number" id="sweepStart" value="100" min="1" max="1000000" onchange="updateSweepConfig()">
                    </div>
                </div>
                <div class="control-group">
                    <div class="control-label">
                        <span class="control-name">Frecuencia Final (Hz)</span>
                        <input type="number" id="sweepEnd" value="10000" min="1" max="1000000" onchange="updateSweepConfig()">
                    </div>
                </div>
                <div class="control-group">
                    <div class="control-label">
                        <span class="control-name">Salto de Frecuencia (Hz)</span>
                        <input type="number" id="sweepStep" value="100" min="1" max="100000" onchange="updateSweepConfig()">
                    </div>
                </div>
                <div class="control-group">
                    <div class="control-label">
                        <span class="control-name">Ciclo de Trabajo (%)</span>
                        <input type="number" id="sweepDuty" value="50" min="0" max="100" onchange="updateSweepConfig()">
                    </div>
                </div>
                <div class="control-group">
                    <div class="control-label">
                        <span class="control-name">Tiempo entre Saltos (ms)</span>
                        <input type="number" id="sweepDelay" value="100" min="10" max="10000" onchange="updateSweepConfig()">
                    </div>
                </div>
            </div>
        </div>
        
        <!-- MODO RUIDO -->
        <div id="noisePanel" class="card hidden">
            <h2 class="card-title">⚡ Generador de Ruido</h2>
            <div class="grid-2">
                <div class="control-group">
                    <div class="control-label">
                        <span class="control-name">Frecuencia Mínima (Hz)</span>
                        <input type="number" id="noiseMinFreq" value="100" min="1" max="1000000" onchange="updateNoiseConfig()">
                    </div>
                </div>
                <div class="control-group">
                    <div class="control-label">
                        <span class="control-name">Frecuencia Máxima (Hz)</span>
                        <input type="number" id="noiseMaxFreq" value="10000" min="1" max="1000000" onchange="updateNoiseConfig()">
                    </div>
                </div>
                <div class="control-group">
                    <div class="control-label">
                        <span class="control-name">Ciclo Mínimo (%)</span>
                        <input type="number" id="noiseMinDuty" value="10" min="0" max="100" onchange="updateNoiseConfig()">
                    </div>
                </div>
                <div class="control-group">
                    <div class="control-label">
                        <span class="control-name">Ciclo Máximo (%)</span>
                        <input type="number" id="noiseMaxDuty" value="90" min="0" max="100" onchange="updateNoiseConfig()">
                    </div>
                </div>
            </div>
        </div>
        
        <!-- MODO TABLA -->
        <div id="tablePanel" class="card hidden">
            <h2 class="card-title">📋 Tabla de Valores</h2>
            <div class="form-row">
                <input type="number" id="tableFreq" placeholder="Frecuencia (Hz)" min="1" max="1000000">
                <input type="number" id="tableDuty" placeholder="Ciclo (%)" min="0" max="100">
                <button class="btn-small btn-add" onclick="addTableEntry()">➕ Añadir</button>
            </div>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Frecuencia (Hz)</th>
                            <th>Ciclo (%)</th>
                            <th>Acción</th>
                        </tr>
                    </thead>
                    <tbody id="tableBody">
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    
    <script>
        let currentMode = 'manual';
        let logScale = false;
        
        // Escala logarítmica para el slider de frecuencia
        function freqToSlider(freq) {
            const min = Math.log10(1);
            const max = Math.log10(1000000);
            const value = Math.log10(Math.max(1, freq));
            return ((value - min) / (max - min)) * 100;
        }
        
        function sliderToFreq(sliderValue) {
            const min = Math.log10(1);
            const max = Math.log10(1000000);
            const value = min + (sliderValue / 100) * (max - min);
            return Math.round(Math.pow(10, value));
        }
        
        function setMode(mode) {
            currentMode = mode;
            
            document.querySelectorAll('.mode-btn').forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');
            
            document.getElementById('manualPanel').classList.add('hidden');
            document.getElementById('sweepPanel').classList.add('hidden');
            document.getElementById('noisePanel').classList.add('hidden');
            document.getElementById('tablePanel').classList.add('hidden');
            
            document.getElementById(mode + 'Panel').classList.remove('hidden');
            
            fetch('/mode?mode=' + mode);
            document.getElementById('liveMode').textContent = mode.charAt(0).toUpperCase() + mode.slice(1);
            
            if (mode === 'table') {
                loadTable();
            }
        }
        
        function updateFreq() {
            const slider = document.getElementById('freqSlider');
            const input = document.getElementById('freqInput');
            const freq = sliderToFreq(slider.value);
            input.value = freq.toLocaleString();
            
            fetch('/pwm?freq=' + freq + '&duty=' + document.getElementById('dutyInput').value);
        }
        
        function updateDuty() {
            const slider = document.getElementById('dutySlider');
            const input = document.getElementById('dutyInput');
            input.value = slider.value;
            
            fetch('/pwm?freq=' + document.getElementById('freqInput').value.replace(/,/g, '') + '&duty=' + slider.value);
        }
        
        function updateFromInput() {
            const freqInput = document.getElementById('freqInput');
            const dutyInput = document.getElementById('dutyInput');
            const freqSlider = document.getElementById('freqSlider');
            const dutySlider = document.getElementById('dutySlider');
            
            const freq = parseInt(freqInput.value.replace(/,/g, '')) || 1000;
            const duty = parseInt(dutyInput.value) || 50;
            
            freqSlider.value = freqToSlider(freq);
            dutySlider.value = duty;
            
            fetch('/pwm?freq=' + freq + '&duty=' + duty);
        }
        
        function updateSweepConfig() {
            const config = {
                start_freq: parseInt(document.getElementById('sweepStart').value) || 100,
                end_freq: parseInt(document.getElementById('sweepEnd').value) || 10000,
                step: parseInt(document.getElementById('sweepStep').value) || 100,
                duty: parseInt(document.getElementById('sweepDuty').value) || 50,
                delay_ms: parseInt(document.getElementById('sweepDelay').value) || 100
            };
            
            fetch('/sweep?config=' + encodeURIComponent(JSON.stringify(config)));
        }
        
        function updateNoiseConfig() {
            const config = {
                min_freq: parseInt(document.getElementById('noiseMinFreq').value) || 100,
                max_freq: parseInt(document.getElementById('noiseMaxFreq').value) || 10000,
                min_duty: parseInt(document.getElementById('noiseMinDuty').value) || 10,
                max_duty: parseInt(document.getElementById('noiseMaxDuty').value) || 90
            };
            
            fetch('/noise?config=' + encodeURIComponent(JSON.stringify(config)));
        }
        
        function loadTable() {
            fetch('/table')
                .then(response => response.json())
                .then(data => {
                    const tbody = document.getElementById('tableBody');
                    tbody.innerHTML = '';
                    
                    data.forEach((entry, index) => {
                        const row = document.createElement('tr');
                        row.innerHTML = `
                            <td>${index + 1}</td>
                            <td>${entry.freq.toLocaleString()}</td>
                            <td>${entry.duty}</td>
                            <td><button class="btn-small btn-delete" onclick="deleteTableEntry(${index})">🗑️</button></td>
                        `;
                        tbody.appendChild(row);
                    });
                });
        }
        
        function addTableEntry() {
            const freq = parseInt(document.getElementById('tableFreq').value) || 1000;
            const duty = parseInt(document.getElementById('tableDuty').value) || 50;
            
            fetch('/table?freq=' + freq + '&duty=' + duty)
                .then(() => loadTable());
            
            document.getElementById('tableFreq').value = '';
            document.getElementById('tableDuty').value = '';
        }
        
        function deleteTableEntry(index) {
            fetch('/table?delete=' + index)
                .then(() => loadTable());
        }
        
        function updateStatus() {
            fetch('/status')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('liveFreq').textContent = data.freq.toLocaleString() + ' Hz';
                    document.getElementById('liveDuty').textContent = data.duty + ' %';
                    
                    if (currentMode === 'manual') {
                        const slider = document.getElementById('freqSlider');
                        const input = document.getElementById('freqInput');
                        if (Math.abs(sliderToFreq(slider.value) - data.freq) > data.freq * 0.01) {
                            slider.value = freqToSlider(data.freq);
                            input.value = data.freq.toLocaleString();
                        }
                    }
                })
                .catch(err => console.log('Error:', err));
        }
        
        // Actualizar estado cada 500ms
        setInterval(updateStatus, 500);
        
        // Inicializar sliders
        document.getElementById('freqSlider').value = freqToSlider(1000);
    </script>
</body>
</html>'''

# ==================== SERVIDOR WEB ====================
def start_server(ip):
    addr = socket.getaddrinfo(ip, 80)[0][-1]
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(addr)
    server.listen(5)
    
    print(f'Servidor web escuchando en http://{ip}:80')
    
    while True:
        client, addr = server.accept()
        try:
            request = client.recv(4096).decode('utf-8')
            lines = request.split('\n')
            
            if len(lines) > 0:
                parts = lines[0].split(' ')
                if len(parts) >= 2:
                    method = parts[0]
                    path = parts[1]
                    
                    # Página principal
                    if path == '/' or path == '/index.html':
                        response = get_web_page()
                        send_response(client, response, 'text/html')
                    
                    # API: Estado actual
                    elif path.startswith('/status'):
                        status = {'freq': current_freq, 'duty': current_duty, 'mode': current_mode}
                        send_response(client, json.dumps(status), 'application/json')
                    
                    # API: Configurar PWM
                    elif path.startswith('/pwm'):
                        handle_pwm_request(path)
                        send_response(client, '{"status":"ok"}', 'application/json')
                    
                    # API: Cambiar modo
                    elif path.startswith('/mode'):
                        if 'mode=' in path:
                            current_mode = path.split('mode=')[1].split('&')[0]
                        send_response(client, '{"status":"ok"}', 'application/json')
                    
                    # API: Configurar barrido
                    elif path.startswith('/sweep'):
                        handle_sweep_request(path)
                        send_response(client, '{"status":"ok"}', 'application/json')
                    
                    # API: Configurar ruido
                    elif path.startswith('/noise'):
                        handle_noise_request(path)
                        send_response(client, '{"status":"ok"}', 'application/json')
                    
                    # API: Tabla de valores
                    elif path.startswith('/table'):
                        handle_table_request(path, client)
                        continue
                    
                    else:
                        send_response(client, '404 Not Found', 'text/plain', 404)
        
        except Exception as e:
            print(f'Error: {e}')
        finally:
            client.close()

def send_response(client, content, content_type, status_code=200):
    status_text = 'OK' if status_code == 200 else 'Not Found'
    response = f'HTTP/1.1 {status_code} {status_text}\r\n'
    response += f'Content-Type: {content_type}\r\n'
    response += f'Content-Length: {len(content)}\r\n'
    response += 'Connection: close\r\n'
    response += 'Access-Control-Allow-Origin: *\r\n'
    response += '\r\n'
    response += content
    
    client.send(response.encode('utf-8'))

def handle_pwm_request(path):
    global current_freq, current_duty
    
    if 'freq=' in path:
        freq_str = path.split('freq=')[1].split('&')[0]
        freq = int(freq_str)
        
        duty = current_duty
        if 'duty=' in path:
            duty_str = path.split('duty=')[1].split('&')[0]
            duty = int(duty_str)
        
        set_pwm(freq, duty)

def handle_sweep_request(path):
    global sweep_config
    
    if 'config=' in path:
        import urllib.parse
        config_str = path.split('config=')[1].split('&')[0]
        config_str = urllib.parse.unquote(config_str)
        
        try:
            new_config = json.loads(config_str)
            sweep_config.update(new_config)
            global sweep_current_freq
            sweep_current_freq = sweep_config["start_freq"]
        except:
            pass

def handle_noise_request(path):
    global noise_config
    
    if 'config=' in path:
        import urllib.parse
        config_str = path.split('config=')[1].split('&')[0]
        config_str = urllib.parse.unquote(config_str)
        
        try:
            new_config = json.loads(config_str)
            noise_config.update(new_config)
        except:
            pass

def handle_table_request(path, client):
    global value_table
    
    if 'delete=' in path:
        index = int(path.split('delete=')[1].split('&')[0])
        if 0 <= index < len(value_table):
            value_table.pop(index)
        send_response(client, '{"status":"ok"}', 'application/json')
    
    elif 'freq=' in path and 'duty=' in path:
        freq = int(path.split('freq=')[1].split('&')[0])
        duty = int(path.split('duty=')[1].split('&')[0])
        value_table.append({'freq': freq, 'duty': duty})
        send_response(client, '{"status":"ok"}', 'application/json')
    
    else:
        send_response(client, json.dumps(value_table), 'application/json')

# ==================== FUNCIÓN PRINCIPAL ====================
def main():
    print('=' * 50)
    print('ESP32 PWM Generator')
    print('=' * 50)
    
    # Conectar WiFi
    ip = connect_wifi()
    if not ip:
        print('No se pudo conectar a WiFi. Reiniciando...')
        time.sleep(5)
        import machine
        machine.reset()
        return
    
    # Inicializar PWM
    init_pwm()
    print(f'PWM inicializado en GPIO{PWM_PIN}')
    print(f'Rango: {MIN_FREQ} Hz - {MAX_FREQ} Hz (1 MHz)')
    
    # Iniciar servidor web
    start_server(ip)

# ==================== EJECUCIÓN ====================
if __name__ == '__main__':
    main()
