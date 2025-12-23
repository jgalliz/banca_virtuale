from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from datetime import datetime
import secrets
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(16))

# Database simulato (in memoria) - NOTA: su Render si resetterà ad ogni riavvio
# Per persistenza reale servirebbero PostgreSQL o Redis
players = {}
pending_registrations = {}
transactions = []
settings = {'initial_balance': 100}

# Template base
BASE_TEMPLATE = '''
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Banca Virtuale Natalizia</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }
        h1, h2 { color: #667eea; margin-bottom: 20px; }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #f0f0f0;
        }
        .btn {
            padding: 10px 20px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
            transition: background 0.3s;
            font-size: 14px;
        }
        .btn:hover { background: #764ba2; }
        .btn-danger { background: #e74c3c; }
        .btn-danger:hover { background: #c0392b; }
        .btn-success { background: #27ae60; }
        .btn-success:hover { background: #229954; }
        .btn-warning { background: #f39c12; }
        .btn-warning:hover { background: #e67e22; }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            color: #333;
        }
        input, select {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 16px;
        }
        .player-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        .player-card {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 10px;
            border-left: 4px solid #667eea;
        }
        .player-card.pending {
            border-left-color: #f39c12;
            opacity: 0.7;
        }
        .player-name { font-weight: bold; font-size: 18px; color: #333; }
        .player-balance {
            font-size: 24px;
            color: #27ae60;
            margin-top: 10px;
        }
        .player-balance.negative { color: #e74c3c; }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background: #667eea;
            color: white;
        }
        tr:hover { background: #f8f9fa; }
        .flash {
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 5px;
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .flash.error {
            background: #f8d7da;
            color: #721c24;
            border-color: #f5c6cb;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        .stat-card {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }
        .stat-value {
            font-size: 32px;
            font-weight: bold;
            color: #667eea;
        }
        .stat-label {
            color: #666;
            margin-top: 5px;
        }
        .badge {
            display: inline-block;
            padding: 5px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
        }
        .badge-pending {
            background: #fff3cd;
            color: #856404;
        }
        .menu {
            display: flex;
            gap: 10px;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }
    </style>
</head>
<body>
    <div class="container">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="flash {{ 'error' if category == 'error' else '' }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        {% block content %}{% endblock %}
    </div>
</body>
</html>
'''

HOME_TEMPLATE = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', '''
    <h1 style="text-align: center;">🎄 Banca Virtuale Natalizia 🎅</h1>
    <div style="max-width: 600px; margin: 50px auto; text-align: center;">
        <p style="font-size: 18px; color: #666; margin-bottom: 40px;">
            Benvenuto! Scegli come vuoi accedere:
        </p>
        <div style="display: grid; gap: 20px;">
            <a href="{{ url_for('admin_login') }}" class="btn" style="padding: 20px; font-size: 18px;">
                🔑 Accesso Amministratore
            </a>
            <a href="{{ url_for('player_register') }}" class="btn btn-success" style="padding: 20px; font-size: 18px;">
                ➕ Registrati come Giocatore
            </a>
            <a href="{{ url_for('player_login') }}" class="btn btn-warning" style="padding: 20px; font-size: 18px;">
                👤 Accedi come Giocatore
            </a>
        </div>
    </div>
''')

ADMIN_LOGIN_TEMPLATE = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', '''
    <h1 style="text-align: center;">🔑 Login Amministratore</h1>
    <div style="max-width: 400px; margin: 50px auto;">
        <form method="POST">
            <div class="form-group">
                <label>Password:</label>
                <input type="password" name="password" required autofocus>
            </div>
            <button type="submit" class="btn" style="width: 100%;">Accedi</button>
        </form>
        <p style="margin-top: 20px; text-align: center;">
            <a href="{{ url_for('index') }}" style="color: #667eea;">← Torna alla home</a>
        </p>
        <p style="margin-top: 20px; text-align: center; color: #666; font-size: 12px;">
            Password predefinita: <strong>admin123</strong>
        </p>
    </div>
