document.addEventListener('DOMContentLoaded', async () => {
  // Initialize Three.js signature animations safely (prevents WebGL support issues from blocking the UI)
  try { initThreeJS(); } catch (e) { console.warn("initThreeJS failed:", e); }
  try { initSharedRoomsThreeJS(); } catch (e) { console.warn("initSharedRoomsThreeJS failed:", e); }
  try { initStreamingAgentsThreeJS(); } catch (e) { console.warn("initStreamingAgentsThreeJS failed:", e); }
  
  try { initTabs(); } catch (e) { console.warn("initTabs failed:", e); }
  try { initFAQ(); } catch (e) { console.warn("initFAQ failed:", e); }
  try { initAuthModal(); } catch (e) { console.warn("initAuthModal failed:", e); }

  // Single-Page View Router based on Authentication State
  const token = localStorage.getItem('forgeroom_token');
  let isPermanentUser = false;
  let userProfile = null;

  if (token) {
    try {
      const meRes = await fetch(`${API_URL}/api/auth/me`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (meRes.ok) {
        userProfile = await meRes.json();
        if (!userProfile.name.startsWith("Guest_")) {
          isPermanentUser = true;
        }
      } else {
        localStorage.removeItem('forgeroom_token');
      }
    } catch (e) {
      console.error("Error fetching user profile:", e);
    }
  }

  const landingView = document.getElementById('landing-page-view');
  const dashboardView = document.getElementById('dashboard-view');

  if (isPermanentUser && userProfile) {
    if (landingView) landingView.style.display = 'none';
    if (dashboardView) dashboardView.style.display = 'grid';
    // Load full screen collaborative workspace
    try { initDashboard(token, userProfile); } catch (e) { console.error("initDashboard failed:", e); }
  } else {
    if (landingView) landingView.style.display = 'block';
    if (dashboardView) dashboardView.style.display = 'none';
    // Load landing page interactive preview console
    try { initLiveConsole(); } catch (e) { console.error("initLiveConsole failed:", e); }

    // Auto-open auth modal if hash is #login or #signup
    const startupHash = window.location.hash;
    if (startupHash === "#login" || startupHash === "#signup") {
      const isSignUp = startupHash === "#signup";
      setTimeout(() => {
        const ctaBtn = document.getElementById(isSignUp ? 'header-cta' : 'nav-login-btn');
        if (ctaBtn) ctaBtn.click();
      }, 300);
    }
  }
});

// Premium Color Palette Constants
const COLORS = {
  aiTeal: 0x00E5FF,       // Electric Teal
  userViolet: 0x8B5CF6,   // Hyper Violet
  userAmber: 0xFFA726,    // Neon Amber
  brandPink: 0xFF2E93,    // Crimson Pink
  gridEmerald: 0x10B981   // Emerald Highlight
};

// Backend API configuration
const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
const isNetlify = window.location.hostname.includes('netlify.app');

// Production backend on Render
const PROD_BACKEND = "https://forgeroom.onrender.com";

const API_URL = isLocalhost 
  ? "http://localhost:8002" 
  : (isNetlify ? PROD_BACKEND : window.location.origin);

const WS_URL = isLocalhost 
  ? "ws://localhost:8002" 
  : (isNetlify 
      ? PROD_BACKEND.replace("https://", "wss://").replace("http://", "ws://") 
      : (window.location.protocol === 'https:' ? 'wss://' : 'ws://') + window.location.host);

// ==========================================
// 1. HERO MAIN THREE.JS SIGNATURE ANIMATION
// ==========================================
function initThreeJS() {
  const container = document.getElementById('threejs-container');
  if (!container) return;

  let gl;
  try {
    const canvas = document.createElement('canvas');
    gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
  } catch (e) {}

  const fallback = document.getElementById('threejs-fallback');
  if (!gl) {
    if (fallback) fallback.style.display = 'flex';
    container.style.display = 'none';
    return;
  }

  const scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x07090e, 0.08);

  const camera = new THREE.PerspectiveCamera(60, container.clientWidth / container.clientHeight, 0.1, 100);
  camera.position.set(0, 3.8, 6.5);
  camera.lookAt(0, 0, 0);

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setSize(container.clientWidth, container.clientHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  container.appendChild(renderer.domElement);

  scene.add(new THREE.AmbientLight(0xffffff, 0.2));
  const dirLight1 = new THREE.DirectionalLight(COLORS.aiTeal, 1.2);
  dirLight1.position.set(5, 8, 5);
  scene.add(dirLight1);

  const dirLight2 = new THREE.DirectionalLight(COLORS.brandPink, 0.6);
  dirLight2.position.set(-5, -8, -5);
  scene.add(dirLight2);

  const pointLight = new THREE.PointLight(COLORS.userViolet, 2, 10);
  pointLight.position.set(0, 2, 0);
  scene.add(pointLight);

  const gridHelper = new THREE.GridHelper(8, 20, 0x2C3E50, COLORS.aiTeal);
  gridHelper.position.y = -0.5;
  scene.add(gridHelper);

  const platformGeo = new THREE.BoxGeometry(8, 0.1, 8);
  const platformMat = new THREE.MeshPhongMaterial({
    color: 0x0c121e,
    transparent: true,
    opacity: 0.7,
    shininess: 80
  });
  const platform = new THREE.Mesh(platformGeo, platformMat);
  platform.position.y = -0.55;
  scene.add(platform);

  const aiNodeGroup = new THREE.Group();
  scene.add(aiNodeGroup);

  const aiCoreGeo = new THREE.IcosahedronGeometry(0.8, 2);
  const aiCoreMat = new THREE.MeshBasicMaterial({
    color: COLORS.aiTeal,
    wireframe: true,
    transparent: true,
    opacity: 0.6
  });
  const aiCore = new THREE.Mesh(aiCoreGeo, aiCoreMat);
  aiNodeGroup.add(aiCore);

  const aiSolidGeo = new THREE.IcosahedronGeometry(0.45, 1);
  const aiSolidMat = new THREE.MeshPhongMaterial({
    color: COLORS.aiTeal,
    emissive: COLORS.userViolet,
    emissiveIntensity: 0.8,
    shininess: 100
  });
  const aiSolid = new THREE.Mesh(aiSolidGeo, aiSolidMat);
  aiNodeGroup.add(aiSolid);
  aiNodeGroup.position.set(0, 1.2, 0);

  const humanGroup = new THREE.Group();
  scene.add(humanGroup);

  const humans = [];
  const humanPositions = [
    { x: -2.2, z: 2.0, color: COLORS.userViolet },
    { x: 2.2, z: 2.0, color: COLORS.userAmber },
    { x: 0, z: -2.8, color: COLORS.brandPink }
  ];

  humanPositions.forEach((pos, idx) => {
    const singleHuman = new THREE.Group();
    
    const bodyGeo = new THREE.CylinderGeometry(0.2, 0.25, 0.9, 16);
    const bodyMat = new THREE.MeshPhongMaterial({ color: pos.color, shininess: 40, flatShading: true });
    const body = new THREE.Mesh(bodyGeo, bodyMat);
    body.position.y = 0.45;
    singleHuman.add(body);

    const headGeo = new THREE.SphereGeometry(0.18, 16, 16);
    const headMat = new THREE.MeshPhongMaterial({ color: 0xF5F7FA, emissive: pos.color, emissiveIntensity: 0.2 });
    const head = new THREE.Mesh(headGeo, headMat);
    head.position.y = 1.05;
    singleHuman.add(head);

    const ringGeo = new THREE.RingGeometry(0.35, 0.4, 32);
    const ringMat = new THREE.MeshBasicMaterial({ color: pos.color, side: THREE.DoubleSide, transparent: true, opacity: 0.5 });
    const ring = new THREE.Mesh(ringGeo, ringMat);
    ring.rotation.x = Math.PI / 2;
    ring.position.y = -0.49;
    singleHuman.add(ring);

    const cursorGeo = new THREE.ConeGeometry(0.08, 0.2, 4);
    const cursorMat = new THREE.MeshBasicMaterial({ color: pos.color });
    const cursor = new THREE.Mesh(cursorGeo, cursorMat);
    cursor.rotation.x = Math.PI / 1.5;
    cursor.position.set(pos.x * 0.6, -0.4, pos.z * 0.6);
    scene.add(cursor);

    singleHuman.position.set(pos.x, 0, pos.z);
    humanGroup.add(singleHuman);

    humans.push({
      mesh: singleHuman,
      cursor: cursor,
      cursorX: pos.x * 0.6,
      cursorZ: pos.z * 0.6,
      angle: Math.random() * Math.PI * 2
    });
  });

  const particlesGeo = new THREE.SphereGeometry(0.05, 8, 8);
  const dataParticles = [];

  for (let i = 0; i < 12; i++) {
    let pColor = COLORS.aiTeal;
    if (i % 3 === 1) pColor = COLORS.userViolet;
    else if (i % 3 === 2) pColor = COLORS.brandPink;

    const pMat = new THREE.MeshBasicMaterial({ color: pColor });
    const p = new THREE.Mesh(particlesGeo, pMat);
    p.userData = {
      humanIndex: i % 3,
      progress: Math.random(),
      direction: Math.random() > 0.4 ? 1 : -1
    };
    scene.add(p);
    dataParticles.push(p);
  }

  const canvasGeo = new THREE.PlaneGeometry(1.6, 1.1);
  const canvasMat = new THREE.MeshBasicMaterial({ color: 0x0c101d, side: THREE.DoubleSide, transparent: true, opacity: 0.85 });
  const floatingCanvas = new THREE.Mesh(canvasGeo, canvasMat);
  floatingCanvas.rotation.x = -Math.PI / 5;
  floatingCanvas.position.set(0, 0.3, 0.6);
  scene.add(floatingCanvas);

  const edgeGeo = new THREE.EdgesGeometry(canvasGeo);
  const edgeMat = new THREE.LineBasicMaterial({ color: COLORS.userViolet, linewidth: 2 });
  const wireframe = new THREE.LineSegments(edgeGeo, edgeMat);
  floatingCanvas.add(wireframe);

  let mouseX = 0, mouseY = 0;
  window.addEventListener('mousemove', (e) => {
    mouseX = (e.clientX / window.innerWidth) * 2 - 1;
    mouseY = -(e.clientY / window.innerHeight) * 2 + 1;
  });

  let time = 0;
  function animate() {
    requestAnimationFrame(animate);
    time += 0.015;

    const pulseScale = 1 + Math.cos(time * 2.5) * 0.08;
    aiSolid.scale.set(pulseScale, pulseScale, pulseScale);
    aiCore.scale.set(pulseScale * 1.05, pulseScale * 1.05, pulseScale * 1.05);
    aiCore.rotation.y += 0.005;
    aiCore.rotation.x += 0.003;

    const r = Math.sin(time) * 0.5 + 0.5;
    aiSolidMat.color.setHSL(r * 0.2 + 0.5, 0.9, 0.5);
    aiSolidMat.emissiveIntensity = 0.7 + Math.sin(time * 5) * 0.25;

    humans.forEach((h, idx) => {
      h.mesh.position.y = Math.sin(time * 2 + idx) * 0.02;
      h.angle += 0.02;
      h.cursor.position.x = h.cursorX + Math.cos(h.angle) * 0.25;
      h.cursor.position.z = h.cursorZ + Math.sin(h.angle) * 0.15;
      h.cursor.position.y = -0.45 + Math.abs(Math.sin(time * 3 + idx)) * 0.05;
    });

    dataParticles.forEach((p) => {
      const h = humans[p.userData.humanIndex];
      p.userData.progress += 0.008 * p.userData.direction;

      if (p.userData.progress > 1) p.userData.progress = 0;
      else if (p.userData.progress < 0) p.userData.progress = 1;

      const start = new THREE.Vector3(0, 1.2, 0);
      const end = new THREE.Vector3(h.mesh.position.x, 0.7, h.mesh.position.z);
      p.position.lerpVectors(start, end, p.userData.progress);
      p.scale.setScalar(Math.sin(p.userData.progress * Math.PI) * 1.2);
    });

    floatingCanvas.position.y = 0.3 + Math.sin(time * 1.5) * 0.04;

    camera.position.x += (mouseX * 1.8 - camera.position.x) * 0.05;
    camera.position.y += (3.8 + mouseY * 0.8 - camera.position.y) * 0.05;
    camera.lookAt(0, 0.3, 0);

    renderer.render(scene, camera);
  }

  window.addEventListener('resize', () => {
    camera.aspect = container.clientWidth / container.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(container.clientWidth, container.clientHeight);
  });

  animate();
}

// ==========================================
// 2. LIVE SHARED ROOMS MINI 3D ANIMATION
// ==========================================
function initSharedRoomsThreeJS() {
  const canvas = document.getElementById('canvas-shared-rooms');
  if (!canvas) return;

  const container = canvas.parentElement;
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 50);
  camera.position.set(0, 2.5, 4.5);
  camera.lookAt(0, 0, 0);

  const renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true, alpha: true });
  renderer.setSize(container.clientWidth, container.clientHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

  scene.add(new THREE.AmbientLight(0xffffff, 0.4));
  const light = new THREE.DirectionalLight(COLORS.aiTeal, 1.2);
  light.position.set(2, 4, 2);
  scene.add(light);

  const centralGeo = new THREE.SphereGeometry(0.35, 16, 16);
  const centralMat = new THREE.MeshPhongMaterial({ color: COLORS.aiTeal, emissive: COLORS.aiTeal, emissiveIntensity: 0.4 });
  const centralNode = new THREE.Mesh(centralGeo, centralMat);
  scene.add(centralNode);

  const orbitsGroup = new THREE.Group();
  scene.add(orbitsGroup);

  const userConfigs = [
    { color: COLORS.userViolet, dist: 1.3, speed: 1.0 },
    { color: COLORS.userAmber, dist: 1.5, speed: 0.7 },
    { color: COLORS.brandPink, dist: 1.7, speed: 1.2 }
  ];

  const userNodes = [];
  const lines = [];

  userConfigs.forEach((uc, idx) => {
    const userGeo = new THREE.SphereGeometry(0.12, 12, 12);
    const userMat = new THREE.MeshPhongMaterial({ color: uc.color, emissive: uc.color });
    const user = new THREE.Mesh(userGeo, userMat);
    orbitsGroup.add(user);

    userNodes.push({
      mesh: user,
      dist: uc.dist,
      speed: uc.speed,
      angle: (idx / userConfigs.length) * Math.PI * 2
    });

    const lineMat = new THREE.LineBasicMaterial({ color: uc.color, transparent: true, opacity: 0.4 });
    const lineGeo = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0, 0, 0), new THREE.Vector3(0, 0, 0)]);
    const line = new THREE.Line(lineGeo, lineMat);
    scene.add(line);
    lines.push(line);
  });

  let time = 0;
  function animate() {
    requestAnimationFrame(animate);
    time += 0.015;

    const scale = 1 + Math.sin(time * 3) * 0.1;
    centralNode.scale.set(scale, scale, scale);

    userNodes.forEach((node, idx) => {
      node.angle += 0.01 * node.speed;
      node.mesh.position.x = Math.cos(node.angle) * node.dist;
      node.mesh.position.z = Math.sin(node.angle) * node.dist;
      node.mesh.position.y = Math.sin(time * 2 + idx) * 0.15;

      const positions = lines[idx].geometry.attributes.position.array;
      positions[3] = node.mesh.position.x;
      positions[4] = node.mesh.position.y;
      positions[5] = node.mesh.position.z;
      lines[idx].geometry.attributes.position.needsUpdate = true;
    });

    orbitsGroup.rotation.y = time * 0.15;
    renderer.render(scene, camera);
  }

  window.addEventListener('resize', () => {
    camera.aspect = container.clientWidth / container.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(container.clientWidth, container.clientHeight);
  });

  animate();
}

