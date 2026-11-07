"use strict";
document.addEventListener("click", (event) => {
  const demo = event.target.closest("[data-demo]");
  if (demo) {
    const role = demo.dataset.demo;
    $('#login-form [name="username"]').value = role;
    $("#password").value = role[0].toUpperCase() + role.slice(1) + "@12345";
    $("#login-error").textContent = "";
  }
  if (event.target.closest('[data-action="toggle-password"]')) {
    const input = $("#password");
    input.type = input.type === "password" ? "text" : "password";
    event.target
      .closest("button")
      .setAttribute(
        "aria-label",
        input.type === "password" ? "Show password" : "Hide password",
      );
  }
});
$("#login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const button = $('button[type="submit"]', e.target);
  await busy(button, async () => {
    try {
      const result = await api(
        "/api/login",
        "POST",
        Object.fromEntries(new FormData(e.target)),
        true,
      );
      location.href = result.redirect;
    } catch (error) {
      $("#login-error").textContent = error.message;
    }
  });
});
