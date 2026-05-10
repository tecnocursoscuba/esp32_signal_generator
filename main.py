import network
import socket
import time
import json
from machine import Pin, PWM
import random

# Configuración WiFi
WIFI_SSID = "x1"
WIFI_PASSWORD = "88888888"

# Pin PWM (GPIO 12 = D12 en muchas placas ESP32)
PWM_PIN = 12

# Variables globales
pwm = None
mode = "manual"  # manual, sweep, noise
sweep_params = {
    "freq_start": 1000,
    "freq_end": 100000,
    "freq_step": 1000,
    "duty": 50,
    "interval_ms": 100,
    "direction": "restart"  # "restart" o "reverse"
}
noise_params = {
    "freq_min": 1000,
    "freq_max": 10000,
    "duty_min": 10,
    "duty_max": 90
}
current_freq = 1000
current_duty = 50
sweep_running = False
sweep_freq = None

def connect_wifi():
    """Conecta a la red WiFi"""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print(f'Conectando a {WIFI_SSID}...')
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        timeout = 30
        while not wlan.isconnected() and timeout > 0:
            time.sleep(1)
            timeout -= 1
            print(f'Esperando conexión... {timeout}s restantes')
    if wlan.isconnected():
        print(f'Conectado! IP: {wlan.ifconfig()[0]}')
        return wlan.ifconfig()[0]
    else:
        print('No se pudo conectar')
        return None

def init_pwm():
    """Inicializa el PWM"""
    global pwm
    pin = Pin(PWM_PIN, Pin.OUT)
    pwm = PWM(pin)
    pwm.freq(1000)
    pwm.duty_u16(32768)  # 50% duty cycle

def set_pwm(freq, duty):
    """Configura frecuencia y ciclo de trabajo"""
    global pwm, current_freq, current_duty
    if pwm is None:
        init_pwm()
    
    # Limitar frecuencia entre 1Hz y 1MHz
    freq = max(1, min(1000000, int(freq)))
    duty = max(0, min(100, int(duty)))
    
    pwm.freq(freq)
    # duty_u16 va de 0 a 65535
    pwm.duty_u16(int(duty * 655.35))
    
    current_freq = freq
    current_duty = duty

def update_sweep():
    """Actualiza el generador de barrido"""
    global sweep_freq, sweep_params, mode, sweep_direction
    
    if mode != "sweep" or sweep_freq is None:
        return
    
    set_pwm(sweep_freq, sweep_params["duty"])
    
    # Calcular siguiente frecuencia según dirección
    if sweep_params["direction"] == "restart":
        # Modo: reiniciar desde el principio
        if sweep_freq < sweep_params["freq_end"]:
            sweep_freq += sweep_params["freq_step"]
            if sweep_freq > sweep_params["freq_end"]:
                sweep_freq = sweep_params["freq_end"]
        else:
            sweep_freq = sweep_params["freq_start"]
    else:
        # Modo: reversa (ida y vuelta)
        if not hasattr(update_sweep, 'going_up'):
            update_sweep.going_up = True
        
        if update_sweep.going_up:
            sweep_freq += sweep_params["freq_step"]
            if sweep_freq >= sweep_params["freq_end"]:
                sweep_freq = sweep_params["freq_end"]
                update_sweep.going_up = False
        else:
            sweep_freq -= sweep_params["freq_step"]
            if sweep_freq <= sweep_params["freq_start"]:
                sweep_freq = sweep_params["freq_start"]
                update_sweep.going_up = True


def update_noise():
    """Actualiza el generador de ruido"""
    global mode, noise_params
    
    if mode != "noise":
        return
    
    freq = random.randint(noise_params["freq_min"], noise_params["freq_max"])
    duty = random.randint(noise_params["duty_min"], noise_params["duty_max"])
    set_pwm(freq, duty)