// ==========================================
// 3. STREAMING AI AGENTS WAVES ANIMATION
// ==========================================
function initStreamingAgentsThreeJS() {
  const canvas = document.getElementById('canvas-streaming-agents');
  if (!canvas) return;

  const container = canvas.parentElement;
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 50);
  camera.position.set(0, 2.5, 3.8);
  camera.lookAt(0, 0, 0);

  const renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true, alpha: true });
  renderer.setSize(container.clientWidth, container.clientHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

  const pointsCount = 10;
  const spacing = 0.28;
  const group = new THREE.Group();
  scene.add(group);

  const spheres = [];
  const sphereGeo = new THREE.SphereGeometry(0.045, 8, 8);

  for (let x = 0; x < pointsCount; x++) {
    for (let z = 0; z < pointsCount; z++) {
      let colorVal;
      const progress = (x + z) / (pointsCount * 2);
      if (progress < 0.3) colorVal = COLORS.aiTeal;
      else if (progress < 0.7) colorVal = COLORS.userViolet;
      else colorVal = COLORS.brandPink;

      const mat = new THREE.MeshBasicMaterial({ color: colorVal });
      const mesh = new THREE.Mesh(sphereGeo, mat);
      mesh.position.x = (x - pointsCount / 2) * spacing;
      mesh.position.z = (z - pointsCount / 2) * spacing;
      group.add(mesh);
      
      spheres.push({ mesh: mesh, offsetX: x, offsetZ: z });
    }
  }

  let time = 0;
  function animate() {
    requestAnimationFrame(animate);
    time += 0.025;

    spheres.forEach(s => {
      s.mesh.position.y = Math.sin(s.offsetX * 0.4 + time) * Math.cos(s.offsetZ * 0.4 + time) * 0.3;
      const hScale = (s.mesh.position.y + 0.3) * 1.5 + 0.5;
      s.mesh.scale.set(hScale, hScale, hScale);
    });

    group.rotation.y = time * 0.1;
    renderer.render(scene, camera);
  }

  window.addEventListener('resize', () => {
    camera.aspect = container.clientWidth / container.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(container.clientWidth, container.clientHeight);
  });

  animate();
}

// ==========================================
// 4. LANDING PREVIEW INLINE CONSOLE
// ==========================================
let previewWs = null;
let previewRoomId = null;

