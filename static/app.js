async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    credentials: "same-origin",
    ...opts,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.erro || "Falha na requisição");
  return data;
}

const brl = (n) =>
  Number(n).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

const LoginPage = {
  init() {
    const form = document.getElementById("login");
    const msg = document.getElementById("msg");
    form.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      msg.textContent = "";
      const payload = Object.fromEntries(new FormData(form).entries());
      try {
        await api("/api/login", { method: "POST", body: JSON.stringify(payload) });
        location.href = "/admin.html";
      } catch (err) {
        msg.className = "toast";
        msg.textContent = err.message;
      }
    });
  },
};

const AlunosPage = {
  async init() {
    const sair = document.getElementById("sair");
    if (sair) {
      sair.addEventListener("click", async (ev) => {
        ev.preventDefault();
        await api("/api/logout", { method: "POST", body: "{}" });
        location.href = "/login.html";
      });
    }
    const form = document.getElementById("form");
    const msg = document.getElementById("msg");
    const cancelar = document.getElementById("btn-cancelar");
    form.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      msg.textContent = "";
      const payload = Object.fromEntries(new FormData(form).entries());
      const id = payload.aluno_id;
      delete payload.aluno_id;
      try {
        if (id) {
          await api("/api/alunos/" + id, { method: "PUT", body: JSON.stringify(payload) });
          msg.textContent = "Dados atualizados.";
        } else {
          await api("/api/alunos", { method: "POST", body: JSON.stringify(payload) });
          msg.textContent = "Aluno cadastrado.";
        }
        this.resetForm();
        msg.className = "okmsg";
        await this.render();
      } catch (err) {
        msg.className = "toast";
        msg.textContent = err.message;
        if (String(err.message).toLowerCase().includes("login")) {
          location.href = "/login.html";
        }
      }
    });
    if (cancelar) cancelar.addEventListener("click", () => this.resetForm());
    await this.render();
  },
  resetForm() {
    const form = document.getElementById("form");
    form.reset();
    form.aluno_id.value = "";
    document.getElementById("btn-salvar").textContent = "Cadastrar aluno";
    const cancelar = document.getElementById("btn-cancelar");
    if (cancelar) cancelar.hidden = true;
  },
  edit(aluno) {
    const form = document.getElementById("form");
    form.aluno_id.value = aluno.id || "";
    form.nome.value = aluno.nome || "";
    form.cpf.value = aluno.cpf || "";
    form.peso.value = aluno.peso || "";
    form.idade.value = aluno.idade || "";
    form.faixa.value = aluno.faixa || "Branca";
    document.getElementById("btn-salvar").textContent = "Salvar alterações";
    const cancelar = document.getElementById("btn-cancelar");
    if (cancelar) cancelar.hidden = false;
    form.scrollIntoView({ behavior: "smooth", block: "start" });
  },
  async render() {
    const lista = document.getElementById("lista");
    try {
      const alunos = await api("/api/alunos");
      if (!alunos.length) {
        lista.innerHTML = '<div class="empty">Nenhum aluno cadastrado ainda.</div>';
        return;
      }
      lista.innerHTML = alunos
        .map(
          (a) => `
        <article class="aluno">
          <div>
            <b>${a.nome}</b>
            <div class="meta">
              ${a.cpf ? "CPF: " + a.cpf + " · " : ""}
              ${a.idade ? "Idade: " + a.idade + " · " : ""}
              ${a.peso ? "Peso: " + a.peso + " · " : ""}
              Faixa: ${a.faixa || "—"}
            </div>
          </div>
          <div class="row-actions">
            <button class="btn ghost" data-edit="${a.id}">Editar</button>
            <button class="btn danger" data-id="${a.id}">Remover</button>
          </div>
        </article>`
        )
        .join("");
      lista.querySelectorAll("button[data-id]").forEach((btn) => {
        btn.addEventListener("click", async () => {
          await api("/api/alunos/" + btn.dataset.id, { method: "DELETE" });
          this.render();
        });
      });
      lista.querySelectorAll("button[data-edit]").forEach((btn) => {
        btn.addEventListener("click", () => {
          const aluno = alunos.find((x) => x.id === btn.dataset.edit);
          if (aluno) this.edit(aluno);
        });
      });
    } catch (err) {
      location.href = "/login.html";
    }
  },
};


