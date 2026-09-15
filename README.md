# Actus Verum

Site da academia com cadastro de alunos e consulta ao ranking oficial do Circuito Interior de Jiu-Jitsu (https://cijj.com.br/ranking/).

## Como rodar

```bash
cd actus-verum
python3 server.py
```

Abra http://127.0.0.1:8080

## O que o sistema faz

- Cadastra alunos da academia (já vêm os 5 nomes de teste).
- Consulta o ranking público do CIJJ por categoria.
- Mostra posição e pontos de cada aluno.
- Se dois alunos da Actus Verum estiverem na mesma categoria, indica quem está melhor colocado.

A primeira atualização completa percorre todas as categorias do CIJJ e pode levar alguns minutos. Depois o resultado fica em cache por 30 minutos (`data/ranking_cache.json`).
