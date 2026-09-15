/* 3D structure view for the browser UI. No external libraries. */
(function () {
  "use strict";
  var canvas = document.getElementById("adit3d");
  if (!canvas || !window.ADIT_SCENE) { return; }
  var scene = window.ADIT_SCENE;
  var ctx = canvas.getContext("2d");
  var state = { rx: -1.05, ry: 0.52, zoom: 1, panx: 0, pany: 0 };

  function rotate(p) {
    var cy = Math.cos(state.ry), sy = Math.sin(state.ry);
    var x = p[0] * cy + p[2] * sy, z = -p[0] * sy + p[2] * cy;
    var cx = Math.cos(state.rx), sx = Math.sin(state.rx);
    return [x, p[1] * cx - z * sx, p[1] * sx + z * cx];
  }

  function project(p) {
    var r = rotate(p);
    var w = canvas.width, h = canvas.height;
    var s = (Math.min(w, h) * 0.42 / scene.scale) * state.zoom;
    return [w / 2 + r[0] * s + state.panx, h / 2 - r[1] * s + state.pany, r[2], s];
  }

  function draw() {
    var w = canvas.width, h = canvas.height;
    var dark = matchMedia && matchMedia("(prefers-color-scheme: dark)").matches;
    ctx.fillStyle = dark ? "#1e1e1e" : "#ffffff";
    ctx.fillRect(0, 0, w, h);
    var i, a, b;
    ctx.strokeStyle = dark ? "#7a7a7a" : "#9a9a9a";
    ctx.lineWidth = 1;
    for (i = 0; i < scene.cell_lines.length; i++) {
      a = project(scene.cell_lines[i][0]); b = project(scene.cell_lines[i][1]);
      ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke();
    }
    for (i = 0; i < scene.bonds.length; i++) {
      var ia = scene.bonds[i][0], ib = scene.bonds[i][1];
      a = project(scene.positions[ia]); b = project(scene.positions[ib]);
      var mx = (a[0] + b[0]) / 2, my = (a[1] + b[1]) / 2;
      var width = Math.max(1.5, 0.16 * a[3]);
      ctx.lineWidth = width + 2;
      ctx.strokeStyle = dark ? "rgba(255,255,255,0.30)" : "rgba(0,0,0,0.35)";
      ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke();
      ctx.lineWidth = width;
      ctx.strokeStyle = scene.colors[ia];
      ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(mx, my); ctx.stroke();
      ctx.strokeStyle = scene.colors[ib];
      ctx.beginPath(); ctx.moveTo(mx, my); ctx.lineTo(b[0], b[1]); ctx.stroke();
    }
    var order = scene.positions.map(function (p, k) { return [project(p), k]; });
    order.sort(function (u, v) { return u[0][2] - v[0][2]; });
    for (i = 0; i < order.length; i++) {
      var q = order[i][0], k = order[i][1];
      var rad = Math.max(2, scene.radii[k] * 0.55 * q[3]);
      var g = ctx.createRadialGradient(q[0] - rad * 0.35, q[1] - rad * 0.35, rad * 0.1, q[0], q[1], rad);
      g.addColorStop(0, "#ffffff"); g.addColorStop(0.35, scene.colors[k]); g.addColorStop(1, scene.colors[k]);
      ctx.fillStyle = g;
      ctx.beginPath(); ctx.arc(q[0], q[1], rad, 0, 2 * Math.PI); ctx.fill();
      ctx.strokeStyle = dark ? "rgba(0,0,0,0.55)" : "rgba(0,0,0,0.35)";
      ctx.lineWidth = 1; ctx.stroke();
    }
    drawAxes(dark);
  }

  
  function drawAxes(dark) {
    var ratio = window.devicePixelRatio || 1;
    var arm = 22 * ratio, ox = 14 * ratio + arm, oy = canvas.height - 14 * ratio - arm;
    var axes = [[1, 0, 0], [0, 1, 0], [0, 0, 1]];
    var colors = dark ? ["#E8756F", "#7BD07B", "#6FA8E8"] : ["#D9534F", "#5CB85C", "#4A90D9"];
    var names = ["x", "y", "z"];
    ctx.font = (11 * ratio) + "px system-ui, sans-serif";
    ctx.textAlign = "center"; ctx.textBaseline = "middle";
    for (var k = 0; k < 3; k++) {
      var v = rotate(axes[k]);
      var ex = ox + v[0] * arm, ey = oy - v[1] * arm;
      ctx.strokeStyle = colors[k]; ctx.fillStyle = colors[k];
      ctx.lineWidth = 1.6 * ratio; ctx.lineCap = "round";
      ctx.beginPath(); ctx.moveTo(ox, oy); ctx.lineTo(ex, ey); ctx.stroke();
      ctx.beginPath(); ctx.arc(ex, ey, 2.2 * ratio, 0, 2 * Math.PI); ctx.fill();
      ctx.fillText(names[k], ox + v[0] * (arm + 9 * ratio), oy - v[1] * (arm + 9 * ratio));
    }
    ctx.textAlign = "start"; ctx.textBaseline = "alphabetic";
  }

  function resize() {
    var ratio = window.devicePixelRatio || 1;
    var width = canvas.clientWidth || 420, height = canvas.clientHeight || 320;
    canvas.width = Math.round(width * ratio); canvas.height = Math.round(height * ratio);
    draw();
  }

  var last = null, button = 0;
  canvas.addEventListener("mousedown", function (e) { last = [e.clientX, e.clientY]; button = e.button; e.preventDefault(); });
  window.addEventListener("mouseup", function () { last = null; });
  window.addEventListener("mousemove", function (e) {
    if (!last) { return; }
    var dx = e.clientX - last[0], dy = e.clientY - last[1];
    last = [e.clientX, e.clientY];
    if (button === 2) { state.panx += dx; state.pany += dy; }
    else { state.ry += dx * 0.01; state.rx += dy * 0.01; }
    draw();
  });
  canvas.addEventListener("contextmenu", function (e) { e.preventDefault(); });
  canvas.addEventListener("wheel", function (e) {
    e.preventDefault();
    state.zoom *= (e.deltaY < 0 ? 1.1 : 1 / 1.1);
    state.zoom = Math.min(20, Math.max(0.2, state.zoom));
    draw();
  }, { passive: false });
  canvas.addEventListener("dblclick", function () {
    state = { rx: -1.05, ry: 0.52, zoom: 1, panx: 0, pany: 0 }; draw();
  });
  var views = document.querySelectorAll("[data-view]");
  for (var v = 0; v < views.length; v++) {
    views[v].addEventListener("click", function (e) {
      var parts = e.currentTarget.getAttribute("data-view").split(",");
      state.rx = parseFloat(parts[0]); state.ry = parseFloat(parts[1]);
      state.zoom = 1; state.panx = 0; state.pany = 0; draw();
    });
  }
  window.addEventListener("resize", resize);
  resize();
})();