const ListaAdmin = {
  alunos: [],
  ordem: "nome",
  async init() {
    const sair = document.getElementById("sair");
    if (sair) {
      sair.addEventListener("click", async (ev) => {
        ev.preventDefault();
        await api("/api/logout", { method: "POST", body: "{}" });
        location.href = "/login.html";
      });
    }
    document.querySelectorAll(".sort-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        this.ordem = btn.dataset.ordem;
        document.querySelectorAll(".sort-btn").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        this.draw();
      });
    });
    document.getElementById("exportar").addEventListener("click", () => {
      location.href = "/api/alunos.xlsx?ordem=" + encodeURIComponent(this.ordem);
    });
    try {
      this.alunos = await api("/api/alunos");
      this.draw();
    } catch (err) {
      location.href = "/login.html";
    }
  },
  draw() {
    const faixaOrdem = ["branca","cinza","amarela","laranja","verde","azul","roxa","marrom","preta","graduado"];
    const num = (txt) => {
      const n = parseFloat(String(txt || "").replace(",", ".").replace(/[^\d.]/g, ""));
      return Number.isFinite(n) ? n : 1e9;
    };
    const itens = [...this.alunos];
    if (this.ordem === "faixa") {
      itens.sort((a, b) => {
        const ia = faixaOrdem.indexOf((a.faixa || "").toLowerCase());
        const ib = faixaOrdem.indexOf((b.faixa || "").toLowerCase());
        return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib) || a.nome.localeCompare(b.nome, "pt-BR");
      });
    } else if (this.ordem === "idade") {
      itens.sort((a, b) => num(a.idade) - num(b.idade) || a.nome.localeCompare(b.nome, "pt-BR"));
    } else if (this.ordem === "peso") {
      itens.sort((a, b) => num(a.peso) - num(b.peso) || a.nome.localeCompare(b.nome, "pt-BR"));
    } else {
      itens.sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR"));
    }
    const tb = document.querySelector("#tabela tbody");
    if (!itens.length) {
      tb.innerHTML = '<tr><td colspan="5" class="empty-cell">Nenhum aluno cadastrado.</td></tr>';
      return;
    }
    tb.innerHTML = itens.map((a) => `<tr>
          <td>${a.nome || ""}</td>
          <td>${a.cpf || "—"}</td>
          <td>${a.idade || "—"}</td>
          <td>${a.peso || "—"}</td>
          <td><span class="belt mini ${beltClass(a.faixa)}"></span> ${a.faixa || "—"}</td>
        </tr>`).join("");
  },
};

const RankingPage = {
  async init() {
    document.getElementById("refresh").addEventListener("click", () => this.load(true));
    await this.load(false);
  },
  async load(force) {
    const board = document.getElementById("board");
    const status = document.getElementById("status");
    const btn = document.getElementById("refresh");
    btn.disabled = true;
    status.textContent = force
      ? "Consultando todas as categorias do CIJJ. Isso pode levar alguns minutos..."
      : "Carregando ranking da equipe...";
    try {
      const data = await api(force ? "/api/refresh" : "/api/ranking");
      const when = data.atualizado_em
        ? new Date(data.atualizado_em * 1000).toLocaleString("pt-BR")
        : "agora";
      status.textContent = "Última leitura do CIJJ: " + when;
      this.renderTop(data.top_pontuadores || []);
      if (!data.itens.length) {
        board.innerHTML = '<div class="empty">Cadastre alunos no painel admin para cruzar com o ranking.</div>';
        return;
      }
      board.innerHTML = data.itens
        .map((item) => {
          const a = item.aluno;
          if (!item.rankings.length) {
            return `<section class="card rank-block">
              <h3>${a.nome}</h3>
              <p class="hint">Não encontrado no ranking 2026 do CIJJ com este nome.</p>
            </section>`;
          }
          const rows = item.rankings
            .map((r) => {
              const colegas = r.colegas_mesma_categoria || [];
              let cmp = "";
              if (colegas.length) {
                const lis = colegas
                  .map((c) => {
                    const tag = c.melhor
                      ? `<span class="lose">está à frente</span>`
                      : `<span class="win">você está à frente</span>`;
                    return `<li><b>${c.nome}</b> — ${c.posicao}º · ${c.pontos} pts — ${tag}</li>`;
                  })
                  .join("");
                cmp = `<div class="compare">
                  <div class="meta">Outros alunos da Actus Verum nesta categoria</div>
                  <ul>${lis}</ul>
                  <div class="meta">Melhor posicionado da academia: <b>${r.melhor_da_academia}</b></div>
                </div>`;
              }
              return `<div class="entry">
                <div class="pos">${r.posicao}º</div>
                <div>
                  <div><b>${r.pontos} pontos</b> ${r.total_na_categoria ? `<span class="badge">${r.total_na_categoria} atletas na categoria</span>` : ""}</div>
                  <div class="cat">${r.categoria}</div>
                  ${cmp}
                </div>
              </div>`;
            })
            .join("");
          return `<section class="card rank-block">
            <div class="rank-head">
              <h3>${a.nome}</h3>
              <span class="badge">${item.rankings.length} categoria(s)</span>
            </div>
            ${rows}
          </section>`;
        })
        .join("");
    } catch (err) {
      status.className = "toast";
      status.textContent = err.message;
    } finally {
      btn.disabled = false;
    }
  },
  renderTop(lista) {
    const top = document.getElementById("top");
    if (!top) return;
    if (!lista.length) {
      top.innerHTML = '<div class="empty">Nenhum aluno cadastrado.</div>';
      return;
    }
    top.innerHTML = `<ol class="top-list">${lista
      .map(
        (p, i) => `<li>
          <span class="top-pos">${i + 1}º</span>
          <span class="top-name">${p.nome}${p.apelido ? ` <em>(${p.apelido})</em>` : ""}</span>
          <span class="top-pts">${String(p.pontos).replace(".", ",")} pts</span>
        </li>`
      )
      .join("")}</ol>`;
  },
};

