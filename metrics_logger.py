import os, json, time, traceback
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional
from datetime import datetime, timezone

def _ymd_utc(ts=None):
    ts = time.time() if ts is None else ts
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")

def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

@dataclass
class MetricEvent:
    ts: float
    kind: str                 # "http_in", "http_out", "llm", "error", "feedback"
    name: str                 # "flask", "naver_news", "openweather", "minimax_via_brain"
    ok: bool
    latency_ms: int = 0

    # http_in
    method: Optional[str] = None
    path: Optional[str] = None
    status_code: Optional[int] = None

    # http_out
    url: Optional[str] = None

    # llm
    request_type: Optional[str] = None   # "chat", "news_chat", "boot_briefing", "voice"...
    response_len: Optional[int] = None
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    cost: Optional[float] = None
    timeout: Optional[bool] = None
    error: Optional[str] = None

    # feedback
    rating: Optional[int] = None
    comment: Optional[str] = None
    session_id: Optional[int] = None

    meta: Optional[Dict[str, Any]] = None

class MetricsLogger:
    def __init__(self, log_dir="logs"):
        self.log_dir = log_dir
        _ensure_dir(log_dir)

    def _events_path(self, ymd: str):
        return os.path.join(self.log_dir, f"events_{ymd}.jsonl")

    def _summary_path(self, ymd: str):
        return os.path.join(self.log_dir, f"summary_{ymd}.json")

    def log(self, ev: MetricEvent):
        ymd = _ymd_utc(ev.ts)
        with open(self._events_path(ymd), "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(ev), ensure_ascii=False) + "\n")

    def log_exception(self, name: str, meta: Optional[Dict[str, Any]] = None):
        self.log(MetricEvent(
            ts=time.time(),
            kind="error",
            name=name,
            ok=False,
            error=traceback.format_exc(),
            meta=meta
        ))

    def compute_daily_summary(self, ymd: str):
        path = self._events_path(ymd)
        if not os.path.exists(path):
            summary = {
                "date": ymd,
                "counts": {},
                "latency_ms": {},
                "rates": {},
                "llm": {},
                "feedback": {}
            }
            with open(self._summary_path(ymd), "w", encoding="utf-8") as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            return summary

        counts = {
            "http_in_total": 0, "http_in_fail": 0,
            "http_out_total": 0, "http_out_fail": 0,
            "llm_total": 0, "llm_timeout": 0, "llm_fail": 0,
            "error_total": 0,
            "feedback_total": 0
        }
        lat_sum = {"http_in": 0, "http_out": 0, "llm": 0}
        lat_n = {"http_in": 0, "http_out": 0, "llm": 0}

        llm_by_type = {}
        rating_sum = 0
        rating_n = 0

        def _init_rt(rt):
            llm_by_type[rt] = {
                "count": 0, "timeout": 0, "fail": 0,
                "avg_latency_ms": 0, "avg_response_len": 0,
                "avg_tokens_in": None, "avg_tokens_out": None, "avg_cost": None,
                "_lat": 0, "_len": 0,
                "_tin": 0, "_tin_n": 0,
                "_tout": 0, "_tout_n": 0,
                "_cost": 0.0, "_cost_n": 0
            }

        interactions = {}

        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                ev = json.loads(line)
                kind = ev.get("kind")
                ok = bool(ev.get("ok"))
                latency_ms = int(ev.get("latency_ms") or 0)
                name = ev.get("name", "unknown")

                if kind == "http_in":
                    counts["http_in_total"] += 1
                    if not ok:
                        counts["http_in_fail"] += 1
                    lat_sum["http_in"] += latency_ms
                    lat_n["http_in"] += 1

                elif kind == "http_out":
                    counts["http_out_total"] += 1
                    if not ok:
                        counts["http_out_fail"] += 1
                    lat_sum["http_out"] += latency_ms
                    lat_n["http_out"] += 1

                elif kind == "llm":
                    counts["llm_total"] += 1
                    if not ok:
                        counts["llm_fail"] += 1
                    if ev.get("timeout"):
                        counts["llm_timeout"] += 1

                    lat_sum["llm"] += latency_ms
                    lat_n["llm"] += 1

                    rt = ev.get("request_type") or "unknown"
                    if rt not in llm_by_type:
                        _init_rt(rt)
                    d = llm_by_type[rt]
                    d["count"] += 1
                    d["_lat"] += latency_ms
                    d["_len"] += int(ev.get("response_len") or 0)
                    if ev.get("timeout"):
                        d["timeout"] += 1
                    if not ok:
                        d["fail"] += 1
                    if ev.get("tokens_in") is not None:
                        d["_tin"] += int(ev["tokens_in"]); d["_tin_n"] += 1
                    if ev.get("tokens_out") is not None:
                        d["_tout"] += int(ev["tokens_out"]); d["_tout_n"] += 1
                    if ev.get("cost") is not None:
                        d["_cost"] += float(ev["cost"]); d["_cost_n"] += 1

                elif kind == "interaction":
                    if name not in interactions:
                        interactions[name] = 0
                    interactions[name] += 1

                elif kind == "error":
                    counts["error_total"] += 1

                elif kind == "feedback":
                    counts["feedback_total"] += 1
                    if ev.get("rating") is not None:
                        rating_sum += int(ev["rating"]); rating_n += 1

                elif kind == "voice":
                    if "voice_total" not in counts: counts["voice_total"] = 0
                    counts["voice_total"] += 1

        latency_avg = {
            "http_in_avg": int(lat_sum["http_in"] / lat_n["http_in"]) if lat_n["http_in"] else 0,
            "http_out_avg": int(lat_sum["http_out"] / lat_n["http_out"]) if lat_n["http_out"] else 0,
            "llm_avg": int(lat_sum["llm"] / lat_n["llm"]) if lat_n["llm"] else 0,
        }
        rates = {
            "http_in_fail_rate": (counts["http_in_fail"] / counts["http_in_total"]) if counts["http_in_total"] else 0.0,
            "http_out_fail_rate": (counts["http_out_fail"] / counts["http_out_total"]) if counts["http_out_total"] else 0.0,
            "llm_fail_rate": (counts["llm_fail"] / counts["llm_total"]) if counts["llm_total"] else 0.0,
            "llm_timeout_rate": (counts["llm_timeout"] / counts["llm_total"]) if counts["llm_total"] else 0.0,
        }

        for rt, d in llm_by_type.items():
            d["avg_latency_ms"] = int(d["_lat"] / d["count"]) if d["count"] else 0
            d["avg_response_len"] = int(d["_len"] / d["count"]) if d["count"] else 0
            d["avg_tokens_in"] = int(d["_tin"] / d["_tin_n"]) if d["_tin_n"] else None
            d["avg_tokens_out"] = int(d["_tout"] / d["_tout_n"]) if d["_tout_n"] else None
            d["avg_cost"] = (d["_cost"] / d["_cost_n"]) if d["_cost_n"] else None
            for k in list(d.keys()):
                if k.startswith("_"):
                    d.pop(k, None)

        feedback = {"avg_rating": (rating_sum / rating_n) if rating_n else None, "rating_count": rating_n}

        summary = {
            "date": ymd,
            "counts": counts,
            "latency_ms": latency_avg,
            "rates": rates,
            "llm": llm_by_type,
            "feedback": feedback,
            "interactions": interactions
        }
        with open(self._summary_path(ymd), "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        return summary

    def get_daily_summary(self, ymd: str):
        # [MOD] Real-time update for today
        # If looking at today's stats, always recompute to show latest data
        import datetime
        today_str = datetime.datetime.utcnow().strftime("%Y-%m-%d")
        
        if ymd == today_str:
            return self.compute_daily_summary(ymd)

        if not os.path.exists(p):
            return self.compute_daily_summary(ymd)
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_global_average(self):
        """과거 모든 summary 파일을 읽어서 평균을 계산"""
        summary_files = [f for f in os.listdir(self.log_dir) if f.startswith("summary_") and f.endswith(".json")]
        
        total_tokens = 0
        total_latency = 0
        count_days = 0
        
        for f_name in summary_files:
            try:
                with open(os.path.join(self.log_dir, f_name), "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # LLM 섹션에서 토큰 합산
                    llm_data = data.get("llm", {})
                    daily_tokens = 0
                    daily_latency_sum = 0
                    daily_req_count = 0
                    
                    for rt, stats in llm_data.items():
                        t_in = stats.get("avg_tokens_in") or 0
                        t_out = stats.get("avg_tokens_out") or 0
                        count = stats.get("count") or 0
                        lat = stats.get("avg_latency_ms") or 0
                        
                        daily_tokens += (t_in + t_out) * count
                        daily_latency_sum += lat * count
                        daily_req_count += count
                        
                    if daily_req_count > 0:
                        total_tokens += daily_tokens
                        total_latency += (daily_latency_sum / daily_req_count) # 일일 평균 Latency 합산
                        count_days += 1
            except: 
                continue

        if count_days == 0:
            return {"avg_tokens": 0, "avg_latency": 0}
            
        return {
            "avg_tokens": int(total_tokens / count_days),
            "avg_latency": int(total_latency / count_days)
        }
