(function () {
  "use strict";

  function fmtTime(iso) {
    if (!iso) return "—";
    var d = new Date(iso);
    return d.toLocaleString(undefined, { hour: "2-digit", minute: "2-digit", month: "short", day: "numeric" });
  }

  function renderConnect(info) {
    var card = document.getElementById("connect-card");
    if (!card || !info) return;
    if (!info.available) {
      card.hidden = true;
      return;
    }
    card.hidden = false;
    var ipEl = document.getElementById("connect-ip");
    var portEl = document.getElementById("connect-port");
    var pwBlock = document.getElementById("connect-password-block");
    var pwEl = document.getElementById("connect-password");

    if (ipEl) ipEl.textContent = window.location.hostname;
    if (portEl) portEl.textContent = info.port;
    if (pwBlock && pwEl) {
      if (info.password) {
        pwEl.textContent = info.password;
        pwBlock.hidden = false;
      } else {
        pwBlock.hidden = true;
      }
    }
  }

  function populateNextEventDisplay(containerId, nameId, whenId, flavorId, nextEventName, nextEventFlavor, nextEventStartDisplay, nextEventStartDisplaySimple) {
    var container = document.getElementById(containerId);
    if (!container) return;
    if (!nextEventName) {
      container.hidden = true;
      return;
    }
    var nameEl = document.getElementById(nameId);
    var whenEl = document.getElementById(whenId);
    var flavorEl = document.getElementById(flavorId);
    if (nameEl) nameEl.textContent = nextEventName;
    if (whenEl) whenEl.textContent = nextEventStartDisplaySimple || nextEventStartDisplay || "";
    if (flavorEl) {
      if (nextEventFlavor) {
        flavorEl.textContent = nextEventFlavor;
        flavorEl.hidden = false;
      } else {
        flavorEl.hidden = true;
      }
    }
    container.hidden = false;
  }

  function renderEvent(activeEvent, nextEventName, nextEventFlavor, nextEventStartDisplay, nextEventStartDisplaySimple, nextEventOverriddenEarly) {
    var activeBadge = document.getElementById("event-active-badge");
    if (activeBadge) {
      var activeNameEl = document.getElementById("event-active-name");
      if (activeEvent) {
        if (activeNameEl) activeNameEl.textContent = activeEvent.name;
        activeBadge.hidden = false;
      } else {
        activeBadge.hidden = true;
      }
    }

    var eventBanner = document.getElementById("event-banner");
    if (eventBanner) {
      fillEventBannerRow(document.getElementById("event-banner-active"), "Event Active: ",
        activeEvent && activeEvent.name,
        [activeEvent && activeEvent.flavor, activeEvent && activeEvent.seconds_left ? "ends in " + fmtDuration(activeEvent.seconds_left) : null]);
      fillEventBannerRow(document.getElementById("event-banner-next"), "Next Event: ",
        nextEventName,
        [nextEventFlavor, nextEventStartDisplaySimple || nextEventStartDisplay]);
      eventBanner.classList.toggle("event-banner-is-active", !!activeEvent);
      eventBanner.hidden = !activeEvent && !nextEventName;
    }

    populateNextEventDisplay("next-event-info", "next-event-name-simple", "next-event-when", "next-event-flavor-simple", nextEventName, nextEventFlavor, nextEventStartDisplay, nextEventStartDisplaySimple);
  }

  function fillEventBannerRow(row, label, name, extras) {
    if (!row) return;
    row.textContent = "";
    if (!name) {
      row.hidden = true;
      return;
    }
    var first = document.createElement("span");
    first.className = "event-announcement-part";
    first.appendChild(document.createTextNode(label));
    var strong = document.createElement("strong");
    strong.textContent = name;
    first.appendChild(strong);
    row.appendChild(first);
    extras.forEach(function (text) {
      if (!text) return;
      var part = document.createElement("span");
      part.className = "event-announcement-part";
      part.textContent = text;
      row.appendChild(part);
    });
    row.hidden = false;
  }

  function fmtDuration(seconds) {
    var h = Math.floor(seconds / 3600);
    var m = Math.floor((seconds % 3600) / 60);
    if (h > 0) return h + "h " + m + "m";
    return m > 0 ? m + "m" : "under a minute";
  }

  var PLAYER_ACTION_PATHS = {
    "kick": "kick",
    "ban": "ban",
    "whitelist-remove": "whitelist/remove",
    "whitelist-add": "whitelist/add",
  };
  var PLAYER_ACTION_LABELS = {
    "kick": "Kick User",
    "ban": "Ban User",
    "whitelist-remove": "Remove WL",
    "whitelist-add": "Add WL",
  };

  function renderPlayers(s) {
    var list = document.getElementById("players-list");
    if (!list) return;
    var names = s.online ? (s.player_names || []) : [];

    list.innerHTML = "";

    function addBubble(className, text, title) {
      var li = document.createElement("li");
      var span = document.createElement("span");
      span.className = className;
      span.textContent = text;
      if (title) span.title = title;
      li.appendChild(span);
      list.appendChild(li);
      return li;
    }

    function rebootTooltip() {
      if (!s.last_restart_at) return "";
      var text = "Last rebooted " + fmtTime(s.last_restart_at);
      return s.last_restart_reason ? text + " — " + s.last_restart_reason + "." : text + ".";
    }

    if (!s.online) {
      addBubble("badge offline", "Server Offline: Live Map Not Available" + (s.offline_reason ? " (starting up)" : ""), s.offline_reason);
    } else {
      addBubble("badge online", "Server Online: Live Map", rebootTooltip());
    }

    names.forEach(function (name) {
      var li = document.createElement("li");
      var pingBtn = document.createElement("button");
      pingBtn.type = "button";
      pingBtn.className = "badge player-ping-btn";
      pingBtn.textContent = name;
      pingBtn.dataset.player = name;
      li.appendChild(pingBtn);
      list.appendChild(li);
    });

    if (typeof s.total_players === "number") {
      var label = s.total_players + " total player" + (s.total_players === 1 ? "" : "s");
      addBubble("badge total-players-badge", label);
    }
  }

  function renderStatus(s) {
    var errorEl = document.getElementById("status-error");

    renderPlayers(s);
    if (errorEl) {
      if (s.error) {
        errorEl.textContent = s.error;
        errorEl.hidden = false;
      } else {
        errorEl.hidden = true;
      }
    }

    renderConnect(s.server_info);
    var connectName = document.getElementById("connect-name");
    if (connectName && s.world_label) connectName.textContent = s.world_label;
    renderEvent(s.active_event, s.next_event_name, s.next_event_flavor, s.next_event_start_display, s.next_event_start_display_simple, s.next_event_overridden_early);
  }

  function pollStatus() {
    var card = document.getElementById("status-card");
    if (!card) return;
    var url = card.dataset.pollUrl;
    var interval = parseInt(card.dataset.pollInterval, 10) || 20000;

    function tick() {
      fetch(url, { credentials: "same-origin" })
        .then(function (r) { return r.json(); })
        .then(renderStatus)
        .catch(function () {});
    }
    tick();
    setInterval(tick, interval);
  }

  var SVG_NS = "http://www.w3.org/2000/svg";

  function svgEl(tag, attrs) {
    var el = document.createElementNS(SVG_NS, tag);
    for (var k in attrs) el.setAttribute(k, attrs[k]);
    return el;
  }

  var MAP_PADDING = 80;
  var MAP_MIN_CROP = 500;

  var OFF_MAP_ZONE = { x: 60, y: 40, w: 900, h: 300 };
  var OFF_MAP_COLS = 8;

  function offMapSlotPosition(index) {
    var cellW = OFF_MAP_ZONE.w / OFF_MAP_COLS;
    var rowH = 70;
    var col = index % OFF_MAP_COLS;
    var row = Math.floor(index / OFF_MAP_COLS);
    return {
      px: OFF_MAP_ZONE.x + cellW * (col + 0.5),
      py: OFF_MAP_ZONE.y + rowH * row + rowH / 2,
    };
  }

  function updateOffMapZoneVisibility(show) {
    var zone = document.getElementById("map-offmap-zone");
    if (zone) zone.hidden = !show;
  }

  var manualViewActive = false;
  var mapFullW = 1400, mapFullH = 1386;
  var MIN_ZOOM_W = 100;

  function updateZoomButtonState() {
    var svg = document.getElementById("map-svg");
    var zoomInBtn = document.getElementById("map-zoom-in-btn");
    var zoomOutBtn = document.getElementById("map-zoom-out-btn");
    if (!svg || (!zoomInBtn && !zoomOutBtn)) return;
    var box = svg.viewBox.baseVal;
    var EPS = 0.5;
    if (zoomInBtn) zoomInBtn.disabled = box.width <= MIN_ZOOM_W + EPS;
    if (zoomOutBtn) zoomOutBtn.disabled = box.width >= mapFullW - EPS;
  }

  var followingPlayer = null;

  function findMapPoint(name) {
    for (var i = 0; i < lastMapPoints.length; i++) {
      if (lastMapPoints[i].name === name) return lastMapPoints[i];
    }
    return null;
  }

  function centerViewOnPoint(px, py, width) {
    var svg = document.getElementById("map-svg");
    if (!svg) return;
    var height = width * (mapFullH / mapFullW);
    var x = Math.max(0, Math.min(mapFullW - width, px - width / 2));
    var y = Math.max(0, Math.min(mapFullH - height, py - height / 2));
    svg.setAttribute("viewBox", [x, y, width, height].join(" "));
    manualViewActive = true;
    updateZoomButtonState();
  }

  function jumpToPlayer(name) {
    stopFollowing();
    var point = findMapPoint(name);
    if (!point) return false;
    centerViewOnPoint(point.px, point.py, MAP_MIN_CROP);
    return true;
  }

  function updateFollowIndicator() {
    var el = document.getElementById("map-follow-indicator");
    if (!el) return;
    if (followingPlayer) {
      var nameEl = el.querySelector(".map-follow-indicator-name");
      if (nameEl) nameEl.textContent = followingPlayer;
      el.hidden = false;
    } else {
      el.hidden = true;
    }
  }

  function stopFollowing() {
    if (!followingPlayer) return;
    followingPlayer = null;
    updateFollowIndicator();
  }

  function startFollowing(name) {
    followingPlayer = name;
    updateFollowIndicator();
    recenterOnFollowedPlayer();
  }

  function recenterOnFollowedPlayer() {
    if (!followingPlayer) return;
    var point = findMapPoint(followingPlayer);
    if (!point) return;
    centerViewOnPoint(point.px, point.py, MAP_MIN_CROP);
  }

  function computeMapViewBox(points, fullW, fullH) {
    if (!points.length) return [0, 0, fullW, fullH];

    var minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    points.forEach(function (p) {
      minX = Math.min(minX, p.px); maxX = Math.max(maxX, p.px);
      minY = Math.min(minY, p.py); maxY = Math.max(maxY, p.py);
    });
    minX -= MAP_PADDING; maxX += MAP_PADDING;
    minY -= MAP_PADDING; maxY += MAP_PADDING;

    var w = Math.max(MAP_MIN_CROP, maxX - minX);
    var h = Math.max(MAP_MIN_CROP, maxY - minY);

    var aspect = fullW / fullH;
    if (w / h > aspect) { h = w / aspect; } else { w = h * aspect; }

    var cx = (minX + maxX) / 2, cy = (minY + maxY) / 2;
    var x = cx - w / 2, y = cy - h / 2;

    w = Math.min(w, fullW);
    h = Math.min(h, fullH);
    x = Math.max(0, Math.min(fullW - w, x));
    y = Math.max(0, Math.min(fullH - h, y));

    return [x, y, w, h];
  }

  var EASTER_EGG_CLICKS = 10;
  var EASTER_EGG_WINDOW_MS = 10000;
  var EASTER_EGG_DURATION_MS = 4700;
  var EASTER_EGG_COOLDOWN_MS = 1000;
  var EASTER_EGG_SOUNDS = [
    "/static/wubby-scream.mp3",
    "/static/o-o-omg.mp3",
    "/static/whatthefuhuhuck.mp3",
    "/static/yeahyeahok.mp3",
  ];
  var eggClickTarget = null;
  var eggClickCount = 0;
  var eggStreakStart = 0;
  var eggActive = false;
  var eggCooldownUntil = 0;
  var eggTimer = null;
  var lastMapPoints = [];

  function playEasterEggSound() {
    try {
      var pick = EASTER_EGG_SOUNDS[Math.floor(Math.random() * EASTER_EGG_SOUNDS.length)];
      var audio = new Audio(pick);
      audio.play().catch(function () {});
    } catch (e) {}
  }

  var CLUSTER_DISTANCE = 22;
  var CLUSTER_RING_BASE = 13;
  var CLUSTER_RING_STEP = 4.5;

  function clusterGroups(points) {
    var n = points.length;
    var visited = new Array(n).fill(false);
    var groups = [];
    for (var i = 0; i < n; i++) {
      if (visited[i]) continue;
      var group = [i];
      visited[i] = true;
      var queue = [i];
      while (queue.length) {
        var cur = queue.pop();
        for (var j = 0; j < n; j++) {
          if (visited[j]) continue;
          var dx = points[cur].px - points[j].px;
          var dy = points[cur].py - points[j].py;
          if (Math.sqrt(dx * dx + dy * dy) < CLUSTER_DISTANCE) {
            visited[j] = true;
            group.push(j);
            queue.push(j);
          }
        }
      }
      groups.push(group);
    }
    return groups;
  }

  function spreadOverlaps(points) {
    var out = points.slice();
    clusterGroups(points).forEach(function (group) {
      if (group.length < 2) return;
      var cx = 0, cy = 0;
      group.forEach(function (i) { cx += points[i].px; cy += points[i].py; });
      cx /= group.length;
      cy /= group.length;
      var radius = CLUSTER_RING_BASE + CLUSTER_RING_STEP * (group.length - 2);
      group.forEach(function (i, idx) {
        var angle = (2 * Math.PI * idx) / group.length - Math.PI / 2;
        out[i] = Object.assign({}, points[i], {
          px: cx + radius * Math.cos(angle),
          py: cy + radius * Math.sin(angle),
        });
      });
    });
    return out;
  }

  function drawDots(points) {
    var dots = document.getElementById("map-dots");
    if (!dots) return;
    while (dots.firstChild) dots.removeChild(dots.firstChild);

    if (eggActive) {
      points.forEach(function (p) {
        var img = svgEl("image", {
          href: "/static/wubby-face.gif",
          x: p.px - 18, y: p.py - 18, width: 36, height: 36,
          class: "map-egg-face",
        });
        var title = svgEl("title", {});
        title.textContent = p.name;
        img.appendChild(title);
        dots.appendChild(img);
      });
      return;
    }

    points.forEach(function (p) {
      var circle = svgEl("circle", {
        cx: p.px, cy: p.py, r: 8,
        class: "map-dot" + (p.onMap ? "" : " map-dot-offmap"),
        "data-player": p.name,
      });
      var title = svgEl("title", {});
      var agoText = p.seconds_ago < 60
        ? "just now"
        : Math.round(p.seconds_ago / 60) + "m ago";
      title.textContent = p.onMap
        ? (p.name + " -- last seen " + agoText)
        : (p.name + " -- off the depicted map area (real coords " + Math.round(p.x) + ", " + Math.round(p.y) + ") -- last update " + agoText);
      circle.appendChild(title);
      dots.appendChild(circle);

      var label = svgEl("text", { x: p.px + 12, y: p.py + 5, class: "map-dot-label" });
      label.textContent = p.name;
      dots.appendChild(label);

      var bbox = label.getBBox();
      var bg = svgEl("rect", {
        x: bbox.x - 3, y: bbox.y - 1.5,
        width: bbox.width + 6, height: bbox.height + 3,
        rx: 3, class: "map-dot-label-bg",
      });
      dots.insertBefore(bg, label);
    });
  }

  function triggerEasterEgg() {
    eggActive = true;
    drawDots(lastMapPoints);
    playEasterEggSound();
    if (eggTimer) clearTimeout(eggTimer);
    eggTimer = setTimeout(function () {
      eggActive = false;
      eggCooldownUntil = Date.now() + EASTER_EGG_COOLDOWN_MS;
      drawDots(lastMapPoints);
    }, EASTER_EGG_DURATION_MS);
  }

  var CLICK_PULSE_MS = 150;

  function pulseDot(circle) {
    circle.classList.remove("map-dot-clicked");
    requestAnimationFrame(function () {
      circle.classList.add("map-dot-clicked");
      setTimeout(function () {
        circle.classList.remove("map-dot-clicked");
      }, CLICK_PULSE_MS);
    });
  }

  function wirePlayerEasterEgg() {
    var dots = document.getElementById("map-dots");
    if (!dots) return;
    dots.addEventListener("click", function (ev) {
      if (eggActive || Date.now() < eggCooldownUntil) return;
      var circle = ev.target.closest(".map-dot");
      if (!circle) return;
      var name = circle.dataset.player;
      var now = Date.now();

      if (name !== eggClickTarget || now - eggStreakStart > EASTER_EGG_WINDOW_MS) {
        eggClickTarget = name;
        eggClickCount = 0;
        eggStreakStart = now;
      }
      eggClickCount++;
      pulseDot(circle);

      if (eggClickCount >= EASTER_EGG_CLICKS) {
        eggClickTarget = null;
        eggClickCount = 0;
        triggerEasterEgg();
      }
    });
  }

  var PING_DURATION_MS = 2200;

  function pingPlayer(name) {
    var pings = document.getElementById("map-pings");
    if (!pings) return;
    var point = findMapPoint(name);
    if (!point) {
      flashPingMiss(name);
      return;
    }

    var ring = svgEl("circle", { cx: point.px, cy: point.py, r: 10, class: "map-ping-ring" });
    pings.appendChild(ring);

    setTimeout(function () {
      if (ring.parentNode) ring.parentNode.removeChild(ring);
    }, PING_DURATION_MS);
  }

  function flashPingMiss(name) {
    var list = document.getElementById("players-list");
    if (!list) return;
    var btns = list.querySelectorAll(".player-ping-btn");
    for (var i = 0; i < btns.length; i++) {
      if (btns[i].dataset.player !== name) continue;
      var btn = btns[i];
      btn.classList.remove("player-ping-btn-miss");
      requestAnimationFrame(function () {
        btn.classList.add("player-ping-btn-miss");
        setTimeout(function () { btn.classList.remove("player-ping-btn-miss"); }, 500);
      });
      break;
    }
  }

  function wirePlayerPing() {
    var list = document.getElementById("players-list");
    if (!list) return;
    list.addEventListener("click", function (ev) {
      var btn = ev.target.closest(".player-ping-btn");
      if (!btn) return;
      jumpToPlayer(btn.dataset.player);
      pingPlayer(btn.dataset.player);
    });
  }

  var mapActionToastTimer = null;
  function showMapActionToast(text, isError) {
    var el = document.getElementById("map-action-toast");
    if (!el) return;
    el.textContent = text;
    el.classList.toggle("map-action-toast-error", !!isError);
    el.classList.add("map-action-toast-visible");
    clearTimeout(mapActionToastTimer);
    mapActionToastTimer = setTimeout(function () {
      el.classList.remove("map-action-toast-visible");
    }, 3000);
  }

  function wireMapContextMenu() {
    var view = document.getElementById("map-view");
    var canvas = document.getElementById("map-canvas");
    var list = document.getElementById("players-list");
    var menu = document.getElementById("map-context-menu");
    if (!view || !canvas || !menu) return;

    var isAdmin = view.dataset.isAdmin === "true";
    var nameEl = document.getElementById("map-context-menu-name");
    var coordsEl = document.getElementById("map-context-menu-coords");
    var followBtn = menu.querySelector('[data-action="follow"]');
    var unfollowBtn = menu.querySelector('[data-action="unfollow"]');
    var adminBlock = document.getElementById("map-context-menu-admin");
    if (adminBlock) adminBlock.hidden = !isAdmin;

    var mainView = document.getElementById("map-context-menu-main");
    var teleportView = document.getElementById("map-context-menu-teleport");
    var teleportListEl = document.getElementById("map-context-menu-teleport-list");

    var followIndicator = document.getElementById("map-follow-indicator");
    if (followIndicator) {
      followIndicator.addEventListener("click", function (ev) {
        if (ev.target.closest(".map-follow-indicator-stop")) stopFollowing();
      });
    }

    var menuPlayer = null;

    function clampMenuPosition() {
      var canvasRect = canvas.getBoundingClientRect();
      var left = parseFloat(menu.style.left) || 0;
      var top = parseFloat(menu.style.top) || 0;
      var maxX = canvasRect.width - menu.offsetWidth - 8;
      var maxY = canvasRect.height - menu.offsetHeight - 8;
      menu.style.left = Math.max(8, Math.min(maxX, left)) + "px";
      menu.style.top = Math.max(8, Math.min(maxY, top)) + "px";
    }

    function showMainView() {
      if (teleportView) teleportView.hidden = true;
      if (mainView) mainView.hidden = false;
      clampMenuPosition();
    }

    function showTeleportList(forPlayer) {
      if (!teleportListEl) return;
      teleportListEl.innerHTML = "";
      var others = list
        ? Array.prototype.slice.call(list.querySelectorAll("[data-player]"))
          .map(function (el) { return el.dataset.player; })
          .filter(function (name) { return name !== forPlayer; })
        : [];

      if (!others.length) {
        var empty = document.createElement("p");
        empty.className = "hint map-context-menu-empty";
        empty.textContent = "No one else online.";
        teleportListEl.appendChild(empty);
      } else {
        others.forEach(function (name) {
          var btn = document.createElement("button");
          btn.type = "button";
          btn.className = "map-context-menu-item";
          btn.dataset.action = "teleport-target";
          btn.dataset.targetPlayer = name;
          btn.textContent = name;
          teleportListEl.appendChild(btn);
        });
      }

      if (mainView) mainView.hidden = true;
      if (teleportView) teleportView.hidden = false;
      clampMenuPosition();
    }

    function closeMenu() {
      menu.hidden = true;
      menuPlayer = null;
      showMainView();
    }

    function openMenuFor(name, clientX, clientY) {
      menuPlayer = name;
      showMainView();
      if (nameEl) nameEl.textContent = name;
      if (coordsEl) {
        var point = findMapPoint(name);
        coordsEl.textContent = point
          ? ("(" + Math.round(point.x) + ", " + Math.round(point.y) + ")")
          : "no known position yet";
      }
      if (followBtn) followBtn.hidden = followingPlayer === name;
      if (unfollowBtn) unfollowBtn.hidden = followingPlayer !== name;

      menu.hidden = false;
      var canvasRect = canvas.getBoundingClientRect();
      var x = clientX - canvasRect.left;
      var y = clientY - canvasRect.top;
      var maxX = canvasRect.width - menu.offsetWidth - 8;
      var maxY = canvasRect.height - menu.offsetHeight - 8;
      menu.style.left = Math.max(8, Math.min(maxX, x)) + "px";
      menu.style.top = Math.max(8, Math.min(maxY, y)) + "px";
    }

    function playerFromEvent(ev) {
      var dot = ev.target.closest(".map-dot");
      if (dot) return dot.dataset.player;
      var bubble = list ? ev.target.closest("[data-player]") : null;
      if (bubble && list.contains(bubble)) return bubble.dataset.player;
      return null;
    }

    document.addEventListener("contextmenu", function (ev) {
      var name = playerFromEvent(ev);
      if (!name) { closeMenu(); return; }
      ev.preventDefault();
      openMenuFor(name, ev.clientX, ev.clientY);
    });

    document.addEventListener("click", function (ev) {
      if (menu.hidden || menu.contains(ev.target)) return;
      closeMenu();
    });
    document.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape") closeMenu();
    });

    menu.addEventListener("click", function (ev) {
      var btn = ev.target.closest("button[data-action]");
      if (!btn || !menuPlayer) return;
      var action = btn.dataset.action;
      var player = menuPlayer;

      if (action === "follow") { startFollowing(player); closeMenu(); return; }
      if (action === "unfollow") { stopFollowing(); closeMenu(); return; }
      if (action === "teleport-to") { showTeleportList(player); return; }
      if (action === "teleport-back") { showMainView(); return; }

      if (action === "teleport-target") {
        var target = btn.dataset.targetPlayer;
        closeMenu();
        postJson(adminEndpoint("teleport"), { username: player, to_username: target })
          .then(function (data) { showMapActionToast(data.message || ("Teleported " + player + " to " + target + "."), false); })
          .catch(function (e) { showMapActionToast("Teleport failed: " + e.message, true); });
        return;
      }

      var actionPath = PLAYER_ACTION_PATHS[action];
      if (!actionPath) return;
      var endpoint = adminEndpoint(actionPath);
      var label = PLAYER_ACTION_LABELS[action] || action;
      var confirmMsg = btn.dataset.confirm ? btn.dataset.confirm.replace("{player}", player) : null;
      closeMenu();
      if (confirmMsg && !window.confirm(confirmMsg)) return;
      postJson(endpoint, { username: player })
        .then(function (data) { showMapActionToast(data.message || (label + " succeeded for " + player), false); })
        .catch(function (e) { showMapActionToast(label + " failed for " + player + ": " + e.message, true); });
    });
  }

  function renderMapPositions(data) {
    var svg = document.getElementById("map-svg");
    if (!svg || !document.getElementById("map-dots")) return;

    var players = data.players || [];
    var originX = data.origin_x || 0;
    var originY = data.origin_y || 0;
    var scale = data.image_scale || 1;
    var fullW = data.image_w || 1400;
    var fullH = data.image_h || 1386;

    var offMapIndex = 0;
    var points = players.map(function (p) {
      var onMap = p.on_map !== false;
      var pos = onMap
        ? { px: (p.x - originX) / scale, py: (p.y - originY) / scale }
        : offMapSlotPosition(offMapIndex++);
      return {
        name: p.name,
        seconds_ago: p.seconds_ago,
        onMap: onMap,
        x: p.x,
        y: p.y,
        px: pos.px,
        py: pos.py,
      };
    });

    var displayPoints = spreadOverlaps(points);
    lastMapPoints = displayPoints;
    drawDots(displayPoints);
    updateOffMapZoneVisibility(points.some(function (p) { return !p.onMap; }));

    mapFullW = fullW;
    mapFullH = fullH;
    if (!manualViewActive) {
      var onMapPoints = points.filter(function (p) { return p.onMap; });
      var box = computeMapViewBox(onMapPoints, fullW, fullH);
      svg.setAttribute("viewBox", box.join(" "));
      updateZoomButtonState();
    } else if (followingPlayer) {
      recenterOnFollowedPlayer();
    }
  }

  function wireMapZoom() {
    var svg = document.getElementById("map-svg");
    var canvas = document.getElementById("map-canvas");
    var hint = document.getElementById("map-zoom-hint");
    var zoomInBtn = document.getElementById("map-zoom-in-btn");
    var zoomOutBtn = document.getElementById("map-zoom-out-btn");
    if (!svg || !canvas) return;

    var HINT_HIDE_DELAY_MS = 1400;

    function zoomBy(factor, centerX, centerY) {
      stopFollowing();
      var box = svg.viewBox.baseVal;
      var newW = box.width * factor;
      var newH = box.height * factor;

      var minH = MIN_ZOOM_W * (mapFullH / mapFullW);
      if (newW < MIN_ZOOM_W) { newW = MIN_ZOOM_W; newH = minH; }
      if (newW > mapFullW) { newW = mapFullW; newH = mapFullH; }

      var newX = centerX - (centerX - box.x) * (newW / box.width);
      var newY = centerY - (centerY - box.y) * (newH / box.height);
      newX = Math.max(0, Math.min(mapFullW - newW, newX));
      newY = Math.max(0, Math.min(mapFullH - newH, newY));

      svg.setAttribute("viewBox", [newX, newY, newW, newH].join(" "));
      manualViewActive = true;
      updateZoomButtonState();
    }

    function svgPointFromClient(clientX, clientY) {
      var ctm = svg.getScreenCTM();
      if (!ctm) return null;
      var pt = svg.createSVGPoint();
      pt.x = clientX;
      pt.y = clientY;
      return pt.matrixTransform(ctm.inverse());
    }

    var hintTimer = null;
    function flashZoomHint() {
      if (!hint) return;
      hint.classList.add("map-zoom-hint-visible");
      clearTimeout(hintTimer);
      hintTimer = setTimeout(function () {
        hint.classList.remove("map-zoom-hint-visible");
      }, HINT_HIDE_DELAY_MS);
    }

    canvas.addEventListener("wheel", function (ev) {
      if (!ev.ctrlKey) { flashZoomHint(); return; }
      ev.preventDefault();
      var svgPt = svgPointFromClient(ev.clientX, ev.clientY);
      if (!svgPt) return;
      zoomBy(ev.deltaY < 0 ? 0.9 : 1.1, svgPt.x, svgPt.y);
    }, { passive: false });

    canvas.addEventListener("dblclick", function (ev) {
      if (ev.target.closest(".map-canvas-controls, .map-zoom-controls")) return;
      ev.preventDefault();
      var svgPt = svgPointFromClient(ev.clientX, ev.clientY);
      if (!svgPt) return;
      zoomBy(0.5, svgPt.x, svgPt.y);
    });

    function zoomAroundCenter(factor) {
      var box = svg.viewBox.baseVal;
      zoomBy(factor, box.x + box.width / 2, box.y + box.height / 2);
    }
    if (zoomInBtn) zoomInBtn.addEventListener("click", function () { zoomAroundCenter(0.7); });
    if (zoomOutBtn) zoomOutBtn.addEventListener("click", function () { zoomAroundCenter(1 / 0.7); });

    updateZoomButtonState();
  }

  function wireMapPan() {
    var svg = document.getElementById("map-svg");
    var canvas = document.getElementById("map-canvas");
    if (!svg || !canvas) return;

    var dragging = false;
    var lastX = 0, lastY = 0;

    function panBy(dxScreen, dyScreen) {
      var ctm = svg.getScreenCTM();
      if (!ctm || !ctm.a || !ctm.d) return;
      stopFollowing();
      var box = svg.viewBox.baseVal;
      var newX = box.x - dxScreen / ctm.a;
      var newY = box.y - dyScreen / ctm.d;
      newX = Math.max(0, Math.min(mapFullW - box.width, newX));
      newY = Math.max(0, Math.min(mapFullH - box.height, newY));
      svg.setAttribute("viewBox", [newX, newY, box.width, box.height].join(" "));
      manualViewActive = true;
    }

    function start(x, y) {
      dragging = true;
      lastX = x;
      lastY = y;
      canvas.classList.add("map-dragging");
    }
    function move(x, y) {
      if (!dragging) return;
      panBy(x - lastX, y - lastY);
      lastX = x;
      lastY = y;
    }
    function end() {
      if (!dragging) return;
      dragging = false;
      canvas.classList.remove("map-dragging");
    }

    canvas.addEventListener("mousedown", function (ev) {
      if (ev.button !== 0) return;
      start(ev.clientX, ev.clientY);
    });
    window.addEventListener("mousemove", function (ev) {
      if (!dragging) return;
      ev.preventDefault();
      move(ev.clientX, ev.clientY);
    });
    window.addEventListener("mouseup", end);

    canvas.addEventListener("touchstart", function (ev) {
      if (ev.touches.length !== 1) return;
      start(ev.touches[0].clientX, ev.touches[0].clientY);
    }, { passive: true });
    canvas.addEventListener("touchmove", function (ev) {
      if (!dragging || ev.touches.length !== 1) return;
      ev.preventDefault();
      move(ev.touches[0].clientX, ev.touches[0].clientY);
    }, { passive: false });
    canvas.addEventListener("touchend", end);
    canvas.addEventListener("touchcancel", end);
  }

  function pollMapPositions() {
    var view = document.getElementById("map-view");
    if (!view) return;
    var url = view.dataset.pollUrl;
    var interval = parseInt(view.dataset.pollInterval, 10) || 10000;

    function tick() {
      fetch(url, { credentials: "same-origin" })
        .then(function (r) { return r.json(); })
        .then(renderMapPositions)
        .catch(function () {});
    }
    tick();
    setInterval(tick, interval);
  }

  function fmtChatTime(iso) {
    if (!iso) return "";
    var d = new Date(iso);
    return d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
  }

  function renderChat(data) {
    var log = document.getElementById("chat-log");
    if (!log) return;
    var wasAtBottom = log.scrollTop + log.clientHeight >= log.scrollHeight - 20;

    var messages = data.messages || [];
    log.innerHTML = "";
    if (messages.length === 0) {
      log.textContent = "(no recent chat)";
    } else {
      messages.forEach(function (m) {
        var line = document.createElement("div");
        line.className = "chat-line" + (m.author ? "" : " chat-server");
        var author = document.createElement("span");
        author.className = "chat-author";
        author.textContent = m.author ? m.author : "[Server]";
        if (m.author) {
          author.classList.add("chat-author-link");
          author.dataset.player = m.author;
        }
        var text = document.createElement("span");
        text.textContent = m.text;
        var time = document.createElement("span");
        time.className = "chat-time";
        time.textContent = fmtChatTime(m.at);
        line.appendChild(author);
        line.appendChild(text);
        line.appendChild(time);
        log.appendChild(line);
      });
    }

    if (wasAtBottom) log.scrollTop = log.scrollHeight;
  }

  function wireChatPlayerLinks() {
    var log = document.getElementById("chat-log");
    if (!log) return;
    log.addEventListener("click", function (ev) {
      var el = ev.target.closest(".chat-author-link");
      if (!el) return;
      var name = el.dataset.player;
      if (jumpToPlayer(name)) {
        pingPlayer(name);
      } else {
        showMapActionToast(name + " has no known position on the map right now.", true);
      }
    });
  }

  function pollChat() {
    var panel = document.getElementById("chat-panel");
    if (!panel) return;
    var url = panel.dataset.pollUrl;
    var interval = parseInt(panel.dataset.pollInterval, 10) || 7000;

    function tick() {
      fetch(url, { credentials: "same-origin" })
        .then(function (r) { return r.json(); })
        .then(renderChat)
        .catch(function () {});
    }
    tick();
    setInterval(tick, interval);
  }

  function wireLeftColumnHeightSync() {
    var left = document.querySelector(".col-left");
    var middle = document.querySelector(".col-middle");
    if (!left || !middle) return;

    var desktop = window.matchMedia("(min-width: 901px)");

    var mapCollapse = document.getElementById("map-collapse");

    function sync() {
      if (!desktop.matches || (mapCollapse && !mapCollapse.open)) {
        left.style.maxHeight = "";
        left.style.overflowY = "";
        return;
      }
      var height = middle.getBoundingClientRect().height;
      left.style.maxHeight = height + "px";
      left.style.overflowY = "auto";
    }

    new ResizeObserver(sync).observe(middle);
    sync();
  }

  function wireAlwaysOpenSections() {
    document.querySelectorAll("details.collapsible-always").forEach(function (d) {
      d.addEventListener("toggle", function () {
        if (!d.open) d.open = true;
      });
    });
  }

  function wireMapCollapse() {
    var details = document.getElementById("map-collapse");
    if (!details) return;
    var KEY = "admin-map-collapsed";
    try {
      if (localStorage.getItem(KEY) === "1") details.open = false;
    } catch (e) { }
    details.addEventListener("toggle", function () {
      try {
        localStorage.setItem(KEY, details.open ? "0" : "1");
      } catch (e) { }
    });
  }

  function wireMapFullscreen() {
    var btn = document.getElementById("map-fullscreen-btn");
    var view = document.getElementById("map-view");
    if (!btn || !view) return;

    function current() {
      return document.fullscreenElement || document.webkitFullscreenElement;
    }

    function updateLabel() {
      btn.textContent = current() === view ? "⛶ Exit Fullscreen" : "⛶ Fullscreen";
    }

    btn.addEventListener("click", function () {
      if (current() === view) {
        var exit = document.exitFullscreen || document.webkitExitFullscreen;
        if (exit) exit.call(document);
      } else {
        var request = view.requestFullscreen || view.webkitRequestFullscreen;
        if (request) request.call(view);
      }
    });

    document.addEventListener("fullscreenchange", updateLabel);
    document.addEventListener("webkitfullscreenchange", updateLabel);
  }

  function wireMapChatDock() {
    var view = document.getElementById("map-view");
    var panel = document.getElementById("chat-panel");
    var toggleBtn = document.getElementById("map-chat-toggle-btn");
    if (!view || !panel || !toggleBtn) return;

    var chatHomeParent = panel.parentNode;
    var chatHomeNext = panel.nextSibling;
    var chatVisible = true;

    function current() {
      return document.fullscreenElement || document.webkitFullscreenElement;
    }

    function updateToggleLabel() {
      toggleBtn.textContent = chatVisible ? "💬 Hide Chat" : "💬 Show Chat";
    }

    toggleBtn.addEventListener("click", function () {
      chatVisible = !chatVisible;
      panel.hidden = !chatVisible;
      updateToggleLabel();
    });

    function onFullscreenChange() {
      if (current() === view) {
        view.appendChild(panel);
        panel.hidden = !chatVisible;
        updateToggleLabel();
      } else if (panel.parentNode === view) {
        chatHomeParent.insertBefore(panel, chatHomeNext);
        panel.hidden = true;
      }
    }

    document.addEventListener("fullscreenchange", onFullscreenChange);
    document.addEventListener("webkitfullscreenchange", onFullscreenChange);
  }

  function csrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.content : "";
  }

  function worldSlug() {
    return document.body.dataset.worldSlug || "";
  }

  function adminEndpoint(path) {
    return "/api/" + worldSlug() + "/admin/" + path;
  }

  var messageTimer = null;

  function showMessage(text, isError) {
    var el = document.getElementById("admin-message");
    if (!el) return;
    el.textContent = text;
    el.className = "admin-toast " + (isError ? "error" : "notice");
    el.hidden = false;
    el.onclick = function () { el.hidden = true; };
    clearTimeout(messageTimer);
    if (!isError) messageTimer = setTimeout(function () { el.hidden = true; }, 5000);
  }

  function postJson(endpoint, payload) {
    return fetch(endpoint, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrfToken(),
      },
      body: JSON.stringify(payload || {}),
    }).then(function (r) {
      return r.json().then(function (data) {
        if (!r.ok) throw new Error(data.detail || data.output || ("request failed (" + r.status + ")"));
        return data;
      });
    });
  }

  function wireActionButtons() {
    document.querySelectorAll(".admin-action").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var confirmMsg = btn.dataset.confirm;
        if (confirmMsg && !window.confirm(confirmMsg)) return;
        btn.disabled = true;
        postJson(btn.dataset.endpoint, {})
          .then(function (data) { showMessage(data.message || "Done.", false); })
          .catch(function (e) { showMessage(e.message, true); })
          .finally(function () { btn.disabled = false; });
      });
    });
  }

  function formToPayload(form) {
    var data = new FormData(form);
    var payload = {};
    for (var pair of data.entries()) {
      var key = pair[0], value = pair[1];
      if (form.querySelector('input[name="' + key + '"][type="checkbox"]')) {
        payload[key] = form.querySelector('input[name="' + key + '"]').checked;
      } else {
        payload[key] = value;
      }
    }
    return payload;
  }

  function wireForms() {
    document.querySelectorAll(".admin-form").forEach(function (form) {
      form.addEventListener("submit", function (ev) {
        ev.preventDefault();
        var endpoint = form.dataset.endpoint;
        var payload = formToPayload(form);
        var submitBtn = form.querySelector("button[type=submit]");
        if (submitBtn) submitBtn.disabled = true;

        postJson(endpoint, payload)
          .then(function (data) {
            showMessage(data.message || (data.output ? data.output : "Done."), false);
            form.reset();
          })
          .catch(function (e) { showMessage(e.message, true); })
          .finally(function () { if (submitBtn) submitBtn.disabled = false; });
      });
    });
  }

  function wireContentEditor() {
    var select = document.getElementById("content-editor-select");
    if (!select) return;

    var mdBlock = document.getElementById("content-editor-markdown");
    var settingsBlock = document.getElementById("content-editor-settings");
    var joinBlock = document.getElementById("content-editor-join");
    var textarea = document.getElementById("content-editor-textarea");
    var overriddenNote = document.getElementById("content-editor-overridden");
    var titleInput = document.getElementById("content-editor-title");
    var subtitleTextInput = document.getElementById("content-editor-subtitle-text");
    var subtitleUrlInput = document.getElementById("content-editor-subtitle-url");
    var joinTitleInput = document.getElementById("content-editor-join-title");
    var saveBtn = document.getElementById("content-editor-save");
    var revertBtn = document.getElementById("content-editor-revert");
    var sectionsBlock = document.getElementById("content-editor-sections");
    var SECTION_KEYS = ["section_join", "section_news", "section_lore"];

    function isSettings() { return select.value === "settings"; }
    function isJoin() { return select.value === "join_title"; }
    function isSections() { return select.value === "sections"; }

    function loadCurrent() {
      mdBlock.hidden = isSettings() || isJoin() || isSections();
      settingsBlock.hidden = !isSettings();
      joinBlock.hidden = !isJoin();
      if (sectionsBlock) sectionsBlock.hidden = !isSections();
      revertBtn.hidden = isSettings() || isSections();

      if (isSections()) {
        fetch("/api/admin/settings", { credentials: "same-origin" })
          .then(function (r) { return r.json(); })
          .then(function (data) {
            SECTION_KEYS.forEach(function (key) {
              var el = document.getElementById("content-editor-" + key);
              if (el && data[key]) el.value = data[key];
            });
          })
          .catch(function () { showMessage("Could not load current settings.", true); });
      } else if (isSettings()) {
        fetch("/api/admin/settings", { credentials: "same-origin" })
          .then(function (r) { return r.json(); })
          .then(function (data) {
            titleInput.value = data.brand_title || "";
            subtitleTextInput.value = data.brand_subtitle_text || "";
            subtitleUrlInput.value = data.brand_subtitle_url || "";
          })
          .catch(function () { showMessage("Could not load current settings.", true); });
      } else if (isJoin()) {
        fetch(adminEndpoint("content/join_title"), { credentials: "same-origin" })
          .then(function (r) { return r.json(); })
          .then(function (data) {
            joinTitleInput.value = data.text || "";
            overriddenNote.hidden = !data.overridden;
          })
          .catch(function () { showMessage("Could not load current content.", true); });
      } else {
        fetch(adminEndpoint("content/" + select.value), { credentials: "same-origin" })
          .then(function (r) { return r.json(); })
          .then(function (data) {
            textarea.value = data.text || "";
            overriddenNote.hidden = !data.overridden;
          })
          .catch(function () { showMessage("Could not load current content.", true); });
      }
    }

    select.addEventListener("change", loadCurrent);
    loadCurrent();

    saveBtn.addEventListener("click", function () {
      saveBtn.disabled = true;
      var done = function () { saveBtn.disabled = false; };
      if (isSections()) {
        var payload = {};
        SECTION_KEYS.forEach(function (key) {
          var el = document.getElementById("content-editor-" + key);
          if (el) payload[key] = el.value;
        });
        postJson("/api/admin/settings", payload)
          .then(function () { showMessage("Section display saved -- live now.", false); })
          .catch(function (e) { showMessage(e.message, true); })
          .finally(done);
      } else if (isSettings()) {
        postJson("/api/admin/settings", {
          brand_title: titleInput.value,
          brand_subtitle_text: subtitleTextInput.value,
          brand_subtitle_url: subtitleUrlInput.value,
        })
          .then(function () { showMessage("Settings saved.", false); })
          .catch(function (e) { showMessage(e.message, true); })
          .finally(done);
      } else if (isJoin()) {
        postJson(adminEndpoint("content/join_title"), { text: joinTitleInput.value })
          .then(function () {
            showMessage("Saved -- live now.", false);
            overriddenNote.hidden = false;
          })
          .catch(function (e) { showMessage(e.message, true); })
          .finally(done);
      } else {
        postJson(adminEndpoint("content/" + select.value), { text: textarea.value })
          .then(function () {
            showMessage("Saved -- live now.", false);
            overriddenNote.hidden = false;
          })
          .catch(function (e) { showMessage(e.message, true); })
          .finally(done);
      }
    });

    revertBtn.addEventListener("click", function () {
      if (isSettings() || isSections()) return;
      if (!confirm("Revert to the bundled default? Your live edit will be discarded.")) return;
      revertBtn.disabled = true;
      var key = isJoin() ? "join_title" : select.value;
      postJson(adminEndpoint("content/" + key + "/revert"), {})
        .then(function () {
          showMessage("Reverted to default.", false);
          loadCurrent();
        })
        .catch(function (e) { showMessage(e.message, true); })
        .finally(function () { revertBtn.disabled = false; });
    });
  }

  function wireWorldsEditor() {
    var list = document.getElementById("worlds-list");
    if (!list) return;

    var addLabel = document.getElementById("worlds-add-label");
    var addColor = document.getElementById("worlds-add-color");
    var addBtn = document.getElementById("worlds-add-btn");
    var saveBtn = document.getElementById("worlds-save-btn");

    var COLOR_NAMES = { good: "Green", accent: "Blue", purple: "Purple", warn: "Orange", bad: "Red" };
    var state = [];

    function slugify(label) {
      var s = label.toLowerCase().trim().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
      return s.slice(0, 40) || "world";
    }

    function uniqueSlug(base) {
      var slug = base, n = 2;
      var existing = state.map(function (w) { return w.slug; });
      while (existing.indexOf(slug) !== -1) {
        slug = (base + "-" + n).slice(0, 40);
        n++;
      }
      return slug;
    }

    function colorOptions(selected) {
      return Object.keys(COLOR_NAMES).map(function (key) {
        return '<option value="' + key + '"' + (key === selected ? " selected" : "") + ">" + COLOR_NAMES[key] + "</option>";
      }).join("");
    }

    function render() {
      list.innerHTML = "";
      state.forEach(function (world, i) {
        var row = document.createElement("div");
        row.className = "worlds-row";
        row.innerHTML =
          '<input type="text" class="worlds-row-label" maxlength="60" value="' + world.label.replace(/"/g, "&quot;") + '">' +
          '<select class="worlds-row-color">' + colorOptions(world.color) + "</select>" +
          '<input type="text" class="worlds-row-image" placeholder="logo filename (optional)" maxlength="200" value="' + (world.image || "").replace(/"/g, "&quot;") + '">' +
          '<span class="worlds-row-slug">/world/' + world.slug + (world.primary ? ' <span class="worlds-row-badge">Live</span>' : "") + "</span>" +
          '<button type="button" class="button-secondary worlds-row-up"' + (i === 0 ? " disabled" : "") + ' aria-label="Move up">&uarr;</button>' +
          '<button type="button" class="button-secondary worlds-row-down"' + (i === state.length - 1 ? " disabled" : "") + ' aria-label="Move down">&darr;</button>' +
          '<button type="button" class="button-secondary worlds-row-delete"' + (world.primary ? " disabled" : "") + ' aria-label="Delete">&#x2715;</button>';

        row.querySelector(".worlds-row-label").addEventListener("input", function (e) { world.label = e.target.value; });
        row.querySelector(".worlds-row-color").addEventListener("change", function (e) { world.color = e.target.value; });
        row.querySelector(".worlds-row-image").addEventListener("input", function (e) { world.image = e.target.value; });
        row.querySelector(".worlds-row-up").addEventListener("click", function () {
          if (i === 0) return;
          state.splice(i - 1, 0, state.splice(i, 1)[0]);
          render();
        });
        row.querySelector(".worlds-row-down").addEventListener("click", function () {
          if (i === state.length - 1) return;
          state.splice(i + 1, 0, state.splice(i, 1)[0]);
          render();
        });
        row.querySelector(".worlds-row-delete").addEventListener("click", function () {
          if (world.primary) return;
          state.splice(i, 1);
          render();
        });

        list.appendChild(row);
      });
    }

    fetch("/api/admin/worlds", { credentials: "same-origin" })
      .then(function (r) { return r.json(); })
      .then(function (data) { state = data; render(); })
      .catch(function () { showMessage("Could not load worlds.", true); });

    addBtn.addEventListener("click", function () {
      var label = addLabel.value.trim();
      if (!label) return;
      state.push({ slug: uniqueSlug(slugify(label)), label: label, color: addColor.value, primary: false, image: "" });
      addLabel.value = "";
      render();
    });

    saveBtn.addEventListener("click", function () {
      saveBtn.disabled = true;
      postJson("/api/admin/worlds", { worlds: state })
        .then(function (data) {
          state = data;
          render();
          showMessage("Worlds saved.", false);
        })
        .catch(function (e) { showMessage(e.message, true); })
        .finally(function () { saveBtn.disabled = false; });
    });
  }

  function wireLinksEditor() {
    var list = document.getElementById("links-list");
    if (!list) return;

    var addLabel = document.getElementById("links-add-label");
    var addUrl = document.getElementById("links-add-url");
    var addColor = document.getElementById("links-add-color");
    var addGroup = document.getElementById("links-add-group");
    var addBtn = document.getElementById("links-add-btn");
    var saveBtn = document.getElementById("links-save-btn");

    var COLOR_NAMES = { good: "Green", accent: "Blue", purple: "Purple", warn: "Orange", bad: "Red" };
    var state = [];

    function colorOptions(selected) {
      return Object.keys(COLOR_NAMES).map(function (key) {
        return '<option value="' + key + '"' + (key === selected ? " selected" : "") + ">" + COLOR_NAMES[key] + "</option>";
      }).join("");
    }

    function render() {
      list.innerHTML = "";
      var items = state;
      items.forEach(function (link, i) {
        var row = document.createElement("div");
        row.className = "worlds-row";
        row.innerHTML =
          '<input type="text" class="links-row-label" maxlength="60" placeholder="Label" value="' + link.label.replace(/"/g, "&quot;") + '">' +
          '<input type="text" class="links-row-url" placeholder="https://..." value="' + link.url.replace(/"/g, "&quot;") + '">' +
          '<select class="links-row-color">' + colorOptions(link.color) + "</select>" +
          '<input type="text" class="links-row-group" maxlength="40" placeholder="Group" value="' + link.group.replace(/"/g, "&quot;") + '">' +
          '<input type="text" class="links-row-icon" maxlength="200" placeholder="icon filename (optional)" value="' + (link.icon || "").replace(/"/g, "&quot;") + '">' +
          '<button type="button" class="button-secondary links-row-up"' + (i === 0 ? " disabled" : "") + ' aria-label="Move up">&uarr;</button>' +
          '<button type="button" class="button-secondary links-row-down"' + (i === items.length - 1 ? " disabled" : "") + ' aria-label="Move down">&darr;</button>' +
          '<button type="button" class="button-secondary links-row-delete" aria-label="Delete">&#x2715;</button>';

        row.querySelector(".links-row-label").addEventListener("input", function (e) { link.label = e.target.value; });
        row.querySelector(".links-row-url").addEventListener("input", function (e) { link.url = e.target.value; });
        row.querySelector(".links-row-color").addEventListener("change", function (e) { link.color = e.target.value; });
        row.querySelector(".links-row-group").addEventListener("input", function (e) { link.group = e.target.value; });
        row.querySelector(".links-row-icon").addEventListener("input", function (e) { link.icon = e.target.value; });
        row.querySelector(".links-row-up").addEventListener("click", function () {
          if (i === 0) return;
          items.splice(i - 1, 0, items.splice(i, 1)[0]);
          render();
        });
        row.querySelector(".links-row-down").addEventListener("click", function () {
          if (i === items.length - 1) return;
          items.splice(i + 1, 0, items.splice(i, 1)[0]);
          render();
        });
        row.querySelector(".links-row-delete").addEventListener("click", function () {
          items.splice(i, 1);
          render();
        });

        list.appendChild(row);
      });
    }

    fetch("/api/admin/links", { credentials: "same-origin" })
      .then(function (r) { return r.json(); })
      .then(function (data) { state = data; render(); })
      .catch(function () { showMessage("Could not load links.", true); });

    addBtn.addEventListener("click", function () {
      var label = addLabel.value.trim();
      var url = addUrl.value.trim();
      var group = addGroup.value.trim();
      if (!label || !url || !group) return;
      state.push({ label: label, url: url, color: addColor.value, group: group, icon: "" });
      addLabel.value = "";
      addUrl.value = "";
      addGroup.value = "";
      render();
    });

    saveBtn.addEventListener("click", function () {
      saveBtn.disabled = true;
      postJson("/api/admin/links", { links: state })
        .then(function (data) {
          state = data;
          render();
          showMessage("Links saved.", false);
        })
        .catch(function (e) { showMessage(e.message, true); })
        .finally(function () { saveBtn.disabled = false; });
    });
  }

  function wireCopyFields() {
    document.querySelectorAll(".copy-field-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var target = document.getElementById(btn.dataset.copyTarget);
        if (!target) return;
        var text = target.textContent || "";
        var done = function () {
          var original = btn.textContent;
          btn.textContent = "Copied!";
          setTimeout(function () { btn.textContent = original; }, 1200);
        };
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(text).then(done).catch(function () {});
        }
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    pollStatus();
    pollMapPositions();
    pollChat();
    wireAlwaysOpenSections();
    wireMapCollapse();
    wireLeftColumnHeightSync();
    wireMapFullscreen();
    wireMapChatDock();
    wireMapZoom();
    wireMapPan();
    wirePlayerEasterEgg();
    wirePlayerPing();
    wireMapContextMenu();
    wireChatPlayerLinks();
    wireActionButtons();
    wireForms();
    wireCopyFields();
    wireContentEditor();
    wireWorldsEditor();
    wireLinksEditor();
  });
})();