# HTML de la página web
HTML_PAGE = '''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Generador de Señales ESP32</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #e0e0e0;
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 900px;
            margin: 0 auto;
        }
        
        h1 {
            text-align: center;
            color: #00d9ff;
            margin-bottom: 30px;
            font-size: 2em;
            text-shadow: 0 0 10px rgba(0, 217, 255, 0.5);
        }
        
        .card {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 20px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }
        
        .card h2 {
            color: #00d9ff;
            margin-bottom: 20px;
            font-size: 1.3em;
            border-bottom: 2px solid rgba(0, 217, 255, 0.3);
            padding-bottom: 10px;
        }
        
        .control-group {
            margin-bottom: 20px;
        }
        
        .control-group label {
            display: block;
            margin-bottom: 8px;
            color: #b0b0b0;
            font-size: 0.9em;
        }
        
        .slider-container {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        input[type="range"] {
            flex: 1;
            height: 8px;
            border-radius: 4px;
            background: linear-gradient(90deg, #0f3460, #00d9ff);
            outline: none;
            -webkit-appearance: none;
        }
        
        input[type="range"]::-webkit-slider-thumb {
            -webkit-appearance: none;
            width: 20px;
            height: 20px;
            border-radius: 50%;
            background: #00d9ff;
            cursor: pointer;
            box-shadow: 0 0 10px rgba(0, 217, 255, 0.5);
        }
        
        input[type="number"] {
            width: 120px;
            padding: 8px 12px;
            border: 1px solid rgba(0, 217, 255, 0.3);
            border-radius: 8px;
            background: rgba(0, 0, 0, 0.3);
            color: #00d9ff;
            font-size: 1em;
            text-align: center;
        }
        
        input[type="number"]:focus {
            outline: none;
            border-color: #00d9ff;
            box-shadow: 0 0 10px rgba(0, 217, 255, 0.3);
        }
        
        .mode-buttons {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        
        .mode-btn {
            flex: 1;
            min-width: 100px;
            padding: 12px 20px;
            border: none;
            border-radius: 8px;
            background: rgba(0, 217, 255, 0.1);
            color: #00d9ff;
            font-size: 1em;
            cursor: pointer;
            transition: all 0.3s ease;
            border: 1px solid rgba(0, 217, 255, 0.3);
        }
        
        .mode-btn:hover {
            background: rgba(0, 217, 255, 0.2);
        }
        
        .mode-btn.active {
            background: #00d9ff;
            color: #1a1a2e;
            box-shadow: 0 0 15px rgba(0, 217, 255, 0.5);
        }
        
        .display-panel {
            background: rgba(0, 0, 0, 0.4);
            border-radius: 10px;
            padding: 20px;
            text-align: center;
            margin-top: 20px;
        }
        
        .display-value {
            font-size: 2.5em;
            color: #00d9ff;
            font-weight: bold;
            text-shadow: 0 0 20px rgba(0, 217, 255, 0.5);
        }
        
        .display-label {
            color: #808080;
            font-size: 0.9em;
            margin-top: 5px;
        }
        
        .grid-2 {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
        }
        
        .hidden {
            display: none;
        }
        
        @media (max-width: 600px) {
            .slider-container {
                flex-direction: column;
                align-items: stretch;
            }
            
            input[type="number"] {
                width: 100%;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎛️ Generador de Señales ESP32</h1>
        
        <div class="card">
            <h2>Modo de Operación</h2>
            <div class="mode-buttons">
                <button class="mode-btn active" onclick="setMode('manual')">Manual</button>
                <button class="mode-btn" onclick="setMode('sweep')">Barrido</button>
                <button class="mode-btn" onclick="setMode('noise')">Ruido</button>
            </div>
        </div>
        
        <div class="card" id="manual-controls">
            <h2>Control Manual</h2>
            <div class="grid-2">
                <div class="control-group">
                    <label>Frecuencia (Hz)</label>
                    <div class="slider-container">
                        <input type="range" id="freq-slider" min="1" max="1000000" value="1000" 
                               oninput="syncInput('freq', this.value)">
                        <input type="number" id="freq-input" min="1" max="1000000" value="1000" 
                               oninput="syncSlider('freq', this.value)">
                    </div>
                </div>
                <div class="control-group">
                    <label>Ciclo de Trabajo (%)</label>
                    <div class="slider-container">
                        <input type="range" id="duty-slider" min="0" max="100" value="50" 
                               oninput="syncInput('duty', this.value)">
                        <input type="number" id="duty-input" min="0" max="100" value="50" 
                               oninput="syncSlider('duty', this.value)">
                    </div>
                </div>
            </div>
        </div>
        
        <div class="card hidden" id="sweep-controls">
            <h2>Generador de Barrido</h2>
            <div class="grid-2">
                <div class="control-group">
                    <label>Frecuencia Inicial (Hz)</label>
                    <input type="number" id="sweep-start" value="1000" onchange="updateParams()">
                </div>
                <div class="control-group">
                    <label>Frecuencia Final (Hz)</label>
                    <input type="number" id="sweep-end" value="100000" onchange="updateParams()">
                </div>
                <div class="control-group">
                    <label>Salto de Frecuencia (Hz)</label>
                    <input type="number" id="sweep-step" value="1000" onchange="updateParams()">
                </div>
                <div class="control-group">
                    <label>Ciclo de Trabajo (%)</label>
                    <input type="number" id="sweep-duty" value="50" min="0" max="100" onchange="updateParams()">
                </div>
                <div class="control-group">
                    <label>Intervalo (ms)</label>
                    <input type="number" id="sweep-interval" value="100" min="10" onchange="updateParams()">
                </div>
                <div class="control-group">
                    <label>Modo al llegar al final</label>
                    <select id="sweep-direction" onchange="updateParams()" style="width: 100%; padding: 8px; border-radius: 8px; background: rgba(0, 0, 0, 0.3); color: #00d9ff; border: 1px solid rgba(0, 217, 255, 0.3);">
                        <option value="restart">Reiniciar desde inicio</option>
                        <option value="reverse">Regresar hacia atrás</option>
                    </select>
                </div>
            </div>
        </div>
        
        <div class="card hidden" id="noise-controls">
            <h2>Generador de Ruido</h2>
            <div class="grid-2">
                <div class="control-group">
                    <label>Frecuencia Mínima (Hz)</label>
                    <input type="number" id="noise-freq-min" value="1000" onchange="updateParams()">
                </div>
                <div class="control-group">
                    <label>Frecuencia Máxima (Hz)</label>
                    <input type="number" id="noise-freq-max" value="10000" onchange="updateParams()">
                </div>
                <div class="control-group">
                    <label>Ciclo Mínimo (%)</label>
                    <input type="number" id="noise-duty-min" value="10" min="0" max="100" onchange="updateParams()">
                </div>
                <div class="control-group">
                    <label>Ciclo Máximo (%)</label>
                    <input type="number" id="noise-duty-max" value="90" min="0" max="100" onchange="updateParams()">
                </div>
            </div>
        </div>
        
        <div class="card">
            <h2>Monitor en Tiempo Real</h2>
            <div class="display-panel">
                <div class="display-value" id="current-freq">1000 Hz</div>
                <div class="display-label">Frecuencia Actual</div>
            </div>
            <div class="display-panel">
                <div class="display-value" id="current-duty">50%</div>
                <div class="display-label">Ciclo de Trabajo Actual</div>
            </div>
        </div>
    </div>
    
    <script>
        let currentMode = 'manual';
        let updateInterval = null;
        
        function syncInput(type, value) {
            document.getElementById(type + '-input').value = value;
            sendUpdate();
        }
        
        function syncSlider(type, value) {
            document.getElementById(type + '-slider').value = value;
            sendUpdate();
        }
        
        function sendUpdate() {
            if (currentMode !== 'manual') return;
            
            const freq = document.getElementById('freq-input').value;
            const duty = document.getElementById('duty-input').value;
            
            fetch('/update', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({freq: parseInt(freq), duty: parseInt(duty)})
            });
        }
        
        function setMode(mode) {
            currentMode = mode;
            
            document.querySelectorAll('.mode-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            event.target.classList.add('active');
            
            document.getElementById('manual-controls').classList.add('hidden');
            document.getElementById('sweep-controls').classList.add('hidden');
            document.getElementById('noise-controls').classList.add('hidden');
            
            if (mode === 'manual') {
                document.getElementById('manual-controls').classList.remove('hidden');
            } else if (mode === 'sweep') {
                document.getElementById('sweep-controls').classList.remove('hidden');
            } else if (mode === 'noise') {
                document.getElementById('noise-controls').classList.remove('hidden');
            }
            
            fetch('/mode', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({mode: mode})
            });
        }
        
        function updateParams() {
            const params = {};
            
            if (currentMode === 'sweep') {
                params.freq_start = parseInt(document.getElementById('sweep-start').value);
                params.freq_end = parseInt(document.getElementById('sweep-end').value);
                params.freq_step = parseInt(document.getElementById('sweep-step').value);
                params.duty = parseInt(document.getElementById('sweep-duty').value);
                params.interval_ms = parseInt(document.getElementById('sweep-interval').value);
                params.direction = document.getElementById('sweep-direction').value;
            } else if (currentMode === 'noise') {
                params.freq_min = parseInt(document.getElementById('noise-freq-min').value);
                params.freq_max = parseInt(document.getElementById('noise-freq-max').value);
                params.duty_min = parseInt(document.getElementById('noise-duty-min').value);
                params.duty_max = parseInt(document.getElementById('noise-duty-max').value);
            }
            
            fetch('/params', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(params)
            });
        }
        
        function updateDisplay() {
            fetch('/status')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('current-freq').textContent = formatFreq(data.freq) + ' Hz';
                    document.getElementById('current-duty').textContent = data.duty + '%';
                    
                    if (currentMode === 'manual') {
                        document.getElementById('freq-slider').value = data.freq;
                        document.getElementById('freq-input').value = data.freq;
                        document.getElementById('duty-slider').value = data.duty;
                        document.getElementById('duty-input').value = data.duty;
                    }
                });
        }
        
        function formatFreq(freq) {
            if (freq >= 1000000) {
                return (freq / 1000000).toFixed(2) + 'M';
            } else if (freq >= 1000) {
                return (freq / 1000).toFixed(2) + 'k';
            }
            return freq.toString();
        }
        
        // Actualizar cada 500ms
        setInterval(updateDisplay, 500);
        
        // Cargar estado inicial
        updateDisplay();
    </script>
</body>
</html>'''