''')

PLAYER_REGISTER_TEMPLATE = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', '''
    <h1 style="text-align: center;">➕ Registrazione Giocatore</h1>
    <div style="max-width: 400px; margin: 50px auto;">
        <form method="POST">
            <div class="form-group">
                <label>Nome e Cognome:</label>
                <input type="text" name="name" required autofocus>
            </div>
            <div class="form-group">
                <label>Crea una Password:</label>
                <input type="password" name="password" required minlength="4">
            </div>
            <button type="submit" class="btn btn-success" style="width: 100%;">Invia Richiesta</button>
        </form>
        <p style="margin-top: 20px; text-align: center; color: #666;">
            La tua registrazione sarà approvata dall'amministratore
        </p>
        <p style="margin-top: 10px; text-align: center;">
            <a href="{{ url_for('index') }}" style="color: #667eea;">← Torna alla home</a>
        </p>
    </div>
''')

PLAYER_LOGIN_TEMPLATE = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', '''
    <h1 style="text-align: center;">👤 Accesso Giocatore</h1>
    <div style="max-width: 400px; margin: 50px auto;">
        <form method="POST">
            <div class="form-group">
                <label>Seleziona il tuo nome:</label>
                <select name="player_id" required>
                    <option value="">Seleziona...</option>
                    {% for player_id, player in players.items() %}
                        <option value="{{ player_id }}">{{ player.name }}</option>
                    {% endfor %}
                </select>
            </div>
            <div class="form-group">
                <label>Password:</label>
                <input type="password" name="password" required>
            </div>
            <button type="submit" class="btn btn-warning" style="width: 100%;">Accedi</button>
        </form>
        <p style="margin-top: 20px; text-align: center;">
            <a href="{{ url_for('index') }}" style="color: #667eea;">← Torna alla home</a>
        </p>
    </div>
