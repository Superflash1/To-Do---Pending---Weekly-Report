import json
import logging
import re
from datetime import date
from time import perf_counter
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


def _render_prompt_template(template: str, context: dict[str, Any]) -> str:
    rendered = template
    for key, value in context.items():
        rendered = rendered.replace(f"{{{key}}}", str(value))
    return rendered


def _extract_json_text(raw_text: str) -> str:
    text = str(raw_text or "").strip()
    if not text:
        return ""

    fenced_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if fenced_match:
        return fenced_match.group(1).strip()

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1].strip()

    return text


def _validate_classification_result(
    result: dict[str, Any],
    categories: list[str],
) -> dict[str, Any]:
    if bool(result.get("llm_failed")):
        result["category"] = None
        result["confidence"] = 0.0
        result["should_retry"] = True
        result["reason"] = str(result.get("reason") or "LLM请求失败，等待重试")
        return result

    confidence_raw = result.get("confidence", 0.0)
    try:
        confidence = float(confidence_raw)
    except (TypeError, ValueError):
        confidence = 0.0

    result["category"] = str(result.get("category") or "").strip()
    result["core_topic"] = str(result.get("core_topic") or "").strip()
    result["reason"] = str(result.get("reason") or "")
    result["confidence"] = max(0.0, min(1.0, confidence))
    result["should_retry"] = False
    result["existing_tag_count"] = len(categories)
    return result


