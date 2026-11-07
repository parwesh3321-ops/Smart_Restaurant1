"use strict";
const tableToken = $("#customer-app").dataset.token;
let menu,
  diner = null,
  guestView = "menu",
  category = "all",
  query = "",
  cart = {},
  orderKey = null,
  paymentKey = null;
try {
  const saved = JSON.parse(
    localStorage.getItem("ember-cart-" + tableToken) || "{}",
  );
  if (saved && typeof saved === "object") cart = saved;
} catch (_) {}
const itemById = (id) => menu.items.find((i) => i.id === Number(id));
function cartLines() {
  return Object.entries(cart)
    .filter(
      ([id, qty]) =>
        itemById(id) && Number.isInteger(qty) && qty > 0 && qty <= 50,
    )
    .map(([id, qty]) => ({ ...itemById(id), quantity: qty }));
}
function cartTotals() {
  const subtotal = cartLines().reduce((s, i) => s + i.price * i.quantity, 0),
    tax = Math.floor((subtotal * menu.restaurant.tax_bps + 5000) / 10000);
  return { subtotal, tax, total: subtotal + tax };
}
function saveCart() {
  try {
    localStorage.setItem("ember-cart-" + tableToken, JSON.stringify(cart));
  } catch (_) {}
  updateCartBar();
}
function updateCartBar() {
  const lines = cartLines(),
    count = lines.reduce((s, i) => s + i.quantity, 0);
  $("#cart-float").hidden = !count;
  $("#cart-float .cart-count").textContent = count;
  $("#cart-float .cart-total").textContent = cash(cartTotals().total);
}
async function refreshState(renderPage = true) {
  try {
    const result = await api("/api/guest/state", "GET", undefined, true);
    diner = result.table.token === tableToken ? result : null;
  } catch (error) {
    if (error.status === 401) diner = null;
    else throw error;
  }
  $("#guest-identity").textContent = diner
    ? `Hello, ${diner.customer.name} · ${diner.customer.points} points`
    : "Make yourself at home";
  $("#guest-start-button").hidden = Boolean(diner && !diner.bill.closed);
  if (renderPage) renderGuest();
}
async function init() {
  try {
    menu = await api("/api/menu/" + tableToken);
    await refreshState();
    updateCartBar();
  } catch (error) {
    $("#guest-content").innerHTML = empty(
      "We couldn’t load your menu",
      error.message,
    );
  }
}
function renderGuest() {
  $$(".guest-nav [data-view]").forEach((n) =>
    n.classList.toggle("active", n.dataset.view === guestView),
  );
  $("#guest-content").innerHTML = {
    menu: menuView,
    orders: ordersView,
    bill: billView,
    more: moreView,
  }[guestView]();
  icons();
}
function joinPrompt() {
  return `<section class="panel bill-panel">${empty("Let’s get you settled", "Join this table to order, call your waiter and share the bill.", "armchair")}<button class="btn primary full" data-action="join">Join table ${menu.table.number}</button></section>`;
}
function menuView() {
  return `${diner?.bill.closed ? '<div class="notice green">Thank you for dining with us! Your last session has closed. <button class="text-btn" data-action="join">Start a new dining session →</button></div>' : ""}<div class="menu-heading"><div><h2>A little of what you love.</h2><p>Fresh flavours, something for everyone.</p></div><div class="search-field">${icon("search")}<input id="menu-search" aria-label="Search the menu" placeholder="Find your favourite…" value="${esc(query)}"></div></div><div class="category-tabs"><button data-category="all" class="${category === "all" ? "active" : ""}">All dishes</button>${menu.categories.map((c) => `<button data-category="${c.id}" class="${category === String(c.id) ? "active" : ""}">${esc(c.name)}</button>`).join("")}</div><div class="guest-food-grid" id="food-grid">${foodCards()}</div>`;
}
function foodCards() {
  const items = menu.items.filter(
    (i) =>
      (category === "all" || String(i.category_id) === category) &&
      (i.name + " " + i.description)
        .toLowerCase()
        .includes(query.toLowerCase()),
  );
  return (
    items
      .map(
        (i) =>
          `<article class="food-card"><div class="food-image"><img src="/static/images/${esc(i.image)}" alt="${esc(i.name)}" loading="lazy"><span class="pill green">${icon(i.vegetarian ? "leaf" : "utensils")}${i.vegetarian ? "VEGETARIAN" : "NON-VEGETARIAN"}</span>${!i.available ? '<div class="out-label">Back soon</div>' : ""}</div><div class="food-info"><span class="eyebrow">${esc(i.category)}</span><h3>${esc(i.name)}</h3><p>${esc(i.description)}</p><div class="food-bottom"><b>${cash(i.price)}</b>${i.available ? (cart[i.id] ? stepper(i.id, cart[i.id]) : `<button class="btn soft" data-action="add" data-id="${i.id}">Add ${icon("plus")}</button>`) : '<span class="help">Unavailable</span>'}</div></div></article>`,
      )
      .join("") ||
    empty("No dishes found", "Try another search or category.", "search")
  );
}
function stepper(id, quantity) {
  return `<div class="quantity-stepper"><button data-action="remove" data-id="${id}" aria-label="Remove one ${esc(itemById(id).name)}">−</button><span>${quantity}</span><button data-action="add" data-id="${id}" aria-label="Add one ${esc(itemById(id).name)}" ${quantity >= 50 ? "disabled" : ""}>+</button></div>`;
}
function cartModal() {
  const lines = cartLines(),
    total = cartTotals();
  modal(
    "Something good is on the way.",
    `${lines.length ? lines.map((i) => `<div class="cart-row"><img src="/static/images/${esc(i.image)}" alt=""><div class="cart-item-copy"><h3>${esc(i.name)}</h3><small>${cash(i.price * i.quantity)}</small></div>${stepper(i.id, i.quantity)}</div>`).join("") + `<div class="bill-summary"><div><span>Subtotal</span><b>${cash(total.subtotal)}</b></div><div><span>Tax (5% demo)</span><b>${cash(total.tax)}</b></div><div class="total"><span>Your total</span><b>${cash(total.total)}</b></div></div><form id="order-form" class="form-stack"><label>Anything we should know?<textarea name="notes" maxlength="300" placeholder="For example: mild spice, please."></textarea></label><p class="help">Tell your waiter about any allergies. Your order joins the shared bill for table ${menu.table.number}.</p><button type="submit" class="btn primary large">${icon("utensils")} ${diner && !diner.bill.closed ? "Place order" : "Join table & continue"}</button></form>` : empty("Your cart is waiting", "Add a little something from the menu.", "shopping-bag")}`,
  );
}
function joinModal(returnToCart = false) {
  modal(
    "Make yourself at home.",
    `<p class="help">You’re at table ${menu.table.number}. Everyone scanning this table’s QR shares one dining bill.</p><form id="join-form" class="form-stack" data-cart="${returnToCart ? "1" : "0"}"><label>Your name<input name="name" value="${esc(diner?.customer.name || "")}" autocomplete="given-name" maxlength="100" placeholder="What should we call you?" required></label><label>Total people in your group<select name="guest_count">${Array.from({ length: menu.table.capacity }, (_, i) => `<option value="${i + 1}" ${i + 1 === (diner?.table.guests || 2) ? "selected" : ""}>${i + 1} ${i ? "guests" : "guest"}</option>`).join("")}</select></label><p class="help">If your group is already seated, you’ll join their current session. Your group size will stay unchanged.</p><button class="btn primary" type="submit">Join table ${menu.table.number} ${icon("arrow-right")}</button></form>`,
  );
}
function progress(status) {
  const current = ["pending", "preparing", "ready", "served"].indexOf(status);
  return `<div class="order-progress">${["Pending", "Preparing", "Ready", "Served"].map((s, i) => `<span class="progress-step ${i <= current ? "done" : ""}">${s}</span>`).join("")}</div>`;
}
function ordersView() {
  if (!diner) return joinPrompt();
  return `<div class="guest-section-heading"><div><h2>Your table, taken care of.</h2><p>${diner.table.guests} guests · updates every 5 seconds${diner.bill.closed ? " · session closed" : ""}</p></div><button class="btn secondary" data-action="call-waiter">${icon("bell-ring")} Call waiter</button></div>${diner.requests
    .filter((r) => r.status !== "completed")
    .map(
      (r) =>
        `<div class="notice green">${esc(r.kind)} request · ${esc(r.status)}. ${r.status === "accepted" ? "Your waiter is on it." : "We’ve let your waiter know."}</div>`,
    )
    .join(
      "",
    )}${diner.bill.orders.map((o) => `<article class="panel order-card"><div class="order-card-top"><div><h3>Order #${String(o.id).padStart(4, "0")}</h3><small>${esc(o.customer)} · ${dateTime(o.created_at)}</small></div>${badge(o.status)}</div>${o.items.map((i) => `<div class="list-line"><span>${i.quantity} × ${esc(i.name)}</span><b>${cash(i.unit_price * i.quantity)}</b></div>`).join("")}<div class="list-line"><span class="muted">Total with tax</span><b>${cash(o.total)}</b></div>${o.notes ? `<p class="help">Note: ${esc(o.notes)}</p>` : ""}${progress(o.status)}</article>`).join("") || empty("Your first delicious moment awaits", "Pick something from the menu to get started.", "utensils")}`;
}
function billView() {
  if (!diner) return joinPrompt();
  const bill = diner.bill;
  if (!bill.orders.length)
    return empty(
      "Your bill is still a blank page",
      "Once you place an order, we’ll keep everything here.",
      "receipt-text",
    );
  return `<div class="guest-section-heading"><div><h2>The bill, made simple.</h2><p>One table. Many ways to share.</p></div><a class="btn secondary" href="/bill/${bill.visit_id}" target="_blank">${icon("printer")} Final bill</a></div><div class="bill-layout"><section class="panel bill-panel"><h3>Your table’s order</h3>${bill.orders
    .flatMap((o) => o.items)
    .map(
      (i) =>
        `<div class="list-line"><span>${i.quantity} × ${esc(i.name)}</span><b>${cash(i.unit_price * i.quantity)}</b></div>`,
    )
    .join(
      "",
    )}<div class="bill-summary"><div><span>Subtotal</span><b>${cash(bill.subtotal)}</b></div><div><span>Tax (5% demo)</span><b>${cash(bill.tax)}</b></div><div class="total"><span>Table total</span><b>${cash(bill.total)}</b></div><div><span>Paid successfully</span><b>${cash(bill.paid)}</b></div></div><h3 style="font-size:14px">Payment history</h3>${bill.payments.map((p) => `<div class="list-line"><div><b>${cash(p.amount)}</b><small>${esc(p.reference)} · ${time(p.created_at)}</small></div>${badge(p.status)}</div>`).join("") || '<p class="help">No payments made yet.</p>'}</section><section class="panel bill-panel"><div class="balance-banner"><span>REMAINING BALANCE</span><strong>${cash(bill.remaining)}</strong><small>${bill.remaining ? "Split it your way. Pay at your pace." : "All settled. Thank you for dining with us."}</small></div>${bill.remaining && !bill.closed ? `<div class="payment-demo">This is a demo checkout. No real money is processed. Please don’t enter any card or banking details.</div>${!bill.paid && !bill.payments.some((p) => p.split_id) ? `<div class="form-row"><button class="btn secondary" data-action="split-equal">${icon("users")} Split equally</button><button class="btn secondary" data-action="split-custom">${icon("sliders-horizontal")} Custom shares</button></div><p class="help" style="margin-top:13px">Splitting or making a successful payment locks this bill to further orders.</p>` : ""}${bill.splits.length ? bill.splits.map((s, i) => `<div class="share-row"><span class="share-avatar">${i + 1}</span><div><b>${esc(s.label)} · ${cash(s.amount)}</b><small>${cash(s.amount - s.paid)} remaining</small></div>${s.amount > s.paid ? `<button class="btn soft small" data-action="pay" data-id="${s.id}">Pay share</button>` : badge("success")}</div>`).join("") : `<button class="btn primary full large" data-action="pay">Continue to demo payment ${icon("arrow-right")}</button>`}` : `<div class="notice green">Your bill is fully paid. Your loyalty points are now available under Little extras. Staff will close the table after serving all dishes.</div><button class="btn soft full" data-view="more">Leave a little feedback ${icon("heart")}</button>`}</section></div>`;
}
function ratingInput(name) {
  return `<div class="rating-input">${[5, 4, 3, 2, 1].map((n) => `<input type="radio" name="${name}" id="${name}-${n}" value="${n}" ${n === 5 ? "checked" : ""}><label for="${name}-${n}" aria-label="${n} stars">★</label>`).join("")}</div>`;
}
function moreView() {
  if (!diner) return joinPrompt();
  return `<div class="guest-section-heading"><div><h2>A few little extras.</h2><p>Stay connected. Play a little. Tell us how we did.</p></div></div><div class="extras-grid"><section class="panel"><span class="extra-icon">${icon("wifi")}</span><h3>Stay a little longer.</h3><p>Good company, good food, and a connection on us.</p><div class="wifi-details"><p>Network: <b>${esc(diner.wifi.name)}</b></p><p>Password</p><code>${esc(diner.wifi.password)}</code></div><button class="btn soft" style="margin-top:16px" data-action="copy-wifi">${icon("copy")} Copy password</button></section><section class="panel"><span class="extra-icon">${icon("gift")}</span><h3>Good taste has its rewards.</h3><div class="reward-number">${diner.customer.points}<span style="font-size:14px;letter-spacing:0"> points</span></div><p>Earn 1 point per ₹100 on each of your orders once your table’s bill is paid. Points stay with this browser’s guest profile.</p><button class="text-btn" data-action="rewards">See your point history ${icon("arrow-right")}</button><p class="help">Demo points · No cash value or redemption.</p></section><section class="panel"><span class="extra-icon">${icon("puzzle")}</span><h3>A bite-sized challenge.</h3><p>One foodie question a day. A correct answer earns 10 points. Order first to unlock your turn.</p><h4 style="font-size:14px;margin-top:20px">${esc(diner.game.question)}</h4>${diner.game.played ? `<div class="notice green">You’ve played today and earned ${diner.game.earned} points. See you tomorrow!</div>` : `<div class="quiz-options">${diner.game.options.map((o, i) => `<button data-action="game" data-answer="${i}" ${diner.bill.closed ? "disabled" : ""}>${esc(o)}</button>`).join("")}</div>`}</section><section class="panel"><span class="extra-icon">${icon("gamepad-2")}</span><h3>A little table-side fun.</h3><p>Find six matching food pairs in as few turns as possible. A relaxed memory game while your meal is prepared.</p><button class="btn soft" data-action="memory-start">Play food pairs</button><p class="help" style="margin-top:15px">Just for fun · No loyalty points awarded.</p></section><section class="panel"><span class="extra-icon">${icon("message-square-heart")}</span><h3>How was your time with us?</h3><p>Your thoughts help us make the next visit even better.</p>${diner.reviewed ? '<div class="notice green">Your review is in. Thank you for sharing a little love.</div>' : `<form id="review-form" class="form-stack"><div><label>The food</label>${ratingInput("food_rating")}</div><div><label>The service</label>${ratingInput("service_rating")}</div><label>A little note (optional)<textarea name="comment" maxlength="1000" placeholder="What made your visit special?"></textarea></label><button class="btn primary" type="submit">Share your experience</button></form>`}</section></div>`;
}
function waiterModal() {
  if (!diner || diner.bill.closed) {
    joinModal();
    return;
  }
  modal(
    "A little help?",
    `<p class="help">Let us know what you need. Your waiter will see your request straight away.</p><form id="waiter-form" class="form-stack"><label>I’d like…<select name="kind"><option value="service">A member of the team</option><option value="water">Some water, please</option><option value="bill">Help with the bill</option></select></label><label>Anything else? (optional)<textarea name="note" maxlength="300" placeholder="Tell us a little more…"></textarea></label><button class="btn primary" type="submit">${icon("bell-ring")} Call my waiter</button></form>`,
  );
}
function equalModal() {
  modal(
    "Good things are better shared.",
    `<p class="help">The full bill of ${cash(diner.bill.total)} will be divided equally. Any extra paise are distributed one at a time.</p><form id="equal-form" class="form-stack"><label>Number of people<input name="count" type="number" min="2" max="20" value="${Math.max(2, diner.table.guests)}" required></label><button class="btn primary" type="submit">Create equal shares</button></form>`,
  );
}
function splitRow(index) {
  return `<div class="split-entry"><input name="label" aria-label="Person ${index} name" placeholder="Guest ${index}" value="Guest ${index}" required maxlength="60"><input name="amount" aria-label="Person ${index} amount in rupees" placeholder="₹ amount" type="number" min="0.01" step="0.01" required><button type="button" class="icon-btn" data-action="remove-share" aria-label="Remove share">${icon("x")}</button></div>`;
}
function customModal() {
  modal(
    "Share it your way.",
    `<p class="help">The shares must total ${cash(diner.bill.total)}, including tax. All amounts are in rupees.</p><form id="custom-form" class="form-stack"><div id="split-entries">${splitRow(1)}${splitRow(2)}</div><button class="btn secondary" type="button" data-action="add-share">+ Add another person</button><button class="btn primary" type="submit">Save custom shares</button></form>`,
  );
}
function payModal(splitId) {
  const bill = diner.bill,
    split = bill.splits.find((s) => s.id === splitId),
    remaining = split ? split.amount - split.paid : bill.remaining;
  paymentKey = requestKey();
  modal(
    "Demo checkout",
    `<div class="payment-demo"><b>Simulated payment only</b><br>This screen never asks for card, bank or UPI credentials. Choose an outcome to test the workflow.</div><form id="payment-form" data-split="${splitId || ""}" class="form-stack"><p class="help">${split ? esc(split.label) : "Table bill"} · ${cash(remaining)} remaining. You can pay a smaller custom amount.</p><label>Amount to pay (₹)<input name="amount" type="number" min="0.01" max="${(remaining / 100).toFixed(2)}" step="0.01" value="${(remaining / 100).toFixed(2)}" required></label><label>Demo result<select name="outcome"><option value="success">Payment succeeds</option><option value="failed">Payment fails (test mode)</option></select></label><button class="btn primary" type="submit">${icon("shield-check")} Simulate payment</button></form>`,
  );
}
document.addEventListener("input", (e) => {
  if (e.target.id === "menu-search") {
    query = e.target.value;
    $("#food-grid").innerHTML = foodCards();
    icons();
  }
});
document.addEventListener("click", async (e) => {
  const v = e.target.closest("[data-view]");
  if (v) {
    guestView = v.dataset.view;
    await refreshState();
    return;
  }
  const c = e.target.closest("[data-category]");
  if (c) {
    category = c.dataset.category;
    renderGuest();
    return;
  }
  const b = e.target.closest("[data-action]");
  if (!b) return;
  const action = b.dataset.action,
    id = Number(b.dataset.id);
  try {
    await busy(b, async () => {
      if (action === "add" || action === "remove") {
        const item = itemById(id);
        if (!item?.available) return;
        cart[id] = Math.max(
          0,
          Math.min(50, (cart[id] || 0) + (action === "add" ? 1 : -1)),
        );
        if (!cart[id]) delete cart[id];
        orderKey = null;
        saveCart();
        if ($("#order-form") || ($("#modal").open && $("#modal .cart-row")))
          cartModal();
        if ($("#food-grid")) {
          $("#food-grid").innerHTML = foodCards();
          icons();
        }
      }
      if (action === "cart") cartModal();
      if (action === "memory-start") startMemory();
      if (action === "memory-flip") flipMemory(Number(b.dataset.index));
      if (action === "join") joinModal();
      if (action === "call-waiter") waiterModal();
      if (action === "split-equal") equalModal();
      if (action === "split-custom") customModal();
      if (action === "add-share") {
        const count = $$(".split-entry").length;
        if (count >= 20) {
          toast("Maximum 20 shares.", true);
          return;
        }
        $("#split-entries").insertAdjacentHTML(
          "beforeend",
          splitRow(count + 1),
        );
        icons();
      }
      if (action === "remove-share") {
        if ($$(".split-entry").length <= 2) {
          toast("Keep at least two shares.", true);
          return;
        }
        b.closest(".split-entry").remove();
      }
      if (action === "pay") {
        await refreshState(false);
        payModal(id);
      }
      if (action === "copy-wifi") {
        if (navigator.clipboard && window.isSecureContext) {
          await navigator.clipboard.writeText(diner.wifi.password);
          toast("Wi-Fi password copied.");
        } else
          modal(
            "Guest Wi-Fi password",
            `<p class="help">Select and copy the password below.</p><input value="${esc(diner.wifi.password)}" readonly aria-label="Wi-Fi password">`,
          );
      }
      if (action === "rewards")
        modal(
          "Your good-taste points",
          diner.rewards
            .map(
              (r) =>
                `<div class="list-line"><div>${esc(r.description)}<small>${dateTime(r.created_at)}</small></div><b>+${r.points}</b></div>`,
            )
            .join("") ||
            empty(
              "A fresh start",
              "Your first points are on their way.",
              "gift",
            ),
        );
      if (action === "game") {
        const result = await api("/api/guest/game", "POST", {
          answer: Number(b.dataset.answer),
        });
        toast(result.message);
        await refreshState();
      }
    });
  } catch (_) {}
});
document.addEventListener("submit", async (e) => {
  const form = e.target;
  if (
    ![
      "join-form",
      "order-form",
      "waiter-form",
      "equal-form",
      "custom-form",
      "payment-form",
      "review-form",
    ].includes(form.id)
  )
    return;
  e.preventDefault();
  await busy($('button[type="submit"]', form), async () => {
    try {
      const data = Object.fromEntries(new FormData(form));
      if (form.id === "join-form") {
        await api("/api/guest/join", "POST", {
          ...data,
          guest_count: Number(data.guest_count),
          token: tableToken,
        });
        await refreshState();
        if (form.dataset.cart === "1") cartModal();
        else closeModal();
        toast("Welcome to the table.");
      }
      if (form.id === "order-form") {
        if (!diner || diner.bill.closed) {
          joinModal(true);
          return;
        }
        orderKey ||= requestKey();
        const result = await api("/api/guest/orders", "POST", {
          items: cartLines().map((i) => ({ id: i.id, quantity: i.quantity })),
          notes: data.notes,
          request_key: orderKey,
        });
        cart = {};
        orderKey = null;
        saveCart();
        closeModal();
        guestView = "orders";
        await refreshState();
        toast(
          `Order #${String(result.order.id).padStart(4, "0")} is with the kitchen.`,
        );
      }
      if (form.id === "waiter-form") {
        const result = await api("/api/guest/requests", "POST", data);
        closeModal();
        await refreshState();
        toast(result.message);
      }
      if (form.id === "equal-form") {
        await api("/api/guest/splits", "POST", {
          mode: "equal",
          count: Number(data.count),
        });
        closeModal();
        await refreshState();
        toast("The bill is shared equally.");
      }
      if (form.id === "custom-form") {
        const shares = $$(".split-entry", form).map((r) => ({
          label: $('[name="label"]', r).value,
          amount: $('[name="amount"]', r).value,
        }));
        await api("/api/guest/splits", "POST", { mode: "custom", shares });
        closeModal();
        await refreshState();
        toast("Your custom shares are saved.");
      }
      if (form.id === "payment-form") {
        const result = await api("/api/guest/payments", "POST", {
          ...data,
          split_id: form.dataset.split ? Number(form.dataset.split) : null,
          request_key: paymentKey,
        });
        paymentKey = null;
        await refreshState();
        const success = result.payment.status === "success";
        modal(
          success ? "All good. Thank you!" : "Let’s try that again.",
          `<div class="payment-result ${success ? "" : "failed"}">${icon(success ? "circle-check" : "circle-x")}<h3>${success ? "Payment successful" : "Payment failed"}</h3><p>${cash(result.payment.amount)} · Demo transaction<br>${esc(result.payment.reference)}</p><p>${success ? "Your table’s remaining balance is " + cash(result.bill.remaining) + "." : "Your balance is unchanged. Close this dialog and choose Pay again."}</p><button class="btn primary full" data-action="close-modal">Back to your bill</button></div>`,
        );
      }
      if (form.id === "review-form") {
        await api("/api/guest/reviews", "POST", {
          ...data,
          food_rating: Number(data.food_rating),
          service_rating: Number(data.service_rating),
        });
        await refreshState();
        toast("Thank you for sharing your experience.");
      }
    } catch (_) {}
  });
});
init();
setInterval(async () => {
  if (
    document.hidden ||
    $("#modal").open ||
    $("#guest-content").contains(document.activeElement)
  )
    return;
  try {
    await refreshState(guestView !== "menu" && guestView !== "more");
  } catch (_) {}
}, 5000);

