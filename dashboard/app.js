console.log("Dashboard frontend loaded.");

/* ===========================
   WebSocket Connection
=========================== */

let socket;

function connectWebSocket() {
    const url = "ws://" + window.location.hostname + ":8001";
    console.log("Connecting WebSocket:", url);

    socket = new WebSocket(url);

    socket.onopen = () => console.log("WebSocket connected.");

    socket.onclose = () => {
        console.log("WebSocket disconnected. Reconnecting in 3s…");
        setTimeout(connectWebSocket, 3000);
    };

    socket.onerror = (err) => {
        console.error("WebSocket error:", err);
    };

    socket.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        console.log("Received:", msg);

        updateSensorCards(msg);
        updateNodes(msg.nodes);

        if (msg.alert) addAlert(msg.alert);
    };
}

connectWebSocket();

/* ===========================
   Nodes UI
=========================== */

function updateNodes(nodes) {
    const container = document.getElementById("node-list");
    container.innerHTML = "";

    if (!nodes || nodes.length === 0) {
        container.innerHTML = `<i>No nodes detected.</i>`;
        return;
    }

    nodes.forEach(n => {
        const div = document.createElement("div");
        div.className = "node-card";
        div.innerHTML = `
            <strong>${n.label}</strong><br>
            Value: ${n.value.toFixed(1)} ${n.unit}<br>
            Distance: ${n.distance.toFixed(2)} ${n.dist_unit}
        `;
        container.appendChild(div);
    });
}

/* ===========================
   Sensor Cards
=========================== */

function updateSensorCards(msg) {
    document.getElementById("mq3-value").textContent = msg.mq3.toFixed(1);
    document.getElementById("temp-value").textContent = msg.temp.toFixed(1);
    document.getElementById("dist-mq3-value").textContent = msg.dist_mq3.toFixed(2);
    document.getElementById("dist-temp-value").textContent = msg.dist_temp.toFixed(2);
}

/* ===========================
   Alerts
=========================== */

function addAlert(message) {
    const container = document.getElementById("alert-feed");

    const card = document.createElement("div");
    card.className = "alert-card";

    card.innerHTML = `
        <strong>${message}</strong>
        <div class="alert-time">${new Date().toLocaleTimeString()}</div>
    `;

    container.prepend(card);
}

/* ===========================
   Log Viewer
=========================== */

async function loadLog() {
    const box = document.getElementById("log-box");
    box.value = "Loading...";

    try {
        const res = await fetch("http://" + window.location.hostname + ":8081/log");
        box.value = await res.text();
    } catch (e) {
        box.value = "Failed to load log.";
    }
}