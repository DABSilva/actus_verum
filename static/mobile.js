document.addEventListener("DOMContentLoaded", () => {
  const inner = document.querySelector(".topbar-inner");
  const nav = inner && inner.querySelector("nav");
  if (!inner || !nav || inner.querySelector(".nav-toggle")) return;
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "nav-toggle";
  btn.setAttribute("aria-label", "Abrir menu");
  btn.textContent = "☰";
  btn.addEventListener("click", () => {
    const open = inner.classList.toggle("nav-open");
    btn.textContent = open ? "✕" : "☰";
    btn.setAttribute("aria-label", open ? "Fechar menu" : "Abrir menu");
  });
  inner.appendChild(btn);
});
