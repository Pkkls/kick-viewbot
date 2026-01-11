#!/usr/bin/env python3
"""
Serveur API pour contrôler les VMs Kali - Kick Viewbot
À exécuter sur ton PC Windows (192.168.1.6)
Sauvegarde ce fichier sous le nom : server.py
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import paramiko
import threading
import time
import os
import re

app = Flask(__name__)
CORS(app)

# ============================================================
# CONFIGURATION - Modifie ces valeurs si nécessaire
# ============================================================

VMS = [
    '192.168.1.101',
    '192.168.1.84',
    '192.168.1.4',
    '192.168.1.11',
    '192.168.1.182'
]

SSH_USER = 'kali'
SSH_PASS = 'kali'
SSH_PORT = 22

REMOTE_PROJECT_DIR = '/home/kali/Desktop/kick-viewbot-main'
LOCAL_KICK_SCRIPT = './kick.py'  # kick.py doit être dans le même dossier que server.py

# Cache des statuts
vm_status = {}
vm_stats = {}

# ============================================================
# FONCTIONS SSH
# ============================================================

def ssh_connect(vm_ip):
    """Établit une connexion SSH à une VM"""
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            vm_ip,
            port=SSH_PORT,
            username=SSH_USER,
            password=SSH_PASS,
            timeout=10,
            allow_agent=False,
            look_for_keys=False
        )
        return client
    except Exception as e:
        print(f"[ERROR] Connexion SSH à {vm_ip}: {e}")
        return None

def execute_ssh_command(vm_ip, command, timeout=30):
    """Exécute une commande SSH sur une VM"""
    client = ssh_connect(vm_ip)
    if not client:
        return None, f"Impossible de se connecter à {vm_ip}"
    
    try:
        stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        output = stdout.read().decode('utf-8')
        error = stderr.read().decode('utf-8')
        return output, error
    except Exception as e:
        return None, str(e)
    finally:
        client.close()

# ============================================================
# FONCTIONS DE DÉPLOIEMENT
# ============================================================

def deploy_script_to_vm(vm_ip):
    """Déploie le script kick.py et les fichiers de setup sur une VM"""
    try:
        client = ssh_connect(vm_ip)
        if not client:
            return False, f"Connexion impossible à {vm_ip}"
        
        sftp = client.open_sftp()
        
        # Créer le dossier si nécessaire
        try:
            sftp.stat(REMOTE_PROJECT_DIR)
        except:
            execute_ssh_command(vm_ip, f'mkdir -p {REMOTE_PROJECT_DIR}')
        
        # Upload kick.py
        if os.path.exists(LOCAL_KICK_SCRIPT):
            remote_kick = f'{REMOTE_PROJECT_DIR}/kick.py'
            print(f"[INFO] Upload de kick.py vers {vm_ip}...")
            sftp.put(LOCAL_KICK_SCRIPT, remote_kick)
            execute_ssh_command(vm_ip, f'chmod +x {remote_kick}')
        else:
            sftp.close()
            client.close()
            return False, f"kick.py introuvable dans {os.path.abspath(LOCAL_KICK_SCRIPT)}"
        
        # Créer ensure_venv.sh
        ensure_venv_content = '''#!/bin/bash
PROJECT="$HOME/Desktop/kick-viewbot-main"
VENV="$PROJECT/venv"
PY="$VENV/bin/python"

cd "$PROJECT" || exit 1

if [ -x "$PY" ] && "$PY" -c "import fake_useragent" >/dev/null 2>&1; then
    exit 0
fi

rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install fake_useragent tls_client typing_extensions websockets
'''
        
        # Créer un fichier temporaire Windows
        temp_file = os.path.join(os.environ.get('TEMP', '.'), 'ensure_venv_tmp.sh')
        with open(temp_file, 'w', newline='\n') as f:
            f.write(ensure_venv_content)
        
        ensure_venv_path = f'{REMOTE_PROJECT_DIR}/ensure_venv.sh'
        sftp.put(temp_file, ensure_venv_path)
        execute_ssh_command(vm_ip, f'chmod +x {ensure_venv_path}')
        
        # Nettoyer le fichier temporaire
        try:
            os.remove(temp_file)
        except:
            pass
        
        # Exécuter le setup du venv
        print(f"[INFO] Installation des dépendances sur {vm_ip}...")
        output, error = execute_ssh_command(vm_ip, f'cd {REMOTE_PROJECT_DIR} && bash ensure_venv.sh', timeout=120)
        
        sftp.close()
        client.close()
        
        return True, "Déploiement réussi"
    except Exception as e:
        return False, f"Erreur déploiement: {e}"

# ============================================================
# FONCTIONS MULLVAD
# ============================================================

def get_random_mullvad_location():
    """Retourne une location Mullvad aléatoire"""
    import random
    
    # Liste de locations Mullvad populaires
    locations = [
        'us-nyc',      # New York
        'us-lax',      # Los Angeles
        'us-mia',      # Miami
        'us-chi',      # Chicago
        'us-dal',      # Dallas
        'ca-tor',      # Toronto
        'gb-lon',      # London
        'de-fra',      # Frankfurt
        'de-ber',      # Berlin
        'fr-par',      # Paris
        'nl-ams',      # Amsterdam
        'se-sto',      # Stockholm
        'ch-zur',      # Zurich
        'au-syd',      # Sydney
        'jp-tyo',      # Tokyo
        'sg-sin',      # Singapore
    ]
    
    return random.choice(locations)

def change_mullvad_location(vm_ip, location=None):
    """Change la location Mullvad sur une VM"""
    try:
        if location is None:
            location = get_random_mullvad_location()
        
        print(f"[INFO] Changement de location Mullvad sur {vm_ip} vers {location}...")
        
        # Déconnecter Mullvad
        execute_ssh_command(vm_ip, 'mullvad disconnect', timeout=10)
        time.sleep(2)
        
        # Changer la location
        output, error = execute_ssh_command(vm_ip, f'mullvad relay set location {location}', timeout=10)
        time.sleep(1)
        
        # Reconnecter
        connect_output, connect_error = execute_ssh_command(vm_ip, 'mullvad connect', timeout=15)
        time.sleep(3)
        
        # Vérifier la connexion
        status_output, _ = execute_ssh_command(vm_ip, 'mullvad status', timeout=10)
        
        if 'Connected' in status_output:
            return True, f"Connecté à {location}"
        else:
            return False, f"Échec de connexion: {status_output}"
            
    except Exception as e:
        return False, f"Erreur Mullvad: {e}"

def reconnect_mullvad(vm_ip):
    """Reconnecte Mullvad (utile si planté)"""
    try:
        print(f"[INFO] Reconnexion Mullvad sur {vm_ip}...")
        
        # Déconnecter d'abord
        execute_ssh_command(vm_ip, 'mullvad disconnect', timeout=10)
        time.sleep(2)
        
        # Reconnecter
        output, error = execute_ssh_command(vm_ip, 'mullvad connect', timeout=15)
        time.sleep(3)
        
        # Vérifier le statut
        status_output, _ = execute_ssh_command(vm_ip, 'mullvad status', timeout=10)
        
        if 'Connected' in status_output:
            return True, "Mullvad reconnecté"
        else:
            return False, f"Échec reconnexion: {status_output}"
            
    except Exception as e:
        return False, f"Erreur reconnexion: {e}"

def get_mullvad_status(vm_ip):
    """Récupère le statut Mullvad d'une VM"""
    try:
        output, _ = execute_ssh_command(vm_ip, 'mullvad status', timeout=10)
        
        if 'Connected' in output:
            # Extraire la location si possible
            import re
            location_match = re.search(r'to ([a-z]{2}-[a-z]{3})', output)
            location = location_match.group(1) if location_match else 'unknown'
            return {
                'connected': True,
                'location': location,
                'status': output.strip()
            }
        else:
            return {
                'connected': False,
                'location': None,
                'status': output.strip()
            }
    except:
        return {
            'connected': False,
            'location': None,
            'status': 'Error'
        }

