#!/usr/bin/env python3
"""Actus Verum — servidor local com cadastro de alunos e ranking CIJJ."""

from __future__ import annotations

import json
import re
import threading
import time
import urllib.parse
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
ALUNOS_FILE = DATA / "alunos.json"
CACHE_FILE = DATA / "ranking_cache.json"
ADMIN_FILE = DATA / "admin.json"
PRODUTOS_FILE = DATA / "produtos.json"
HORARIOS_FILE = DATA / "horarios.json"
STATIC = ROOT / "static"
SESSIONS: dict[str, float] = {}
SESSION_TTL = 60 * 60 * 12

UA = "Mozilla/5.0 (compatible; ActusVerum/1.0)"
CATS_URL = "https://cijj.com.br/painel/ranking_categorias.php"
RANK_URL = "https://cijj.com.br/painel/ranking_a_categoria.php"

CACHE_TTL = 60 * 30  # 30 min
_lock = threading.Lock()
_cache: dict = {"ts": 0, "categorias": [], "by_name": {}, "by_cat": {}}


def _http_get(url: str, timeout: int = 25) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace")


def load_alunos() -> list:
    if not ALUNOS_FILE.exists():
        return []
    return json.loads(ALUNOS_FILE.read_text(encoding="utf-8"))


def save_alunos(alunos: list) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    ALUNOS_FILE.write_text(json.dumps(alunos, ensure_ascii=False, indent=2), encoding="utf-8")


FAIXA_ORDEM = [
    "branca", "cinza", "amarela", "laranja", "verde",
    "azul", "roxa", "marrom", "preta", "graduado",
]


def _num(texto: str) -> float:
    s = re.sub(r"[^\d,\.]", "", texto or "")
    s = s.replace(".", "").replace(",", ".") if s.count(",") == 1 and s.count(".") > 1 else s.replace(",", ".")
    try:
        return float(s) if s else 10**9
    except ValueError:
        return 10**9


def sort_alunos(alunos: list, ordem: str) -> list:
    itens = list(alunos)
    if ordem == "faixa":
        itens.sort(key=lambda a: (FAIXA_ORDEM.index(a.get("faixa", "").lower()) if a.get("faixa", "").lower() in FAIXA_ORDEM else 99, (a.get("nome") or "").lower()))
    elif ordem == "idade":
        itens.sort(key=lambda a: (_num(a.get("idade") or ""), (a.get("nome") or "").lower()))
    elif ordem == "peso":
        itens.sort(key=lambda a: (_num(a.get("peso") or ""), (a.get("nome") or "").lower()))
    else:
        itens.sort(key=lambda a: (a.get("nome") or "").lower())
    return itens


def alunos_to_xlsx(alunos: list) -> bytes:
    import io
    import zipfile
    from xml.sax.saxutils import escape

    def cell(ref: str, value: str, style: int = 1) -> str:
        return f'<c r="{ref}" t="inlineStr" s="{style}"><is><t>{escape(value)}</t></is></c>'

    headers = ["Nome", "CPF", "Idade", "Peso", "Faixa"]
    rows_xml = []
    hdr = "".join(cell(f"{chr(65+i)}1", h, 2) for i, h in enumerate(headers))
    rows_xml.append(f'<row r="1">{hdr}</row>')
    for idx, a in enumerate(alunos, start=2):
        vals = [a.get("nome") or "", a.get("cpf") or "", a.get("idade") or "", a.get("peso") or "", a.get("faixa") or ""]
        body = "".join(cell(f"{chr(65+i)}{idx}", v) for i, v in enumerate(vals))
        rows_xml.append(f'<row r="{idx}">{body}</row>')
    sheet = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<sheetData>{''.join(rows_xml)}</sheetData>
</worksheet>'''
    workbook = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<sheets><sheet name="Alunos" sheetId="1" r:id="rId1"/></sheets>
</workbook>'''
    rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>'''
    wb_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>'''
    ctypes = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>'''
    styles = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<fonts count="2">
<font><sz val="11"/><name val="Calibri"/></font>
<font><b/><sz val="11"/><name val="Calibri"/></font>
</fonts>
<fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>
<borders count="1"><border/></borders>
<cellStyleXfs count="1"><xf/></cellStyleXfs>
<cellXfs count="3">
<xf xfId="0"/>
<xf xfId="0"/>
<xf xfId="0" fontId="1" applyFont="1"/>
</cellXfs>
</styleSheet>'''
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ctypes)
        z.writestr("_rels/.rels", rels)
        z.writestr("xl/workbook.xml", workbook)
        z.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        z.writestr("xl/worksheets/sheet1.xml", sheet)
        z.writestr("xl/styles.xml", styles)
    return buf.getvalue()


