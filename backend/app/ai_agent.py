import json
import os
import re
from functools import lru_cache
from numbers import Number
from typing import Dict, List, Optional, Set, Tuple

import duckdb

try:
    from chat_format import format_compact_response, humanize_source_line
except ImportError:
    from .chat_format import format_compact_response, humanize_source_line
import pandas as pd
import requests


GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")
DB_PATH = os.environ.get("AGENT_DB_PATH", ":memory:")
DATA_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Data"))
ENABLE_XLSX_AGENT_LOAD = os.environ.get("ENABLE_XLSX_AGENT_LOAD", "0") == "1"
AGENT_CHAT_VERBOSE = os.environ.get("AGENT_CHAT_VERBOSE", "0") == "1"
MAX_TABLE_CANDIDATES = 12
MAX_SQL_ROWS = 200


def _slugify(name: str) -> str:
    name = name.lower()
    name = re.sub(r"[^a-z0-9]+", "_", name).strip("_")
    if not name:
        name = "table"
    if name[0].isdigit():
        name = f"t_{name}"
    return name[:120]


def _escape_sql_path(path: str) -> str:
    return path.replace("'", "''")


def _discover_local_data_files() -> List[Tuple[str, str]]:
    files: List[Tuple[str, str]] = []
    for root, _, filenames in os.walk(DATA_ROOT):
        for filename in filenames:
            lower = filename.lower()
            if lower.startswith("~$"):
                continue
            if lower.endswith(".csv") or (ENABLE_XLSX_AGENT_LOAD and lower.endswith(".xlsx")):
                abs_path = os.path.join(root, filename)
                rel_path = os.path.relpath(abs_path, DATA_ROOT).replace("\\", "/")
                files.append((rel_path, abs_path))
    files.sort(key=lambda x: x[0])
    return files


def _tokenize(text: str) -> List[str]:
    return [t for t in re.split(r"[^a-z0-9]+", text.lower()) if len(t) >= 3]