const EquipePage = {
  async init() {
    const box = document.getElementById("equipe");
    const alunos = await api("/api/equipe");
    if (!alunos.length) {
      box.innerHTML = '<div class="empty">Nenhum aluno cadastrado ainda.</div>';
      return;
    }
    const colunas = [
      ["Branca", "branca"],
      ["Cinza", "cinza"],
      ["Amarela", "amarela"],
      ["Laranja", "laranja"],
      ["Verde", "verde"],
      ["Azul", "azul"],
      ["Roxa", "roxa"],
      ["Marrom", "marrom"],
      ["Preta", "preta"],
    ];
    const grupos = { outros: [] };
    colunas.forEach(([, k]) => (grupos[k] = []));
    alunos.forEach((a) => {
      const k = beltClass(a.faixa).replace("belt-", "");
      if (k === "graduado") grupos.preta.push(a);
      else if (grupos[k]) grupos[k].push(a);
      else grupos.outros.push(a);
    });
    const html = colunas
      .map(([label, k]) => {
        const lista = grupos[k];
        const cards = lista.length
          ? lista
              .map(
                (a) => `<article class="athlete-card">
                  <h3>${a.nome}</h3>
                </article>`
              )
              .join("")
          : '<p class="meta">—</p>';
        return `<section class="belt-col">
          <header class="belt-col-head">
            <div class="belt ${beltClass(label)}"></div>
            <h3>${label}</h3>
          </header>
          ${cards}
        </section>`;
      })
      .join("");
    box.className = "belt-board";
    box.innerHTML = html;
  },
};

function beltClass(faixa) {
  const t = (faixa || "").toLowerCase();
  if (t.includes("preta")) return "belt-preta";
  if (t.includes("marrom")) return "belt-marrom";
  if (t.includes("roxa")) return "belt-roxa";
  if (t.includes("azul")) return "belt-azul";
  if (t.includes("verde")) return "belt-verde";
  if (t.includes("laranja")) return "belt-laranja";
  if (t.includes("amarela")) return "belt-amarela";
  if (t.includes("cinza")) return "belt-cinza";
  if (t.includes("graduado")) return "belt-graduado";
  return "belt-branca";
}

const HorariosPage = {
  async init() {
    const grade = document.getElementById("grade");
    const itens = await api("/api/horarios");
    if (!itens.length) {
      grade.innerHTML = '<div class="empty">Nenhum horário cadastrado ainda.</div>';
      return;
    }
    grade.innerHTML = itens
      .map(
        (h) => `<article class="card schedule-card">
          <div class="when">${h.horario}</div>
          <h3>${h.idade}</h3>
          <p>Turma de jiu-jitsu</p>
        </article>`
      )
      .join("");
  },
};

const HorariosAdmin = {
  async init() {
    const form = document.getElementById("form-horario");
    const msg = document.getElementById("msg-horario");
    if (!form) return;
    form.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      msg.textContent = "";
      const payload = Object.fromEntries(new FormData(form).entries());
      try {
        await api("/api/horarios", { method: "POST", body: JSON.stringify(payload) });
        form.reset();
        msg.className = "okmsg";
        msg.textContent = "Horário cadastrado. Já aparece em Horário de treinos.";
        await this.render();
      } catch (err) {
        msg.className = "toast";
        msg.textContent = err.message;
      }
    });
    await this.render();
  },
  async render() {
    const lista = document.getElementById("lista-horarios");
    const itens = await api("/api/horarios");
    if (!itens.length) {
      lista.innerHTML = '<div class="empty">Nenhum horário cadastrado.</div>';
      return;
    }
    lista.innerHTML = itens
      .map(
        (h) => `<article class="aluno">
          <div>
            <b>${h.idade}</b>
            <div class="meta">${h.horario}</div>
          </div>
          <button class="btn danger" data-hid="${h.id}">Remover</button>
        </article>`
      )
      .join("");
    lista.querySelectorAll("button[data-hid]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        await api("/api/horarios/" + btn.dataset.hid, { method: "DELETE" });
        this.render();
      });
    });
  },
};

const ProdutosPage = {
  async init() {
    const loja = document.getElementById("loja");
    const produtos = await api("/api/produtos");
    const wa = "https://wa.me/5517992196708"; // troque SEUNUMERO pelo WhatsApp da academia, só dígitos com DDD
    loja.innerHTML = produtos
      .map((p) => {
        const text = encodeURIComponent(
          `Olá! Quero comprar: ${p.nome} (${brl(p.preco)}) — Actus Verum Team`
        );
        return `<article class="card">
          <div class="card-thumb shop-thumb">${p.categoria}</div>
          <h3>${p.nome}</h3>
          <p>${p.descricao}</p>
          <div class="price">${brl(p.preco)}</div>
          <a class="btn" href="${wa}?text=${text}" target="_blank" rel="noopener">Comprar no WhatsApp</a>
        </article>`;
      })
      .join("");
  },
};