# ============================================================
# FONCTIONS DE CONTRÔLE
# ============================================================

def start_script_on_vm(vm_ip, channel, viewers):
    """Démarre le script kick.py sur une VM"""
    try:
        # Arrêter les instances existantes
        print(f"[INFO] Arrêt des anciennes instances sur {vm_ip}...")
        execute_ssh_command(vm_ip, f'pkill -f "python.*kick.py"')
        time.sleep(1)
        
        # Créer un script de démarrage automatique
        input_script = f'''#!/bin/bash
cd {REMOTE_PROJECT_DIR}
source venv/bin/activate
echo -e "{channel}\\n{viewers}" | python kick.py > kick.log 2>&1 &
'''
        
        # Upload et exécuter
        client = ssh_connect(vm_ip)
        if not client:
            return False, "Connexion impossible"
        
        sftp = client.open_sftp()
        start_script_path = f'{REMOTE_PROJECT_DIR}/start_kick.sh'
        
        with sftp.open(start_script_path, 'w') as f:
            f.write(input_script)
        
        execute_ssh_command(vm_ip, f'chmod +x {start_script_path}')
        print(f"[INFO] Démarrage du script sur {vm_ip}...")
        output, error = execute_ssh_command(vm_ip, f'bash {start_script_path}')
        
        sftp.close()
        client.close()
        
        time.sleep(2)
        
        # Vérifier que le script tourne
        output, _ = execute_ssh_command(vm_ip, 'pgrep -f "python.*kick.py"')
        if output and output.strip():
            return True, "Script démarré avec succès"
        else:
            return False, f"Le script n'a pas démarré. Error: {error}"
    except Exception as e:
        return False, f"Erreur démarrage: {e}"

