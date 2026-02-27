#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一 AI 模型调用类

所有需要调用大模型的地方统一通过此类进行，支持:
- 多提供商配置（OpenAI 兼容接口 / 自定义 URL）
- 按调用者（caller）动态路由到不同模型
- 配置以 JSON 持久化到本地文件
"""

import os
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'data', 'ai_models.json'
)


def _default_config() -> Dict[str, Any]:
    return {
        'providers': [],
        'caller_mapping': {},
        'default_provider_id': '',
    }


def _load_config() -> Dict[str, Any]:
    if os.path.exists(_CONFIG_PATH):
        try:
            with open(_CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"读取 AI 模型配置失败: {e}")
    return _default_config()


def _save_config(cfg: Dict[str, Any]):
    os.makedirs(os.path.dirname(_CONFIG_PATH), exist_ok=True)
    with open(_CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


class AIModelManager:
    """
    AI 模型管理器 — 单例式使用

    提供商数据结构:
    {
      "id": "minimax-1",
      "name": "MiniMax",
      "base_url": "https://api.minimaxi.com/v1",
      "model_id": "MiniMax-M2.5",
      "api_key": "sk-xxx",
      "enabled": true,
      "created_at": "2026-02-27 10:00:00"
    }

    调用者映射:
    {
      "deep_analysis": "minimax-1",
      "stock_analyzer": "openai-1",
      ...
    }
    """

    # 预定义的调用者标识
    CALLERS = {
        'deep_analysis': '深度分析',
        'stock_analyzer': '股票分析引擎',
        'explain_generator': '策略解释生成',
        'daily_report': '日报生成',
        'general': '通用调用',
    }

    def __init__(self):
        self._cfg = _load_config()

    def reload(self):
        self._cfg = _load_config()

    def _save(self):
        _save_config(self._cfg)

    # ------------------------------------------------------------------
    # 提供商 CRUD
    # ------------------------------------------------------------------

    def list_providers(self) -> List[Dict[str, Any]]:
        return self._cfg.get('providers', [])

    def get_provider(self, provider_id: str) -> Optional[Dict[str, Any]]:
        for p in self._cfg.get('providers', []):
            if p['id'] == provider_id:
                return p
        return None

    def add_provider(self, data: Dict[str, Any]) -> Dict[str, Any]:
        pid = data.get('id') or f"provider-{int(datetime.now().timestamp())}"
        provider = {
            'id': pid,
            'name': data.get('name', '自定义'),
            'base_url': data.get('base_url', ''),
            'model_id': data.get('model_id', ''),
            'api_key': data.get('api_key', ''),
            'enabled': data.get('enabled', True),
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        self._cfg.setdefault('providers', []).append(provider)
        if not self._cfg.get('default_provider_id'):
            self._cfg['default_provider_id'] = pid
        self._save()
        return provider

    def update_provider(self, provider_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        for p in self._cfg.get('providers', []):
            if p['id'] == provider_id:
                for k in ('name', 'base_url', 'model_id', 'api_key', 'enabled'):
                    if k in data:
                        p[k] = data[k]
                self._save()
                return p
        return None

    def delete_provider(self, provider_id: str) -> bool:
        providers = self._cfg.get('providers', [])
        before = len(providers)
        self._cfg['providers'] = [p for p in providers if p['id'] != provider_id]
        if self._cfg.get('default_provider_id') == provider_id:
            self._cfg['default_provider_id'] = self._cfg['providers'][0]['id'] if self._cfg['providers'] else ''
        mapping = self._cfg.get('caller_mapping', {})
        for k, v in list(mapping.items()):
            if v == provider_id:
                del mapping[k]
        self._save()
        return len(self._cfg['providers']) < before

    def set_default_provider(self, provider_id: str):
        self._cfg['default_provider_id'] = provider_id
        self._save()

    # ------------------------------------------------------------------
    # 调用者映射
    # ------------------------------------------------------------------

    def get_caller_mapping(self) -> Dict[str, str]:
        return self._cfg.get('caller_mapping', {})

    def set_caller_provider(self, caller: str, provider_id: str):
        self._cfg.setdefault('caller_mapping', {})[caller] = provider_id
        self._save()

    def remove_caller_mapping(self, caller: str):
        self._cfg.get('caller_mapping', {}).pop(caller, None)
        self._save()

    def get_caller_list(self) -> List[Dict[str, str]]:
        """返回所有调用者信息及其当前绑定"""
        mapping = self._cfg.get('caller_mapping', {})
        result = []
        for cid, label in self.CALLERS.items():
            result.append({
                'caller_id': cid,
                'label': label,
                'provider_id': mapping.get(cid, ''),
            })
        return result

    # ------------------------------------------------------------------
    # 统一模型调用
    # ------------------------------------------------------------------

    def _resolve_provider(self, caller: str = 'general') -> Optional[Dict[str, Any]]:
        mapping = self._cfg.get('caller_mapping', {})
        pid = mapping.get(caller) or self._cfg.get('default_provider_id', '')
        if pid:
            p = self.get_provider(pid)
            if p and p.get('enabled', True):
                return p
        for p in self._cfg.get('providers', []):
            if p.get('enabled', True):
                return p
        return None

    def chat(self, prompt: str, caller: str = 'general',
             system_prompt: str = '', max_tokens: int = 4000,
             temperature: float = 0.7) -> str:
        """
        统一模型调用入口

        @param prompt        用户提示词
        @param caller        调用者标识（用于路由到不同模型）
        @param system_prompt 系统提示词
        @param max_tokens    最大 token 数
        @param temperature   温度
        @returns 模型回复文本；无可用模型时返回空字符串
        """
        provider = self._resolve_provider(caller)
        if not provider:
            logger.warning(f"[{caller}] 无可用 AI 模型提供商")
            return ''

        base_url = provider.get('base_url', '').rstrip('/')
        model_id = provider.get('model_id', '')
        api_key = provider.get('api_key', '')

        if not base_url or not api_key:
            logger.warning(f"[{caller}] 提供商 {provider['name']} 配置不完整")
            return ''

        logger.info(f"[{caller}] 调用模型 {provider['name']} / {model_id}")

        try:
            import requests
            messages = []
            if system_prompt:
                messages.append({'role': 'system', 'content': system_prompt})
            messages.append({'role': 'user', 'content': prompt})

            resp = requests.post(
                f"{base_url}/chat/completions",
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json',
                },
                json={
                    'model': model_id,
                    'messages': messages,
                    'max_tokens': max_tokens,
                    'temperature': temperature,
                },
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data['choices'][0]['message']['content']
            logger.info(f"[{caller}] 模型调用成功，返回 {len(content)} 字符")
            return content
        except Exception as e:
            logger.error(f"[{caller}] 模型调用失败: {e}")
            return ''

    def test_provider(self, provider_id: str) -> Dict[str, Any]:
        """测试提供商连通性"""
        provider = self.get_provider(provider_id)
        if not provider:
            return {'success': False, 'message': '提供商不存在'}

        base_url = provider.get('base_url', '').rstrip('/')
        api_key = provider.get('api_key', '')
        model_id = provider.get('model_id', '')

        if not base_url or not api_key:
            return {'success': False, 'message': '配置不完整，请填写 URL 和 API Key'}

        try:
            import requests
            resp = requests.post(
                f"{base_url}/chat/completions",
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json',
                },
                json={
                    'model': model_id,
                    'messages': [{'role': 'user', 'content': '请回复"连接成功"'}],
                    'max_tokens': 20,
                },
                timeout=30,
            )
            if resp.status_code == 200:
                data = resp.json()
                reply = data.get('choices', [{}])[0].get('message', {}).get('content', '')
                return {'success': True, 'message': f'连接成功: {reply[:50]}'}
            else:
                return {'success': False, 'message': f'HTTP {resp.status_code}: {resp.text[:200]}'}
        except Exception as e:
            return {'success': False, 'message': f'连接失败: {str(e)}'}


# 全局单例
_instance: Optional[AIModelManager] = None


def get_ai_model_manager() -> AIModelManager:
    global _instance
    if _instance is None:
        _instance = AIModelManager()
    return _instance