async function initLiveConsole() {
  const dot = document.getElementById('connection-status-dot');
  const text = document.getElementById('connection-status-text');
  const body = document.getElementById('console-body');
  const form = document.getElementById('console-chat-form');
  const input = document.getElementById('console-input');
  const send = document.getElementById('console-send-btn');
  const tag = document.getElementById('console-tag-btn');
  
  if (!body || !form) return;

  function updateStatus(state) {
    dot.className = "status-dot " + state;
    if (state === "online") {
      text.textContent = "Live Connected";
      input.disabled = false;
      send.disabled = false;
      tag.disabled = false;
    } else {
      text.textContent = state === "connecting" ? "Connecting..." : "Offline";
      input.disabled = true;
      send.disabled = true;
      tag.disabled = true;
    }
  }

  tag.addEventListener('click', () => {
    input.value = "@ForgeBot " + input.value.replace("@ForgeBot", "").trim();
    input.focus();
  });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const txt = input.value.trim();
    if (!txt || !previewWs || previewWs.readyState !== WebSocket.OPEN) return;
    
    // Push message via WebSocket
    previewWs.send(JSON.stringify({ content: txt }));
    input.value = "";

    // Trigger REST Agent response if tagging @ForgeBot
    if (txt.toLowerCase().includes("@forgebot")) {
      try {
        await fetch(`${API_URL}/api/agent/respond`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            room_id: previewRoomId,
            user_message: txt,
            conversation_history: []
          })
        });
      } catch (err) {
        console.error("REST Agent trigger error", err);
      }
    }
  });

  async function connectPreview() {
    updateStatus("connecting");
    try {
      let token = localStorage.getItem('forgeroom_token');
      if (!token) {
        const rand = Math.floor(Math.random() * 90000) + 10000;
        const reg = await fetch(`${API_URL}/api/auth/register`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: `Guest_${rand}`,
            email: `guest_${rand}@forgeroom.com`,
            password: `password_${rand}`
          })
        });
        if (!reg.ok) throw new Error("Guest reg failed");
        
        const login = await fetch(`${API_URL}/api/auth/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            email: `guest_${rand}@forgeroom.com`,
            password: `password_${rand}`
          })
        });
        if (!login.ok) throw new Error("Guest login failed");
        const tokData = await login.json();
        token = tokData.access_token;
        localStorage.setItem('forgeroom_token', token);
      }

      const me = await fetch(`${API_URL}/api/auth/me`, { headers: { 'Authorization': `Bearer ${token}` } });
      if (!me.ok) {
        localStorage.removeItem('forgeroom_token');
        throw new Error("Expired guest token");
      }
      const profile = await me.json();
      updateNavbarProfile(profile.name);

      const list = await fetch(`${API_URL}/api/rooms/list`, { headers: { 'Authorization': `Bearer ${token}` } });
      let rooms = await list.json();
      let sandbox = rooms[0];

      if (!sandbox) {
        const create = await fetch(`${API_URL}/api/rooms`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: "Sandbox Preview", created_by_id: profile.id || profile._id })
        });
        sandbox = await create.json();
        
        // Auto join
        await fetch(`${API_URL}/api/rooms/${sandbox.room_id || sandbox._id || sandbox.id}/join`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user_id: profile.id || profile._id, username: profile.name })
        });
      }
      previewRoomId = sandbox.room_id || sandbox.id || sandbox._id;

      previewWs = new WebSocket(`${WS_URL}/ws/rooms/${previewRoomId}?token=${token}`);
      previewWs.onopen = async () => {
        updateStatus("online");
        body.innerHTML = '<div class="console-system-msg" style="color: var(--accent-teal);">✓ Interactive Sandbox linked. Try chatting and tag @ForgeBot!</div>';
      };

      previewWs.onmessage = (e) => {
        const payload = JSON.parse(e.data);
        if (payload.type === "presence") {
          const listSpan = document.getElementById('presence-list');
          if (listSpan) listSpan.textContent = payload.active_users.join(", ");
        } else if (payload.type === "message") {
          appendLog({ username: payload.username, content: payload.content, message_type: payload.message_type });
        } else if (payload.type === "stream_start") {
          clearIndicators();
          const wrap = document.createElement('div');
          wrap.className = "console-log active-stream";
          wrap.innerHTML = `<div class="log-user"><span class="user-badge ai">@${payload.sender_name}</span></div><div class="log-content typing"></div>`;
          body.appendChild(wrap);
          body.scrollTop = body.scrollHeight;
        } else if (payload.type === "stream_token") {
          const content = body.querySelector('.active-stream .log-content');
          if (content) {
            content.textContent += payload.content;
            body.scrollTop = body.scrollHeight;
          }
        } else if (payload.type === "stream_end") {
          const content = body.querySelector('.active-stream .log-content');
          if (content) content.classList.remove('typing');
          body.querySelectorAll('.active-stream').forEach(el => el.classList.remove('active-stream'));
          clearIndicators();
        }
      };

      previewWs.onclose = () => {
        updateStatus("offline");
        setTimeout(connectPreview, 6000);
      };

    } catch (e) {
      updateStatus("offline");
      setTimeout(connectPreview, 6000);
    }
  }

  function appendLog(msg) {
    clearIndicators();
    body.querySelectorAll('.active-stream').forEach(el => el.remove());
    
    const div = document.createElement('div');
    div.className = "console-log";
    const isAi = msg.message_type === "agent";
    const badge = isAi ? "user-badge ai" : "user-badge alex";
    const prefix = isAi ? "" : "@";

    div.innerHTML = `<div class="log-user"><span class="${badge}">${prefix}${msg.username}</span></div><div class="log-content">${msg.content}</div>`;
    body.appendChild(div);
    body.scrollTop = body.scrollHeight;
  }

  function clearIndicators() {
    body.querySelectorAll('.active-indicator').forEach(i => i.remove());
  }

  connectPreview();
}

// ==========================================
// 5. INTERACTIVE COLLABORATIVE DASHBOARD MVP
// ==========================================
let dbWs = null;
let activeRoomId = null;
let activeUserRole = "owner";
let activeStreamContent = null;
let activeParticipants = [];

function initDashboard(token, profile) {
  const roomsList = document.getElementById('dashboard-rooms-list');
  const createForm = document.getElementById('dashboard-create-room-form');
  const inviteForm = document.getElementById('db-invite-member-form');
  const chatForm = document.getElementById('db-chat-form');
  const chatInput = document.getElementById('db-chat-input');
  const tagBtn = document.getElementById('db-tag-btn');
  const chatBody = document.getElementById('db-chat-body');
  const canvasBody = document.getElementById('db-canvas-body');
  const roomTitle = document.getElementById('db-active-room-title');
  const roomPresence = document.getElementById('db-active-room-presence');
  const logoutBtn = document.getElementById('dashboard-logout-btn');
  const versionsList = document.getElementById('dashboard-versions-list');
  
  function renderPresence(users) {
    if (!roomPresence) return;
    roomPresence.innerHTML = "";
    if (!users || users.length === 0) {
      roomPresence.innerHTML = `<span style="font-size: 0.75rem; color: var(--text-secondary);">Collaborators: None</span>`;
      return;
    }
    
    // Header label
    const label = document.createElement('span');
    label.style.fontSize = "0.75rem";
    label.style.color = "var(--text-secondary)";
    label.style.marginRight = "8px";
    label.textContent = "Collaborators: ";
    roomPresence.appendChild(label);

    const avatarContainer = document.createElement('div');
    avatarContainer.style.display = "inline-flex";
    avatarContainer.style.alignItems = "center";
    avatarContainer.style.verticalAlign = "middle";

    users.forEach((username, idx) => {
      const initial = username.charAt(0).toUpperCase();
      // Generate a distinct color using a simple hash
      let hash = 0;
      for (let i = 0; i < username.length; i++) {
        hash = username.charCodeAt(i) + ((hash << 5) - hash);
      }
      const hue = Math.abs(hash % 360);
      const color = `hsl(${hue}, 80%, 60%)`;

      const avatar = document.createElement('span');
      avatar.className = "presence-avatar-circle";
      avatar.style.display = "inline-flex";
      avatar.style.alignItems = "center";
      avatar.style.justifyContent = "center";
      avatar.style.width = "24px";
      avatar.style.height = "24px";
      avatar.style.borderRadius = "50%";
      avatar.style.background = `rgba(${hue % 2 === 0 ? '0, 229, 255' : '139, 92, 246'}, 0.15)`;
      avatar.style.border = `1.5px solid ${color}`;
      avatar.style.color = "#ffffff";
      avatar.style.fontSize = "0.75rem";
      avatar.style.fontWeight = "700";
      avatar.style.marginRight = "-6px";
      avatar.style.position = "relative";
      avatar.style.zIndex = 10 - idx;
      avatar.style.textShadow = "0 1px 2px rgba(0,0,0,0.5)";
      avatar.title = username;
      avatar.textContent = initial;

      avatarContainer.appendChild(avatar);
    });

    roomPresence.appendChild(avatarContainer);

    const textSpan = document.createElement('span');
    textSpan.style.marginLeft = "12px";
    textSpan.style.fontSize = "0.75rem";
    textSpan.style.color = "var(--text-secondary)";
    textSpan.style.verticalAlign = "middle";
    textSpan.textContent = `(${users.length} active)`;
    roomPresence.appendChild(textSpan);
  }
  
  // Modals & triggers
  const contractModal = document.getElementById('contract-modal');
  const uploadClauseBtn = document.getElementById('db-upload-clause-btn');
  const contractClose = document.getElementById('contract-modal-close');
  const contractForm = document.getElementById('contract-form');
  
  const snapshotModal = document.getElementById('snapshot-modal');
  const saveSnapshotBtn = document.getElementById('db-save-snapshot-btn');
  const snapshotClose = document.getElementById('snapshot-modal-close');
  const snapshotForm = document.getElementById('snapshot-form');
  
  const exportSelect = document.getElementById('db-export-select');
  const summarizeBtn = document.getElementById('db-summarize-btn');
  
  // Advanced Features Controls Elements
  const templateSelect = document.getElementById('sidebar-template-select');
  const suggestionsBox = document.getElementById('db-mention-suggestions');
  const streamControls = document.getElementById('db-stream-controls');
  const tokenCountSpan = document.getElementById('stream-token-count');
  const pauseBtn = document.getElementById('stream-pause-btn');
  const takeoverBtn = document.getElementById('stream-takeover-btn');
  const redirectForm = document.getElementById('stream-redirect-form');
  const redirectInput = document.getElementById('stream-redirect-input');

  // Load Profile elements
  document.getElementById('db-profile-name').textContent = profile.name;
  document.getElementById('db-profile-email').textContent = profile.email;

  let isGenerationPaused = false;

  // Logout Click
  if (logoutBtn) {
    logoutBtn.addEventListener('click', () => {
      localStorage.removeItem('forgeroom_token');
      window.location.hash = "";
      location.reload();
    });
  }

  // Tag helper key shortcut
  if (tagBtn && chatInput) {
    tagBtn.addEventListener('click', () => {
      chatInput.value = "@ForgeBot " + chatInput.value.replace("@ForgeBot", "").trim();
      chatInput.focus();
    });
  }

  // --- Modals logic toggles ---
  if (uploadClauseBtn && contractModal) {
    uploadClauseBtn.addEventListener('click', () => toggleModal(contractModal, true));
    contractClose.addEventListener('click', () => toggleModal(contractModal, false));
  }

  if (saveSnapshotBtn && snapshotModal) {
    saveSnapshotBtn.addEventListener('click', () => toggleModal(snapshotModal, true));
    snapshotClose.addEventListener('click', () => toggleModal(snapshotModal, false));
  }

  // Share link banner listeners
  const shareBanner = document.getElementById('share-banner');
  const shareClose = document.getElementById('share-banner-close');
  const shareCopyBtn = document.getElementById('share-copy-btn');
  const shareInput = document.getElementById('share-link-input');

  if (shareBanner && shareClose) {
    shareClose.addEventListener('click', () => {
      shareBanner.style.transform = 'translateX(-50%) translateY(-150%)';
    });
  }

  if (shareCopyBtn && shareInput) {
    shareCopyBtn.addEventListener('click', () => {
      shareInput.select();
      navigator.clipboard.writeText(shareInput.value).then(() => {
        const originalText = shareCopyBtn.innerHTML;
        shareCopyBtn.innerHTML = "<span>✓</span> Copied!";
        setTimeout(() => {
          shareCopyBtn.innerHTML = originalText;
        }, 2000);
      }).catch(err => {
        console.error("Copy failed:", err);
      });
    });
  }

  // Active room header invite link copy button
  const headerCopyLinkBtn = document.getElementById('db-header-copy-link-btn');
  if (headerCopyLinkBtn) {
    headerCopyLinkBtn.addEventListener('click', () => {
      if (!activeRoomId) return;
      const shareUrl = `${window.location.origin}/#room=${activeRoomId}`;
      navigator.clipboard.writeText(shareUrl).then(() => {
        const originalText = headerCopyLinkBtn.innerHTML;
        headerCopyLinkBtn.innerHTML = "<span>✓</span> Copied Link!";
        setTimeout(() => {
          headerCopyLinkBtn.innerHTML = originalText;
        }, 2000);
      }).catch(err => {
        console.error("Copy failed:", err);
      });
    });
  }

  function toggleModal(modal, open) {
    if (open) {
      modal.style.display = "flex";
      setTimeout(() => modal.classList.add('open'), 10);
    } else {
      modal.classList.remove('open');
      setTimeout(() => {
        modal.style.display = "none";
        const form = modal.querySelector('form');
        if (form) form.reset();
      }, 300);
    }
  }

  // --- Advanced Features bindings ---
  
  // A. Load templates dropdown
  async function fetchTemplates() {
    if (!templateSelect) return;
    try {
      const res = await fetch(`${API_URL}/api/templates`);
      const data = await res.json();
      templateSelect.innerHTML = '<option value="" disabled selected>✨ Select template...</option>';
      data.templates.forEach(t => {
        const opt = document.createElement('option');
        opt.value = t.slug;
        opt.textContent = `${t.icon} ${t.name}`;
        templateSelect.appendChild(opt);
      });
    } catch (e) {
      console.error("Templates fetch failed:", e);
    }
  }
  
  if (templateSelect) {
    templateSelect.addEventListener('change', async () => {
      const slug = templateSelect.value;
      if (!slug) return;
      const customName = prompt("Enter a custom room title (optional):");
      
      try {
        const res = await fetch(`${API_URL}/api/templates/${slug}/create-room`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
          body: JSON.stringify({
            created_by_id: profile.id || profile._id,
            custom_name: customName || undefined
          })
        });
        if (res.ok) {
          const roomData = await res.json();
          
          // Auto Join
          await fetch(`${API_URL}/api/rooms/${roomData.room_id}/join`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify({ user_id: profile.id || profile._id, username: profile.name })
          });
          
          window.location.hash = `#room=${roomData.room_id}`;
          location.reload();
        }
      } catch (err) {
        console.error("Creating template room failed:", err);
      }
    });
  }

  // B. Summarize session click
  if (summarizeBtn) {
    summarizeBtn.addEventListener('click', async () => {
      if (!activeRoomId) return;
      summarizeBtn.disabled = true;
      summarizeBtn.textContent = "Analyzing...";
      
      try {
        const res = await fetch(`${API_URL}/api/rooms/${activeRoomId}/summarize`, {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          
          // Render summary directly in chat history as system printout card
          appendSystemCard("Workspace Summary & Action Items", data.markdown);
        }
      } catch (e) {
        console.error("Summarization failed:", e);
      } finally {
        summarizeBtn.disabled = false;
        summarizeBtn.textContent = "✨ Summarize";
      }
    });
  }

  // C. Autocomplete @Mentions triggers on input
  if (chatInput && suggestionsBox) {
    chatInput.addEventListener('input', async (e) => {
      const text = chatInput.value;
      const cursor = chatInput.selectionStart;
      const textBeforeCursor = text.slice(0, cursor);
      const lastAt = textBeforeCursor.lastIndexOf('@');
      
      if (lastAt !== -1 && (lastAt === 0 || textBeforeCursor[lastAt - 1] === ' ')) {
        const afterAt = textBeforeCursor.slice(lastAt + 1);
        
        // Filter usernames
        const matched = activeParticipants.filter(name => 
          name.toLowerCase().startsWith(afterAt.toLowerCase())
        );
        
        // Always suggest ForgeBot
        let list = [...matched.map(name => ({ name, type: 'user' }))];
        if ("forgebot".startsWith(afterAt.toLowerCase())) {
          list.push({ name: "ForgeBot", type: 'agent' });
        }
        
        if (list.length > 0) {
          suggestionsBox.innerHTML = "";
          list.forEach(item => {
            const li = document.createElement('li');
            li.style.padding = "8px 16px";
            li.style.cursor = "pointer";
            li.style.fontSize = "0.8rem";
            li.style.color = item.type === 'agent' ? "var(--accent-teal)" : "var(--text-primary)";
            li.innerHTML = `<strong>@${item.name}</strong> ${item.type === 'agent' ? '(AI Agent)' : ''}`;
            
            li.addEventListener('click', () => {
              const replacement = `@${item.name} `;
              chatInput.value = text.slice(0, lastAt) + replacement + text.slice(cursor);
              suggestionsBox.style.display = "none";
              chatInput.focus();
            });
            suggestionsBox.appendChild(li);
          });
          suggestionsBox.style.display = "block";
        } else {
          suggestionsBox.style.display = "none";
        }
      } else {
        suggestionsBox.style.display = "none";
      }
    });

    // Close popover if user clicks outside
    document.addEventListener('click', (e) => {
      if (e.target !== chatInput) suggestionsBox.style.display = "none";
    });
  }

  // D. Streaming controls endpoints
  if (pauseBtn) {
    pauseBtn.addEventListener('click', async () => {
      if (!activeRoomId) return;
      
      if (!isGenerationPaused) {
        // Pause
        await fetch(`${API_URL}/api/agent/${activeRoomId}/pause`, { method: 'POST', headers: { 'Authorization': `Bearer ${token}` } });
      } else {
        // Resume
        await fetch(`${API_URL}/api/agent/${activeRoomId}/resume`, { method: 'POST', headers: { 'Authorization': `Bearer ${token}` } });
      }
    });
  }

  if (takeoverBtn) {
    takeoverBtn.addEventListener('click', async () => {
      if (!activeRoomId) return;
      await fetch(`${API_URL}/api/agent/${activeRoomId}/takeover`, { method: 'POST', headers: { 'Authorization': `Bearer ${token}` } });
      if (streamControls) streamControls.style.display = "none";
    });
  }

  if (redirectForm) {
    redirectForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const instruct = redirectInput.value.trim();
      if (!instruct || !activeRoomId) return;
      
      await fetch(`${API_URL}/api/agent/${activeRoomId}/redirect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ message: instruct })
      });
      redirectInput.value = "";
    });
  }

  // --- API form actions submissions ---
  // A. Contract paste
  if (contractForm) {
    contractForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const txt = document.getElementById('contract-clause-input').value.trim();
      if (!txt || !activeRoomId) return;

      try {
        const res = await fetch(`${API_URL}/api/rooms/${activeRoomId}/upload-contract`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
          body: JSON.stringify({ contract_text: txt })
        });
        if (res.ok) {
          toggleModal(contractModal, false);
          appendSystemMsg("System: Contract clause uploaded successfully! Ready for analysis.");
        }
      } catch (err) {
        console.error("Contract upload failed:", err);
      }
    });
  }

  // B. Snapshot create
  if (snapshotForm) {
    snapshotForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const label = document.getElementById('snapshot-label-input').value.trim();
      if (!label || !activeRoomId) return;

      try {
        const res = await fetch(`${API_URL}/api/rooms/${activeRoomId}/versions`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
          body: JSON.stringify({ user_id: profile.id || profile._id, label: label })
        });
        if (res.ok) {
          toggleModal(snapshotModal, false);
          appendSystemMsg(`System: Snapshot version '${label}' saved.`);
          fetchSnapshots(); // Reload snapshots sidebar list
        }
      } catch (err) {
        console.error("Snapshot creation failed:", err);
      }
    });
  }

  // C. Invite member
  if (inviteForm) {
    inviteForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const emailInput = document.getElementById('invite-email');
      const email = emailInput.value.trim();
      if (!email || !activeRoomId) return;

      try {
        const res = await fetch(`${API_URL}/api/rooms/${activeRoomId}/add-member`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
          body: JSON.stringify({ user_email: email })
        });
        if (res.ok) {
          alert(`Successfully invited ${email} to this review session!`);
          emailInput.value = "";
        } else {
          const err = await res.json();
          alert(err.detail || "Invitation failed.");
        }
      } catch (err) {
        console.error("Member invite error:", err);
      }
    });
  }

  // D. Create Room
  if (createForm) {
    createForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const input = document.getElementById('new-room-title');
      const name = input.value.trim();
      if (!name) return;

      try {
        const orgSelect = document.getElementById('sidebar-org-select');
        const orgId = orgSelect ? orgSelect.value : "";
        const res = await fetch(`${API_URL}/api/rooms`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
          body: JSON.stringify({ 
            name: name, 
            created_by_id: profile.id || profile._id,
            org_id: orgId || null
          })
        });
        if (res.ok) {
          input.value = "";
          const newRoom = await res.json();
          const rId = newRoom.room_id || newRoom.id;
          
          // Auto join
          await fetch(`${API_URL}/api/rooms/${rId}/join`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify({ user_id: profile.id || profile._id, username: profile.name })
          });
          
          // Set hash in URL
          window.location.hash = `#room=${rId}`;
          
          // Trigger the share link banner popup at the top
          const shareBanner = document.getElementById('share-banner');
          const shareInput = document.getElementById('share-link-input');
          if (shareBanner && shareInput) {
            const shareUrl = `${window.location.origin}/#room=${rId}`;
            shareInput.value = shareUrl;
            
            // Slide down banner from the top
            shareBanner.style.transform = 'translateX(-50%) translateY(0)';
          }
          
          // Select and reload
          await fetchRooms(rId);
        }
      } catch (err) {
        console.error("Room create error:", err);
      }
    });
  }

  // E. Chat Form
  if (chatForm) {
    chatForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const txt = chatInput.value.trim();
      if (!txt || !dbWs || dbWs.readyState !== WebSocket.OPEN) return;

      // Send to WebSocket
      dbWs.send(JSON.stringify({ content: txt }));
      chatInput.value = "";

      // Trigger AI agent workflow REST call if tagging @ForgeBot
      if (txt.toLowerCase().includes("@forgebot")) {
        try {
          await fetch(`${API_URL}/api/agent/respond`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify({
              room_id: activeRoomId,
              user_message: txt,
              conversation_history: []
            })
          });
        } catch (err) {
          console.error("REST respond trigger error:", err);
        }
      }
    });
  }

  // F. Exports select change
  if (exportSelect) {
    exportSelect.addEventListener('change', async () => {
      const val = exportSelect.value;
      if (!val || !activeRoomId) return;

      if (val === "markdown") {
        window.open(`${API_URL}/api/rooms/${activeRoomId}/export/markdown`);
      } else if (val === "pdf") {
        window.open(`${API_URL}/api/rooms/${activeRoomId}/export/pdf`);
      } else if (val === "copy") {
        try {
          const res = await fetch(`${API_URL}/api/rooms/${activeRoomId}/export/copy`);
          const data = await res.json();
          await navigator.clipboard.writeText(data.markdown);
          alert("Markdown transcript copied to clipboard!");
        } catch (e) {
          alert("Failed to copy transcript.");
        }
      }
      exportSelect.value = ""; // Reset dropdown selection
    });
  }

  // Rooms list fetcher
  async function fetchRooms(selectRoomId = null) {
    try {
      const orgSelect = document.getElementById('sidebar-org-select');
      const orgId = orgSelect ? orgSelect.value : "";
      let url = `${API_URL}/api/rooms/list`;
      if (orgId) {
        url += `?org_id=${orgId}`;
      }
      const res = await fetch(url, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const rooms = await res.json();
      roomsList.innerHTML = "";
      
      rooms.forEach(room => {
        const rId = room.room_id || room.id || room._id;
        const li = document.createElement('li');
        li.className = `room-list-item`;
        li.textContent = `# ${room.name || room.title}`;
        li.dataset.roomId = rId;
        
        li.addEventListener('click', () => {
          window.location.hash = `#room=${rId}`;
          location.reload(); // Hard reload for clean WebSocket resets
        });
        roomsList.appendChild(li);
      });

      // Retrieve room ID from URL hash or fallback to first room in list
      let hashRoomId = window.location.hash.startsWith("#room=") ? window.location.hash.substring(6) : null;
      if (rooms.length > 0) {
        const targetId = hashRoomId || selectRoomId || rooms[0].room_id || rooms[0].id || rooms[0]._id;
        const targetRoom = rooms.find(r => (r.room_id || r.id || r._id) === targetId) || rooms[0];
        
        // Highlight active item
        document.querySelectorAll('.room-list-item').forEach(el => {
          if (el.dataset.roomId === targetId) el.classList.add('active');
        });
        
        loadRoom(targetId, targetRoom.name || targetRoom.title);
      }
    } catch (err) {
      console.error("Rooms loading error:", err);
    }
  }

  // Load snapshots sidebar list
  async function fetchSnapshots() {
    if (!activeRoomId) return;
    try {
      const res = await fetch(`${API_URL}/api/rooms/${activeRoomId}/versions`);
      const data = await res.json();
      versionsList.innerHTML = "";
      
      if (!data.versions || data.versions.length === 0) {
        versionsList.innerHTML = '<li style="font-size: 0.8rem; color: var(--text-secondary); font-style: italic;">No snapshots saved yet.</li>';
        return;
      }
      
      data.versions.forEach(v => {
        const li = document.createElement('li');
        li.className = "snapshot-item";
        
        const time = new Date(v.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        li.innerHTML = `
          <div class="snapshot-item-label">v${v.version_number} - ${v.label}</div>
          <div class="snapshot-item-time">Saved at ${time}</div>
          <button class="snapshot-branch-btn" data-version-id="${v.id || v._id}">🌿 Branch from here</button>
        `;
        
        // Bind branch action
        li.querySelector('.snapshot-branch-btn').addEventListener('click', async (e) => {
          const vId = e.target.dataset.versionId;
          const bName = prompt("Enter name for alternate branched channel:", `Branch - ${v.label}`);
          if (!bName) return;
          
          try {
            const branchRes = await fetch(`${API_URL}/api/rooms/${activeRoomId}/versions/${vId}/branch`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
              body: JSON.stringify({ user_id: profile.id || profile._id, name: bName })
            });
            if (branchRes.ok) {
              const resData = await branchRes.json();
              
              // Join the newly branched room
              await fetch(`${API_URL}/api/rooms/${resData.new_room_id}/join`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify({ user_id: profile.id || profile._id, username: profile.name })
              });
              
              window.location.hash = `#room=${resData.new_room_id}`;
              location.reload();
            }
          } catch (err) {
            console.error("Branching error:", err);
          }
        });
        versionsList.appendChild(li);
      });
    } catch (e) {
      console.error("Snapshots list load failed:", e);
    }
  }

  // Load specific room details
  async function loadRoom(roomId, title) {
    if (activeRoomId === roomId && dbWs) return;
    activeRoomId = roomId;
    roomTitle.textContent = title;
    chatBody.innerHTML = '<div class="console-system-msg" style="color: var(--accent-teal);">Syncing chat connection...</div>';
    
    // Close prior WS
    if (dbWs) dbWs.close();

    // Call join API to assert presence
    await fetch(`${API_URL}/api/rooms/${roomId}/join`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: JSON.stringify({ user_id: profile.id || profile._id, username: profile.name })
    });

    try {
      // Get Room Details: participants, contract, and canvas cards list
      const res = await fetch(`${API_URL}/api/rooms/${roomId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const details = await res.json();
        activeUserRole = details.user_role || "owner";
        
        // Update presence avatars
        activeParticipants = details.participants.map(p => p.username);
        renderPresence(activeParticipants);
        
        // Load canvas cards
        renderCanvasCards(details.outputs);
        
        // Apply RBAC role locks
        applyRBACPermissions(activeUserRole);
        
        // Fetch and populate Room Workflow Selector
        await populateRoomWorkflowSelector(details.room);
      }
    } catch (err) {
      console.error("Room loading error:", err);
    }

    // Connect WebSocket
    dbWs = new WebSocket(`${WS_URL}/ws/rooms/${roomId}?token=${token}`);
    
    dbWs.onopen = async () => {
      chatBody.innerHTML = "";
      appendSystemMsg("✓ Joined review workspace. Invite teammates to collaborate!");
      
      // Re-fetch rooms lists and versions history
      fetchSnapshots();
    };

    dbWs.onmessage = (e) => {
      const data = JSON.parse(e.data);
      if (data.type === "presence") {
        activeParticipants = data.active_users;
        renderPresence(data.active_users);
      } 
      else if (data.type === "message") {
        appendChatMsg(data);
        
        // Dynamic re-fetch canvas cards to see new AI outputs instantly
        if (data.message_type === "agent") {
          reloadCanvasOutputs();
        }
      }
      else if (data.type === "research_status") {
        appendSystemMsg(data.content);
      }
      else if (data.type === "stream_start") {
        if (streamControls) {
          streamControls.style.display = "flex";
          tokenCountSpan.textContent = "0";
          pauseBtn.textContent = "⏸ Pause";
          isGenerationPaused = false;
        }
        
        const wrap = document.createElement('div');
        wrap.className = "console-log db-stream";
        wrap.innerHTML = `
          <div class="log-user" style="display: flex; align-items: center;">
            <span class="user-badge ai">@${data.sender_name}</span>
            <div class="typing-indicator" style="display: inline-flex; align-items: center; gap: 4px; padding: 4px 8px; background: rgba(0, 229, 255, 0.05); border-radius: 4px; margin-left: 8px;">
              <span style="font-size: 0.7rem; color: var(--accent-teal); font-family: var(--font-mono);">thinking</span>
              <span style="width: 4px; height: 4px; background: var(--accent-teal); border-radius: 50%; animation: pulse-dot 1s infinite 0s;"></span>
              <span style="width: 4px; height: 4px; background: var(--accent-teal); border-radius: 50%; animation: pulse-dot 1s infinite 0.2s;"></span>
              <span style="width: 4px; height: 4px; background: var(--accent-teal); border-radius: 50%; animation: pulse-dot 1s infinite 0.4s;"></span>
            </div>
          </div>
          <div class="log-content typing"></div>
        `;
        chatBody.appendChild(wrap);
        activeStreamContent = wrap.querySelector('.log-content');
        chatBody.scrollTop = chatBody.scrollHeight;
      }
      else if (data.type === "stream_token") {
        if (activeStreamContent) {
          const wrap = activeStreamContent.parentElement;
          const indicator = wrap.querySelector('.typing-indicator');
          if (indicator) indicator.remove();
          
          activeStreamContent.textContent += data.content;
          chatBody.scrollTop = chatBody.scrollHeight;
        }
        if (tokenCountSpan) {
          tokenCountSpan.textContent = data.token_count || "0";
        }
      }
      else if (data.type === "stream_end") {
        if (activeStreamContent) {
          activeStreamContent.classList.remove('typing');
          activeStreamContent = null;
        }
        chatBody.querySelectorAll('.db-stream').forEach(el => el.classList.remove('db-stream'));
        if (streamControls) streamControls.style.display = "none";
        
        // Reload cards immediately
        reloadCanvasOutputs();
      }
      else if (data.type === "paused") {
        isGenerationPaused = true;
        if (pauseBtn) pauseBtn.textContent = "▶ Resume";
        appendSystemMsg("System: Agent review stream paused.");
      }
      else if (data.type === "resumed") {
        isGenerationPaused = false;
        if (pauseBtn) pauseBtn.textContent = "⏸ Pause";
        appendSystemMsg("System: Agent review stream resumed.");
      }
      else if (data.type === "redirected") {
        if (activeStreamContent) {
          activeStreamContent.textContent = ""; // Clear on redirect redirection
        }
        appendSystemMsg(`System: Agent redirected direction: "${data.new_message}"`);
      }
      else if (data.type === "feedback_update") {
        // Real-time update of specific canvas card reaction scores
        const cardElem = document.querySelector(`[data-output-id="${data.output_id}"]`);
        if (cardElem) {
          updateCardFeedbackUI(cardElem, data);
        }
      }
      else if (data.type === "card_update_broadcast") {
        const cardElem = document.querySelector(`[data-output-id="${data.output.id}"]`);
        if (cardElem) {
          const textarea = cardElem.querySelector('.canvas-card-textarea');
          if (!textarea) {
            const contentDiv = cardElem.querySelector('.canvas-card-content');
            if (contentDiv) contentDiv.textContent = data.output.content;
          }
          const isFinalized = data.output.status === "finalized";
          const finalizeBtn = cardElem.querySelector('.finalize-card-btn');
          if (finalizeBtn) {
            finalizeBtn.textContent = isFinalized ? 'Reopen' : '✓ Finalize';
            if (isFinalized) {
              finalizeBtn.style.background = 'rgba(16, 185, 129, 0.1)';
              finalizeBtn.style.borderColor = 'rgba(16, 185, 129, 0.3)';
              finalizeBtn.style.color = '#10b981';
            } else {
              finalizeBtn.style.background = '';
              finalizeBtn.style.borderColor = '';
              finalizeBtn.style.color = '';
            }
          }
          if (isFinalized) {
            cardElem.classList.add('finalized');
          } else {
            cardElem.classList.remove('finalized');
          }
          
          // Update badge in title
          const titleContainer = cardElem.querySelector('.canvas-card-title div');
          if (titleContainer) {
            // Remove existing badge
            const existingBadge = titleContainer.querySelector('.finalized-badge, .draft-badge');
            if (existingBadge) existingBadge.remove();
            
            const badgeSpan = document.createElement('span');
            if (isFinalized) {
              badgeSpan.className = "finalized-badge";
              badgeSpan.style.cssText = "display: inline-flex; align-items: center; gap: 4px; background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.4); color: #10b981; border-radius: 4px; padding: 2px 6px; font-size: 0.65rem; font-weight: 700; font-family: var(--font-display); text-transform: uppercase; letter-spacing: 0.05em; box-shadow: 0 0 6px rgba(16, 185, 129, 0.2);";
              badgeSpan.innerHTML = '<span style="display: inline-block; width: 5px; height: 5px; background: #10b981; border-radius: 50%; box-shadow: 0 0 4px #10b981;"></span> ✓ Finalized Review';
            } else {
              badgeSpan.className = "draft-badge";
              badgeSpan.style.cssText = "display: inline-flex; align-items: center; gap: 4px; background: rgba(255, 167, 38, 0.1); border: 1px solid rgba(255, 167, 38, 0.25); color: #ffa726; border-radius: 4px; padding: 2px 6px; font-size: 0.65rem; font-weight: 700; font-family: var(--font-display); text-transform: uppercase; letter-spacing: 0.05em;";
              badgeSpan.innerHTML = '<span style="display: inline-block; width: 5px; height: 5px; background: #ffa726; border-radius: 50%;"></span> Draft Review';
            }
            titleContainer.appendChild(badgeSpan);
          }
        }
      }
    };

    dbWs.onclose = () => {
      appendSystemMsg("⚠ WebSocket disconnected. Reconnecting...");
    };
  }

  async function populateRoomWorkflowSelector(room) {
    const select = document.getElementById('db-workflow-select');
    if (!select) return;
    
    select.innerHTML = '<option value="">🤖 Agent: Default (Contract Analyzer)</option>';
    
    const orgId = orgSelect.value;
    const isViewer = activeUserRole === "viewer";
    select.disabled = isViewer;
    
    if (!orgId) {
      select.value = "";
      return;
    }
    
    try {
      // 1. Fetch agents
      const agentsRes = await fetch(`${API_URL}/api/orgs/${orgId}/agents`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const agents = await agentsRes.json();
      
      const agentsGroup = document.createElement('optgroup');
      agentsGroup.label = "Single AI Agents";
      
      agents.forEach(agent => {
        const opt = document.createElement('option');
        opt.value = `agent:${agent.slug}`;
        opt.textContent = `${agent.icon} ${agent.name}`;
        agentsGroup.appendChild(opt);
      });
      select.appendChild(agentsGroup);
      
      // 2. Fetch chains
      const chainsRes = await fetch(`${API_URL}/api/orgs/${orgId}/chains`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const chains = await chainsRes.json();
      
      const chainsGroup = document.createElement('optgroup');
      chainsGroup.label = "Multi-Agent Pipelines";
      
      chains.forEach(chain => {
        const opt = document.createElement('option');
        opt.value = `chain:${chain.id}`;
        opt.textContent = `⛓️ ${chain.name}`;
        chainsGroup.appendChild(opt);
      });
      select.appendChild(chainsGroup);
      
      if (room.active_chain_id) {
        select.value = `chain:${room.active_chain_id}`;
      } else if (room.active_agent_id) {
        select.value = `agent:${room.active_agent_id}`;
      } else {
        select.value = "";
      }
    } catch (e) {
      console.error("Workflow selector loading failed:", e);
    }
  }

  const workflowSelect = document.getElementById('db-workflow-select');
  if (workflowSelect) {
    workflowSelect.addEventListener('change', async () => {
      if (!activeRoomId) return;
      
      const val = workflowSelect.value;
      let activeAgentId = null;
      let activeChainId = null;
      
      if (val.startsWith("agent:")) {
        activeAgentId = val.split("agent:")[1];
      } else if (val.startsWith("chain:")) {
        activeChainId = val.split("chain:")[1];
      }
      
      try {
        const res = await fetch(`${API_URL}/api/rooms/${activeRoomId}/workflow`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
          body: JSON.stringify({ active_agent_id: activeAgentId, active_chain_id: activeChainId })
        });
        if (res.ok) {
          appendSystemMsg("✓ Changed room active AI workflow.");
        } else {
          alert("Failed to update room workflow");
        }
      } catch (err) {
        console.error("Save workflow error:", err);
      }
    });
  }

  async function reloadCanvasOutputs() {
    try {
      const res = await fetch(`${API_URL}/api/rooms/${activeRoomId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const details = await res.json();
        renderCanvasCards(details.outputs);
      }
    } catch (e) {
      console.error("Canvas reload failed:", e);
    }
  }

  function renderCanvasCards(cards) {
    canvasBody.innerHTML = "";
    if (!cards || cards.length === 0) {
      canvasBody.innerHTML = `<div style="text-align: center; color: var(--text-secondary); font-size: 0.85rem; padding: 32px 0;">Agent review cards will appear here. Paste a contract clause and tag @ForgeBot to analyze!</div>`;
      return;
    }
    
    cards.forEach(async (card) => {
      const cardId = card.id || card._id;
      const isFinalized = card.status === "finalized";
      
      const div = document.createElement('div');
      div.className = `canvas-card ${isFinalized ? 'finalized' : ''}`;
      div.dataset.outputId = cardId;
      
      div.innerHTML = `
        <div class="canvas-card-title" style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
          <div style="display: flex; align-items: center; gap: 8px;">
            <span style="font-weight: 700; font-family: var(--font-display);">${card.title}</span>
            ${isFinalized ? `
              <span class="finalized-badge" style="display: inline-flex; align-items: center; gap: 4px; background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.4); color: #10b981; border-radius: 4px; padding: 2px 6px; font-size: 0.65rem; font-weight: 700; font-family: var(--font-display); text-transform: uppercase; letter-spacing: 0.05em; box-shadow: 0 0 6px rgba(16, 185, 129, 0.2);">
                <span style="display: inline-block; width: 5px; height: 5px; background: #10b981; border-radius: 50%; box-shadow: 0 0 4px #10b981;"></span>
                ✓ Finalized Review
              </span>
            ` : `
              <span class="draft-badge" style="display: inline-flex; align-items: center; gap: 4px; background: rgba(255, 167, 38, 0.1); border: 1px solid rgba(255, 167, 38, 0.25); color: #ffa726; border-radius: 4px; padding: 2px 6px; font-size: 0.65rem; font-weight: 700; font-family: var(--font-display); text-transform: uppercase; letter-spacing: 0.05em;">
                <span style="display: inline-block; width: 5px; height: 5px; background: #ffa726; border-radius: 50%;"></span>
                Draft Review
              </span>
            `}
          </div>
          ${activeUserRole !== "viewer" ? `
            <div class="canvas-card-actions" style="display: flex; gap: 6px;">
              <button class="canvas-btn edit-card-btn" style="font-size: 0.75rem; border-radius: 4px; padding: 3px 8px; cursor: pointer; transition: all 0.2s;">Edit</button>
              <button class="canvas-btn finalize finalize-card-btn" style="font-size: 0.75rem; border-radius: 4px; padding: 3px 8px; cursor: pointer; transition: all 0.2s; ${isFinalized ? 'background: rgba(16, 185, 129, 0.1); border-color: rgba(16, 185, 129, 0.3); color: #10b981;' : ''}">
                ${isFinalized ? 'Reopen' : '✓ Finalize'}
              </button>
            </div>
          ` : ''}
        </div>
        <div class="canvas-card-content">${card.content}</div>
        
        <!-- Feedback Reaction widgets bar -->
        <div class="feedback-reaction-bar" style="display: flex; gap: 8px; margin-top: 12px; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 10px; align-items: center;">
          <button class="canvas-btn react-btn" data-type="thumbs_up">👍 <span class="count-val">0</span></button>
          <button class="canvas-btn react-btn" data-type="thumbs_down">👎 <span class="count-val">0</span></button>
          <button class="canvas-btn react-btn" data-type="emoji" data-emoji="😍">😍 <span class="count-val">0</span></button>
          <button class="canvas-btn react-btn" data-type="emoji" data-emoji="🤔">🤔 <span class="count-val">0</span></button>
          <button class="canvas-btn react-btn" data-type="emoji" data-emoji="❌">❌ <span class="count-val">0</span></button>
          <div class="quality-score-label" style="margin-left: auto; font-size: 0.7rem; color: var(--text-secondary);">Quality: 50%</div>
        </div>
      `;
      
      // Bind reactions clicks
      div.querySelectorAll('.react-btn').forEach(btn => {
        btn.addEventListener('click', async () => {
          const type = btn.dataset.type;
          const emoji = btn.dataset.emoji || null;
          
          try {
            await fetch(`${API_URL}/api/outputs/${cardId}/feedback`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
              body: JSON.stringify({
                room_id: activeRoomId,
                user_id: profile.id || profile._id,
                feedback_type: type,
                emoji: emoji
              })
            });
          } catch (err) {
            console.error("Recording reaction error:", err);
          }
        });
      });
      
      // Fetch initial feedback summary totals
      try {
        const fRes = await fetch(`${API_URL}/api/outputs/${cardId}/feedback`);
        if (fRes.ok) {
          const fData = await fRes.json();
          updateCardFeedbackUI(div, fData);
        }
      } catch (err) {
        console.error("Loading card feedback summary failed:", err);
      }
      
      // Bind finalise card action
      div.querySelector('.finalize-card-btn').addEventListener('click', async () => {
        const nextStatus = isFinalized ? "draft" : "finalized";
        try {
          const patchRes = await fetch(`${API_URL}/api/rooms/${activeRoomId}/outputs/${cardId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify({ status: nextStatus })
          });
          if (patchRes.ok) {
            reloadCanvasOutputs();
          }
        } catch (e) {
          console.error("Finalize patch error:", e);
        }
      });
      
      // Bind Edit card toggle
      div.querySelector('.edit-card-btn').addEventListener('click', async (e) => {
        const contentDiv = div.querySelector('.canvas-card-content');
        const isEditing = e.target.textContent === "Save";
        
        if (!isEditing) {
          // Switch to Edit Textarea
          const currentVal = contentDiv.textContent;
          const textarea = document.createElement('textarea');
          textarea.className = "canvas-card-textarea";
          textarea.value = currentVal;
          div.replaceChild(textarea, contentDiv);
          e.target.textContent = "Save";
        } else {
          // Save changes
          const textarea = div.querySelector('.canvas-card-textarea');
          const newVal = textarea.value.trim();
          
          try {
            const patchRes = await fetch(`${API_URL}/api/rooms/${activeRoomId}/outputs/${cardId}`, {
              method: 'PATCH',
              headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
              body: JSON.stringify({ content: newVal })
            });
            if (patchRes.ok) {
              reloadCanvasOutputs();
            }
          } catch (err) {
            console.error("Edit patch failed:", err);
          }
        }
      });

      canvasBody.appendChild(div);
    });
  }

  function updateCardFeedbackUI(cardElem, data) {
    const thumbsUp = cardElem.querySelector('[data-type="thumbs_up"] .count-val');
    if (thumbsUp) thumbsUp.textContent = data.thumbs_up_count || 0;
    
    const thumbsDown = cardElem.querySelector('[data-type="thumbs_down"] .count-val');
    if (thumbsDown) thumbsDown.textContent = data.thumbs_down_count || 0;
    
    const emojiMap = data.emoji_reactions || {};
    cardElem.querySelectorAll('[data-emoji]').forEach(btn => {
      const emoji = btn.dataset.emoji;
      const countSpan = btn.querySelector('.count-val');
      if (countSpan) countSpan.textContent = emojiMap[emoji] || 0;
    });
    
    const scoreLabel = cardElem.querySelector('.quality-score-label');
    if (scoreLabel) {
      scoreLabel.textContent = `Quality: ${Math.round((data.quality_score || 0.5) * 100)}%`;
    }
  }

  function appendChatMsg(msg) {
    clearDbIndicators();
    chatBody.querySelectorAll('.db-stream').forEach(el => el.remove());
    
    const div = document.createElement('div');
    div.className = "console-log";
    const isAi = msg.message_type === "agent";
    const badge = isAi ? "user-badge ai" : "user-badge alex";
    const prefix = isAi ? "" : "@";

    div.innerHTML = `<div class="log-user"><span class="${badge}">${prefix}${msg.username}</span></div><div class="log-content">${msg.content}</div>`;
    chatBody.appendChild(div);
    chatBody.scrollTop = chatBody.scrollHeight;
  }

  function appendSystemMsg(txt) {
    const div = document.createElement('div');
    div.className = "console-system-msg";
    div.textContent = txt;
    chatBody.appendChild(div);
    chatBody.scrollTop = chatBody.scrollHeight;
  }

  function appendSystemCard(title, markdown) {
    const div = document.createElement('div');
    div.className = "console-log";
    div.style.border = "1px solid var(--accent-teal)";
    div.style.background = "rgba(0, 229, 255, 0.02)";
    div.style.borderRadius = "8px";
    div.style.padding = "16px";
    
    // Very basic markdown translation for highlights
    const htmlText = markdown
      .replace(/# (.*)/g, '<h4 style="color:var(--accent-teal);margin-bottom:8px;">$1</h4>')
      .replace(/## (.*)/g, '<h5 style="color:var(--accent-teal);margin-top:12px;margin-bottom:6px;">$1</h5>')
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      .replace(/- \[\ \]/g, '☐')
      .replace(/- (.*)/g, '• $1')
      .replace(/\n/g, '<br/>');
      
    div.innerHTML = `
      <div style="font-family: var(--font-display); font-weight: 700; color: var(--accent-teal); margin-bottom: 8px;">📋 ${title}</div>
      <div style="font-size: 0.8rem; line-height: 1.5; font-family: var(--font-mono); color: var(--text-primary);">${htmlText}</div>
    `;
    chatBody.appendChild(div);
    chatBody.scrollTop = chatBody.scrollHeight;
  }

  function clearDbIndicators() {
    chatBody.querySelectorAll('.db-indicator').forEach(i => i.remove());
  }

  // ==========================================
  // ORG WORKSPACE & RBAC INTEGRATION
  // ==========================================
  const orgSelect = document.getElementById('sidebar-org-select');
  const createOrgBtn = document.getElementById('sidebar-create-org-btn');
  const orgPanelBtn = document.getElementById('sidebar-org-panel-btn');
  
  const orgModal = document.getElementById('org-panel-modal');
  const orgModalClose = document.getElementById('org-panel-close');
  const orgModalTitle = document.getElementById('org-panel-title');
  const orgInviteForm = document.getElementById('org-invite-form');
  const orgAgentForm = document.getElementById('org-agent-config-form');
  const orgBillingForm = document.getElementById('org-billing-form');
  const orgMembersBody = document.getElementById('org-members-table-body');
  const orgAuditList = document.getElementById('org-audit-logs-list');
  const orgTabButtons = document.querySelectorAll('.org-tab-btn');
  const orgTabContents = document.querySelectorAll('.org-tab-content');

  // RBAC UI restrict helper
  function applyRBACPermissions(role) {
    // 1. Chat input locking
    if (chatInput) {
      if (role === 'viewer') {
        chatInput.disabled = true;
        chatInput.placeholder = "[Read-only] Viewer role cannot send chats";
        if (tagBtn) tagBtn.style.display = "none";
      } else {
        chatInput.disabled = false;
        chatInput.placeholder = "Send message to teammates or tag @ForgeBot...";
        if (tagBtn) tagBtn.style.display = "inline-flex";
      }
    }
    // 2. Snapshot, clause upload, and actions locking
    const snapshotBtn = document.getElementById('db-save-snapshot-btn');
    const uploadBtn = document.getElementById('db-upload-clause-btn');
    const summarizeBtn = document.getElementById('db-summarize-btn');
    
    if (role === 'viewer') {
      if (snapshotBtn) snapshotBtn.style.display = "none";
      if (uploadBtn) uploadBtn.style.display = "none";
      if (summarizeBtn) summarizeBtn.style.display = "none";
    } else {
      if (snapshotBtn) snapshotBtn.style.display = "inline-flex";
      if (uploadBtn) uploadBtn.style.display = "inline-flex";
      if (summarizeBtn) summarizeBtn.style.display = "inline-flex";
    }
  }

  // Load Orgs List in selector
  async function fetchOrgs() {
    if (!orgSelect) return;
    try {
      const res = await fetch(`${API_URL}/api/orgs`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const orgs = await res.json();
      
      // Preserve first "Personal Workspace" option
      orgSelect.innerHTML = '<option value="">Personal Workspace</option>';
      orgs.forEach(o => {
        const opt = document.createElement('option');
        opt.value = o.id || o._id;
        opt.textContent = o.name;
        orgSelect.appendChild(opt);
      });
      
      // Try to restore selection from local storage
      const cachedOrg = localStorage.getItem('forgeroom_selected_org');
      if (cachedOrg) {
        orgSelect.value = cachedOrg;
        if (orgPanelBtn) orgPanelBtn.style.display = "block";
      }
    } catch (e) {
      console.error("Orgs fetch error:", e);
    }
  }

  // Bind Selector change
  if (orgSelect) {
    orgSelect.addEventListener('change', () => {
      const orgId = orgSelect.value;
      localStorage.setItem('forgeroom_selected_org', orgId);
      if (orgId) {
        if (orgPanelBtn) orgPanelBtn.style.display = "block";
      } else {
        if (orgPanelBtn) orgPanelBtn.style.display = "none";
      }
      // Re-load rooms list
      fetchRooms();
    });
  }

  // Bind Create Org button
  if (createOrgBtn) {
    createOrgBtn.addEventListener('click', async () => {
      const name = prompt("Enter new Organization name:");
      if (!name) return;
      
      try {
        const res = await fetch(`${API_URL}/api/orgs`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
          body: JSON.stringify({ name })
        });
        if (res.ok) {
          const org = await res.json();
          await fetchOrgs();
          orgSelect.value = org.id || org._id;
          localStorage.setItem('forgeroom_selected_org', org.id || org._id);
          if (orgPanelBtn) orgPanelBtn.style.display = "block";
          fetchRooms();
        }
      } catch (e) {
        console.error("Create org error:", e);
      }
    });
  }

  // Open Org settings panel
  if (orgPanelBtn && orgModal) {
    orgPanelBtn.addEventListener('click', () => {
      const orgId = orgSelect.value;
      const orgName = orgSelect.options[orgSelect.selectedIndex].text;
      if (!orgId) return;
      
      if (orgModalTitle) orgModalTitle.textContent = `${orgName} Management Settings`;
      
      toggleModal(orgModal, true);
      loadOrgTab("members");
    });
  }

  if (orgModalClose) {
    orgModalClose.addEventListener('click', () => toggleModal(orgModal, false));
  }

  // Tab switching logic
  orgTabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const tab = btn.dataset.tab;
      orgTabButtons.forEach(b => {
        b.classList.remove('active');
        b.style.borderBottomColor = "transparent";
        b.style.color = "var(--text-secondary)";
      });
      btn.classList.add('active');
      btn.style.borderBottomColor = "var(--accent-teal)";
      btn.style.color = "var(--text-primary)";
      
      loadOrgTab(tab);
    });
  });

  async function loadOrgTab(tab) {
    const orgId = orgSelect.value;
    if (!orgId) return;
    
    orgTabContents.forEach(c => c.style.display = "none");
    const activeContent = document.getElementById(`org-tab-${tab}`);
    if (activeContent) activeContent.style.display = "block";
    
    if (tab === "members") {
      await fetchOrgMembers(orgId);
    } else if (tab === "agent") {
      await fetchOrgAgents(orgId);
    } else if (tab === "chains") {
      await fetchOrgChains(orgId);
    } else if (tab === "audit") {
      await fetchOrgAuditLogs(orgId);
    } else if (tab === "billing") {
      await fetchOrgBilling(orgId);
    }
  }

  // --- Members Actions ---
  async function fetchOrgMembers(orgId) {
    try {
      const res = await fetch(`${API_URL}/api/orgs/${orgId}/members`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const members = await res.json();
      orgMembersBody.innerHTML = "";
      
      // Determine if current user is owner (to permit actions)
      const curMember = members.find(m => m.user_id === (profile.id || profile._id));
      const curUserIsOwner = curMember && curMember.role === "owner";
      
      // Hide invite form if not owner
      const inviteFormWrapper = document.getElementById('org-invite-form');
      const inviteHeader = document.getElementById('org-invite-header');
      if (!curUserIsOwner) {
        if (inviteFormWrapper) inviteFormWrapper.style.display = "none";
        if (inviteHeader) inviteHeader.style.display = "none";
      } else {
        if (inviteFormWrapper) inviteFormWrapper.style.display = "flex";
        if (inviteHeader) inviteHeader.style.display = "block";
      }

      members.forEach(m => {
        const tr = document.createElement('tr');
        tr.style.borderBottom = "1px solid rgba(255,255,255,0.05)";
        
        let roleOptionsHtml = "";
        if (curUserIsOwner && m.user_id !== (profile.id || profile._id)) {
          roleOptionsHtml = `
            <select class="member-role-select" data-user-id="${m.user_id}" style="background: rgba(12, 16, 29, 0.9); border: 1px solid var(--border-slate); color: var(--text-primary); border-radius: 4px; padding: 4px; font-size: 0.8rem; cursor: pointer;">
              <option value="owner" ${m.role === 'owner' ? 'selected' : ''}>Owner</option>
              <option value="editor" ${m.role === 'editor' ? 'selected' : ''}>Editor</option>
              <option value="viewer" ${m.role === 'viewer' ? 'selected' : ''}>Viewer</option>
            </select>
          `;
        } else {
          roleOptionsHtml = `<span style="text-transform: capitalize; color: var(--text-secondary);">${m.role}</span>`;
        }
        
        let actionsHtml = "";
        if (curUserIsOwner && m.user_id !== (profile.id || profile._id)) {
          actionsHtml = `<button class="canvas-btn remove-member-btn" data-user-id="${m.user_id}" style="background: rgba(239,83,80,0.1); border-color: rgba(239,83,80,0.3); color: #ef5350; font-size: 0.75rem; border-radius: 4px; padding: 2px 6px;">Remove</button>`;
        } else {
          actionsHtml = `<span style="font-size: 0.75rem; color: var(--text-secondary); font-style: italic;">No actions</span>`;
        }

        tr.innerHTML = `
          <td style="padding: 10px 16px; font-weight: 600;">${m.username} ${m.user_id === (profile.id || profile._id) ? '<span style="color:var(--accent-teal); font-size: 0.7rem;">(You)</span>' : ''}</td>
          <td style="padding: 10px 16px;">${roleOptionsHtml}</td>
          <td style="padding: 10px 16px;">${actionsHtml}</td>
        `;
        
        // Listeners for role updates
        const roleSel = tr.querySelector('.member-role-select');
        if (roleSel) {
          roleSel.addEventListener('change', async () => {
            const uId = roleSel.dataset.userId;
            const newRole = roleSel.value;
            try {
              await fetch(`${API_URL}/api/orgs/${orgId}/members/${uId}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify({ role: newRole })
              });
            } catch (err) {
              console.error("Role update failed:", err);
            }
          });
        }
        
        // Listener for remove member
        const removeBtn = tr.querySelector('.remove-member-btn');
        if (removeBtn) {
          removeBtn.addEventListener('click', async () => {
            const uId = removeBtn.dataset.userId;
            if (!confirm("Are you sure you want to remove this member?")) return;
            try {
              const res = await fetch(`${API_URL}/api/orgs/${orgId}/members/${uId}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` }
              });
              if (res.ok) fetchOrgMembers(orgId);
            } catch (err) {
              console.error("Member delete failed:", err);
            }
          });
        }
        
        orgMembersBody.appendChild(tr);
      });
    } catch (e) {
      console.error("Error loading members:", e);
    }
  }

  // Invite Form Submit
  if (orgInviteForm) {
    orgInviteForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const orgId = orgSelect.value;
      const emailInput = document.getElementById('org-invite-email');
      const roleSelect = document.getElementById('org-invite-role');
      const email = emailInput.value.trim();
      const role = roleSelect.value;
      if (!email || !orgId) return;
      
      try {
        const res = await fetch(`${API_URL}/api/orgs/${orgId}/members`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
          body: JSON.stringify({ email, role })
        });
        if (res.ok) {
          emailInput.value = "";
          fetchOrgMembers(orgId);
        } else {
          const err = await res.json();
          alert(err.detail || "Invite failed");
        }
      } catch (err) {
        console.error("Invite submit error:", err);
      }
    });
  }

  // --- Agent Library & Customization ---
  let selectedAgentSlug = null;
  let currentChainSequence = [];

  async function fetchOrgAgents(orgId) {
    try {
      const res = await fetch(`${API_URL}/api/orgs/${orgId}/agents`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const agents = await res.json();
      
      const container = document.getElementById('org-agents-list-container');
      if (container) container.innerHTML = "";
      
      // Populate agent selector select inside Chain Builder too
      const selector = document.getElementById('org-chain-agent-selector');
      if (selector) selector.innerHTML = "";
      
      agents.forEach(agent => {
        // Add option to chain selector
        if (selector) {
          const opt = document.createElement('option');
          opt.value = agent.slug;
          opt.textContent = `${agent.icon} ${agent.name}`;
          selector.appendChild(opt);
        }
        
        // Add select button to sidebar list
        if (container) {
          const btn = document.createElement('button');
          btn.className = `room-list-item ${selectedAgentSlug === agent.slug ? 'active' : ''}`;
          btn.style.width = "100%";
          btn.style.textAlign = "left";
          btn.style.display = "flex";
          btn.style.alignItems = "center";
          btn.style.gap = "8px";
          btn.style.padding = "8px 12px";
          btn.style.background = selectedAgentSlug === agent.slug ? "rgba(0, 229, 255, 0.05)" : "transparent";
          btn.style.border = "1px solid " + (selectedAgentSlug === agent.slug ? "var(--accent-teal)" : "transparent");
          btn.style.color = selectedAgentSlug === agent.slug ? "var(--text-primary)" : "var(--text-secondary)";
          btn.style.borderRadius = "6px";
          btn.style.cursor = "pointer";
          btn.style.fontSize = "0.8rem";
          btn.style.marginBottom = "6px";
          
          // Overrides or custom badge
          let badgeHtml = "";
          if (agent.is_custom) {
            badgeHtml = `<span style="font-size:0.6rem; background:rgba(0,229,255,0.1); color:var(--accent-teal); border:1px solid rgba(0,229,255,0.2); border-radius:4px; padding:1px 4px; margin-left:auto;">Custom</span>`;
          } else if (agent.is_overridden) {
            badgeHtml = `<span style="font-size:0.6rem; background:rgba(139,92,246,0.15); color:var(--accent-violet); border:1px solid rgba(139,92,246,0.25); border-radius:4px; padding:1px 4px; margin-left:auto;">Edited</span>`;
          }
          
          btn.innerHTML = `
            <span>${agent.icon}</span>
            <span style="font-weight:600; text-overflow:ellipsis; overflow:hidden; white-space:nowrap;">${agent.name}</span>
            ${badgeHtml}
          `;
          
          btn.addEventListener('click', () => {
            selectedAgentSlug = agent.slug;
            container.querySelectorAll('button').forEach(b => {
              b.style.background = "transparent";
              b.style.borderColor = "transparent";
              b.style.color = "var(--text-secondary)";
            });
            btn.style.background = "rgba(0, 229, 255, 0.05)";
            btn.style.borderColor = "var(--accent-teal)";
            btn.style.color = "var(--text-primary)";
            
            renderAgentForm(agent);
          });
          
          container.appendChild(btn);
        }
      });
      
      // If selected slug is set, reload form values
      if (selectedAgentSlug) {
        const activeAgent = agents.find(a => a.slug === selectedAgentSlug);
        if (activeAgent) renderAgentForm(activeAgent);
      }
    } catch (e) {
      console.error("Agents fetch error:", e);
    }
  }

  function renderAgentForm(agent) {
    const fallback = document.getElementById('org-agent-editor-fallback');
    if (fallback) fallback.style.display = "none";
    
    const form = document.getElementById('org-agent-detail-form');
    if (form) form.style.display = "flex";
    
    const fields = {
      'org-agent-detail-slug': agent.slug || "",
      'org-agent-detail-name': agent.name || "",
      'org-agent-detail-desc': agent.description || "",
      'org-agent-detail-icon': agent.icon || "🤖",
      'org-agent-detail-model': agent.suggested_model || agent.model_name || "meta/llama-3.1-70b-instruct",
      'org-agent-detail-temp': agent.temperature !== undefined ? agent.temperature : 0.5,
      'org-agent-detail-prompt': agent.system_prompt || ""
    };
    
    for (const [id, val] of Object.entries(fields)) {
      const el = document.getElementById(id);
      if (el) el.value = val;
    }
    
    checkOrgRoleAndRestrictAgentForm();
    fetchAgentVersions(orgSelect.value, agent.slug);
  }

  async function checkOrgRoleAndRestrictAgentForm() {
    const orgId = orgSelect.value;
    const saveBtn = document.getElementById('org-agent-detail-save-btn');
    const createBtn = document.getElementById('org-create-agent-btn');
    
    try {
      const res = await fetch(`${API_URL}/api/orgs/${orgId}/members`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const members = await res.json();
      const curMember = members.find(m => m.user_id === (profile.id || profile._id));
      const isViewer = curMember && curMember.role === "viewer";
      
      const formFields = [
        'org-agent-detail-name', 'org-agent-detail-desc', 'org-agent-detail-icon', 
        'org-agent-detail-model', 'org-agent-detail-temp', 'org-agent-detail-prompt'
      ];
      
      formFields.forEach(fId => {
        const el = document.getElementById(fId);
        if (el) el.disabled = isViewer;
      });
      
      if (saveBtn) {
        saveBtn.disabled = isViewer;
        saveBtn.style.opacity = isViewer ? "0.5" : "1";
      }
      if (createBtn) {
        createBtn.disabled = isViewer;
        createBtn.style.opacity = isViewer ? "0.5" : "1";
      }
    } catch (e) {
      console.error("Role verify error:", e);
    }
  }

  async function fetchAgentVersions(orgId, agentId) {
    const versionsList = document.getElementById('org-agent-versions-list');
    if (!versionsList) return;
    versionsList.innerHTML = `<li style="font-size:0.75rem; color:var(--text-secondary); font-style:italic;">Loading history...</li>`;
    
    try {
      const res = await fetch(`${API_URL}/api/orgs/${orgId}/agents/${agentId}/versions`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const versions = await res.json();
      versionsList.innerHTML = "";
      
      if (versions.length === 0) {
        versionsList.innerHTML = `<li style="font-size:0.75rem; color:var(--text-secondary); font-style:italic;">No prompt changes recorded yet.</li>`;
        return;
      }
      
      const membersRes = await fetch(`${API_URL}/api/orgs/${orgId}/members`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const members = await membersRes.json();
      const curMember = members.find(m => m.user_id === (profile.id || profile._id));
      const isViewer = curMember && curMember.role === "viewer";

      versions.forEach(v => {
        const li = document.createElement('li');
        li.style.display = "flex";
        li.style.alignItems = "center";
        li.style.justifyContent = "space-between";
        li.style.fontSize = "0.75rem";
        li.style.padding = "4px 8px";
        li.style.background = "rgba(255,255,255,0.02)";
        li.style.border = "1px solid var(--border-slate)";
        li.style.borderRadius = "4px";
        li.style.marginBottom = "4px";
        
        const dateStr = new Date(v.updated_at).toLocaleDateString();
        li.innerHTML = `
          <span>Version ${v.version} (saved on ${dateStr})</span>
          ${!isViewer ? `<button class="canvas-btn revert-btn" data-ver="${v.version}" style="font-size:0.65rem; padding: 1px 6px; border-radius:4px; color:var(--accent-teal); border-color:rgba(0,229,255,0.2);">Revert</button>` : ''}
        `;
        
        const revertBtn = li.querySelector('.revert-btn');
        if (revertBtn) {
          revertBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            const versionNum = parseInt(revertBtn.dataset.ver);
            if (!confirm(`Are you sure you want to revert prompt to Version ${versionNum}? This will create a new version snapshot.`)) return;
            
            try {
              const revertRes = await fetch(`${API_URL}/api/orgs/${orgId}/agents/${agentId}/revert`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify({ version: versionNum })
              });
              if (revertRes.ok) {
                alert(`Reverted to Version ${versionNum} successfully!`);
                await fetchOrgAgents(orgId);
              }
            } catch (err) {
              console.error("Revert prompt error:", err);
            }
          });
        }
        
        versionsList.appendChild(li);
      });
    } catch (e) {
      console.error("Versions history fetch error:", e);
    }
  }

  // Create New Agent Button Event
  const createAgentBtn = document.getElementById('org-create-agent-btn');
  if (createAgentBtn) {
    createAgentBtn.addEventListener('click', (e) => {
      e.preventDefault();
      selectedAgentSlug = null;
      
      const container = document.getElementById('org-agents-list-container');
      if (container) {
        container.querySelectorAll('button').forEach(b => {
          b.style.background = "transparent";
          b.style.borderColor = "transparent";
          b.style.color = "var(--text-secondary)";
        });
      }
      
      const fallback = document.getElementById('org-agent-editor-fallback');
      if (fallback) fallback.style.display = "none";
      const form = document.getElementById('org-agent-detail-form');
      if (form) form.style.display = "flex";
      
      document.getElementById('org-agent-detail-slug').value = "";
      document.getElementById('org-agent-detail-name').value = "";
      document.getElementById('org-agent-detail-desc').value = "";
      document.getElementById('org-agent-detail-icon').value = "🤖";
      document.getElementById('org-agent-detail-model').value = "meta/llama-3.1-70b-instruct";
      document.getElementById('org-agent-detail-temp').value = 0.5;
      document.getElementById('org-agent-detail-prompt').value = "";
      
      document.getElementById('org-agent-versions-list').innerHTML = `
        <li style="font-size:0.75rem; color:var(--text-secondary); font-style:italic;">Save agent to initialize versions history.</li>
      `;
      
      checkOrgRoleAndRestrictAgentForm();
    });
  }

  // Submit Detail Form Handler
  const agentDetailForm = document.getElementById('org-agent-detail-form');
  if (agentDetailForm) {
    agentDetailForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const orgId = orgSelect.value;
      const slug = document.getElementById('org-agent-detail-slug').value;
      const name = document.getElementById('org-agent-detail-name').value;
      const desc = document.getElementById('org-agent-detail-desc').value;
      const icon = document.getElementById('org-agent-detail-icon').value;
      const model = document.getElementById('org-agent-detail-model').value;
      const temp = parseFloat(document.getElementById('org-agent-detail-temp').value);
      const promptText = document.getElementById('org-agent-detail-prompt').value;
      
      const payload = {
        name,
        description: desc,
        icon,
        system_prompt: promptText,
        model_name: model,
        temperature: temp
      };
      
      try {
        let res;
        if (slug) {
          res = await fetch(`${API_URL}/api/orgs/${orgId}/agents/${slug}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify(payload)
          });
        } else {
          res = await fetch(`${API_URL}/api/orgs/${orgId}/agents`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify(payload)
          });
        }
        
        if (res.ok) {
          const data = await res.json();
          selectedAgentSlug = data.slug || data.agent_id;
          alert("Agent configuration saved successfully!");
          await fetchOrgAgents(orgId);
        } else {
          const err = await res.json();
          alert(err.detail || "Failed to save agent settings");
        }
      } catch (err) {
        console.error("Save agent settings error:", err);
      }
    });
  }

  // --- Pipeline Chains Actions ---
  async function fetchOrgChains(orgId) {
    try {
      const res = await fetch(`${API_URL}/api/orgs/${orgId}/chains`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const chains = await res.json();
      
      const container = document.getElementById('org-chains-list');
      if (!container) return;
      container.innerHTML = "";
      
      if (chains.length === 0) {
        container.innerHTML = `<li style="font-size:0.8rem; color:var(--text-secondary); font-style:italic; padding: 12px 0;">No multi-agent chains configured.</li>`;
      }
      
      const membersRes = await fetch(`${API_URL}/api/orgs/${orgId}/members`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const members = await membersRes.json();
      const curMember = members.find(m => m.user_id === (profile.id || profile._id));
      const isViewer = curMember && curMember.role === "viewer";

      chains.forEach(chain => {
        const li = document.createElement('li');
        li.style.border = "1px solid var(--border-slate)";
        li.style.borderRadius = "6px";
        li.style.padding = "10px";
        li.style.background = "rgba(255,255,255,0.01)";
        li.style.display = "flex";
        li.style.flexDirection = "column";
        li.style.gap = "6px";
        li.style.marginBottom = "8px";
        
        const sequenceStr = chain.agents.join(" ➔ ");
        
        li.innerHTML = `
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <strong style="color:var(--text-primary); font-size:0.85rem;">${chain.name}</strong>
            ${!isViewer ? `<button class="canvas-btn remove-chain-btn" data-id="${chain.id}" style="font-size:0.65rem; border-radius:4px; padding: 2px 6px; border-color:rgba(239,83,80,0.3); color:#ef5350;">Delete</button>` : ''}
          </div>
          <span style="font-size:0.75rem; color:var(--text-secondary);">${chain.description || 'No description'}</span>
          <div style="font-family:var(--font-mono); font-size:0.7rem; color:var(--accent-teal); padding: 4px 8px; background:rgba(0,229,255,0.03); border-radius:4px; border:1px solid rgba(0,229,255,0.1); width:fit-content; max-width:100%; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
            ${sequenceStr}
          </div>
        `;
        
        const delBtn = li.querySelector('.remove-chain-btn');
        if (delBtn) {
          delBtn.addEventListener('click', async () => {
            if (!confirm(`Are you sure you want to delete the pipeline chain '${chain.name}'?`)) return;
            try {
              const delRes = await fetch(`${API_URL}/api/orgs/${orgId}/chains/${chain.id}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` }
              });
              if (delRes.ok) fetchOrgChains(orgId);
            } catch (err) {
              console.error("Delete chain error:", err);
            }
          });
        }
        
        container.appendChild(li);
      });
      
      await fetchOrgAgents(orgId);
      renderChainSteps();
    } catch (e) {
      console.error("Chains fetch failed:", e);
    }
  }

  function renderChainSteps() {
    const seqContainer = document.getElementById('org-chain-steps-sequence');
    const emptyInd = document.getElementById('org-chain-empty-steps-indicator');
    if (!seqContainer) return;
    
    seqContainer.querySelectorAll('.chain-step-row-item').forEach(el => el.remove());
    
    if (currentChainSequence.length === 0) {
      if (emptyInd) emptyInd.style.display = "block";
      return;
    }
    
    if (emptyInd) emptyInd.style.display = "none";
    
    currentChainSequence.forEach((agentSlug, index) => {
      const stepDiv = document.createElement('div');
      stepDiv.className = 'chain-step-row-item';
      stepDiv.style.display = "flex";
      stepDiv.style.alignItems = "center";
      stepDiv.style.justifyContent = "space-between";
      stepDiv.style.background = "rgba(255,255,255,0.02)";
      stepDiv.style.border = "1px solid var(--border-slate)";
      stepDiv.style.borderRadius = "4px";
      stepDiv.style.padding = "6px 12px";
      stepDiv.style.fontSize = "0.75rem";
      stepDiv.style.marginBottom = "4px";
      
      stepDiv.innerHTML = `
        <span style="font-weight:600;"><span style="color:var(--accent-teal);">Step ${index+1}:</span> ${agentSlug}</span>
        <button type="button" class="remove-step-idx-btn" data-idx="${index}" style="background:none; border:none; color:#ef5350; cursor:pointer; font-size:1rem; padding:0;">&times;</button>
      `;
      
      stepDiv.querySelector('.remove-step-idx-btn').addEventListener('click', () => {
        currentChainSequence.splice(index, 1);
        renderChainSteps();
      });
      
      seqContainer.appendChild(stepDiv);
    });
  }

  // Chain events wireup
  const addStepBtn = document.getElementById('org-chain-add-step-btn');
  if (addStepBtn) {
    addStepBtn.addEventListener('click', () => {
      const sel = document.getElementById('org-chain-agent-selector');
      if (!sel || !sel.value) return;
      currentChainSequence.push(sel.value);
      renderChainSteps();
    });
  }

  const clearChainBtn = document.getElementById('org-chain-clear-btn');
  if (clearChainBtn) {
    clearChainBtn.addEventListener('click', () => {
      currentChainSequence = [];
      renderChainSteps();
      document.getElementById('org-chain-name').value = "";
      document.getElementById('org-chain-desc').value = "";
    });
  }

  const chainCreateForm = document.getElementById('org-chain-create-form');
  if (chainCreateForm) {
    chainCreateForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const orgId = orgSelect.value;
      const name = document.getElementById('org-chain-name').value.trim();
      const desc = document.getElementById('org-chain-desc').value.trim();
      
      if (currentChainSequence.length < 2) {
        alert("Please add at least 2 steps to construct an execution chain pipeline.");
        return;
      }
      
      try {
        const res = await fetch(`${API_URL}/api/orgs/${orgId}/chains`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
          body: JSON.stringify({ name, description: desc, agents: currentChainSequence })
        });
        
        if (res.ok) {
          alert("Pipeline chain created successfully!");
          currentChainSequence = [];
          document.getElementById('org-chain-name').value = "";
          document.getElementById('org-chain-desc').value = "";
          fetchOrgChains(orgId);
        } else {
          const err = await res.json();
          alert(err.detail || "Failed to save chain workflow");
        }
      } catch (err) {
        console.error("Save chain pipeline error:", err);
      }
    });
  }

  // --- Audit Logs ---
  async function fetchOrgAuditLogs(orgId) {
    try {
      const res = await fetch(`${API_URL}/api/orgs/${orgId}/audit-logs`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (!res.ok) {
        orgAuditList.innerHTML = '<li style="font-size:0.8rem; color:var(--text-secondary); font-style:italic; padding: 12px 0;">Access Denied: Only organization Owners can view compliance audit logs.</li>';
        return;
      }
      
      const logs = await res.json();
      orgAuditList.innerHTML = "";
      if (logs.length === 0) {
        orgAuditList.innerHTML = '<li style="font-size:0.8rem; color:var(--text-secondary); font-style:italic; padding: 12px 0;">No activities logged yet.</li>';
        return;
      }
      
      logs.forEach(l => {
        const li = document.createElement('li');
        li.style.borderBottom = "1px solid rgba(255,255,255,0.03)";
        li.style.padding = "6px 0";
        li.style.lineHeight = "1.4";
        
        const time = new Date(l.timestamp).toLocaleTimeString();
        li.innerHTML = `
          <span style="color:var(--accent-teal); margin-right: 6px;">[${time}]</span>
          <strong style="color:var(--text-primary); margin-right: 4px;">${l.username}</strong>
          <span style="color: #a0aec0;">(${l.action}):</span>
          <span style="color:var(--text-secondary);">${l.details}</span>
        `;
        orgAuditList.appendChild(li);
      });
    } catch (e) {
      console.error("Audit log loading failed:", e);
    }
  }

  // --- Billing ---
  async function fetchOrgBilling(orgId) {
    try {
      const res = await fetch(`${API_URL}/api/orgs/${orgId}/billing`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      
      document.getElementById('org-billing-status').textContent = data.billing_status;
      document.getElementById('org-billing-tier-select').value = data.billing_plan;
      
      // Restrict plan select if not owner
      const saveBtn = document.getElementById('org-billing-save-btn');
      const tierSelect = document.getElementById('org-billing-tier-select');
      
      // Fetch members to check role
      const membersRes = await fetch(`${API_URL}/api/orgs/${orgId}/members`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const members = await membersRes.json();
      const curMember = members.find(m => m.user_id === (profile.id || profile._id));
      const curUserIsOwner = curMember && curMember.role === "owner";
      
      if (saveBtn) {
        saveBtn.disabled = !curUserIsOwner;
        saveBtn.style.opacity = curUserIsOwner ? "1" : "0.5";
      }
      if (tierSelect) {
        tierSelect.disabled = !curUserIsOwner;
      }
    } catch (e) {
      console.error("Billing fetch failed:", e);
    }
  }

  if (orgBillingForm) {
    orgBillingForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const orgId = orgSelect.value;
      const plan = document.getElementById('org-billing-tier-select').value;
      if (!orgId) return;
      
      try {
        const res = await fetch(`${API_URL}/api/orgs/${orgId}/billing`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
          body: JSON.stringify({ billing_plan: plan })
        });
        if (res.ok) {
          alert("Billing plan updated successfully!");
        } else {
          alert("Failed to update plan.");
        }
      } catch (err) {
        console.error("Update billing plan error:", err);
      }
    });
  }

  // Initialize org list
  fetchOrgs();

  fetchRooms();
  fetchTemplates();
}

function updateNavbarProfile(name) {
  const loginBtn = document.getElementById('nav-login-btn');
  if (loginBtn) {
    if (name.startsWith("Guest_")) {
      loginBtn.textContent = "Login";
    } else {
      loginBtn.textContent = `Hi, ${name}`;
    }
  }
}

// ==========================================
// 6. AUTHENTICATION MODAL HANDLERS
// ==========================================
function initAuthModal() {
  const authModal = document.getElementById('auth-modal');
  const closeBtn = document.getElementById('modal-close');
  const toggleLink = document.getElementById('modal-toggle-link');
  const modalTitle = document.getElementById('modal-title');
  const submitBtn = document.getElementById('auth-submit-btn');
  const nameGroup = document.getElementById('name-group');
  const toggleMsg = document.getElementById('modal-toggle-message');
  const authForm = document.getElementById('auth-form');
  const errorDiv = document.getElementById('modal-error');
  
  if (!authModal) return;

  let isSignUpMode = true; 

  const ctaIds = ['header-cta', 'hero-btn-primary', 'cta-btn-primary', 'nav-login-btn'];
  ctaIds.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener('click', (e) => {
        e.preventDefault();
        const isGuest = el.textContent === "Login" || el.id !== "nav-login-btn";
        const token = localStorage.getItem('forgeroom_token');
        if (token && id === 'nav-login-btn' && !isGuest) {
          if (confirm("Would you like to log out?")) {
            localStorage.removeItem('forgeroom_token');
            window.location.hash = "";
            location.reload();
          }
          return;
        }
        openModal(id !== 'nav-login-btn');
      });
    }
  });

  closeBtn.addEventListener('click', closeModal);
  authModal.addEventListener('click', (e) => {
    if (e.target === authModal) closeModal();
  });

  function openModal(signUpDefault = true) {
    authModal.style.display = "flex";
    setTimeout(() => {
      authModal.classList.add('open');
    }, 10);
    setMode(signUpDefault);
  }

  function closeModal() {
    authModal.classList.remove('open');
    setTimeout(() => {
      authModal.style.display = "none";
      errorDiv.style.display = "none";
      authForm.reset();
    }, 300);
  }

  function setMode(signUp) {
    isSignUpMode = signUp;
    errorDiv.style.display = "none";
    if (signUp) {
      modalTitle.textContent = "Create Account";
      submitBtn.textContent = "Sign Up";
      nameGroup.style.display = "flex";
      toggleMsg.textContent = "Already have an account?";
      toggleLink.textContent = "Sign In";
    } else {
      modalTitle.textContent = "Sign In";
      submitBtn.textContent = "Sign In";
      nameGroup.style.display = "none";
      toggleMsg.textContent = "Don't have an account?";
      toggleLink.textContent = "Sign Up";
    }
  }

  toggleLink.addEventListener('click', (e) => {
    e.preventDefault();
    setMode(!isSignUpMode);
  });

  authForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    errorDiv.style.display = "none";

    const name = document.getElementById('auth-name').value.trim();
    const email = document.getElementById('auth-email').value.trim();
    const password = document.getElementById('auth-password').value;

    try {
      if (isSignUpMode) {
        const regRes = await fetch(`${API_URL}/api/auth/register`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, email, password })
        });
        
        if (!regRes.ok) {
          const errData = await regRes.json();
          throw new Error(errData.detail || "Signup failed");
        }
      }

      const loginRes = await fetch(`${API_URL}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });

      if (!loginRes.ok) {
        const errData = await loginRes.json();
        throw new Error(errData.detail || "Login failed");
      }

      const tokenData = await loginRes.json();
      localStorage.setItem('forgeroom_token', tokenData.access_token);
      
      closeModal();
      location.reload(); 

    } catch (err) {
      errorDiv.textContent = err.message;
      errorDiv.style.display = "block";
    }
  });
}