def stop_script_on_vm(vm_ip):
    """Arrête le script kick.py sur une VM"""
    try:
        print(f"[INFO] Arrêt du script sur {vm_ip}...")
        output, error = execute_ssh_command(vm_ip, 'pkill -f "python.*kick.py"')
        time.sleep(1)
        
        # Vérifier que c'est bien arrêté
        check, _ = execute_ssh_command(vm_ip, 'pgrep -f "python.*kick.py"')
        if not check or not check.strip():
            return True, "Script arrêté"
        else:
            return False, "Le script tourne encore"
    except Exception as e:
        return False, f"Erreur arrêt: {e}"

def check_vm_status(vm_ip):
    """Vérifie le statut d'une VM"""
    try:
        # Vérifier si le script tourne
        output, _ = execute_ssh_command(vm_ip, 'pgrep -f "python.*kick.py"', timeout=5)
        
        if output and output.strip():
            status = 'running'
            
            # Essayer de récupérer les stats du log
            log_output, _ = execute_ssh_command(vm_ip, f'tail -20 {REMOTE_PROJECT_DIR}/kick.log', timeout=5)
            
            stats = parse_stats_from_log(log_output)
            
            # Récupérer le statut Mullvad
            mullvad_status = get_mullvad_status(vm_ip)
            if stats:
                stats['mullvad'] = mullvad_status
            else:
                stats = {'mullvad': mullvad_status}
            
            vm_stats[vm_ip] = stats
        else:
            status = 'stopped'
            # Même arrêté, on peut vérifier Mullvad
            mullvad_status = get_mullvad_status(vm_ip)
            vm_stats[vm_ip] = {'mullvad': mullvad_status}
        
        vm_status[vm_ip] = status
        return status
    except:
        vm_status[vm_ip] = 'offline'
        return 'offline'

def parse_stats_from_log(log_text):
    """Parse les statistiques depuis les logs"""
    if not log_text:
        return None
    
    stats = {
        'connections': 0,
        'viewers': 0,
        'pings': 0,
        'heartbeats': 0
    }
    
    try:
        # Chercher les lignes de stats
        connections_match = re.search(r'Connections:\s*(\d+)', log_text)
        viewers_match = re.search(r'Viewers:\s*(\d+)', log_text)
        pings_match = re.search(r'Pings:\s*(\d+)', log_text)
        heartbeats_match = re.search(r'Heartbeats:\s*(\d+)', log_text)
        
        if connections_match:
            stats['connections'] = int(connections_match.group(1))
        if viewers_match:
            stats['viewers'] = int(viewers_match.group(1))
        if pings_match:
            stats['pings'] = int(pings_match.group(1))
        if heartbeats_match:
            stats['heartbeats'] = int(heartbeats_match.group(1))
        
        return stats
    except:
        return stats

def status_monitor_thread():
    """Thread pour monitorer les VMs en continu"""
    while True:
        for vm_ip in VMS:
            check_vm_status(vm_ip)
        time.sleep(10)

# ============================================================
# ROUTES API
# ============================================================

@app.route('/status', methods=['GET'])
def get_status():
    """Retourne le statut de toutes les VMs"""
    result = {}
    for vm_ip in VMS:
        result[vm_ip] = {
            'status': vm_status.get(vm_ip, 'unknown'),
            'stats': vm_stats.get(vm_ip)
        }
    return jsonify(result)