def start_server(ip):
    """Inicia el servidor web"""
    addr = socket.getaddrinfo(ip, 80)[0][-1]
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(addr)
    server.listen(5)
    print(f'Servidor web escuchando en http://{ip}:80')
    return server

def handle_client(client):
    """Maneja la solicitud de un cliente"""
    global mode, sweep_params, noise_params, sweep_freq, sweep_running
    
    try:
        request = client.recv(4096).decode()
        lines = request.split('\n')
        
        if not lines:
            return
        
        first_line = lines[0].split()
        if len(first_line) < 2:
            return
        
        method = first_line[0]
        path = first_line[1]
        
        # Servir página HTML
        if path == '/' and method == 'GET':
            response = 'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n'
            client.send(response.encode())
            client.send(HTML_PAGE.encode())
        
        # Actualizar PWM (modo manual)
        elif path == '/update' and method == 'POST':
            # Encontrar el cuerpo de la solicitud
            body_start = request.find('\r\n\r\n')
            if body_start != -1:
                body = request[body_start + 4:]
                try:
                    data = json.loads(body)
                    freq = data.get('freq', current_freq)
                    duty = data.get('duty', current_duty)
                    set_pwm(freq, duty)
                    mode = 'manual'
                except:
                    pass
            
            response = 'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n{"status":"ok"}'
            client.send(response.encode())
        
        # Cambiar modo
        elif path == '/mode' and method == 'POST':
            body_start = request.find('\r\n\r\n')
            if body_start != -1:
                body = request[body_start + 4:]
                try:
                    data = json.loads(body)
                    new_mode = data.get('mode', 'manual')
                    
                    if new_mode in ['manual', 'sweep', 'noise']:
                        mode = new_mode
                        
                        if new_mode == 'sweep':
                            sweep_freq = sweep_params['freq_start']
                            sweep_running = True
                        elif new_mode == 'noise':
                            sweep_running = True
                        else:
                            sweep_running = False
                            set_pwm(current_freq, current_duty)
                except:
                    pass
            
            response = 'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n{"status":"ok"}'
            client.send(response.encode())
        
        # Actualizar parámetros
        elif path == '/params' and method == 'POST':
            body_start = request.find('\r\n\r\n')
            if body_start != -1:
                body = request[body_start + 4:]
                try:
                    data = json.loads(body)
                    
                    if 'freq_start' in data:
                        sweep_params['freq_start'] = data['freq_start']
                    if 'freq_end' in data:
                        sweep_params['freq_end'] = data['freq_end']
                    if 'freq_step' in data:
                        sweep_params['freq_step'] = data['freq_step']
                    if 'duty' in data:
                        sweep_params['duty'] = data['duty']
                    if 'interval_ms' in data:
                        sweep_params['interval_ms'] = data['interval_ms']
                    if 'direction' in data:
                        sweep_params['direction'] = data['direction']
                        # Reset direction state when changing mode
                        if hasattr(update_sweep, 'going_up'):
                            del update_sweep.going_up
                    if 'freq_min' in data:
                        noise_params['freq_min'] = data['freq_min']
                    if 'freq_max' in data:
                        noise_params['freq_max'] = data['freq_max']
                    if 'duty_min' in data:
                        noise_params['duty_min'] = data['duty_min']
                    if 'duty_max' in data:
                        noise_params['duty_max'] = data['duty_max']
                except:
                    pass
            
            response = 'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n{"status":"ok"}'
            client.send(response.encode())
        
        # Obtener estado actual
        elif path == '/status' and method == 'GET':
            status = json.dumps({'freq': current_freq, 'duty': current_duty})
            response = f'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nConnection: close\r\n\r\n{status}'
            client.send(response.encode())
        
        client.close()
        
    except Exception as e:
        print(f'Error: {e}')
        try:
            client.close()
        except:
            pass

