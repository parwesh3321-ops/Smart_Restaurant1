"use strict";
let state,
  view,
  chart,
  zone = "all",
  orderFilter = "all",
  menuQuery = "";
const navs = [
  ["overview", "Overview", "layout-dashboard", ["admin"]],
  ["tables", "Live floor map", "armchair", ["admin", "waiter"]],
  ["orders", "Orders", "receipt-text", ["admin", "waiter"]],
  ["kitchen", "Kitchen display", "chef-hat", ["admin", "kitchen"]],
  ["requests", "Waiter requests", "bell-ring", ["admin", "waiter"]],
  ["menu", "Menu management", "utensils", ["admin"]],
  ["payments", "Payments", "wallet", ["admin"]],
  ["reviews", "Guest reviews", "message-square-heart", ["admin"]],
  ["settings", "Settings", "settings-2", ["admin"]],
];
const statuses = ["pending", "preparing", "ready", "served"];
const initialView = () =>
  state.user.role === "kitchen"
    ? "kitchen"
    : state.user.role === "waiter"
      ? "tables"
      : "overview";
function heading(title, description, actions = "") {
  return `<div class="page-heading"><div><span class="eyebrow">EMBER & OLIVE · ${esc(state.user.role.toUpperCase())} WORKSPACE</span><h1>${esc(title)}</h1><p>${esc(description)}</p></div><div class="heading-actions">${actions}</div></div>`;
}
function stat(label, value, note, symbol) {
  return `<article class="stat-card"><div class="stat-label">${label}<span class="stat-icon">${icon(symbol)}</span></div><div class="stat-value">${value}</div><div class="stat-meta">${note}</div></article>`;
}
async function load(refresh = false) {
  try {
    state = await api("/api/staff/bootstrap", "GET", undefined, true);
    $("#live-status").innerHTML = '<span class="dot"></span> Live updates';
    $("#restaurant-label").textContent = state.restaurant.name;
    if (!view) {
      const hash = location.hash.slice(1);
      view = navs.some((n) => n[0] === hash && n[3].includes(state.user.role))
        ? hash
        : initialView();
    }
    if (state.notifications)
      $("#notification-count").textContent =
        state.notifications.filter((n) => !n.read).length || "";
    if (
      !refresh ||
      (!$("#modal").open &&
        !["settings", "menu"].includes(view) &&
        !$("#staff-content").contains(document.activeElement))
    )
      render();
  } catch (error) {
    $("#live-status").textContent = "Connection paused";
    if (error.status === 401) location.href = "/login";
    else if (!refresh)
      $("#staff-content").innerHTML = empty(
        "Workspace unavailable",
        error.message,
      );
  }
}
function render() {
  if (chart) {
    chart.destroy();
    chart = null;
  }
  $("#staff-nav").innerHTML = navs
    .filter((n) => n[3].includes(state.user.role))
    .map(
      ([id, label, symbol]) =>
        `<button class="nav-item ${view === id ? "active" : ""}" data-view="${id}">${icon(symbol)}${label}</button>`,
    )
    .join("");
  $("#breadcrumb").textContent =
    navs.find((n) => n[0] === view)?.[1] || "Workspace";
  const html = {
    overview: overview,
    tables: tablesView,
    orders: ordersView,
    kitchen: kitchenView,
    requests: requestsView,
    menu: menuView,
    payments: paymentsView,
    reviews: reviewsView,
    settings: settingsView,
  }[view]();
  $("#staff-content").innerHTML = html;
  icons();
  if (view === "overview") drawChart();
}
function floorMarkup() {
  const list = state.tables.filter((t) => zone === "all" || t.zone === zone);
  const zones = [...new Set(state.tables.map((t) => t.zone))];
  return `<div class="floor-toolbar"><div class="segmented"><button data-zone="all" class="${zone === "all" ? "active" : ""}">All areas</button>${zones.map((z) => `<button data-zone="${esc(z)}" class="${zone === z ? "active" : ""}">${esc(z)}</button>`).join("")}</div><div class="legend"><span><i class="dot available-color"></i>Available</span><span><i class="dot occupied-color"></i>Occupied</span><span><i class="dot reserved-color"></i>Reserved</span></div></div><div class="floor-stage"><span class="floor-caption">${zone === "all" ? "THE RESTAURANT" : esc(zone.toUpperCase())}</span><div class="floor-grid">${list.map((t) => `<button class="floor-table ${t.status} ${t.capacity <= 2 ? "round" : ""}" data-action="table" data-id="${t.id}" aria-label="Table ${t.number}, ${t.status}, ${t.guests} guests"><span class="chair top"></span><span class="chair bottom"></span>${t.capacity > 2 ? '<span class="chair left"></span><span class="chair right"></span>' : ""}<b>T${String(t.number).padStart(2, "0")}</b><small>${t.status === "occupied" ? `${t.guests} guests` : t.status === "reserved" ? "Reserved" : `${t.capacity} seats`}</small></button>`).join("")}</div><div class="floor-bottom"><span>ENTRANCE ↓</span><span>⊙ KITCHEN & SERVICE</span></div></div><div class="floor-summary">${icon("info")} Select any table to view details, its bill or QR code.</div>`;
}
function overview() {
  const available = state.tables.filter((t) => t.status === "available").length,
    occupied = state.tables.filter((t) => t.status === "occupied").length;
  const active = state.orders.filter((o) => o.status !== "served").slice(0, 4),
    pending = state.requests.filter((r) => r.status !== "completed").length;
  const first = state.user.name.split(" ")[0];
  return (
    heading(
      `A good day to serve, ${first}.`,
      "Here’s what’s happening at your restaurant today.",
      `<span class="date-pill">${icon("calendar-days")}${new Date().toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}</span><button class="btn primary" data-view="tables">${icon("armchair")} Manage tables</button>`,
    ) +
    `<div class="stats-grid">${stat("Today’s revenue", cash(state.stats.daily_revenue), "<strong>Successful demo payments</strong> · today", "indian-rupee")}${stat("Orders today", state.stats.today_orders, `${state.stats.total_orders} orders across all days`, "receipt-text")}${stat("Occupied tables", `${occupied}<span style="font-size:14px;color:#a5ac9b"> / ${state.tables.length}</span>`, `${state.tables.filter((t) => t.status === "reserved").length} tables reserved`, "armchair")}${stat("Available tables", available, "Ready for your next guests", "circle-check")}</div>
  <div class="overview-grid"><section class="panel"><header class="panel-header"><div><h2>Live floor map</h2><p>A little overview of every seat.</p></div><button class="text-btn" data-view="tables">View floor ${icon("arrow-up-right")}</button></header><div class="panel-body">${floorMarkup()}</div></section><section class="panel"><header class="panel-header"><div><h2>Service in motion</h2><p>Fresh from the dining room.</p></div><span class="pill green">LIVE</span></header><div class="panel-body"><div class="activity-list">${active.length ? active.map((o) => `<div class="activity-row"><span class="activity-icon ${o.status === "pending" ? "orange" : ""}">${icon(o.status === "ready" ? "bell-ring" : "utensils")}</span><div><b>Table ${String(o.table_number).padStart(2, "0")} <span class="muted">·</span> #${String(o.id).padStart(4, "0")}</b><p>${o.items.reduce((s, i) => s + i.quantity, 0)} items · ${cash(o.total)}</p>${badge(o.status)}</div><span class="time-ago">${time(o.created_at)}</span></div>`).join("") : empty("All caught up", "New orders will appear here.")}<div class="service-banner">${icon("bell-ring")}<div><b>${pending} waiter request${pending === 1 ? "" : "s"}</b><p>${pending ? "A little help goes a long way." : "Every guest is taken care of."}</p></div><button class="icon-btn" data-view="requests" aria-label="View waiter requests">${icon("arrow-right")}</button></div></div></div></section></div>
  <div class="lower-grid"><section class="panel"><header class="panel-header"><div><h2>A week at a glance</h2><p>Successful payment revenue · last 7 days</p></div><span class="pill green">${cash(state.revenue.reduce((s, d) => s + d.amount, 0))}</span></header><div class="chart-box"><canvas id="revenue-chart" aria-label="Revenue over the last seven days" role="img"></canvas></div></section><section class="panel"><header class="panel-header"><div><h2>The crowd favourites</h2><p>Most ordered, most loved.</p></div><button class="text-btn" data-view="menu">Our menu ${icon("arrow-up-right")}</button></header><div class="panel-body">${state.popular.map((p) => `<div class="popular-row"><img src="/static/images/${esc(state.menu.find((m) => m.name === p.name)?.image || "pasta.jpg")}" alt=""><div><b>${esc(p.name)}</b><p>ALL-TIME ORDERS</p></div><span>${p.quantity} <small class="muted">sold</small></span></div>`).join("") || empty("No orders yet")}</div></section></div>`
  );
}
function drawChart() {
  if (!window.Chart) return;
  chart = new Chart($("#revenue-chart"), {
    type: "bar",
    data: {
      labels: state.revenue.map((r) => r.day),
      datasets: [
        {
          data: state.revenue.map((r) => r.amount / 100),
          backgroundColor: state.revenue.map((_, i) =>
            i === 6 ? "#295b48" : "#dce8d5",
          ),
          borderRadius: 5,
          barThickness: 25,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: (c) => cash(c.raw * 100) } },
      },
      scales: {
        x: {
          grid: { display: false },
          border: { display: false },
          ticks: { font: { size: 9 }, color: "#929b87" },
        },
        y: {
          grid: { color: "#f0f2eb" },
          border: { display: false },
          ticks: {
            font: { size: 8 },
            color: "#a0a893",
            callback: (v) => "₹" + (v >= 1000 ? v / 1000 + "k" : v),
          },
        },
      },
    },
  });
}
function tablesView() {
  const admin = state.user.role === "admin";
  return (
    heading(
      "Every table, in view.",
      "Seat guests, manage reservations and keep the dining room flowing.",
      `<a class="btn secondary" href="/staff/qr-print" target="_blank">${icon("qr-code")} Print QR cards</a>${admin ? '<button class="btn primary" data-action="new-table">+ Add table</button>' : ""}`,
    ) +
    `<section class="panel"><header class="panel-header"><div><h2>Your dining room</h2><p>${state.tables.length} tables · ${state.tables.reduce((s, t) => s + t.capacity, 0)} seats · ${state.tables.reduce((s, t) => s + t.guests, 0)} guests seated</p></div></header><div class="panel-body">${floorMarkup()}</div></section>`
  );
}
function orderButton(o) {
  const next = { pending: "preparing", preparing: "ready", ready: "served" }[
    o.status
  ];
  if (!next) return "";
  if (
    (state.user.role === "waiter" && next !== "served") ||
    (state.user.role === "kitchen" && next === "served")
  )
    return "";
  return `<button class="btn ${next === "ready" ? "primary" : "soft"} small" data-action="order-status" data-id="${o.id}" data-status="${next}">${{ preparing: "Start preparing", ready: "Mark ready", served: "Mark served" }[next]}</button>`;
}
function ordersView() {
  const orders = state.orders.filter(
    (o) => orderFilter === "all" || o.status === orderFilter,
  );
  return (
    heading(
      "Orders, all together.",
      "Track every dish from the first tap to the final plate.",
    ) +
    `<div class="toolbar"><div class="segmented">${["all", ...statuses].map((s) => `<button data-filter="${s}" class="${orderFilter === s ? "active" : ""}">${s[0].toUpperCase() + s.slice(1)}</button>`).join("")}</div><span class="help">All recorded orders</span></div><div class="panel data-scroll"><table class="data-table"><thead><tr><th>Order</th><th>Table / guest</th><th>Items</th><th>Total</th><th>Status</th><th>Next step</th></tr></thead><tbody>${orders.map((o) => `<tr><td><button class="table-action" data-action="order-detail" data-id="${o.id}">#${String(o.id).padStart(4, "0")}</button><small>${dateTime(o.created_at)}</small></td><td>Table ${String(o.table_number).padStart(2, "0")}<small>${esc(o.customer)}</small></td><td>${o.items.reduce((s, i) => s + i.quantity, 0)} dishes</td><td>${cash(o.total)}</td><td>${badge(o.status)}</td><td>${orderButton(o) || '<span class="muted">—</span>'}</td></tr>`).join("")}</tbody></table>${!orders.length ? empty("No orders in this view") : ""}</div>`
  );
}
function kitchenView() {
  return (
    heading(
      "Made with a little care.",
      "Incoming orders refresh every 5 seconds. Prepare, plate, and pass it on.",
      `<span class="pill green">${icon("radio")} LIVE KITCHEN</span>`,
    ) +
    `<div class="kanban">${statuses
      .map((s) => {
        const orders = state.orders
          .filter((o) => o.status === s)
          .slice(0, s === "served" ? 8 : undefined);
        return `<section class="kanban-column"><div class="kanban-heading">${badge(s)}<span>${orders.length}</span></div>${orders.map((o) => `<article class="kitchen-card"><div class="kitchen-card-header">Table ${String(o.table_number).padStart(2, "0")}<small>#${String(o.id).padStart(4, "0")}</small></div><p class="muted">${dateTime(o.created_at)} · ${esc(o.customer)}</p><div class="kitchen-items">${o.items.map((i) => `<p><b>${i.quantity}×</b><span>${esc(i.name)}</span></p>`).join("")}</div>${o.notes ? `<p class="order-note">${esc(o.notes)}</p>` : ""}${orderButton(o) || '<span class="help">' + (s === "ready" ? "Waiting for waiter pickup." : "Delivered to the table.") + "</span>"}</article>`).join("") || '<p class="help" style="text-align:center;padding:30px 0">Nothing here just yet.</p>'}</section>`;
      })
      .join("")}</div>`
  );
}
function requestsView() {
  return (
    heading(
      "A little help, right on time.",
      "Accept guest requests and mark them complete once taken care of.",
    ) +
    `<div class="request-grid">${state.requests.map((r) => `<article class="panel request-card"><div class="request-card-top"><span class="extra-icon" style="margin:0">${icon(r.kind === "water" ? "glass-water" : r.kind === "bill" ? "receipt" : "bell-ring")}</span>${badge(r.status)}</div><h3>Table ${String(r.table_number).padStart(2, "0")}</h3><b style="font-size:12px;text-transform:capitalize">${esc(r.kind)} request</b><p>${esc(r.note || "Our guest would love a little assistance.")}</p><div class="request-card-footer"><small>${dateTime(r.created_at)}</small>${r.status !== "completed" ? `<button class="btn ${r.status === "pending" ? "primary" : "soft"} small" data-action="request-status" data-id="${r.id}" data-status="${r.status === "pending" ? "accepted" : "completed"}">${r.status === "pending" ? "Accept request" : "Complete"}</button>` : icon("check-check")}</div></article>`).join("") || empty("Every guest is taken care of", "New requests will appear here.", "bell-ring")}</div>`
  );
}
function menuView() {
  return (
    heading(
      "Your menu, thoughtfully curated.",
      "Manage dishes, prices and availability. Past orders retain their original prices.",
      `<button class="btn secondary" data-action="categories">Categories</button><button class="btn primary" data-action="edit-item">+ Add dish</button>`,
    ) +
    `<div class="toolbar"><div class="search-field">${icon("search")}<input id="admin-menu-search" aria-label="Search dishes" placeholder="Search your dishes…" value="${esc(menuQuery)}"></div><span class="help">${state.menu.length} dishes on your menu</span></div><div class="menu-admin-grid" id="admin-menu-grid">${menuCards()}</div>`
  );
}
function menuCards() {
  return (
    state.menu
      .filter((m) =>
        (m.name + " " + m.category)
          .toLowerCase()
          .includes(menuQuery.toLowerCase()),
      )
      .map(
        (m) =>
          `<article class="food-card"><div class="food-image"><img src="/static/images/${esc(m.image)}" alt="${esc(m.name)}" loading="lazy"><span class="pill green">${icon(m.vegetarian ? "leaf" : "utensils")}${m.vegetarian ? "Vegetarian" : "Non-vegetarian"}</span>${!m.available ? '<span class="out-label">Currently unavailable</span>' : ""}</div><div class="food-info"><span class="eyebrow">${esc(m.category)}</span><h3>${esc(m.name)}</h3><p>${esc(m.description)}</p><div class="food-bottom"><b>${cash(m.price)}</b><button class="btn soft" data-action="edit-item" data-id="${m.id}">${icon("pencil")} Edit dish</button></div></div></article>`,
      )
      .join("") || empty("No dishes found")
  );
}
function paymentsView() {
  return (
    heading(
      "Every payment, accounted for.",
      "Transaction records are simulated. No real money or payment credentials are used.",
    ) +
    `<div class="notice">Demo ledger · Failed payments do not reduce the remaining balance. All amounts are in INR. Showing all recorded transactions.</div><div class="panel data-scroll"><table class="data-table"><thead><tr><th>Transaction</th><th>Table</th><th>Amount</th><th>Result</th><th>Time</th><th>Bill</th></tr></thead><tbody>${state.payments.map((p) => `<tr><td>${esc(p.reference)}<small>Demo payment</small></td><td>Table ${String(p.table_number).padStart(2, "0")}</td><td>${cash(p.amount)}</td><td>${badge(p.status)}</td><td>${dateTime(p.created_at)}</td><td><a class="table-action" href="/bill/${p.visit_id}" target="_blank">View bill ↗</a></td></tr>`).join("")}</tbody></table>${!state.payments.length ? empty("No transactions yet") : ""}</div>`
  );
}
function reviewsView() {
  return (
    heading(
      "Good food starts with listening.",
      "Guest feedback on the food, the service and everything in between.",
    ) +
    `<div class="review-grid">${state.reviews.map((r) => `<article class="panel review-card"><div class="review-card-header"><span class="avatar">${esc(r.customer[0])}</span><div><b>${esc(r.customer)}</b><small>Table ${r.table_number} · ${dateTime(r.created_at)}</small></div></div><div class="rating-pair"><div><small>FOOD</small><span class="stars">${"★".repeat(r.food_rating)}${"☆".repeat(5 - r.food_rating)}</span></div><div><small>SERVICE</small><span class="stars">${"★".repeat(r.service_rating)}${"☆".repeat(5 - r.service_rating)}</span></div></div><p>${esc(r.comment || "A lovely rating, without a written note.")}</p></article>`).join("") || empty("Your first review is on its way")}</div>`
  );
}
function passwordForm() {
  return `<form class="form-stack" id="password-form"><label>Current password<input name="current_password" type="password" autocomplete="current-password" required maxlength="200"></label><label>New password · at least 10 characters<input name="new_password" type="password" autocomplete="new-password" minlength="10" maxlength="200" required></label><button class="btn primary" type="submit">Update password</button></form>`;
}
function settingsView() {
  const s = state.settings;
  return (
    heading(
      "The details that make it yours.",
      "Manage your restaurant, guest Wi-Fi and table QR destinations.",
    ) +
    `<div class="settings-grid"><section class="panel"><h2>Restaurant details</h2><form id="settings-form" class="form-stack">${[
      ["name", "Restaurant name"],
      ["address", "Address"],
      ["wifi_name", "Guest Wi-Fi name"],
      ["wifi_password", "Guest Wi-Fi password"],
      ["public_base_url", "QR base URL"],
    ]
      .map(
        ([key, label]) =>
          `<label>${label}<input name="${key}" value="${esc(s[key])}" required maxlength="${key === "address" ? 200 : key === "public_base_url" ? 250 : key === "name" ? 100 : 80}"></label>`,
      )
      .join(
        "",
      )}<p class="help">For a phone, use your Mac’s Wi-Fi address, for example http://192.168.1.20:5001. Both devices must use the same Wi-Fi. Restart with HOST=0.0.0.0, then print fresh QR cards.</p><button class="btn primary" type="submit">Save restaurant settings</button></form></section><div><section class="panel"><h2>Account security</h2><p class="help">Change the password for your current ${esc(state.user.role)} account.</p>${passwordForm()}</section><section class="notice" style="margin-top:20px">Tax is fixed at 5% for this demo. Rewards are earned once a table’s bill is paid in full: 1 point for every ₹100 per order. Rewards have no monetary value.</section></div></div>`
  );
}
async function tableModal(id) {
  const t = state.tables.find((t) => t.id === id);
  const admin = state.user.role === "admin";
  modal(
    `Table ${String(t.number).padStart(2, "0")}`,
    `<div class="mini-stats"><div><small>STATUS</small>${badge(t.status)}</div><div><small>SEATED GUESTS</small><b>${t.guests} <span class="muted" style="font-size:14px">/ ${t.capacity}</span></b></div><div><small>BALANCE</small><b>${cash(t.remaining)}</b></div></div><div class="detail-grid"><form class="form-stack" id="table-form" data-id="${t.id}">${admin ? `<div class="form-row"><label>Table number<input name="number" type="number" min="1" max="999" value="${t.number}" required></label><label>Seats<input name="capacity" type="number" min="1" max="20" value="${t.capacity}" required></label></div><label>Zone<input name="zone" maxlength="40" value="${esc(t.zone)}" required></label>` : ""}<label>Status<select name="status">${["available", "occupied", "reserved"].map((s) => `<option ${s === t.status ? "selected" : ""}>${s}</option>`).join("")}</select></label><label>Group size (when seating)<input name="guest_count" type="number" min="1" max="${t.capacity}" value="${t.guests || 1}" required></label><label>Reservation name (if reserved)<input name="reservation_name" maxlength="100" value="${esc(t.reservation_name)}"></label><button type="submit" class="btn primary">Save table</button></form><div class="qr-preview"><img src="/api/tables/${t.id}/qr" alt="Table ${t.number} QR code"><p>Scan to explore the menu</p><a class="btn secondary full" href="${esc(t.menu_path)}" target="_blank">${icon("external-link")} Open digital menu</a><a class="btn soft full" href="/api/tables/${t.id}/qr?download=1">${icon("download")} Download QR</a><p class="help" style="overflow-wrap:anywhere">${esc(t.menu_url)}</p></div></div><div class="modal-actions">${t.visit_id ? `<a class="btn secondary" href="/bill/${t.visit_id}" target="_blank">${icon("receipt")} View bill</a><button class="btn soft" data-action="close-table" data-id="${t.id}">Close dining session</button>` : admin ? `<button class="btn danger" data-action="delete-table" data-id="${t.id}">Archive table</button>` : ""}</div><p class="help" style="margin-top:15px">Close a session only after all dishes are served and its bill is paid. To change a seated group’s size, enter the new group size and save.</p>`,
    true,
  );
}
function itemModal(id) {
  const item = state.menu.find((i) => i.id === id) || {
    name: "",
    description: "",
    price: 0,
    category_id: state.categories[0]?.id,
    image: "pasta.jpg",
    vegetarian: true,
    available: true,
  };
  if (!state.categories.length) {
    toast("Add a category first.", true);
    return;
  }
  modal(
    id ? "Edit your dish" : "Add something delicious",
    `<form class="form-stack" id="item-form" data-id="${id || ""}"><label>Dish name<input name="name" value="${esc(item.name)}" required maxlength="100"></label><label>Description<textarea name="description" required maxlength="500">${esc(item.description)}</textarea></label><div class="form-row"><label>Category<select name="category_id">${state.categories.map((c) => `<option value="${c.id}" ${c.id === item.category_id ? "selected" : ""}>${esc(c.name)}</option>`).join("")}</select></label><label>Price (₹)<input name="price" type="number" min="0.01" max="1000000" step="0.01" value="${item.price ? (item.price / 100).toFixed(2) : ""}" required></label></div><div><div class="photo-label">Choose a food photo</div><div class="image-select">${["pasta", "pizza", "salad", "soup", "curry", "bowl", "cake", "icecream", "coffee", "lemonade", "bread", "grill"].map((n) => `<label class="image-option"><input type="radio" name="image" value="${n}.jpg" ${item.image === n + ".jpg" ? "checked" : ""}><img src="/static/images/${n}.jpg" alt="${n}"><span>${n}</span></label>`).join("")}</div></div><div class="form-row"><label class="check-label"><input name="vegetarian" type="checkbox" ${item.vegetarian ? "checked" : ""}>Vegetarian</label><label class="check-label"><input name="available" type="checkbox" ${item.available ? "checked" : ""}>Available to order</label></div><button class="btn primary" type="submit">Save dish</button>${id ? `<button type="button" class="btn danger" data-action="delete-item" data-id="${id}">Archive dish</button>` : ""}</form>`,
    true,
  );
}
function categoryModal() {
  modal(
    "Menu categories",
    `<div class="category-list">${state.categories.map((c) => `<div class="category-row"><b>${esc(c.name)}</b><button class="icon-btn" data-action="edit-category" data-id="${c.id}" aria-label="Edit ${esc(c.name)}">${icon("pencil")}</button><button class="icon-btn" data-action="delete-category" data-id="${c.id}" aria-label="Delete ${esc(c.name)}">${icon("trash-2")}</button></div>`).join("")}</div><div class="modal-divider"></div><form class="form-stack" id="category-form"><label>New category<input name="name" required maxlength="60" placeholder="For example, Chef’s specials"></label><button class="btn primary" type="submit">Add category</button></form>`,
  );
}
function orderDetail(id) {
  const o = state.orders.find((o) => o.id === id);
  modal(
    `Order #${String(o.id).padStart(4, "0")}`,
    `<p class="help">Table ${o.table_number} · ${esc(o.customer)} · ${dateTime(o.created_at)}</p>${badge(o.status)}${o.items.map((i) => `<div class="list-line"><span>${i.quantity} × ${esc(i.name)}</span><b>${cash(i.quantity * i.unit_price)}</b></div>`).join("")}<div class="list-line"><span>Tax</span><b>${cash(o.tax)}</b></div><div class="list-line"><b>Total</b><b>${cash(o.total)}</b></div>${o.notes ? `<p class="notice">${esc(o.notes)}</p>` : ""}<div class="modal-actions">${orderButton(o)}<a class="btn secondary small" href="/bill/${o.visit_id}" target="_blank">View table bill</a></div>`,
  );
}
function confirmAction(title, message, action, id) {
  modal(
    title,
    `<p class="help">${esc(message)}</p><div class="modal-actions"><button class="btn secondary" data-action="close-modal">Keep it</button><button class="btn danger" data-action="${action}" data-id="${id}">Confirm</button></div>`,
  );
}
document.addEventListener("input", (e) => {
  if (e.target.id === "admin-menu-search") {
    menuQuery = e.target.value;
    $("#admin-menu-grid").innerHTML = menuCards();
    icons();
  }
});
document.addEventListener("click", async (e) => {
  const nav = e.target.closest("[data-view]");
  if (nav) {
    view = nav.dataset.view;
    location.hash = view;
    $("#sidebar").classList.remove("open");
    render();
    return;
  }
  const z = e.target.closest("[data-zone]");
  if (z) {
    zone = z.dataset.zone;
    render();
    return;
  }
  const filter = e.target.closest("[data-filter]");
  if (filter) {
    orderFilter = filter.dataset.filter;
    render();
    return;
  }
  const b = e.target.closest("[data-action]");
  if (!b) return;
  const action = b.dataset.action,
    id = Number(b.dataset.id);
  try {
    await busy(b, async () => {
      if (action === "sidebar") $("#sidebar").classList.toggle("open");
      if (action === "logout") {
        await api("/api/logout", "POST", {});
        location.href = "/login";
      }
      if (action === "refresh") {
        await load();
        toast("Workspace refreshed.");
      }
      if (action === "table") tableModal(id);
      if (action === "new-table")
        modal(
          "Make room for more.",
          `<form class="form-stack" id="new-table-form"><div class="form-row"><label>Table number<input name="number" type="number" min="1" max="999" required></label><label>Seats<input name="capacity" type="number" min="1" max="20" value="4" required></label></div><label>Zone<input name="zone" value="Main dining" maxlength="40" required></label><button class="btn primary" type="submit">Create table & QR</button></form>`,
        );
      if (action === "close-table") {
        await api(`/api/tables/${id}/close`, "POST", {});
        closeModal();
        await load();
        toast("Table is ready for the next guests.");
      }
      if (action === "delete-table")
        confirmAction(
          "Archive this table?",
          "Only available tables can be archived. Historical orders and payments will be kept.",
          "confirm-delete-table",
          id,
        );
      if (action === "confirm-delete-table") {
        await api(`/api/tables/${id}`, "DELETE");
        closeModal();
        await load();
        toast("Table archived.");
      }
      if (action === "order-detail") orderDetail(id);
      if (action === "order-status") {
        await api(`/api/orders/${id}/status`, "PATCH", {
          status: b.dataset.status,
        });
        closeModal();
        await load();
        toast("Order status updated.");
      }
      if (action === "request-status") {
        await api(`/api/requests/${id}`, "PATCH", { status: b.dataset.status });
        await load();
        toast("Request updated.");
      }
      if (action === "edit-item") itemModal(id);
      if (action === "delete-item")
        confirmAction(
          "Archive this dish?",
          "This dish will leave the menu. Past orders and prices are retained.",
          "confirm-delete-item",
          id,
        );
      if (action === "confirm-delete-item") {
        await api(`/api/menu/${id}`, "DELETE");
        closeModal();
        await load();
        toast("Dish archived.");
      }
      if (action === "categories") categoryModal();
      if (action === "edit-category") {
        const c = state.categories.find((c) => c.id === id);
        modal(
          "Rename category",
          `<form id="category-form" data-id="${id}" class="form-stack"><label>Category name<input name="name" value="${esc(c.name)}" required maxlength="60"></label><button class="btn primary" type="submit">Save category</button></form>`,
        );
      }
      if (action === "delete-category")
        confirmAction(
          "Delete category?",
          "Only categories with no current or archived items can be deleted.",
          "confirm-delete-category",
          id,
        );
      if (action === "confirm-delete-category") {
        await api(`/api/categories/${id}`, "DELETE");
        await load();
        categoryModal();
        toast("Category deleted.");
      }
      if (action === "notifications")
        modal(
          "Around the restaurant",
          `${state.notifications.map((n) => `<div class="list-line"><span>${esc(n.message)}<small>${dateTime(n.created_at)}</small></span>${!n.read ? '<span class="dot available-color"></span>' : ""}</div>`).join("") || empty("All quiet for now")}<div class="modal-actions"><button class="btn soft" data-action="read-notifications">Mark all as read</button></div>`,
        );
      if (action === "read-notifications") {
        await api("/api/notifications/read", "POST", {});
        closeModal();
        await load();
      }
      if (action === "account")
        modal(
          "Your account",
          `<p class="help">${esc(state.user.name)} · ${esc(state.user.role)}</p>${passwordForm()}`,
        );
    });
  } catch (_) {}
});
document.addEventListener("submit", async (e) => {
  const form = e.target;
  if (
    ![
      "table-form",
      "new-table-form",
      "item-form",
      "category-form",
      "settings-form",
      "password-form",
    ].includes(form.id)
  )
    return;
  e.preventDefault();
  await busy($('button[type="submit"]', form), async () => {
    try {
      let data = Object.fromEntries(new FormData(form)),
        id = Number(form.dataset.id);
      if (form.id === "new-table-form") {
        data.number = Number(data.number);
        data.capacity = Number(data.capacity);
        await api("/api/tables", "POST", data);
      }
      if (form.id === "table-form") {
        if (data.number) data.number = Number(data.number);
        if (data.capacity) data.capacity = Number(data.capacity);
        data.guest_count = Number(data.guest_count);
        if (data.status !== "occupied") delete data.guest_count;
        await api(`/api/tables/${id}`, "PATCH", data);
      }
      if (form.id === "item-form") {
        data.category_id = Number(data.category_id);
        data.vegetarian = form.elements.vegetarian.checked;
        data.available = form.elements.available.checked;
        await api(
          id ? `/api/menu/${id}` : "/api/menu",
          id ? "PUT" : "POST",
          data,
        );
      }
      if (form.id === "category-form")
        await api(
          id ? `/api/categories/${id}` : "/api/categories",
          id ? "PATCH" : "POST",
          data,
        );
      if (form.id === "settings-form") await api("/api/settings", "PUT", data);
      if (form.id === "password-form") await api("/api/password", "POST", data);
      closeModal();
      await load();
      toast("Changes saved.");
    } catch (_) {}
  });
});
window.addEventListener("hashchange", () => {
  const hash = location.hash.slice(1);
  if (
    state &&
    navs.some((n) => n[0] === hash && n[3].includes(state.user.role)) &&
    hash !== view
  ) {
    view = hash;
    render();
  }
});
load();
setInterval(() => {
  if (!document.hidden) load(true);
}, 5000);
