// No libraries or build step. textContent keeps incoming data out of HTML markup.
const page = document.body.dataset.page;
const projectName = document.body.dataset.project;
let wizardName = "";
let refreshing = false;
let configuration = {};
const $ = id => document.getElementById(id);
function node(tag, text = "", className = "") {
  const item = document.createElement(tag);
  item.textContent = text;
  if (className) item.className = className;
  return item;
}
function notice(message) { $("notice").textContent = message; $("notice").hidden = !message; }
function fixed(value, digits = 1) { return value == null ? "—" : Number(value).toFixed(digits); }
function stamp(value) { return value ? new Date(value * 1000).toLocaleTimeString() : "Not seen yet"; }
function age(value) {
  if (!value) return "No live data yet";
  const seconds = Math.max(0, Math.floor(Date.now() / 1000 - value));
  return seconds < 60 ? `${seconds}s ago` : seconds < 3600 ? `${Math.floor(seconds / 60)}m ago` : `${Math.floor(seconds / 3600)}h ago`;
}
function badge(text, kind = "") { return node("span", text, "badge " + kind); }
function empty(target, title, description) {
  const box = node("div", "", "empty");
  box.append(node("strong", title), node("span", description));
  target.replaceChildren(box);
}
async function api(path, body) {
  const response = await fetch(path, body ? {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)} : {});
  if (!response.ok) {
    const result = await response.json().catch(() => ({}));
    throw new Error(result.error || `Request failed (${response.status}). Please try again.`);
  }
  return response.json();
}
function table(target, headings, rows) {
  const element = node("table"), head = node("thead"), header = node("tr"), body = node("tbody");
  headings.forEach(text => header.append(node("th", text)));
  head.append(header);
  rows.forEach(values => { const row = node("tr"); values.forEach(value => { const cell = node("td"); cell.append(value instanceof Node ? value : document.createTextNode(String(value))); row.append(cell); }); body.append(row); });
  element.append(head, body); target.replaceChildren(element);
}
function stats(items) {
  $("stats").replaceChildren(...items.map(([label, value, hint]) => {
    const card = node("div", "", "stat");
    card.append(node("span", label, "stat-label"), node("strong", value), node("small", hint));
    return card;
  }));
}
function projects(overview) {
  const list = overview.projects;
  stats([["Projects", list.length, "Discovered or created"], ["Online now", list.filter(p => p.online).length, "Message in the last 15 seconds"], ["Connected devices", list.reduce((sum, p) => sum + p.devices, 0), "Seen within retained history"], ["Message rate", fixed(list.reduce((sum, p) => sum + p.rate, 0)) + " /s", "15-second average"]]);
  $("project-count").textContent = list.length;
  if (!list.length) empty($("projects"), "Your first reading starts here.", "Connect a board or start a simulator. Projects appear automatically.");
  else $("projects").replaceChildren(...list.map(project => {
    const card = node("a", "", "project-card"); card.href = "/projects/" + project.name;
    const top = node("div", "", "card-top"); top.append(node("span", "⌁", "project-icon"), badge(project.online ? "● Online" : "○ Offline", project.online ? "online" : ""));
    const foot = node("div", "", "card-foot"); foot.append(node("span", `${project.devices} devices · ${fixed(project.rate)} msg/s`), node("span", "Open workspace →", "arrow"));
    card.append(top, node("h3", project.name), node("span", "Last seen · " + age(project.last_seen), "subtle"), foot);
    return card;
  }));
  table($("metrics"), ["Project", "First valid data", "Time to first data"], list.map(p => [p.name, stamp(p.first_data), p.started ? p.first_data_seconds == null ? "Waiting…" : fixed(p.first_data_seconds, 2) + " s" : "Wizard not started"]));
}
function svgNode(tag, attributes = {}) {
  const item = document.createElementNS("http://www.w3.org/2000/svg", tag);
  Object.entries(attributes).forEach(([key, value]) => item.setAttribute(key, value));
  return item;
}
function chart(rows, label) {
  const svg = svgNode("svg", {viewBox: "0 0 420 126", role: "img", "aria-label": label});
  const values = rows.map(row => row.value), low = Math.min(...values), high = Math.max(...values);
  const span = high - low || 1, first = rows[0].received, elapsed = rows.at(-1).received - first || 1;
  [20, 65, 110].forEach(y => svg.append(svgNode("line", {x1: 38, x2: 415, y1: y, y2: y, class: "chart-grid"})));
  [[20, high], [110, low]].forEach(([y, value]) => { const text = svgNode("text", {x: 0, y: y + 4, class: "chart-text"}); text.textContent = fixed(value); svg.append(text); });
  const points = rows.map(row => `${38 + (row.received - first) / elapsed * 377},${high === low ? 65 : 110 - (row.value - low) / span * 90}`);
  svg.append(svgNode("polyline", {points: points.join(" "), class: "chart-line"}));
  if (rows.length === 1) svg.append(svgNode("circle", {cx: 38, cy: 65, r: 3, fill: "#08775f"}));
  return svg;
}
function project(detail) {
  const p = detail.project;
  $("project-description").textContent = `${p.online ? "Online" : "Offline"} · Last seen ${age(p.last_seen)} · Updates arrive automatically`;
  stats([["Devices", p.devices, "Seen within retained history"], ["Live sensor series", Object.keys(detail.series).length, "Latest chart window"], ["Message rate", fixed(p.rate) + " /s", "15-second average"], ["Time to first data", p.first_data_seconds == null ? "—" : fixed(p.first_data_seconds, 2) + " s", p.started ? "Measured from wizard start" : "Start a wizard to record this"]]);
  const series = Object.entries(detail.series);
  if (!series.length) empty($("sensors"), "Waiting for your first reading", "Keep this page open while you connect your board.");
  else $("sensors").replaceChildren(...series.map(([key, rows]) => {
    const latest = rows.at(-1), card = node("article", "", "sensor-card"), head = node("div", "", "sensor-head");
    const title = node("div"); title.append(node("h3", latest.sensor), node("span", latest.device, "subtle")); head.append(title);
    if (latest.simulated) head.append(badge("Simulated", "simulated"));
    card.append(head, node("div", fixed(latest.value, 2), "sensor-value"), chart(rows, key + " over time"));
    const meta = node("div", "", "chart-meta"); meta.append(node("span", stamp(rows[0].received)), node("span", stamp(latest.received))); card.append(meta); return card;
  }));
  table($("devices"), ["Device", "Last seen"], detail.devices.map(d => [d.device, age(d.last_seen)]));
  if (!detail.events.length) $("events").replaceChildren(node("p", "No alerts or summaries yet. Summaries appear after 10 readings per sensor.", "subtle"));
  else $("events").replaceChildren(...detail.events.map(event => {
    const data = JSON.parse(event.payload), item = node("div", "", "event");
    item.append(badge(event.kind === "alerts" ? "Threshold alert" : "Window summary", event.kind === "alerts" ? "warning" : "online"), node("p", `${data.device} / ${data.sensor}`), node("p", event.kind === "alerts" ? `${fixed(data.value)} ${data.direction} ${data.limit}` : `avg ${fixed(data.avg)} · min ${fixed(data.min)} · max ${fixed(data.max)} · ${data.count} readings`, "subtle"));
    if (data.simulated) item.append(badge("Simulated", "simulated"));
    return item;
  }));
  $("messages").replaceChildren(...detail.messages.map(message => {
    const item = node("div", "", "message"), top = node("div", "", "message-top"), data = JSON.parse(message.payload);
    top.append(node("code", message.topic), node("span", stamp(message.received), "subtle"));
    item.append(top, node("pre", JSON.stringify(data)));
    if (data.simulated) item.append(badge("Simulated", "simulated"));
    if (data.retained) item.append(badge("Retained history"));
    return item;
  }));
  problems(detail.problems);
}
function problems(items) {
  $("problem-count").textContent = items.length;
  $("problems").replaceChildren(...items.map(item => {
    const box = node("div", "", "problem"); box.append(node("code", item.topic), node("p", item.problem), node("p", "Try this: " + item.fix, "subtle")); return box;
  }));
  if (!items.length) $("problems").append(node("p", "No message problems recorded. Incoming readings are checked automatically.", "subtle"));
}
function troubleshooting(overview) {
  const expected = projectName || wizardName;
  const different = overview.projects.filter(p => p.name !== expected && p.last_seen);
  const checks = [[overview.broker_connected, overview.broker_connected ? "Dashboard is connected to the broker." : "Broker connection is unavailable. Start the platform and check Docker."],
    [!!overview.last_any, overview.last_any ? `A message reached lab/# ${age(overview.last_any)}.` : "No message has reached lab/# since this dashboard started."]];
  if (expected) checks.push([!different.length, different.length ? `Other projects are receiving data: ${different.map(p => p.name).join(", ")}. Check PROJECT = "${expected}" in your sketch.` : `Expected sketch project: PROJECT = "${expected}".`]);
  $("troubleshooting").replaceChildren(...checks.map(([ok, text]) => { const item = node("div", "", "check"); item.append(node("span", ok ? "✓" : "○", "check-mark"), node("span", text)); return item; }));
}
function copyBlock(title, value) {
  const block = node("div", "", "copy-block"), header = node("header"), button = node("button", "Copy", "button"); button.type = "button";
  button.addEventListener("click", async () => {
    try { await navigator.clipboard.writeText(value); button.textContent = "Copied ✓"; setTimeout(() => button.textContent = "Copy", 1500); }
    catch { notice("Clipboard access is unavailable. Select and copy the text below manually."); }
  });
  header.append(node("span", title), button); block.append(header, node("pre", value)); return block;
}
function checklist(result) {
  const p = result.project; wizardName = p.name; $("checklist").hidden = false;
  const steps = [];
  function step(title, description, block) { const item = node("li"); item.append(node("h3", title), node("p", description)); if (block) item.append(block); steps.push(item); }
  step("Start the platform", "Run from the Git root in PowerShell. Keep this page open.", copyBlock("PowerShell", "& .\\tools\\workspace.ps1 -Action Start"));
  if (p.board === "esp32") {
    step("Add your WiFi settings locally", `Laptop LAN IP: ${configuration.lan_ip || "not supplied — run tools/show_ip.py on the laptop"}. Fill in WiFi and BROKER_IP yourself. Never paste credentials into this page.`, copyBlock("PowerShell · copies the example only if secrets.h is missing", "$folder = 'edge-lab-platform-starter\\edge-lab-platform\\firmware\\esp32_publisher'\nif (-not (Test-Path \"$folder\\secrets.h\")) { Copy-Item \"$folder\\secrets.example.h\" \"$folder\\secrets.h\" }\n.\\.venv\\Scripts\\python.exe tools\\show_ip.py --write"));
  } else step("Connect the Uno by USB", "WiFi settings and secrets.h are not needed for Uno. Select its COM port in Arduino IDE; COM3 is an example.");
  step("Paste your generated sketch", "Use Arduino IDE. The ESP32 needs the ESP32 board package and PubSubClient library. Custom sensor names read the analog input until you change the read expression.", copyBlock("Arduino sketch · " + p.board, result.sketch));
  step("Flash the board yourself", "Select the correct board and port, then upload. For Uno, close Serial Monitor before starting the gateway. For ESP32, join the laptop and board to your 2.4 GHz hotspot and allow inbound TCP 1883.", p.board === "uno" ? copyBlock("PowerShell · substitute your actual COM port", ".\\.venv\\Scripts\\python.exe gateway\\serial_gateway.py COM3") : null);
  step("Wait for the first valid live reading", "The timer begins when you create this checklist. Invalid messages and retained old messages do not complete it.");
  $("steps").replaceChildren(...steps); updateFirstData(p);
}
function updateFirstData(p) {
  const box = $("first-data");
  if (p.first_data_seconds == null) { box.className = "first-data"; box.textContent = `Waiting for first message… ${Math.max(0, Math.floor(Date.now() / 1000 - p.started))} seconds elapsed`; }
  else { box.className = "first-data success"; box.textContent = `✓ First valid data arrived in ${fixed(p.first_data_seconds, 2)} seconds`; const link = node("a", "Open " + p.name + " workspace →"); link.href = "/projects/" + p.name; box.append(link); }
}
function benchmarks(runs) {
  const running = runs.find(run => run.status === "running"); $("run-benchmark").disabled = !!running;
  $("benchmark-status").textContent = running ? "Measuring 100 local and 100 public-broker round trips… This continues if you leave the page." : "Ready. An unreachable public broker is reported without stopping the dashboard.";
  const latest = runs.find(run => run.result);
  if (!latest) empty($("benchmark-results"), "No measurements yet", "Run your first comparison to see real numbers here.");
  else {
    const pairs = [["Local edge", latest.result.local], ["Cloud stand-in", latest.result.cloud]];
    table($("benchmark-results"), ["Path", "Status", "Mean ms", "Min ms", "Max ms", "Std dev ms", "Lost / 100"], pairs.map(([label, result]) => [label, result.status, fixed(result.mean, 2), fixed(result.min, 2), fixed(result.max, 2), fixed(result.stddev, 2), result.lost]));
    const svg = svgNode("svg", {viewBox: "0 0 650 130", role: "img", "aria-label": "Mean MQTT round-trip milliseconds"});
    const max = Math.max(1, ...pairs.map(([, r]) => r.mean || 0));
    pairs.forEach(([label, r], index) => { const y = index * 53 + 10, text = svgNode("text", {x: 0, y: y + 18, class: "chart-text"}); text.textContent = label; svg.append(text); svg.append(svgNode("rect", {x: 120, y, width: r.mean == null ? 0 : Math.max(2, r.mean / max * 400), height: 27, rx: 4, class: index ? "bar-cloud" : "bar-local"})); const value = svgNode("text", {x: 535, y: y + 18, class: "chart-text"}); value.textContent = r.mean == null ? "Unreachable" : fixed(r.mean, 2) + " ms"; svg.append(value); });
    $("benchmark-chart").replaceChildren(svg);
  }
  table($("benchmark-history"), ["Started", "Public broker", "Status", "Local mean", "Cloud mean"], runs.slice(0,20).map(run => [new Date(run.started * 1000).toLocaleString(), run.cloud_host, run.status, fixed(run.result?.local.mean, 2), run.result?.cloud.status === "unreachable" ? "Unreachable" : fixed(run.result?.cloud.mean, 2)]));
}
async function refresh() {
  if (refreshing) return;
  refreshing = true;
  try {
    const overview = await api("/api/overview");
    $("connection").textContent = overview.broker_connected ? "● Broker connected" : "○ Broker unavailable";
    $("connection").className = "badge " + (overview.broker_connected ? "online" : "warning");
    if (page === "home") { projects(overview); problems(overview.problems); }
    if (page === "project") project(await api("/api/projects/" + projectName));
    if (page === "new") { problems(overview.problems); if (wizardName) updateFirstData((await api("/api/projects/" + wizardName)).project); }
    if (page === "benchmark") benchmarks((await api("/api/benchmarks")).runs);
    else troubleshooting(overview);
  } catch (error) { notice(error.message); }
  finally { refreshing = false; }
}
$("project-form")?.addEventListener("submit", async event => {
  event.preventDefault(); const button = event.target.querySelector("button"); button.disabled = true;
  try { const result = await api("/api/projects", Object.fromEntries(new FormData(event.target))); checklist(result); notice(""); refresh(); }
  catch (error) { notice(error.message); } finally { button.disabled = false; }
});
$("benchmark-form")?.addEventListener("submit", async event => {
  event.preventDefault(); $("run-benchmark").disabled = true;
  try { await api("/api/benchmarks", Object.fromEntries(new FormData(event.target))); notice(""); }
  catch (error) { notice(error.message); } finally { refresh(); }
});
api("/api/config").then(config => { configuration = config; if ($("cloud-host")) $("cloud-host").value = config.cloud_broker; }).catch(error => notice(error.message));
const events = new EventSource("/events");
events.addEventListener("update", refresh);
// Polling also expires online badges when no new MQTT messages arrive, and works
// as a fallback when the small lab server's eight SSE slots are occupied.
setInterval(refresh, 5000);
refresh();

// Rules load separately so live chart refreshes never overwrite a student's form.
async function loadRules() {
  if (!$("rule-values")) return;
  const result = await api('/api/projects/' + projectName + '/rules');
  $("rule-values").textContent = Object.entries(result.rules).map(([sensor, rule]) => `${sensor}: ${rule[0]} ${rule[1]}`).join('\n');
}
$("rule-form")?.addEventListener('submit', async event => {
  event.preventDefault();
  const body = Object.fromEntries(new FormData(event.target));
  body.limit = Number(body.limit);
  try {
    await api('/api/projects/' + projectName + '/rules', body);
    $("rule-status").textContent = 'Saved. The next readings will use this rule within three seconds.';
    await loadRules();
  } catch (error) { notice(error.message); }
});
loadRules().catch(error => notice(error.message));