class LLMService:
    async def classify_link(
        self,
        title: str,
        summary: str,
        categories: list[str],
        provider_config: dict[str, Any] | None = None,
        classification_prompt_template: str | None = None,
    ) -> dict[str, Any]:
        config = provider_config or {}
        api_key = str(config.get("api_key") or settings.llm_api_key or "").strip()

        def fallback_result(
            reason: str,
            raw_output: str = "",
            *,
            llm_failed: bool = False,
        ) -> dict[str, Any]:
            base = {
                "category": categories[0] if categories else "其他",
                "confidence": 0.5,
                "reason": reason,
                "raw_output": raw_output[:500],
                "llm_failed": llm_failed,
            }
            return _validate_classification_result(base, categories)

        if not api_key:
            return fallback_result("未配置LLM，使用默认分类")

        default_template = (
            "你是链接标签分类助手。\n"
            "任务：先提炼主题，再在现有标签中做语义匹配，并严格遵循阈值策略。\n\n"
            "输入：\n"
            "- 现有标签：{existing_tags}\n"
            "- 现有标签数量：{existing_tag_count}\n"
            "- 匹配阈值：{match_threshold}\n"
            "- 策略说明：{new_tag_policy}\n"
            "- 标题：{title}\n"
            "- 摘要：{summary}\n\n"
            "步骤：\n"
            "1) 先提炼核心主题（core_topic），一句话概括链接主要内容。\n"
            "2) 将 core_topic 与每个现有标签做语义相似度评估（0~1）。\n"
            "3) 选择相似度最高的标签作为 category，并将 confidence 输出为该最高相似度。\n"
            "4) 若最高相似度 < 匹配阈值，category 输出建议新标签名（不要输出“其他/未分类/未打标签”）。\n"
            "5) 禁止输出虚高置信度，必须反映真实语义接近程度。\n\n"
            "输出要求：\n"
            "- 只输出 JSON，不要任何额外文本\n"
            "- JSON 结构："
            "{\"core_topic\":\"...\",\"category\":\"最接近的已有标签或建议新标签名\",\"confidence\":0.0,\"reason\":\"简述主题与标签的语义关系，并说明是否低于阈值\"}"
        )
        template = (classification_prompt_template or default_template).strip()
        existing_tag_count = len(categories)
        match_threshold = 0.9 if existing_tag_count < 10 else 0.7
        new_tag_policy = (
            "当最高相似度 >= 阈值时必须复用现有标签；当最高相似度 < 阈值时建议新建标签。"
        )
        context = {
            "existing_tags": json.dumps(categories, ensure_ascii=False),
            "existing_tag_count": existing_tag_count,
            "match_threshold": f"{match_threshold:.1f}",
            "new_tag_policy": new_tag_policy,
            "title": title,
            "summary": summary,
        }
        prompt = _render_prompt_template(template, context)
        base_url = str(config.get("api_base_url") or settings.llm_base_url).rstrip("/")
        model = str(config.get("model") or settings.llm_model)

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "你是严谨的分类器。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
        }

        started = perf_counter()
        logger.info(
            "link_llm_request_start model=%s base_url=%s timeout_seconds=%s tag_count=%s",
            model,
            base_url,
            settings.llm_timeout_seconds,
            len(categories),
        )

        async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
            try:
                resp = await client.post(
                    f"{base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json=payload,
                )
                elapsed_ms = int((perf_counter() - started) * 1000)
                logger.info(
                    "link_llm_response_http status_code=%s elapsed_ms=%s",
                    resp.status_code,
                    elapsed_ms,
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception as exc:
                elapsed_ms = int((perf_counter() - started) * 1000)
                logger.warning(
                    "link_llm_request_failed elapsed_ms=%s error=%s",
                    elapsed_ms,
                    str(exc),
                )
                return fallback_result(f"LLM请求失败，等待重试: {exc}", llm_failed=True)

            choices = data.get("choices") if isinstance(data, dict) else None
            if not choices:
                logger.warning(
                    "link_llm_response_invalid_format data_type=%s preview=%s",
                    type(data).__name__,
                    json.dumps(data, ensure_ascii=False, default=str)[:200],
                )
                return fallback_result(
                    f"LLM返回格式异常，使用默认分类: {type(data).__name__}",
                    raw_output=json.dumps(data, ensure_ascii=False, default=str),
                )

            content = (
                (choices[0] or {}).get("message", {}).get("content")
                if isinstance(choices, list)
                else None
            )
            text = str(content or "").strip()
            logger.info("link_llm_response_content_length chars=%s", len(text))
            if not text:
                return fallback_result("LLM返回空内容，使用默认分类")

            json_text = _extract_json_text(text)
            try:
                parsed = json.loads(json_text)
                if isinstance(parsed, dict) and parsed.get("category"):
                    logger.info(
                        "link_llm_response_parsed category=%s confidence=%s core_topic=%s",
                        str(parsed.get("category") or ""),
                        str(parsed.get("confidence") or ""),
                        str(parsed.get("core_topic") or "")[:80],
                    )
                    parsed.setdefault("raw_output", text[:500])
                    parsed.setdefault("reason", "LLM分类成功")
                    return _validate_classification_result(parsed, categories)
            except json.JSONDecodeError:
                logger.warning(
                    "link_llm_response_json_decode_failed preview=%s extracted_preview=%s",
                    text[:200],
                    json_text[:200],
                )

            return fallback_result("LLM未返回可解析JSON，使用默认分类", raw_output=text)

    async def generate_weekly_report(
        self,
        prompt: str,
        facts: str,
        period_start: date,
        period_end: date,
        provider_config: dict[str, Any] | None = None,
    ) -> str:
        config = provider_config or {}
        api_key = str(config.get("api_key") or settings.llm_api_key or "").strip()
        if not api_key:
            return f"【简洁执行版周报】\n\n{facts}"

        base_url = str(config.get("api_base_url") or settings.llm_base_url).rstrip("/")
        model = str(config.get("model") or settings.llm_model)

        period_start_text = period_start.isoformat()
        period_end_text = period_end.isoformat()
        period_range_text = f"{period_start_text} 至 {period_end_text}"
        prompt_rendered = _render_prompt_template(
            prompt,
            {
                "completed_start_date": period_start_text,
                "completed_end_date": period_end_text,
                "completed_range_text": period_range_text,
            },
        )

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "你是周报助手，输出简洁执行版周报。"},
                {
                    "role": "user",
                    "content": f"{prompt_rendered}\n\n已完成事项时间范围：{period_range_text}\n\n以下是已完成事项:\n{facts}",
                },
            ],
            "temperature": 0.2,
        }
        async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
            try:
                resp = await client.post(
                    f"{base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception:
                return f"【简洁执行版周报】\n\n{facts}"

            choices = data.get("choices") if isinstance(data, dict) else None
            if not choices:
                return f"【简洁执行版周报】\n\n{facts}"

            content = (
                (choices[0] or {}).get("message", {}).get("content")
                if isinstance(choices, list)
                else None
            )
            return str(content or f"【简洁执行版周报】\n\n{facts}")


llm_service = LLMService()
