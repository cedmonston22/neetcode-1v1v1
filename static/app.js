const MONACO_BASE = "https://cdn.jsdelivr.net/npm/monaco-editor@0.52.2/min";
const NAME_KEY = "ncv-name";
const TOKEN_KEY = "ncv-token";
const CODE_SEND_DELAY_MS = 400;
const LANE_COLORS = ["var(--lane-0)", "var(--lane-1)", "var(--lane-2)"];

const roomCode = window.location.pathname.split("/").pop().toUpperCase();
const $ = (id) => document.getElementById(id);

const app = {
  name: null,
  socket: null,
  fatal: false,
  retryMs: 500,
  state: null,
  clockOffset: 0,
  matchKey: null,
  resultsKey: null,
  token: null,
  myEditor: null,
  inFlight: false,
  codeTimer: null,
  lanUrl: window.location.origin,
  toastTimer: null,
};

function loadName() {
  const fromUrl = new URLSearchParams(window.location.search).get("name");
  if (fromUrl) return fromUrl.trim();
  try {
    return (localStorage.getItem(NAME_KEY) || "").trim();
  } catch {
    return "";
  }
}

function loadToken() {
  try {
    const saved = localStorage.getItem(TOKEN_KEY);
    if (saved) return saved;
  } catch {
    return randomToken();
  }
  const token = randomToken();
  try {
    localStorage.setItem(TOKEN_KEY, token);
  } catch {
    return token;
  }
  return token;
}

