from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

active_pcs = {}
ALL_LOGS = []

@app.route('/log', methods=['POST'])
def receive_log():
    data = request.json
    if not data:
        return jsonify({"error": "No data"}), 400
    
    pc = data.get("pc", "Unknown")
    time_str = data.get("time", "")
    log_msg = data.get("log", "")
    event_type = data.get("event_type", "log")
    
    log_entry = {
        "pc": pc,
        "log": log_msg,
        "type": event_type
    }
    ALL_LOGS.append(log_entry)
    if len(ALL_LOGS) > 200:
        ALL_LOGS.pop(0)
        
    if pc not in active_pcs:
        active_pcs[pc] = {
            "lastSeen": time_str,
            "totalSaved": 0,
            "remainingMails": 0,
            "lastLog": log_msg,
            "eventType": event_type
        }
    
    if event_type == "mail_done":
        active_pcs[pc]["totalSaved"] += 1

    if "remaining" in data and data["remaining"] is not None:
        try:
            rem_val = int(data["remaining"])
            if rem_val > 0:
                active_pcs[pc]["remainingMails"] = rem_val
            elif event_type == "start" and rem_val == 0:
                active_pcs[pc]["remainingMails"] = 0
        except ValueError:
            pass

    active_pcs[pc]["lastSeen"] = time_str
    active_pcs[pc]["lastLog"] = log_msg
    active_pcs[pc]["eventType"] = event_type
    
    return jsonify({"status": "ok"}), 200

@app.route('/api/stats', methods=['GET'])
def get_stats():
    grand_total_saved = 0
    grand_total_remaining = 0
    pc_list = []
    
    for pc, info in active_pcs.items():
        grand_total_saved += info["totalSaved"]
        grand_total_remaining += info["remainingMails"]
        pc_list.append({
            "pcName": pc,
            "saved": info["totalSaved"],
            "remaining": info["remainingMails"],
            "lastActive": info["lastSeen"],
            "lastLog": info["lastLog"]
        })
        
    return jsonify({
        "totalConnectedPCs": len(active_pcs),
        "grandTotalSaved": grand_total_saved,
        "grandTotalRemaining": grand_total_remaining,
        "pcDetails": pc_list,
        "logs": ALL_LOGS[-50:]
    })

@app.route('/api/delete/<pc_name>', methods=['POST'])
def delete_pc(pc_name):
    if pc_name in active_pcs:
        del active_pcs[pc_name]
    return jsonify({"status": "deleted"})

@app.route('/api/clear-all', methods=['POST'])
def clear_all():
    global active_pcs, ALL_LOGS
    active_pcs = {}
    ALL_LOGS = []
    return jsonify({"status": "cleared"})

