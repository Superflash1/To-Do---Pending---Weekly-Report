import json
from datetime import date
from typing import Any

import httpx

from app.config import settings


def _render_prompt_template(template: str, context: dict[str, Any]) -> str:
    rendered = template
    for key, value in context.items():
        rendered = rendered.replace(f"{{{key}}}", str(value))
    return rendered


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
        if not api_key:
            return {
                "category": categories[0] if categories else "未分类",
                "confidence": 0.5,
                "reason": "未配置LLM，使用默认分类",
            }

        default_template = (
            "你是链接标签助手。请严格先从 {existing_tags} 中选择一个最匹配标签；"
            "只有都不匹配时才创建新标签。"
            "链接标题：{title}；链接摘要：{summary}。"
            "输出JSON: {\"category\":\"...\",\"confidence\":0-1,\"reason\":\"...\"}"
        )
        template = (classification_prompt_template or default_template).strip()
        context = {
            "existing_tags": json.dumps(categories, ensure_ascii=False),
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

        async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
            try:
                resp = await client.post(
                    f"{base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception as exc:
                return {
                    "category": categories[0] if categories else "未分类",
                    "confidence": 0.5,
                    "reason": f"LLM请求失败，使用默认分类: {exc}",
                }

            choices = data.get("choices") if isinstance(data, dict) else None
            if not choices:
                return {
                    "category": categories[0] if categories else "未分类",
                    "confidence": 0.5,
                    "reason": f"LLM返回格式异常，使用默认分类: {data}",
                }

            content = (
                (choices[0] or {}).get("message", {}).get("content")
                if isinstance(choices, list)
                else None
            )
            text = str(content or "").strip()
            if not text:
                return {
                    "category": categories[0] if categories else "未分类",
                    "confidence": 0.5,
                    "reason": "LLM返回空内容，使用默认分类",
                }

            try:
                parsed = json.loads(text)
                if isinstance(parsed, dict) and parsed.get("category"):
                    return parsed
            except json.JSONDecodeError:
                pass

            return {
                "category": categories[0] if categories else "未分类",
                "confidence": 0.5,
                "reason": f"LLM未返回可解析JSON，使用默认分类: {text}",
            }

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