function randomToken() {
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

function saveName(name) {
  try {
    localStorage.setItem(NAME_KEY, name);
  } catch {
    return;
  }
}

function showToast(message) {
  const toast = $("toast");
  toast.textContent = message;
  toast.classList.remove("hidden");
  clearTimeout(app.toastTimer);
  app.toastTimer = setTimeout(() => toast.classList.add("hidden"), 4000);
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text ?? "";
  return div.innerHTML;
}

function formatClock(seconds) {
  const s = Math.max(0, Math.ceil(seconds));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

function serverNow() {
  return Date.now() / 1000 + app.clockOffset;
}

const monacoReady = new Promise((resolve) => {
  if (typeof window.require !== "function") {
    resolve(null);
    return;
  }
  window.MonacoEnvironment = {
    getWorkerUrl: () =>
      `data:text/javascript;charset=utf-8,${encodeURIComponent(
        `self.MonacoEnvironment={baseUrl:'${MONACO_BASE}/'};importScripts('${MONACO_BASE}/vs/base/worker/workerMain.js');`,
      )}`,
  };
  window.require.config({ paths: { vs: `${MONACO_BASE}/vs` } });
  const fallback = setTimeout(() => resolve(null), 8000);
  window.require(
    ["vs/editor/editor.main"],
    () => {
      clearTimeout(fallback);
      window.monaco.editor.defineTheme("ncv", {
        base: "vs-dark",
        inherit: true,
        rules: [],
        colors: {
          "editor.background": "#151931",
          "editor.lineHighlightBackground": "#1c2140",
          "editorLineNumber.foreground": "#4b5387",
        },
      });
      resolve(window.monaco);
    },
    (error) => {
      console.error("Monaco failed to load, using a plain text editor", error);
      clearTimeout(fallback);
      resolve(null);
    },
  );
});

async function createEditor(host, { readOnly, value, onChange }) {
  const monaco = await monacoReady;
  host.innerHTML = "";
  if (monaco) {
    const editor = monaco.editor.create(host, {
      value,
      language: "python",
      theme: "ncv",
      readOnly,
      automaticLayout: true,
      minimap: { enabled: false },
      fontFamily: "JetBrains Mono, Consolas, monospace",
      fontSize: 14,
      tabSize: 4,
      insertSpaces: true,
      scrollBeyondLastLine: false,
      renderLineHighlight: readOnly ? "none" : "line",
    });
    if (onChange) editor.onDidChangeModelContent(() => onChange());
    return {
      getValue: () => editor.getValue(),
      setValue: (text) => {
        if (editor.getValue() !== text) editor.setValue(text);
      },
      dispose: () => editor.dispose(),
    };
  }
  const area = document.createElement("textarea");
  area.value = value;
  area.readOnly = readOnly;
  area.spellcheck = false;
  area.setAttribute("aria-label", readOnly ? "Opponent's code" : "Your code");
  if (onChange) area.addEventListener("input", onChange);
  area.addEventListener("keydown", (event) => {
    if (event.key === "Tab" && !readOnly) {
      event.preventDefault();
      area.setRangeText("    ", area.selectionStart, area.selectionEnd, "end");
      onChange?.();
    }
  });
  host.appendChild(area);
  return {
    getValue: () => area.value,
    setValue: (text) => {
      if (area.value !== text) area.value = text;
    },
    dispose: () => area.remove(),
  };
}

function send(message) {
  if (app.socket?.readyState === WebSocket.OPEN) {
    app.socket.send(JSON.stringify(message));
    return true;
  }
  showToast("Not connected to the server. Reconnecting…");
  return false;
}

function connect() {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const query = `name=${encodeURIComponent(app.name)}&token=${encodeURIComponent(app.token)}`;
  const socket = new WebSocket(`${protocol}://${window.location.host}/ws/${roomCode}?${query}`);
  app.socket = socket;
  socket.addEventListener("open", () => {
    app.retryMs = 500;
    app.inFlight = false;
  });
  socket.addEventListener("message", (event) => {
    let message;
    try {
      message = JSON.parse(event.data);
    } catch (error) {
      console.error("bad message from server", error);
      return;
    }
    onServerMessage(message);
  });
  socket.addEventListener("close", () => {
    if (app.fatal || app.socket !== socket) return;
    showToast("Lost connection. Reconnecting…");
    setTimeout(connect, app.retryMs);
    app.retryMs = Math.min(app.retryMs * 2, 5000);
  });
}

function onServerMessage(message) {
  if (message.type === "state") {
    app.clockOffset = message.serverNow - Date.now() / 1000;
    app.state = message;
    render();
  } else if (message.type === "result") {
    app.inFlight = false;
    renderResult(message);
    updateRunButtons();
  } else if (message.type === "error") {
    app.inFlight = false;
    updateRunButtons();
    if (message.fatal) {
      app.fatal = true;
      $("fatal-message").textContent = capitalize(message.message) + ".";
      $("fatal").classList.remove("hidden");
    } else {
      showToast(capitalize(message.message) + ".");
    }
  }
}

function capitalize(text) {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function laneColor(state, name) {
  const index = state.players.findIndex((p) => p.name === name);
  return LANE_COLORS[Math.max(0, index) % LANE_COLORS.length];
}

function render() {
  const state = app.state;
  $("room-code").textContent = state.room;
  document.title = `NeetCode 1v1v1 room ${state.room}`;
  renderLanes(state);
  renderClock();

  $("lobby").classList.toggle("hidden", state.phase !== "lobby" && state.phase !== "countdown");
  $("arena").classList.toggle("hidden", state.phase !== "playing");
  $("results").classList.toggle("hidden", state.phase !== "finished");
  $("countdown").classList.toggle("hidden", state.phase !== "countdown");

  if (state.phase === "lobby" || state.phase === "countdown") {
    app.resultsKey = null;
    renderLobby(state);
  }
  if (state.phase === "playing") renderArena(state);
  if (state.phase === "finished") renderResults(state);
}

function renderLanes(state) {
  const lanes = $("lanes");
  const total = state.totalTests;
  const signature = JSON.stringify(state.players.map((p) => p.name));
  if (lanes.dataset.signature !== signature) {
    lanes.dataset.signature = signature;
    lanes.innerHTML = state.players
      .map((p) => {
        const me = p.name === app.name ? ' <span class="you">(you)</span>' : "";
        return `<div class="lane" data-player="${escapeHtml(p.name)}">
          <div class="lane-name" style="color:${laneColor(state, p.name)}">${escapeHtml(p.name)}${me}</div>
          <div class="lane-bar"><div class="lane-fill" style="background:${laneColor(state, p.name)}"></div></div>
          <div class="lane-count"></div>
        </div>`;
      })
      .join("");
  }
  state.players.forEach((p, i) => {
    const lane = lanes.children[i];
    lane.classList.toggle("offline", !p.connected);
    lane.querySelector(".lane-bar").classList.toggle("busy", p.busy);
    lane.querySelector(".lane-fill").style.width = `${total ? (100 * p.bestPassed) / total : 0}%`;
    lane.querySelector(".lane-count").textContent = total ? `${p.bestPassed}/${total}` : p.ready ? "ready" : "";
  });
}

function renderClock() {
  const state = app.state;
  if (!state) return;
  const clock = $("clock");
  let remaining = state.matchSeconds;
  if (state.phase === "playing" && state.deadline) remaining = state.deadline - serverNow();
  if (state.phase === "finished") remaining = 0;
  clock.textContent = formatClock(remaining);
  clock.classList.toggle("low", state.phase === "playing" && remaining <= 60);
  if (state.phase === "countdown" && state.countdownEndsAt) {
    $("countdown-number").textContent = String(Math.max(1, Math.ceil(state.countdownEndsAt - serverNow())));
  }
}

function renderLobby(state) {
  $("share-link").value = `${app.lanUrl}/room/${state.room}`;

  const slots = [];
  for (let i = 0; i < state.maxPlayers; i += 1) {
    const p = state.players[i];
    if (!p) {
      slots.push(`<li class="empty">Waiting for a player</li>`);
      continue;
    }
    slots.push(`<li>
      <span class="swatch" style="background:${laneColor(state, p.name)}"></span>
      <span>${escapeHtml(p.name)}${p.name === app.name ? ' <span class="soft">(you)</span>' : ""}</span>
      <span class="status${p.ready ? " ready" : ""}">${p.ready ? "Ready" : "Not ready"}</span>
    </li>`);
  }
  $("roster").innerHTML = slots.join("");

  renderChips($("topic-chips"), state.allTopics, state.topics, "topic");
  renderChips($("difficulty-chips"), state.allDifficulties, state.difficulties, "difficulty");
  renderMinuteChips(state);

  const me = state.players.find((p) => p.name === app.name);
  const readyButton = $("ready");
  readyButton.textContent = me?.ready ? "Not ready" : "I'm ready";
  readyButton.className = me?.ready ? "" : "go";
  readyButton.disabled = state.phase !== "lobby";

  const hint = $("ready-hint");
  if (state.poolSize === 0) {
    hint.textContent = "No problems match these settings. Pick at least one topic and difficulty.";
  } else if (state.players.length < state.minPlayers) {
    hint.textContent = `${state.poolSize} problems in the pool. Waiting for at least one opponent.`;
  } else {
    const waiting = state.players.filter((p) => !p.ready).map((p) => p.name);
    hint.textContent = waiting.length
      ? `${state.poolSize} problems in the pool. Waiting on ${waiting.join(" and ")}.`
      : "Starting…";
  }
}

function renderChips(container, all, selected, group) {
  const signature = JSON.stringify([all, selected]);
  if (container.dataset.signature === signature) return;
  container.dataset.signature = signature;
  container.innerHTML = all
    .map(
      (value) => `<label class="chip"><input type="checkbox" data-group="${group}" value="${escapeHtml(value)}"${
        selected.includes(value) ? " checked" : ""
      } /><span>${escapeHtml(value)}</span></label>`,
    )
    .join("");
}

function renderMinuteChips(state) {
  const container = $("minute-chips");
  const selected = state.matchSeconds / 60;
  const signature = JSON.stringify([state.minMinutes, state.maxMinutes, selected]);
  if (container.dataset.signature === signature) return;
  container.dataset.signature = signature;
  const chips = [];
  for (let m = state.minMinutes; m <= state.maxMinutes; m += 1) {
    chips.push(`<label class="chip"><input type="radio" name="minutes" data-group="minutes" value="${m}"${
      m === selected ? " checked" : ""
    } /><span>${m} min</span></label>`);
  }
  container.innerHTML = chips.join("");
}

function sendSettings() {
  const checked = (group) =>
    [...document.querySelectorAll(`input[data-group="${group}"]:checked`)].map((input) => input.value);
  const minutes = document.querySelector('input[data-group="minutes"]:checked');
  send({
    type: "settings",
    topics: checked("topic"),
    difficulties: checked("difficulty"),
    minutes: minutes ? Number(minutes.value) : undefined,
  });
}

async function renderArena(state) {
  const key = `${state.problem.slug}@${state.startedAt}`;
  const me = state.players.find((p) => p.name === app.name);

  if (app.matchKey !== key) {
    app.matchKey = key;
    const problem = state.problem;
    $("problem-title").textContent = `${problem.title}`;
    $("problem-difficulty").textContent = problem.difficulty;
    $("problem-difficulty").className = problem.difficulty;
    $("problem-topic").textContent = problem.topic;
    $("problem-body").innerHTML = problem.content;
    $("console").innerHTML =
      '<p class="soft">Run your code against the examples, or submit it against every test.</p>';

    app.myEditor?.dispose();
    app.myEditor = null;
    app.myEditor = await createEditor($("my-editor"), {
      readOnly: false,
      value: me?.code || problem.starterCode,
      onChange: scheduleCodeSend,
    });
  }

  updateRunButtons();
}

function updateRunButtons() {
  const me = app.state?.players.find((p) => p.name === app.name);
  const blocked = app.inFlight || Boolean(me?.busy);
  $("run").disabled = blocked;
  $("submit").disabled = blocked;
}

function scheduleCodeSend() {
  clearTimeout(app.codeTimer);
  app.codeTimer = setTimeout(() => {
    if (app.myEditor && app.state?.phase === "playing") send({ type: "code", code: app.myEditor.getValue() });
  }, CODE_SEND_DELAY_MS);
}

function evaluate(kind) {
  if (!app.myEditor || app.state?.phase !== "playing" || app.inFlight) return;
  const me = app.state.players.find((p) => p.name === app.name);
  if (me?.busy) return;
  clearTimeout(app.codeTimer);
  if (send({ type: kind, code: app.myEditor.getValue() })) {
    app.inFlight = true;
    updateRunButtons();
    $("console").innerHTML = `<p class="soft">${kind === "run" ? "Running the examples…" : "Running every test…"}</p>`;
  }
}

function renderResult(result) {
  const parts = [];
  const label = result.kind === "run" ? "examples" : "tests";
  if (result.compileError) {
    parts.push(`<div class="verdict fail">Your code didn't compile</div><pre>${escapeHtml(result.compileError)}</pre>`);
  } else {
    const allPassed = result.passed === result.total;
    parts.push(
      `<div class="verdict ${allPassed ? "pass" : "fail"}">${result.passed} of ${result.total} ${label} passed</div>`,
    );
    if (result.timedOut) {
      parts.push(
        `<p class="error-text">Time limit exceeded (${result.timeLimit}s). Your solution is too slow for the larger tests, and tests that didn't finish count as failed.</p>`,
      );
    }
    if (result.crash) parts.push(`<pre class="error-text">${escapeHtml(result.crash)}</pre>`);
    if (result.kind === "submit" && result.cases.length) parts.push(`<p class="soft">First failing test:</p>`);
    for (const c of result.cases) {
      const rows = c.input.map((arg) => `<dt>${escapeHtml(arg.name)}</dt><dd>${escapeHtml(arg.value)}</dd>`);
      rows.push(`<dt>Expected</dt><dd>${escapeHtml(c.expected ?? "")}</dd>`);
      rows.push(`<dt>Output</dt><dd>${escapeHtml(c.actual ?? "no output")}</dd>`);
      if (c.error) rows.push(`<dt>Error</dt><dd class="error-text">${escapeHtml(c.error)}</dd>`);
      if (c.stdout) rows.push(`<dt>Printed</dt><dd>${escapeHtml(c.stdout)}</dd>`);
      parts.push(`<div class="case${c.passed ? " pass" : ""}"><dl>${rows.join("")}</dl></div>`);
    }
  }
  $("console").innerHTML = parts.join("");
}

function renderResults(state) {
  const key = `${state.problem?.slug}@${state.startedAt}`;
  if (app.resultsKey === key) return;
  app.resultsKey = key;

  const winner = state.winner;
  $("results-title").textContent = !winner ? "No winner this round" : winner === app.name ? "You won" : `${winner} won`;
  const reason =
    state.endReason === "solved"
      ? `${winner} passed all ${state.totalTests} tests on ${state.problem.title}.`
      : winner
        ? `Time ran out. ${winner} passed the most tests on ${state.problem.title}.`
        : `Time ran out before anyone passed a test on ${state.problem.title}.`;
  $("results-sub").textContent = reason;

  const ranked = [...state.players].sort(
    (a, b) => b.bestPassed - a.bestPassed || (a.bestAt ?? Infinity) - (b.bestAt ?? Infinity),
  );
  $("solutions").innerHTML = ranked
    .map((p) => {
      const detail = p.solvedAt != null ? `solved in ${formatClock(p.solvedAt)}` : `${p.bestPassed}/${state.totalTests} tests`;
      const subs = `${p.submissions} submission${p.submissions === 1 ? "" : "s"}`;
      return `<section class="solution" style="--lane-color:${laneColor(state, p.name)}">
        <header><strong>${escapeHtml(p.name)}</strong><span class="soft">${detail}, ${subs}</span></header>
        <pre><code>${escapeHtml(p.code)}</code></pre>
      </section>`;
    })
    .join("");
}

function wireUi() {
  $("copy-link").addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText($("share-link").value);
      $("copy-link").textContent = "Copied";
    } catch (error) {
      console.error("clipboard write failed", error);
      $("share-link").select();
      $("copy-link").textContent = "Press Ctrl+C";
    }
    setTimeout(() => ($("copy-link").textContent = "Copy link"), 2000);
  });

  document.addEventListener("change", (event) => {
    if (event.target.matches("input[data-group]")) sendSettings();
  });

  $("ready").addEventListener("click", () => {
    const me = app.state?.players.find((p) => p.name === app.name);
    send({ type: "ready", ready: !me?.ready });
  });

  $("run").addEventListener("click", () => evaluate("run"));
  $("submit").addEventListener("click", () => evaluate("submit"));
  $("back-to-lobby").addEventListener("click", () => send({ type: "lobby" }));

  document.addEventListener(
    "keydown",
    (event) => {
      if (event.key !== "Enter" || !(event.ctrlKey || event.metaKey)) return;
      if (app.state?.phase !== "playing") return;
      event.preventDefault();
      event.stopPropagation();
      evaluate(event.shiftKey ? "submit" : "run");
    },
    true,
  );

  $("name-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const name = $("name-input").value.trim();
    if (!name) return;
    start(name);
  });

  setInterval(renderClock, 250);
}

async function loadLanUrl() {
  try {
    const response = await fetch("/api/info");
    if (!response.ok) throw new Error(`server returned ${response.status}`);
    app.lanUrl = (await response.json()).lanUrl;
    if (app.state) $("share-link").value = `${app.lanUrl}/room/${app.state.room}`;
  } catch (error) {
    console.error("couldn't load the LAN address", error);
  }
}

function start(name) {
  app.name = name;
  app.token = loadToken();
  saveName(name);
  $("name-dialog").classList.add("hidden");
  const url = new URL(window.location.href);
  url.searchParams.delete("name");
  window.history.replaceState(null, "", url);
  connect();
}

wireUi();
loadLanUrl();
const initialName = loadName();
if (initialName) {
  start(initialName);
} else {
  $("name-dialog").classList.remove("hidden");
  $("name-input").focus();
}