def aluno_fields(body: dict) -> dict:
    return {
        "nome": (body.get("nome") or "").strip(),
        "cpf": (body.get("cpf") or "").strip(),
        "peso": (body.get("peso") or "").strip(),
        "idade": (body.get("idade") or "").strip(),
        "faixa": (body.get("faixa") or "").strip(),
    }


def load_admin() -> dict:
    if not ADMIN_FILE.exists():
        return {"usuario": "admin", "senha": "actus2026"}
    return json.loads(ADMIN_FILE.read_text(encoding="utf-8"))


def load_produtos() -> list:
    if not PRODUTOS_FILE.exists():
        return []
    return json.loads(PRODUTOS_FILE.read_text(encoding="utf-8"))


def load_horarios() -> list:
    if not HORARIOS_FILE.exists():
        return []
    return json.loads(HORARIOS_FILE.read_text(encoding="utf-8"))


def save_horarios(itens: list) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    HORARIOS_FILE.write_text(json.dumps(itens, ensure_ascii=False, indent=2), encoding="utf-8")


def new_session() -> str:
    import secrets

    token = secrets.token_hex(16)
    SESSIONS[token] = time.time() + SESSION_TTL
    return token


def valid_session(token: str | None) -> bool:
    if not token:
        return False
    exp = SESSIONS.get(token)
    if not exp:
        return False
    if exp < time.time():
        SESSIONS.pop(token, None)
        return False
    return True


def normalize(name: str) -> str:
    n = name.upper().strip()
    n = (
        n.replace("Á", "A")
        .replace("À", "A")
        .replace("Â", "A")
        .replace("Ã", "A")
        .replace("É", "E")
        .replace("Ê", "E")
        .replace("Í", "I")
        .replace("Ó", "O")
        .replace("Ô", "O")
        .replace("Õ", "O")
        .replace("Ú", "U")
        .replace("Ç", "C")
    )
    n = re.sub(r"\s+", " ", n)
    return n


def parse_points(s: str) -> float:
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def parse_place(s: str) -> int:
    m = re.search(r"(\d+)", s)
    return int(m.group(1)) if m else 9999


def fetch_categorias() -> list[str]:
    html = _http_get(CATS_URL)
    return re.findall(r'<option value="([^"]+)"', html)


def fetch_categoria(cat: str) -> list[dict]:
    url = RANK_URL + "?" + urllib.parse.urlencode({"categoria": cat, "exc": 0})
    html = _http_get(url)
    rows = []
    for block in re.findall(r'class="rankatleta">(.*?)</div>', html, flags=re.S):
        text = re.sub(r"<[^>]+>", " ", block)
        text = re.sub(r"\s+", " ", text).strip()
        m = re.search(
            r"(\d+)[ºo]?\s*Lugar\s*-\s*(.+?)\s+pontos:\s*([\d.,]+)",
            text,
            flags=re.I,
        )
        if not m:
            continue
        rows.append(
            {
                "posicao": int(m.group(1)),
                "nome": m.group(2).strip(),
                "pontos": parse_points(m.group(3)),
                "categoria": cat,
            }
        )
    return rows


def refresh_cache(force: bool = False) -> dict:
    with _lock:
        now = time.time()
        if not force and _cache["ts"] and now - _cache["ts"] < CACHE_TTL and _cache["by_name"]:
            return _cache

        if CACHE_FILE.exists() and not force:
            try:
                disk = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
                if now - disk.get("ts", 0) < CACHE_TTL:
                    _cache.update(disk)
                    return _cache
            except Exception:
                pass

        alunos = load_alunos()
        targets = {normalize(a["nome"]) for a in alunos}
        # also keep common variants
        extra = set()
        for t in list(targets):
            extra.add(t.replace("JOAO", "JOÃO") if False else t)
        targets |= extra

        print("[cijj] baixando categorias...")
        cats = fetch_categorias()
        by_name: dict[str, list] = {}
        by_cat: dict[str, list] = {}

        # First pass: search only categories likely needed is too risky.
        # Scan all — cached for 30 min.
        for i, cat in enumerate(cats):
            try:
                rows = fetch_categoria(cat)
            except Exception as e:
                print("[cijj] erro", cat, e)
                continue
            hits = []
            for row in rows:
                key = normalize(row["nome"])
                if key in targets or any(key == normalize(a["nome"]) for a in alunos):
                    hits.append(row)
                    by_name.setdefault(key, []).append(row)
            if hits:
                by_cat[cat] = rows
            if i % 50 == 0:
                print(f"[cijj] {i}/{len(cats)}")

        _cache.update({"ts": now, "categorias": cats, "by_name": by_name, "by_cat": by_cat})
        CACHE_FILE.write_text(json.dumps(_cache, ensure_ascii=False), encoding="utf-8")
        print("[cijj] cache atualizado")
        return _cache