// ==========================================
// 7. USE CASES TAB NAVIGATION
// ==========================================
function initTabs() {
  const tabButtons = document.querySelectorAll('.uc-tab-btn');
  const panes = document.querySelectorAll('.uc-content-pane');

  tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const target = btn.dataset.tab;
      if (!target) return;

      tabButtons.forEach(b => b.classList.remove('active'));
      panes.forEach(p => p.classList.remove('active'));

      btn.classList.add('active');
      const targetPane = document.getElementById(`uc-${target}`);
      if (targetPane) {
        targetPane.classList.add('active');
      }
    });
  });
}

// ==========================================
// 8. FAQ ACCORDION TRANSITIONS
// ==========================================
function initFAQ() {
  const faqQuestions = document.querySelectorAll('.faq-question');

  faqQuestions.forEach(q => {
    q.addEventListener('click', () => {
      const item = q.parentElement;
      const answer = item.querySelector('.faq-answer');
      const isActive = item.classList.contains('active');

      document.querySelectorAll('.faq-item').forEach(otherItem => {
        otherItem.classList.remove('active');
        otherItem.querySelector('.faq-answer').style.maxHeight = null;
      });

      if (!isActive) {
        item.classList.add('active');
        answer.style.maxHeight = answer.scrollHeight + 'px';
      }
    });
  });
}

// --- Research Tool Modal Event Handlers ---
const researchBtn = document.getElementById('db-research-btn');
const researchModal = document.getElementById('research-modal');
const researchClose = document.getElementById('research-modal-close');
const researchForm = document.getElementById('research-form');
const researchInput = document.getElementById('research-query-input');

if (researchBtn && researchModal) {
  researchBtn.addEventListener('click', () => {
    if (activeUserRole === "viewer") {
      alert("Viewer role cannot trigger research lookups.");
      return;
    }
    toggleModal(researchModal, true);
  });
}

if (researchClose && researchModal) {
  researchClose.addEventListener('click', () => toggleModal(researchModal, false));
}

if (researchForm) {
  researchForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const queryText = researchInput.value.trim();
    if (!queryText || !activeRoomId) return;

    toggleModal(researchModal, false);
    researchInput.value = "";

    try {
      appendSystemMsg(`System: Research request sent for "${queryText}"...`);
      const res = await fetch(`${API_URL}/api/rooms/${activeRoomId}/research`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ query: queryText })
      });
      if (!res.ok) {
        const err = await res.json();
        alert(err.detail || "Research lookup request failed.");
      }
    } catch (err) {
      console.error("Research REST request failed:", err);
    }
  });
}
