console.log("Dashboard frontend loaded.");

function setNodeStatus(isOnline) {
    const valueElement = document.querySelector(".value");
  
    if (isOnline) {
      valueElement.textContent = "Online";
      valueElement.classList.remove("offline");
      valueElement.classList.add("online");
    } else {
      valueElement.textContent = "Offline";
      valueElement.classList.remove("online");
      valueElement.classList.add("offline");
    }
  }  

function addAlert(message) {
  const alertFeed = document.getElementById("alert-feed");

  const alertCard = document.createElement("div");
  alertCard.className = "alert-card";

  const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  alertCard.innerHTML = `
  <div class="alert-icon">⚠️</div>
  <div class="alert-content">
    <strong>${message}</strong>
    <div class="alert-time">Received at ${timestamp}</div>
  </div>
`;

  // Inserare alertă nouă la începutul listei
  alertFeed.prepend(alertCard);

  // Animație fade-in
  alertCard.style.opacity = 0;
  setTimeout(() => {
    alertCard.style.transition = "opacity 0.4s ease";
    alertCard.style.opacity = 1;
  }, 10);

  alertCard.classList.add("new");
setTimeout(() => alertCard.classList.remove("new"), 800);

}

// SETUP WEBSOCKET (placeholder until backend is ready)
let socket;

function connectWebSocket() {
  socket = new WebSocket("ws://localhost:8001/ws"); // backend-ul real va rula pe acest port

  socket.onopen = () => {
    console.log("WebSocket connected!");
    setNodeStatus(true);
  };

  socket.onmessage = (event) => {
    console.log("Received:", event.data);
    const data = JSON.parse(event.data);

    if (data.type === "alert") {
      addAlert(data.message);
    }

    if (data.type === "status") {
      setNodeStatus(data.online);
    }
  };

  socket.onclose = () => {
    console.log("WebSocket disconnected. Reconnecting in 3s…");
    setNodeStatus(false);
    setTimeout(connectWebSocket, 3000);
  };

  socket.onerror = (err) => {
    console.error("WebSocket error:", err);
    socket.close();
  };
}

connectWebSocket();

// TEMP: Simulare WebSocket dacă backend-ul nu rulează
setTimeout(() => {
    console.log("Simulated WS: sending test messages…");
  
    // Simulare online
    setNodeStatus(true);
  
    // Simulare alertă la 3 sec.
    setTimeout(() => {
      addAlert("🚨 Test Alert: Scream detected (fake message)");
    }, 3000);
  
  }, 2000);

  alertCard.classList.add("alert-type-danger");

  document.querySelector("section").classList.add("animate-fade");

  // =============================
// LIVE LINE CHART (NO LIBRARIES)
// =============================

const canvas = document.getElementById("soundChart");
const ctx = canvas.getContext("2d");

let dataPoints = [];
const maxPoints = 50;   // câte puncte afișăm simultan

function drawChart() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // Axă orizontală
  ctx.strokeStyle = "#444";
  ctx.beginPath();
  ctx.moveTo(0, canvas.height - 20);
  ctx.lineTo(canvas.width, canvas.height - 20);
  ctx.stroke();

  if (dataPoints.length < 2) return;

  ctx.strokeStyle = "#ff4b5c";  // crimson line
  ctx.lineWidth = 2;
  
  ctx.beginPath();
  let step = canvas.width / (dataPoints.length - 1);

  dataPoints.forEach((value, i) => {
    let x = i * step;
    let y = canvas.height - 20 - value;
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });

  ctx.stroke();
}

// Adaugă un nou punct pe grafic
function addSoundLevel(value) {
  dataPoints.push(value);

  if (dataPoints.length > maxPoints) {
    dataPoints.shift();  // eliminăm cel mai vechi punct
  }

  drawChart();
}
// Simulare valori sunet (0 - 150)
setInterval(() => {
    const simulatedValue = Math.random() * 150;
    addSoundLevel(simulatedValue);
  }, 500);
  

  