@app.route('/execute', methods=['POST'])
def execute_action():
    """Exécute une action sur une ou toutes les VMs"""
    data = request.json
    action = data.get('action')
    vm_ip = data.get('vm_ip')
    channel = data.get('channel', '')
    viewers = data.get('viewers', 100)
    
    print(f"\n[ACTION] {action} - Channel: {channel} - Viewers: {viewers}")
    
    if action == 'deploy':
        # Déployer sur toutes les VMs
        results = []
        for ip in VMS:
            success, msg = deploy_script_to_vm(ip)
            results.append(f"{ip}: {msg}")
            print(f"  {ip}: {msg}")
        return jsonify({
            'success': True,
            'message': 'Déploiement terminé\n' + '\n'.join(results)
        })
    
    elif action == 'start_all':
        results = []
        for ip in VMS:
            success, msg = start_script_on_vm(ip, channel, viewers)
            results.append(f"{ip}: {msg}")
            print(f"  {ip}: {msg}")
        return jsonify({
            'success': True,
            'message': 'Démarrage sur toutes les VMs\n' + '\n'.join(results)
        })
    
    elif action == 'stop_all':
        results = []
        for ip in VMS:
            success, msg = stop_script_on_vm(ip)
            results.append(f"{ip}: {msg}")
            print(f"  {ip}: {msg}")
        return jsonify({
            'success': True,
            'message': 'Arrêt sur toutes les VMs\n' + '\n'.join(results)
        })
    
    elif action == 'start' and vm_ip:
        success, msg = start_script_on_vm(vm_ip, channel, viewers)
        return jsonify({'success': success, 'message': msg})
    
    elif action == 'stop' and vm_ip:
        success, msg = stop_script_on_vm(vm_ip)
        return jsonify({'success': success, 'message': msg})
    
    elif action == 'mullvad_reconnect_all':
        results = []
        for ip in VMS:
            success, msg = reconnect_mullvad(ip)
            results.append(f"{ip}: {msg}")
            print(f"  {ip}: {msg}")
        return jsonify({
            'success': True,
            'message': 'Reconnexion Mullvad terminée\n' + '\n'.join(results)
        })
    
    elif action == 'mullvad_random_all':
        results = []
        for ip in VMS:
            success, msg = change_mullvad_location(ip)
            results.append(f"{ip}: {msg}")
            print(f"  {ip}: {msg}")
        return jsonify({
            'success': True,
            'message': 'Changement de locations Mullvad terminé\n' + '\n'.join(results)
        })
    
    elif action == 'mullvad_reconnect' and vm_ip:
        success, msg = reconnect_mullvad(vm_ip)
        return jsonify({'success': success, 'message': msg})
    
    elif action == 'mullvad_random' and vm_ip:
        success, msg = change_mullvad_location(vm_ip)
        return jsonify({'success': success, 'message': msg})
    
    else:
        return jsonify({'success': False, 'message': 'Action invalide'})

@app.route('/logs/<vm_ip>', methods=['GET'])
def get_logs(vm_ip):
    """Récupère les logs d'une VM"""
    if vm_ip not in VMS:
        return jsonify({'error': 'VM invalide'}), 404
    
    output, error = execute_ssh_command(vm_ip, f'tail -100 {REMOTE_PROJECT_DIR}/kick.log')
    
    if output:
        logs = output.strip().split('\n')
        return jsonify({'logs': logs})
    else:
        return jsonify({'logs': [], 'error': error})

# ============================================================
# DÉMARRAGE DU SERVEUR
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Serveur API Kick Viewbot Control")
    print("=" * 60)
    print(f"Démarrage sur http://192.168.1.6:5000")
    print(f"VMs configurées: {len(VMS)}")
    print(f"Script local: {os.path.abspath(LOCAL_KICK_SCRIPT)}")
    print("=" * 60)
    print("\nLe serveur surveille les VMs toutes les 10 secondes...")
    print("Appuie sur Ctrl+C pour arrêter\n")
    
    # Démarrer le thread de monitoring
    monitor = threading.Thread(target=status_monitor_thread, daemon=True)
    monitor.start()
    
    # Démarrer le serveur Flask
    app.run(host='0.0.0.0', port=5000, debug=False)