@app.route('/', methods=['GET'])
def home():
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Bulk Automation Monitor by Imran</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 20px; }
            .container { max-width: 1100px; margin: 0 auto; }
            .header-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; }
            h1 { color: #38bdf8; margin: 0; font-size: 24px; }
            .btn-clear-all { background: #dc2626; color: white; border: none; padding: 10px 18px; border-radius: 8px; cursor: pointer; font-weight: bold; font-size: 14px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
            .btn-clear-all:hover { background: #b91c1c; }
            .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 20px; margin-bottom: 25px; }
            .card { background: #1e293b; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); border-left: 5px solid #38bdf8; }
            .card.green { border-left-color: #22c55e; }
            .card.orange { border-left-color: #f59e0b; }
            .card h3 { margin: 0; font-size: 14px; color: #94a3b8; text-transform: uppercase; }
            .card p { font-size: 28px; font-weight: bold; margin: 10px 0 0 0; color: #fff; }
            table { width: 100%; border-collapse: collapse; background: #1e293b; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.3); margin-bottom: 25px; }
            th, td { padding: 15px; text-align: left; border-bottom: 1px solid #334155; }
            th { background: #334155; color: #38bdf8; text-transform: uppercase; font-size: 12px; }
            tr:hover { background: #273548; }
            .badge { background: #0284c7; color: white; padding: 4px 8px; border-radius: 6px; font-size: 12px; }
            .btn-delete { background: #ef4444; color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 12px; }
            .btn-delete:hover { background: #dc2626; }
            
            .log-section-title { color: #f1f5f9; font-size: 18px; margin-bottom: 10px; }
            .log-container { background: #111318; border: 1px solid #334155; border-radius: 12px; padding: 15px; height: 220px; overflow-y: auto; font-family: 'Consolas', monospace; font-size: 12px; color: #98c379; box-shadow: inset 0 2px 4px rgba(0,0,0,0.5); }
            .log-line { margin-bottom: 4px; word-break: break-all; }
            .refresh-note { text-align: center; color: #64748b; margin-top: 15px; font-size: 13px; }
        </style>
        <script>
            async function fetchStats() {
                try {
                    let res = await fetch('/api/stats');
                    let data = await res.json();
                    document.getElementById('pcs').innerText = data.totalConnectedPCs;
                    document.getElementById('saved').innerText = data.grandTotalSaved;
                    document.getElementById('remaining').innerText = data.grandTotalRemaining;
                    
                    let tbody = document.getElementById('pc-table-body');
                    let existingRows = {};
                    for (let row of tbody.rows) {
                        if (row.cells.length > 0 && row.cells[0].innerText) {
                            existingRows[row.cells[0].innerText.trim()] = row;
                        }
                    }

                    if(data.pcDetails.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; color:#64748b;">No PC connected or history cleared.</td></tr>';
                    } else {
                        if(tbody.rows.length === 1 && tbody.rows[0].cells.length === 1) {
                            tbody.innerHTML = '';
                        }

                        data.pcDetails.forEach(pc => {
                            let logMsg = pc.lastLog || 'No activity';
                            let activeTime = pc.lastActive || '';

                            if (existingRows[pc.pcName]) {
                                let row = existingRows[pc.pcName];
                                row.cells[1].innerText = pc.saved;
                                row.cells[2].innerText = pc.remaining;
                                row.cells[3].innerText = logMsg;
                                row.cells[4].innerText = activeTime;
                                delete existingRows[pc.pcName];
                            } else {
                                let tr = document.createElement('tr');
                                tr.innerHTML = `<td><span class="badge">${pc.pcName}</span></td>
                                                <td style="color: #22c55e; font-weight:bold;">${pc.saved}</td>
                                                <td style="color: #f59e0b; font-weight:bold;">${pc.remaining}</td>
                                                <td style="color: #cbd5e1; font-family:monospace; font-size:12px;">${logMsg}</td>
                                                <td style="color: #94a3b8; font-size:13px;">${activeTime}</td>
                                                <td><button class="btn-delete" onclick="deletePC('${pc.pcName}')">🗑️ Delete</button></td>`;
                                tbody.appendChild(tr);
                            }
                        });

                        for (let pcName in existingRows) {
                            existingRows[pcName].remove();
                        }
                    }

                    let logBox = document.getElementById('live-log-box');
                    let isScrolledToBottom = logBox.scrollHeight - logBox.clientHeight <= logBox.scrollTop + 20;
                    
                    let logHtml = '';
                    if(data.logs && data.logs.length > 0) {
                        data.logs.forEach(l => {
                            let color = l.type === 'stop' ? '#ef4444' : (l.type === 'start' ? '#38bdf8' : '#98c379');
                            logHtml += `<div class="log-line" style="color: ${color};">[${l.pc}] ${l.log}</div>`;
                        });
                    } else {
                        logHtml = '<div style="color: #64748b;">Waiting for activity logs...</div>';
                    }
                    logBox.innerHTML = logHtml;
                    
                    if (isScrolledToBottom) {
                        logBox.scrollTop = logBox.scrollHeight;
                    }

                } catch(e) { console.log(e); }
            }

            async function deletePC(pcName) {
                if(confirm(pcName + ' er history remove korte chan?')) {
                    await fetch('/api/delete/' + pcName, { method: 'POST' });
                    fetchStats();
                }
            }

            async function clearAllHistory() {
                if(confirm('Apni ki shob PC-r history clear korte chan?')) {
                    await fetch('/api/clear-all', { method: 'POST' });
                    fetchStats();
                }
            }

            setInterval(fetchStats, 1000);
            window.onload = fetchStats;
        </script>
    </head>
    <body>
        <div class="container">
            <div class="header-row">
                <h1>📧 Bulk Automation Monitor Dashboard by Imran</h1>
                <button class="btn-clear-all" onclick="clearAllHistory()">🗑️ Clear All History</button>
            </div>
            
            <div class="cards">
                <div class="card">
                    <h3>Connected PCs</h3>
                    <p id="pcs">0</p>
                </div>
                <div class="card green">
                    <h3>Total Mails Saved</h3>
                    <p id="saved">0</p>
                </div>
                <div class="card orange">
                    <h3>Total Remaining</h3>
                    <p id="remaining">0</p>
                </div>
            </div>
            
            <h2 style="color: #f1f5f9; font-size: 18px; margin-bottom: 12px;">Bulk Automation PCs Status</h2>
            <table>
                <thead>
                    <tr>
                        <th>PC Name</th>
                        <th>Completed</th>
                        <th>Remaining</th>
                        <th>Latest Activity</th>
                        <th>Last Active Time</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody id="pc-table-body">
                    <!-- Dynamic Rows -->
                </tbody>
            </table>

            <div class="log-section-title">📜 Live System Logs</div>
            <div id="live-log-box" class="log-container">
                <!-- Live Logs -->
            </div>

            <div class="refresh-note">🔄 Live Instant Syncing...</div>
        </div>
    </body>
    </html>
    """
    return render_template_string(html_template)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