// A small in-browser memory game. Loyalty rewards belong only to the server quiz.
let memoryGame;
function startMemory() {
  const cards = ["🍋", "🍒", "🥑", "🍕", "🥐", "🍓"];
  const deck = [...cards, ...cards];
  for (let i = deck.length - 1; i > 0; i--) {
    const j = crypto.getRandomValues(new Uint32Array(1))[0] % (i + 1);
    [deck[i], deck[j]] = [deck[j], deck[i]];
  }
  memoryGame = { deck, matched: [], flipped: [], moves: 0, locked: false };
  renderMemory();
}
function renderMemory() {
  const g = memoryGame;
  modal(
    "A delicious little memory test.",
    `<p class="help">Match all six pairs. Moves: <b>${g.moves}</b> · Pairs: <b>${g.matched.length / 2}/6</b></p><div class="memory-grid">${g.deck
      .map((symbol, i) => {
        const shown = g.matched.includes(i) || g.flipped.includes(i);
        return `<button class="memory-card ${shown ? "revealed" : ""}" data-action="memory-flip" data-index="${i}" aria-label="${shown ? symbol : "Hidden food card " + (i + 1)}" ${g.matched.includes(i) ? "disabled" : ""}>${shown ? symbol : "?"}</button>`;
      })
      .join(
        "",
      )}</div>${g.matched.length === 12 ? `<p class="notice green" style="margin-top:20px">All six pairs found in ${g.moves} moves. Nicely done!</p>` : ""}<button class="btn secondary full" style="margin-top:20px" data-action="memory-start">New game</button>`,
  );
}
function flipMemory(index) {
  const g = memoryGame;
  if (!g || g.locked || g.matched.includes(index) || g.flipped.includes(index))
    return;
  g.flipped.push(index);
  if (g.flipped.length === 2) {
    g.moves++;
    const [a, b] = g.flipped;
    if (g.deck[a] === g.deck[b]) {
      g.matched.push(a, b);
      g.flipped = [];
    } else {
      g.locked = true;
      setTimeout(() => {
        if (memoryGame !== g) return;
        g.flipped = [];
        g.locked = false;
        if ($("#modal").open && $(".memory-grid")) renderMemory();
      }, 850);
    }
  }
  renderMemory();
}