def main():
    """Función principal"""
    print('=' * 50)
    print('Generador de Señales ESP32')
    print('=' * 50)
    
    # Conectar WiFi
    ip = connect_wifi()
    if ip is None:
        print('No se pudo conectar a WiFi. Saliendo...')
        return
    
    # Inicializar PWM
    init_pwm()
    print(f'PWM inicializado en GPIO {PWM_PIN}')
    
    # Iniciar servidor
    server = start_server(ip)
    
    last_sweep_update = 0
    
    print('\nServidor iniciado. Abre tu navegador y ve a la IP mostrada arriba.')
    print('Presiona Ctrl+C para detener.\n')
    
    try:
        while True:
            # Manejar clientes con timeout
            try:
                server.settimeout(0.1)
                client, addr = server.accept()
                handle_client(client)
            except OSError:
                pass  # Timeout, continuar
            
            # Actualizar barrido o ruido
            current_time = time.ticks_ms()
            
            if mode == 'sweep' and sweep_running:
                if time.ticks_diff(current_time, last_sweep_update) >= sweep_params['interval_ms']:
                    update_sweep()
                    last_sweep_update = current_time
            
            elif mode == 'noise' and sweep_running:
                if time.ticks_diff(current_time, last_sweep_update) >= 50:  # Actualizar cada 50ms
                    update_noise()
                    last_sweep_update = current_time
            
            time.sleep_ms(10)
            
    except KeyboardInterrupt:
        print('\nDeteniendo servidor...')
        if pwm:
            pwm.deinit()
        server.close()
        print('Servidor detenido.')

if __name__ == '__main__':
    main()