''')

PLAYER_DASHBOARD_TEMPLATE = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', '''
    <div class="header">
        <h1>👤 Ciao, {{ player.name }}!</h1>
        <a href="{{ url_for('logout') }}" class="btn btn-danger">Esci</a>
    </div>
    
    <div style="text-align: center; margin: 50px 0;">
        <div style="background: #f8f9fa; padding: 40px; border-radius: 15px; max-width: 400px; margin: 0 auto;">
            <div style="color: #666; margin-bottom: 10px;">Il tuo saldo attuale:</div>
            <div style="font-size: 72px; font-weight: bold; color: {{ '#27ae60' if player.balance >= 0 else '#e74c3c' }};">
                €{{ player.balance }}
            </div>
        </div>
    </div>

    <h2>📜 Le tue transazioni</h2>
    {% if player_transactions %}
        <table>
            <thead>
                <tr>
                    <th>Data/Ora</th>
                    <th>Tipo</th>
                    <th>Importo</th>
                    <th>Motivo</th>
                </tr>
            </thead>
            <tbody>
                {% for t in player_transactions|reverse %}
                <tr>
                    <td>{{ t.timestamp }}</td>
                    <td>
                        {% if t.to_player == player.name %}
                            <span style="color: #27ae60;">📥 Ricevuto</span>
                        {% else %}
                            <span style="color: #e74c3c;">📤 Inviato</span>
                        {% endif %}
                    </td>
                    <td style="font-weight: bold; color: {{ '#27ae60' if t.to_player == player.name else '#e74c3c' }};">
                        {{ '+' if t.to_player == player.name else '-' }}€{{ t.amount }}
                    </td>
                    <td>{{ t.reason }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    {% else %}
        <p style="text-align: center; color: #999; padding: 40px;">Nessuna transazione ancora</p>
    {% endif %}

    <h2 style="margin-top: 40px;">👥 Classifica Giocatori</h2>
    <div class="player-grid">
        {% for p_id, p in all_players.items() %}
            <div class="player-card {{ 'pending' if p_id == player_id else '' }}">
                <div class="player-name">
                    {{ p.name }}
                    {% if p_id == player_id %}
                        <span style="color: #667eea;">(Tu)</span>
                    {% endif %}
                </div>
                <div class="player-balance {{ 'negative' if p.balance < 0 else '' }}">
                    €{{ p.balance }}
                </div>
            </div>
        {% endfor %}
    </div>
''')

ADMIN_DASHBOARD_TEMPLATE = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', '''
    <div class="header">
        <h1>🎮 Dashboard Amministratore</h1>
        <a href="{{ url_for('logout') }}" class="btn btn-danger">Esci</a>
    </div>
    
    {% if pending_registrations %}
    <div style="background: #fff3cd; border: 2px solid #ffc107; padding: 20px; border-radius: 10px; margin-bottom: 30px;">
        <h2 style="color: #856404; margin-bottom: 15px;">⏳ Richieste in Attesa ({{ pending_registrations|length }})</h2>
        {% for reg_id, reg in pending_registrations.items() %}
        <div style="background: white; padding: 15px; border-radius: 8px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
            <div>
                <strong>{{ reg.name }}</strong>
                <span style="color: #666; font-size: 14px; margin-left: 10px;">Richiesta: {{ reg.timestamp }}</span>
            </div>
            <div style="display: flex; gap: 10px;">
                <form method="POST" action="{{ url_for('approve_player', reg_id=reg_id) }}" style="display: inline;">
                    <button type="submit" class="btn btn-success">✓ Approva</button>
                </form>
                <form method="POST" action="{{ url_for('reject_player', reg_id=reg_id) }}" style="display: inline;">
                    <button type="submit" class="btn btn-danger">✗ Rifiuta</button>
                </form>
            </div>
        </div>
        {% endfor %}
    </div>
    {% endif %}
    
    <div class="menu">
        <a href="{{ url_for('transfer') }}" class="btn">💸 Nuovo Trasferimento</a>
        <a href="{{ url_for('final_report') }}" class="btn">📊 Report Finale</a>
        <a href="{{ url_for('settings_page') }}" class="btn">⚙️ Impostazioni</a>
    </div>

    <div class="stats">
        <div class="stat-card">
            <div class="stat-value">{{ players|length }}</div>
            <div class="stat-label">Giocatori Attivi</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{{ pending_registrations|length }}</div>
            <div class="stat-label">In Attesa</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{{ transactions|length }}</div>
            <div class="stat-label">Transazioni</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">€{{ total_money }}</div>
            <div class="stat-label">Denaro in Circolazione</div>
        </div>
    </div>

    <h2>👥 Giocatori</h2>
    {% if players %}
        <div class="player-grid">
            {% for player_id, player in players.items() %}
                <div class="player-card">
                    <div class="player-name">{{ player.name }}</div>
                    <div class="player-balance {{ 'negative' if player.balance < 0 else '' }}">
                        €{{ player.balance }}
                    </div>
                </div>
            {% endfor %}
        </div>
    {% else %}
        <p style="text-align: center; color: #999; padding: 40px;">Nessun giocatore approvato</p>
    {% endif %}

    <h2 style="margin-top: 40px;">📜 Ultime Transazioni</h2>
    {% if transactions %}
        <table>
            <thead>
                <tr>
                    <th>Data/Ora</th>
                    <th>Da</th>
                    <th>A</th>
                    <th>Importo</th>
                    <th>Motivo</th>
                </tr>
            </thead>
            <tbody>
                {% for t in transactions[-10:]|reverse %}
                <tr>
                    <td>{{ t.timestamp }}</td>
                    <td>{{ t.from_player }}</td>
                    <td>{{ t.to_player }}</td>
                    <td style="color: #27ae60; font-weight: bold;">€{{ t.amount }}</td>
                    <td>{{ t.reason }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    {% else %}
        <p style="text-align: center; color: #999; padding: 40px;">Nessuna transazione</p>
    {% endif %}
''')

TRANSFER_TEMPLATE = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', '''
    <div class="header">
        <h1>💸 Nuovo Trasferimento</h1>
        <a href="{{ url_for('admin_dashboard') }}" class="btn">← Dashboard</a>
    </div>
    
    <div style="max-width: 500px; margin: 0 auto;">
        <form method="POST">
            <div class="form-group">
                <label>Da Giocatore:</label>
                <select name="from_player" required>
                    <option value="">Seleziona...</option>
                    {% for player_id, player in players.items() %}
                        <option value="{{ player_id }}">{{ player.name }} (€{{ player.balance }})</option>
                    {% endfor %}
                </select>
            </div>
            <div class="form-group">
                <label>A Giocatore:</label>
                <select name="to_player" required>
                    <option value="">Seleziona...</option>
                    {% for player_id, player in players.items() %}
                        <option value="{{ player_id }}">{{ player.name }} (€{{ player.balance }})</option>
                    {% endfor %}
                </select>
            </div>
            <div class="form-group">
                <label>Importo:</label>
                <input type="number" name="amount" min="1" required>
            </div>
            <div class="form-group">
                <label>Motivo:</label>
                <input type="text" name="reason" placeholder="es. Vinto alla tombola" required>
            </div>
            <button type="submit" class="btn btn-success" style="width: 100%;">Effettua Trasferimento</button>
        </form>
    </div>
''')

REPORT_TEMPLATE = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', '''
    <div class="header">
        <h1>📊 Report Finale</h1>
        <a href="{{ url_for('admin_dashboard') }}" class="btn">← Dashboard</a>
    </div>
    
    <h2>Riepilogo Saldi</h2>
    <table>
        <thead>
            <tr>
                <th>Giocatore</th>
                <th>Saldo Iniziale</th>
                <th>Saldo Finale</th>
                <th>Differenza</th>
                <th>Azione</th>
            </tr>
        </thead>
        <tbody>
            {% for player_id, player in players.items() %}
            <tr>
                <td><strong>{{ player.name }}</strong></td>
                <td>€{{ initial_balance }}</td>
                <td style="font-weight: bold; color: {{ '#27ae60' if player.balance >= 0 else '#e74c3c' }}">
                    €{{ player.balance }}
                </td>
                <td style="font-weight: bold; color: {{ '#27ae60' if player.balance >= initial_balance else '#e74c3c' }}">
                    {{ '+' if player.balance >= initial_balance else '' }}€{{ player.balance - initial_balance }}
                </td>
                <td>
                    {% if player.balance > initial_balance %}
                        <span style="color: #27ae60;">✅ Deve ricevere €{{ player.balance - initial_balance }}</span>
                    {% elif player.balance < initial_balance %}
                        <span style="color: #e74c3c;">💰 Deve dare €{{ initial_balance - player.balance }}</span>
                    {% else %}
                        <span style="color: #999;">➖ Pari</span>
                    {% endif %}
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

    <div style="background: #fff3cd; border: 1px solid #ffc107; padding: 20px; border-radius: 10px; margin-top: 30px;">
        <h3 style="color: #856404;">💡 Come regolare i conti:</h3>
        <ul style="margin-left: 20px; color: #856404;">
            <li>Chi ha un saldo MAGGIORE del saldo iniziale deve RICEVERE la differenza in soldi veri</li>
            <li>Chi ha un saldo MINORE del saldo iniziale deve DARE la differenza in soldi veri</li>
            <li>Chi ha lo stesso saldo iniziale non deve dare né ricevere nulla</li>
        </ul>
    </div>
''')

SETTINGS_TEMPLATE = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', '''
    <div class="header">
        <h1>⚙️ Impostazioni</h1>
        <a href="{{ url_for('admin_dashboard') }}" class="btn">← Dashboard</a>
    </div>
    
    <div style="max-width: 500px; margin: 0 auto;">
        <form method="POST">
            <div class="form-group">
                <label>Saldo Iniziale Predefinito:</label>
                <input type="number" name="initial_balance" value="{{ settings.initial_balance }}" required>
            </div>
            <button type="submit" class="btn btn-success" style="width: 100%;">Salva Impostazioni</button>
        </form>
        
        <div style="margin-top: 40px; padding: 20px; background: #f8d7da; border-radius: 10px;">
            <h3 style="color: #721c24;">⚠️ Zona Pericolosa</h3>
            <form method="POST" action="{{ url_for('reset_all') }}" 
                  onsubmit="return confirm('Sei sicuro di voler resettare TUTTO? Questa azione non può essere annullata!');">
                <button type="submit" class="btn btn-danger" style="width: 100%; margin-top: 10px;">
                    🗑️ Reset Completo (Cancella Tutto)
                </button>
            </form>
        </div>
    </div>
''')

# ROUTES
@app.route('/')
def index():
    if 'admin' in session:
        return redirect(url_for('admin_dashboard'))
    if 'player_id' in session:
        return redirect(url_for('player_dashboard'))
    return render_template_string(HOME_TEMPLATE)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == 'admin123':
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
        flash('Password errata!', 'error')
    return render_template_string(ADMIN_LOGIN_TEMPLATE)

@app.route('/player/register', methods=['GET', 'POST'])
def player_register():
    if request.method == 'POST':
        name = request.form.get('name')
        password = request.form.get('password')
        
        if len(players) + len(pending_registrations) >= 20:
            flash('Limite massimo di 20 giocatori raggiunto!', 'error')
            return redirect(url_for('index'))
        
        reg_id = f"reg_{len(pending_registrations) + 1}"
        pending_registrations[reg_id] = {
            'name': name,
            'password': password,
            'timestamp': datetime.now().strftime('%d/%m/%Y %H:%M')
        }
        flash('Richiesta inviata! Attendi l\'approvazione dell\'amministratore.', 'success')
        return redirect(url_for('index'))
    
    return render_template_string(PLAYER_REGISTER_TEMPLATE)

@app.route('/player/login', methods=['GET', 'POST'])
def player_login():
    if request.method == 'POST':
        player_id = request.form.get('player_id')
        password = request.form.get('password')
        
        if player_id in players and players[player_id]['password'] == password:
            session['player_id'] = player_id
            return redirect(url_for('player_dashboard'))
        flash('Credenziali errate!', 'error')
    
    return render_template_string(PLAYER_LOGIN_TEMPLATE, players=players)

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    
    total_money = sum(p['balance'] for p in players.values())
    return render_template_string(ADMIN_DASHBOARD_TEMPLATE, 
                                 players=players,
                                 pending_registrations=pending_registrations,
                                 transactions=transactions,
                                 total_money=total_money)

@app.route('/player/dashboard')
def player_dashboard():
    if 'player_id' not in session:
        return redirect(url_for('player_login'))
    
    player_id = session['player_id']
    if player_id not in players:
        session.pop('player_id', None)
        flash('Account non trovato!', 'error')
        return redirect(url_for('index'))
    
    player = players[player_id]
    player_transactions = [t for t in transactions if t['from_player'] == player['name'] or t['to_player'] == player['name']]
    
    return render_template_string(PLAYER_DASHBOARD_TEMPLATE,
                                 player=player,
                                 player_id=player_id,
                                 player_transactions=player_transactions,
                                 all_players=players)

@app.route('/admin/approve/<reg_id>', methods=['POST'])
def approve_player(reg_id):
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    
    if reg_id in pending_registrations:
        reg = pending_registrations.pop(reg_id)
        player_id = f"player_{len(players) + 1}"
        players[player_id] = {
            'name': reg['name'],
            'password': reg['password'],
            'balance': settings['initial_balance']
        }
        flash(f'Giocatore {reg["name"]} approvato!', 'success')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/reject/<reg_id>', methods=['POST'])
def reject_player(reg_id):
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    
    if reg_id in pending_registrations:
        reg = pending_registrations.pop(reg_id)
        flash(f'Richiesta di {reg["name"]} rifiutata.', 'success')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/transfer', methods=['GET', 'POST'])
def transfer():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        from_player = request.form.get('from_player')
        to_player = request.form.get('to_player')
        amount = int(request.form.get('amount'))
        reason = request.form.get('reason')
        
        if from_player == to_player:
            flash('Non puoi trasferire denaro allo stesso giocatore!', 'error')
            return redirect(url_for('transfer'))
        
        if players[from_player]['balance'] < amount:
            flash('Saldo insufficiente!', 'error')
            return redirect(url_for('transfer'))
        
        players[from_player]['balance'] -= amount
        players[to_player]['balance'] += amount
        
        transactions.append({
            'timestamp': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
            'from_player': players[from_player]['name'],
            'to_player': players[to_player]['name'],
            'amount': amount,
            'reason': reason
        })
        
        flash(f'Trasferimento di €{amount} completato!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template_string(TRANSFER_TEMPLATE, players=players)

@app.route('/admin/report')
def final_report():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    
    return render_template_string(REPORT_TEMPLATE, 
                                 players=players, 
                                 initial_balance=settings['initial_balance'])

@app.route('/admin/settings', methods=['GET', 'POST'])
def settings_page():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        settings['initial_balance'] = int(request.form.get('initial_balance'))
        flash('Impostazioni salvate!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template_string(SETTINGS_TEMPLATE, settings=settings)

@app.route('/admin/reset', methods=['POST'])
def reset_all():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    
    players.clear()
    pending_registrations.clear()
    transactions.clear()
    flash('Tutti i dati sono stati cancellati!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    flash('Disconnesso con successo!', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
