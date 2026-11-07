"use strict";
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const cash = (paise) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(paise / 100);
const icon = (name) => `<i data-lucide="${name}"></i>`;
const icons = () => window.lucide?.createIcons();
const time = (value) =>
  new Date(value).toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
  });
const dateTime = (value) =>
  new Date(value).toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
const requestKey = () =>
  Array.from(crypto.getRandomValues(new Uint8Array(20)), (n) =>
    n.toString(16).padStart(2, "0"),
  ).join("");
async function api(url, method = "GET", data, quiet = false) {
  try {
    const response = await fetch(url, {
      method,
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": $('meta[name="csrf-token"]').content,
      },
      body: data === undefined ? undefined : JSON.stringify(data),
    });
    const body = await response.json();
    if (!response.ok) {
      const error = new Error(body.error || "Unable to complete this action.");
      error.status = response.status;
      throw error;
    }
    return body;
  } catch (error) {
    if (!quiet)
      toast(error.message || "Connection lost. Please try again.", true);
    throw error;
  }
}
function toast(message, error = false) {
  const el = document.createElement("div");
  el.className = `toast ${error ? "error" : ""}`;
  el.innerHTML = `${icon(error ? "circle-alert" : "circle-check")}<span>${esc(message)}</span>`;
  $("#toast-stack").append(el);
  icons();
  setTimeout(() => el.remove(), 5500);
}
function modal(title, content, wide = false) {
  const el = $("#modal");
  el.classList.toggle("wide", wide);
  $("#modal-content").innerHTML =
    `<header class="modal-header"><h2>${esc(title)}</h2><button class="icon-btn" data-action="close-modal" aria-label="Close dialog">${icon("x")}</button></header><div class="modal-body">${content}</div>`;
  if (!el.open) el.showModal();
  icons();
}
function closeModal() {
  $("#modal").close();
}
function empty(title, note = "", symbol = "inbox") {
  return `<div class="empty-state">${icon(symbol)}<h3>${esc(title)}</h3><p>${esc(note)}</p></div>`;
}
function badge(status) {
  return `<span class="status-badge ${esc(status)}"><span class="dot"></span>${esc(status)}</span>`;
}
async function busy(button, fn) {
  if (button?.disabled) return;
  if (button) button.disabled = true;
  try {
    return await fn();
  } finally {
    if (button?.isConnected) button.disabled = false;
  }
}
document.addEventListener("click", (e) => {
  const target = e.target.closest("[data-action]");
  if (!target) return;
  if (target.dataset.action === "close-modal") closeModal();
  if (target.dataset.action === "print") window.print();
});
document.addEventListener("DOMContentLoaded", icons);