@lru_cache(maxsize=1)
def _get_conn() -> duckdb.DuckDBPyConnection:
    conn = duckdb.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS data_catalog (
            table_name TEXT PRIMARY KEY,
            rel_path TEXT,
            abs_path TEXT,
            file_type TEXT,
            status TEXT
        )
        """
    )

    discovered = _discover_local_data_files()
    for rel_path, abs_path in discovered:
        table_name = _slugify(rel_path)
        file_type = "xlsx" if rel_path.lower().endswith(".xlsx") else "csv"
        status = "ok"
        try:
            if file_type == "csv":
                sql_path = _escape_sql_path(abs_path)
                conn.execute(
                    f"""
                    CREATE OR REPLACE VIEW "{table_name}" AS
                    SELECT * FROM read_csv_auto('{sql_path}', HEADER=TRUE, IGNORE_ERRORS=TRUE, SAMPLE_SIZE=-1)
                    """
                )
            else:
                # Optional XLSX support; disabled by default for startup performance.
                try:
                    df = pd.read_excel(abs_path)
                    conn.register("tmp_xlsx_df", df)
                    conn.execute(f'CREATE OR REPLACE TABLE "{table_name}" AS SELECT * FROM tmp_xlsx_df')
                    conn.unregister("tmp_xlsx_df")
                except Exception:
                    status = "skipped_xlsx"
        except Exception:
            status = "load_failed"

        conn.execute(
            """
            INSERT INTO data_catalog (table_name, rel_path, abs_path, file_type, status)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(table_name) DO UPDATE SET
                rel_path=excluded.rel_path,
                abs_path=excluded.abs_path,
                file_type=excluded.file_type,
                status=excluded.status
            """,
            [table_name, rel_path, abs_path, file_type, status],
        )

    return conn


def _catalog_map() -> Dict[str, Dict[str, str]]:
    rows = _list_tables(limit=5000)
    return {r["table_name"]: r for r in rows}


def _list_tables(limit: int = 60) -> List[Dict[str, str]]:
    conn = _get_conn()
    rows = conn.execute(
        """
        SELECT table_name, rel_path, file_type, status
        FROM data_catalog
        WHERE status IN ('ok', 'skipped_xlsx')
        ORDER BY rel_path
        LIMIT ?
        """,
        [limit],
    ).fetchall()
    return [
        {"table_name": r[0], "rel_path": r[1], "file_type": r[2], "status": r[3]}
        for r in rows
    ]


def _suggest_tables(question: str, limit: int = MAX_TABLE_CANDIDATES) -> List[Dict[str, str]]:
    tokens = _tokenize(question)
    tables = _list_tables(limit=5000)
    if not tokens:
        return tables[:limit]

    ranked: List[Tuple[float, Dict[str, str]]] = []
    for entry in tables:
        rel_path = entry["rel_path"].lower()
        table_name = entry["table_name"].lower()
        score = 0.0
        for token in tokens:
            if token in table_name:
                score += 2.5
            if token in rel_path:
                score += 1.5
        # Bias toward likely context tables for generic words
        if "program" in question.lower() and "program" in rel_path:
            score += 4.0
        if "pageview" in question.lower() and "pageview" in rel_path:
            score += 4.0
        if "portal" in question.lower() and "portal" in rel_path:
            score += 4.0
        if "311" in question.lower() and "311" in rel_path:
            score += 3.0
        if "zip" in question.lower() and "zipcode" in rel_path:
            score += 2.0
        ql = question.lower()
        if any(w in ql for w in ("health", "brfss", "disease", "prevalence", "chronic")):
            if "health_places" in rel_path or "/clean/health" in rel_path.replace("\\", "/"):
                score += 6.0
            if "places" in rel_path and "better_health" in rel_path.replace(" ", "").lower():
                score += 2.0
        if "78207" in question and "78207" in rel_path:
            score += 2.5
        if score > 0:
            ranked.append((score, entry))

    if not ranked:
        return tables[:limit]
    ranked.sort(key=lambda x: (-x[0], x[1]["rel_path"]))
    return [entry for _, entry in ranked[:limit]]


def _describe_table(table_name: str) -> List[Dict[str, str]]:
    conn = _get_conn()
    try:
        rows = conn.execute(f'PRAGMA table_info("{table_name}")').fetchall()
    except Exception:
        return []
    return [{"column": r[1], "type": r[2]} for r in rows]


def _extract_sql_tables(sql: str) -> Set[str]:
    names: Set[str] = set()
    patterns = [
        r'\bfrom\s+"([^"]+)"',
        r"\bfrom\s+([a-zA-Z0-9_]+)",
        r'\bjoin\s+"([^"]+)"',
        r"\bjoin\s+([a-zA-Z0-9_]+)",
    ]
    for pattern in patterns:
        for match in re.findall(pattern, sql, flags=re.IGNORECASE):
            names.add(match.lower())
    return names


def _validate_sql_tables(sql: str, allowed_tables: Set[str]) -> Optional[str]:
    referenced = _extract_sql_tables(sql)
    if not referenced:
        return "SQL must reference at least one table."
    unknown = [t for t in referenced if t not in allowed_tables]
    if unknown:
        return f"SQL references unknown/unapproved table(s): {', '.join(sorted(unknown))}"
    return None


def _run_sql(sql: str, max_rows: int = MAX_SQL_ROWS) -> Tuple[pd.DataFrame, Optional[str]]:
    safe = sql.strip()
    if not re.match(r"^\s*(select|with)\b", safe, flags=re.IGNORECASE):
        return pd.DataFrame(), "Only SELECT/ WITH queries are allowed."
    if ";" in safe.strip().rstrip(";"):
        return pd.DataFrame(), "Multiple statements are not allowed."
    limited = safe if re.search(r"\blimit\s+\d+\b", safe, flags=re.IGNORECASE) else f"{safe}\nLIMIT {max_rows}"

    conn = _get_conn()
    try:
        df = conn.execute(limited).fetchdf()
        return df, None
    except Exception as exc:
        return pd.DataFrame(), f"SQL execution failed: {exc}"


def _call_groq(messages: List[Dict[str, str]], temperature: float = 0.0, max_tokens: int = 1024) -> Optional[str]:
    if not GROQ_API_KEY:
        return None
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    try:
        resp = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=45)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception:
        return None


def _parse_json_text(raw: str) -> Optional[Dict[str, object]]:
    if not raw:
        return None
    try:
        json_text = raw.strip()
        if "```" in json_text:
            json_text = re.sub(r"^```(?:json)?|```$", "", json_text, flags=re.MULTILINE).strip()
        parsed = json.loads(json_text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        return None
    return None


def _format_breakdown_line(line: str) -> str:
    s = (line or "").strip()
    if not s:
        return ""
    if s[:2] in ("- ", "• "):
        return s
    return f"- {s}"


def _data_basis_from_sources(sources: Optional[List[str]]) -> Optional[List[str]]:
    if not sources:
        return None
    out: List[str] = []
    for s in sources[:8]:
        s = (s or "").strip()
        if "(" in s and s.endswith(")"):
            inner = s[s.rindex("(") + 1 : -1].strip()
            out.append(humanize_source_line(inner))
        else:
            out.append(humanize_source_line(s))
    return out or None


def _render_chat_reply(
    answer: str,
    breakdown: Optional[List[str]] = None,
    *,
    sql_used: str = "",
    sources: Optional[List[str]] = None,
    limitations: Optional[str] = None,
) -> str:
    lead = (answer or "").strip() or (
        "No clear numeric answer was returned from the loaded datasets for this question."
    )
    bullets: List[str] = []
    for x in breakdown or []:
        s = re.sub(r"^[-•*]\s*", "", (_format_breakdown_line(x) or "").strip())
        if s:
            bullets.append(s)
    notes = [limitations.strip()] if limitations and limitations.strip() else None
    text = format_compact_response(lead, bullets if bullets else None, notes=notes)
    if AGENT_CHAT_VERBOSE and (sql_used or sources):
        dbg: List[str] = ["", "---", "Debug (AGENT_CHAT_VERBOSE=1):"]
        if sql_used.strip():
            sq = sql_used.strip()
            if len(sq) > 1200:
                sq = sq[:1200] + " ... [truncated]"
            dbg.append(f"• SQL: {sq}")
        if sources:
            basis = _data_basis_from_sources(sources) or []
            for b in basis[:6]:
                dbg.append(f"• Source: {b}")
        text += "\n".join(dbg)
    return text


def _breakdown_from_dataframe(df: pd.DataFrame, max_lines: int = 12) -> List[str]:
    """Turn a small result table into bullet lines (e.g. category: value)."""
    if df is None or df.empty:
        return []
    lines: List[str] = []
    if len(df.columns) == 1:
        col = df.columns[0]
        for _, row in df.head(max_lines).iterrows():
            v = row[col]
            if pd.notna(v):
                lines.append(str(v).strip())
        return [x for x in lines if x]
    if len(df.columns) >= 2:
        c0, c1 = df.columns[0], df.columns[1]
        for _, row in df.head(max_lines).iterrows():
            a, b = row[c0], row[c1]
            if pd.isna(a) and pd.isna(b):
                continue
            if isinstance(b, Number) and not isinstance(b, bool):
                try:
                    bv = float(b)
                    if bv == int(bv):
                        bv_s = str(int(bv))
                    else:
                        bv_s = f"{bv:.2f}".rstrip("0").rstrip(".")
                except (TypeError, ValueError):
                    bv_s = str(b)
                lines.append(f"{a}: {bv_s}")
            else:
                lines.append(f"{a}: {b}")
        return lines
    return []


def _fallback_chat_reply(
    question: str,
    result_df: pd.DataFrame,
    sql_used: str,
    sources: List[str],
) -> str:
    if result_df.empty:
        return _render_chat_reply(
            "No rows matched the executed query in the currently registered tables.",
            breakdown=None,
            sql_used=sql_used,
            sources=sources,
            limitations="The question may require columns or files not loaded, or different filters.",
        )
    if len(result_df) == 1 and len(result_df.columns) == 1:
        v = result_df.iloc[0, 0]
        return _render_chat_reply(
            f"The computed result is {v}.",
            breakdown=None,
            sql_used=sql_used,
            sources=sources,
        )
    bd = _breakdown_from_dataframe(result_df)
    if bd:
        return _render_chat_reply(
            f"The query returned {len(result_df)} row(s); key values are listed below.",
            breakdown=bd,
            sql_used=sql_used,
            sources=sources,
            limitations="Preview is limited to the first several rows of the result set.",
        )
    preview = result_df.head(8).to_string(index=False)
    return _render_chat_reply(
        f"Partial tabular preview ({len(result_df)} rows in result):",
        breakdown=[ln.strip() for ln in preview.splitlines() if ln.strip()][:10],
        sql_used=sql_used,
        sources=sources,
    )


def _plan_sql(question: str, candidates: List[Dict[str, str]]) -> Optional[Dict[str, str]]:
    table_brief = []
    for t in candidates:
        cols = _describe_table(t["table_name"])[:18]
        col_names = ", ".join(c["column"] for c in cols) if cols else "unknown columns"
        table_brief.append(f'- {t["table_name"]} ({t["rel_path"]}) columns: {col_names}')
    table_text = "\n".join(table_brief)

    system_msg = (
        "You are a SQL planning assistant for DuckDB. "
        "Return ONLY valid JSON with keys: action, sql, rationale. "
        "action must be one of: sql, not_available. "
        "If answer cannot be derived from available tables, action=not_available and sql=''. "
        "Use only provided table names and columns exactly as listed (quoted identifiers if needed). Use SELECT only. "
        "For ZIP/ZCTA health or BRFSS-style questions, prefer tables whose columns include zcta, measure, category, value "
        "over wide raw exports with odd column names. "
        "Filter ZIP with a real column name such as zcta = '78207', never use a number as a column name."
    )
    user_msg = (
        f"User question:\n{question}\n\n"
        f"Available tables:\n{table_text}\n\n"
        'Return JSON like {"action":"sql","sql":"SELECT ...","rationale":"..."}'
    )
    raw = _call_groq(
        [{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}],
        temperature=0.0,
        max_tokens=800,
    )
    if not raw:
        return None
    try:
        plan = _parse_json_text(raw)
        if not plan:
            return None
        return {
            "action": str(plan.get("action", "")).strip(),
            "sql": str(plan.get("sql", "")).strip(),
            "rationale": str(plan.get("rationale", "")).strip(),
        }
    except Exception:
        return None


def _repair_sql(question: str, bad_sql: str, error_text: str, candidates: List[Dict[str, str]]) -> Optional[str]:
    table_text = "\n".join([f'- {t["table_name"]} ({t["rel_path"]})' for t in candidates])
    system_msg = (
        "You fix DuckDB SQL. Return ONLY JSON with key sql. "
        "Use SELECT/ WITH only and only tables listed."
    )
    user_msg = (
        f"Question:\n{question}\n\n"
        f"Broken SQL:\n{bad_sql}\n\n"
        f"Error:\n{error_text}\n\n"
        f"Allowed tables:\n{table_text}\n\n"
        'Return JSON like {"sql":"SELECT ..."}'
    )
    raw = _call_groq(
        [{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}],
        temperature=0.0,
        max_tokens=450,
    )
    if not raw:
        return None
    try:
        repaired = _parse_json_text(raw)
        if not repaired:
            return None
        sql = str(repaired.get("sql", "")).strip()
        return sql or None
    except Exception:
        return None


def get_agent_response(question: str) -> Optional[str]:
    if not GROQ_API_KEY:
        return None

    _get_conn()
    candidates = _suggest_tables(question, limit=MAX_TABLE_CANDIDATES)
    plan = _plan_sql(question, candidates)
    if not plan:
        return None
    if plan["action"] == "not_available":
        return format_compact_response(
            "This question cannot be answered from the tables currently loaded in the agent.",
            notes=[
                "No safe SQL plan matched the available columns for your request.",
                "Add the relevant CSV under the data folder or rephrase using fields that exist in the catalog.",
            ],
        )
    if plan["action"] != "sql" or not plan["sql"]:
        return None

    allowed_tables = {t["table_name"].lower() for t in candidates}
    table_validation_err = _validate_sql_tables(plan["sql"], allowed_tables)
    if table_validation_err:
        return f"I could not run a safe query for this question. {table_validation_err}"

    result_df, err = _run_sql(plan["sql"])
    if err:
        repaired_sql = _repair_sql(question, plan["sql"], err, candidates)
        if repaired_sql:
            table_validation_err = _validate_sql_tables(repaired_sql, allowed_tables)
            if table_validation_err:
                return f"I could not run a safe query for this question. {table_validation_err}"
            result_df, err = _run_sql(repaired_sql)
            if not err:
                plan["sql"] = repaired_sql
        if err:
            return f"I could not run a safe query for this question. {err}"

    preview = result_df.head(20).to_string(index=False) if not result_df.empty else "(no rows)"
    referenced_tables = _extract_sql_tables(plan["sql"])
    catalog = _catalog_map()
    sources = []
    for t in sorted(referenced_tables):
        entry = catalog.get(t)
        if entry:
            sources.append(f"{entry['table_name']} ({entry['rel_path']})")
        else:
            sources.append(t)
    source_text = "; ".join(sources) if sources else "unknown source"

    synth_system = (
        "You format answers like the Buffi municipal chat UI: one clear opening line, then bullet metrics. "
        "Use ONLY the query result — do not invent numbers or national benchmarks unless they appear in the preview. "
        "Return ONLY valid JSON with keys: "
        "answer (first line: short title or direct answer; when listing metrics, end with a colon, e.g. "
        "'Pavement Condition Index (PCI) for zip code 78259:' or 'Found 32 pothole reports for San Pedro Ave in 2021:'), "
        "breakdown (array of strings; each row one bullet fact, e.g. 'Average PCI: 76.0', 'SAN PEDRO AVE: 26 reports'). "
        "When grouping counts by year then month, use breakdown lines like '🗓️ 2023' then 'Feb: 2', 'Mar: 6' "
        "(emoji + bold year is optional in plain text: you may output '🗓️ 2023' as a line). "
        "limitations (optional string; short caveat only, e.g. ZIP-level estimates only). "
        "No SQL, no internal table names, no chit-chat. "
        "If no rows, answer states no matching records; breakdown: []."
    )
    synth_system = (
        "You are a senior municipal data analyst. "
        "Tone: formal, precise, direct, concise. "
        "Use ONLY the query result. Do not invent numbers, benchmarks, or explanations not shown in the data preview. "
        "Return ONLY valid JSON with keys: "
        "answer (one direct sentence answering the question), "
        "breakdown (array of short strings such as 'Average PCI: 76.0' or 'SAN PEDRO AVE: 26 reports'), "
        "limitations (optional short caveat). "
        "Do not mention SQL, internal table names, confidence, or implementation details. "
        "If no rows, say the requested value was not found in the loaded data and use an empty breakdown array."
    )
    synth_user = (
        f"Question:\n{question}\n\n"
        f"SQL used:\n{plan['sql']}\n\n"
        f"Result rows (preview):\n{preview}\n\n"
        f"Dataset hint (internal):\n{source_text}\n\n"
        'Return JSON only: {"answer":"...","breakdown":["..."],"limitations":"..."}'
    )
    final_raw = _call_groq(
        [{"role": "system", "content": synth_system}, {"role": "user", "content": synth_user}],
        temperature=0.1,
        max_tokens=1100,
    )
    if final_raw:
        parsed = _parse_json_text(final_raw)
        if parsed:
            answer = str(parsed.get("answer", "")).strip()
            breakdown = parsed.get("breakdown", parsed.get("evidence", []))
            if not isinstance(breakdown, list):
                breakdown = [str(breakdown)] if breakdown else []
            breakdown = [str(x).strip() for x in breakdown if str(x).strip()]
            lim = parsed.get("limitations")
            limitations = str(lim).strip() if lim else None
            if not breakdown and not result_df.empty and len(result_df) > 1:
                breakdown = _breakdown_from_dataframe(result_df)
            return _render_chat_reply(
                answer,
                breakdown=breakdown or None,
                sql_used=plan["sql"],
                sources=sources,
                limitations=limitations,
            )

    return _fallback_chat_reply(
        question=question,
        result_df=result_df,
        sql_used=plan["sql"],
        sources=sources,
    )
