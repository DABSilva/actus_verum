document.addEventListener("DOMContentLoaded", () => {
  const path = location.pathname.replace(/\/$/, "") || "/";
  const tabs = [
    { href: "/", label: "Início", icon: "⌂" },
    { href: "/horarios.html", label: "Treinos", icon: "◷" },
    { href: "/alunos.html", label: "Alunos", icon: "♟" },
    { href: "/ranking.html", label: "Rank", icon: "★" },
    { href: "/fotos.html", label: "Mais", icon: "☰" },
  ];
  const bar = document.createElement("nav");
  bar.className = "app-tabbar";
  bar.innerHTML = tabs
    .map((t) => {
      const on =
        t.href === "/"
          ? path === "/" || path.endsWith("/index.html")
          : path.endsWith(t.href);
      return `<a class="${on ? "on" : ""}" href="${t.href}"><span>${t.icon}</span>${t.label}</a>`;
    })
    .join("");
  document.body.appendChild(bar);
  document.body.classList.add("app-mobile");

  const inner = document.querySelector(".topbar-inner");
  const nav = inner && inner.querySelector("nav");
  if (inner && nav && !inner.querySelector(".nav-toggle")) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "nav-toggle";
    btn.setAttribute("aria-label", "Menu");
    btn.textContent = "☰";
    btn.addEventListener("click", () => {
      const open = inner.classList.toggle("nav-open");
      btn.textContent = open ? "✕" : "☰";
    });
    inner.appendChild(btn);
  }
});