def ranking_for_alunos() -> dict:
    cache = refresh_cache()
    alunos = load_alunos()
    out = []
    for aluno in alunos:
        key = normalize(aluno["nome"])
        entries = cache.get("by_name", {}).get(key, [])
        # fallback: substring match
        if not entries:
            for nkey, rows in cache.get("by_name", {}).items():
                if key in nkey or nkey in key:
                    entries = rows
                    break
        enriched = []
        for e in entries:
            cat = e["categoria"]
            full = cache.get("by_cat", {}).get(cat, [])
            colegas = []
            for other in alunos:
                if other["id"] == aluno["id"]:
                    continue
                okey = normalize(other["nome"])
                for r in full:
                    if normalize(r["nome"]) == okey:
                        colegas.append(
                            {
                                "nome": other["nome"],
                                "posicao": r["posicao"],
                                "pontos": r["pontos"],
                                "melhor": r["posicao"] < e["posicao"]
                                or (
                                    r["posicao"] == e["posicao"] and r["pontos"] > e["pontos"]
                                ),
                            }
                        )
            colegas.sort(key=lambda x: (x["posicao"], -x["pontos"]))
            melhor_academia = None
            same_cat_academy = [
                {"nome": aluno["nome"], "posicao": e["posicao"], "pontos": e["pontos"]}
            ] + [
                {"nome": c["nome"], "posicao": c["posicao"], "pontos": c["pontos"]}
                for c in colegas
            ]
            same_cat_academy.sort(key=lambda x: (x["posicao"], -x["pontos"]))
            if same_cat_academy:
                melhor_academia = same_cat_academy[0]["nome"]
            enriched.append(
                {
                    **e,
                    "colegas_mesma_categoria": colegas,
                    "melhor_da_academia": melhor_academia,
                    "total_na_categoria": len(full) or None,
                }
            )
        out.append({"aluno": aluno, "rankings": enriched})
    top = []
    for item in out:
        total = round(sum(r.get("pontos") or 0 for r in item["rankings"]), 2)
        a = item["aluno"]
        top.append(
            {
                "id": a.get("id"),
                "nome": a.get("nome"),
                "apelido": (a.get("apelido") or "").strip(),
                "faixa": a.get("faixa") or "",
                "pontos": total,
                "categorias": len(item["rankings"]),
            }
        )
    top.sort(key=lambda x: (-x["pontos"], x["nome"]))
    return {"atualizado_em": cache.get("ts", 0), "itens": out, "top_pontuadores": top}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC), **kwargs)

    def _json(self, code: int, payload) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return {}

    def _cookie_token(self) -> str | None:
        raw = self.headers.get("Cookie") or ""
        for part in raw.split(";"):
            if part.strip().startswith("av_admin="):
                return part.split("=", 1)[1].strip()
        return None

    def _is_admin(self) -> bool:
        return valid_session(self._cookie_token())

    def _json_auth(self, payload, token: str | None = None, code: int = 200) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        if token:
            self.send_header("Set-Cookie", f"av_admin={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age={SESSION_TTL}")
        if token == "":
            self.send_header("Set-Cookie", "av_admin=; Path=/; Max-Age=0")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):  # noqa: N802
        path = urllib.parse.urlparse(self.path).path
        if path == "/api/session":
            return self._json(200, {"admin": self._is_admin()})
        if path == "/api/produtos":
            return self._json(200, load_produtos())
        if path == "/api/horarios":
            return self._json(200, load_horarios())
        if path == "/api/equipe":
            publico = []
            for a in load_alunos():
                item = {
                    "nome": a.get("nome") or "",
                    "faixa": a.get("faixa") or "",
                }
                publico.append(item)
            publico.sort(key=lambda x: x["nome"].lower())
            return self._json(200, publico)
        if path == "/api/alunos":
            if not self._is_admin():
                return self._json(401, {"erro": "Faça login como administrador."})
            return self._json(200, load_alunos())
        if path == "/api/ranking":
            try:
                return self._json(200, ranking_for_alunos())
            except Exception as exc:
                return self._json(500, {"erro": str(exc)})
        if path == "/api/refresh":
            try:
                refresh_cache(force=True)
                return self._json(200, ranking_for_alunos())
            except Exception as exc:
                return self._json(500, {"erro": str(exc)})
        if path in ("/admin.html", "/admin-lista.html", "/admin-horarios.html"):
            if not self._is_admin():
                self.path = "/login.html"
        if path == "/api/alunos.xlsx":
            if not self._is_admin():
                return self._json(401, {"erro": "Faça login como administrador."})
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            ordem = (qs.get("ordem") or ["nome"])[0]
            data = sort_alunos(load_alunos(), ordem)
            raw = alunos_to_xlsx(data)
            self.send_response(200)
            self.send_header("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            self.send_header("Content-Disposition", 'attachment; filename="alunos-actus-verum.xlsx"')
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(raw)
            return
        if path == "/":
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):  # noqa: N802
        path = urllib.parse.urlparse(self.path).path
        body = self._read_body()
        if path == "/api/login":
            admin = load_admin()
            usuario = (body.get("usuario") or "").strip()
            senha = body.get("senha") or ""
            if usuario == admin.get("usuario") and senha == admin.get("senha"):
                token = new_session()
                return self._json_auth({"ok": True}, token=token)
            return self._json(401, {"erro": "Usuário ou senha inválidos."})
        if path == "/api/logout":
            tok = self._cookie_token()
            if tok:
                SESSIONS.pop(tok, None)
            return self._json_auth({"ok": True}, token="")
        if path == "/api/alunos":
            if not self._is_admin():
                return self._json(401, {"erro": "Faça login como administrador."})
            dados = aluno_fields(body)
            nome = dados["nome"]
            if len(nome) < 3:
                return self._json(400, {"erro": "Informe o nome completo do aluno."})
            alunos = load_alunos()
            if any(normalize(a["nome"]) == normalize(nome) for a in alunos):
                return self._json(409, {"erro": "Este aluno já está cadastrado."})
            novo = {"id": str(int(time.time() * 1000)), **dados}
            alunos.append(novo)
            save_alunos(alunos)
            with _lock:
                _cache["ts"] = 0
            return self._json(201, novo)
        if path == "/api/horarios":
            if not self._is_admin():
                return self._json(401, {"erro": "Faça login como administrador."})
            idade = (body.get("idade") or "").strip()
            horario = (body.get("horario") or "").strip()
            if not idade or not horario:
                return self._json(400, {"erro": "Preencha idade e horário."})
            itens = load_horarios()
            novo = {
                "id": str(int(time.time() * 1000)),
                "idade": idade,
                "horario": horario,
            }
            itens.append(novo)
            save_horarios(itens)
            return self._json(201, novo)
        return self._json(404, {"erro": "não encontrado"})

    def do_DELETE(self):  # noqa: N802
        path = urllib.parse.urlparse(self.path).path
        if path.startswith("/api/alunos/"):
            if not self._is_admin():
                return self._json(401, {"erro": "Faça login como administrador."})
            aluno_id = path.rsplit("/", 1)[-1]
            alunos = [a for a in load_alunos() if a["id"] != aluno_id]
            save_alunos(alunos)
            return self._json(200, {"ok": True})
        if path.startswith("/api/horarios/"):
            if not self._is_admin():
                return self._json(401, {"erro": "Faça login como administrador."})
            hid = path.rsplit("/", 1)[-1]
            save_horarios([h for h in load_horarios() if h["id"] != hid])
            return self._json(200, {"ok": True})
        return self._json(404, {"erro": "não encontrado"})

    def do_PUT(self):  # noqa: N802
        path = urllib.parse.urlparse(self.path).path
        body = self._read_body()
        if path.startswith("/api/alunos/"):
            if not self._is_admin():
                return self._json(401, {"erro": "Faça login como administrador."})
            aluno_id = path.rsplit("/", 1)[-1]
            dados = aluno_fields(body)
            if len(dados["nome"]) < 3:
                return self._json(400, {"erro": "Informe o nome completo do aluno."})
            alunos = load_alunos()
            alvo = None
            for a in alunos:
                if a["id"] == aluno_id:
                    alvo = a
                    break
            if not alvo:
                return self._json(404, {"erro": "Aluno não encontrado."})
            if any(a["id"] != aluno_id and normalize(a["nome"]) == normalize(dados["nome"]) for a in alunos):
                return self._json(409, {"erro": "Já existe outro aluno com este nome."})
            alvo.update(dados)
            save_alunos(alunos)
            with _lock:
                _cache["ts"] = 0
            return self._json(200, alvo)
        return self._json(404, {"erro": "não encontrado"})

    def log_message(self, fmt: str, *args) -> None:
        print("[http]", self.address_string(), "-", fmt % args)


def lan_ip() -> str:
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except Exception:
        return ""


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    if not ALUNOS_FILE.exists():
        save_alunos([])
    port = int(__import__("os").environ.get("PORT", "8080"))
    ip = lan_ip()
    print(f"No computador:  http://127.0.0.1:{port}")
    if ip:
        print(f"No celular (mesma rede):  http://{ip}:{port}")
    print("Deixe esta janela aberta. Se o celular nao abrir, libere a porta 8080 no Firewall do Windows.")

    def warmup():
        try:
            refresh_cache(force=False)
        except Exception as e:
            print("[cijj] warmup falhou:", e)

    threading.Thread(target=warmup, daemon=True).start()
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
