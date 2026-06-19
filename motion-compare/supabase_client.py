"""Singleton Supabase client cho motion-compare server.

Dùng service_role key (bypass RLS) vì server tin cậy.
Khi insert session, server tự gán user_id mà client đã gửi qua WebSocket init.
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

_url: str = os.environ.get("SUPABASE_URL", "")
_key: str = os.environ.get("SUPABASE_SERVICE_KEY", "")

if not _url or not _key:
    raise RuntimeError(
        "Chưa cấu hình SUPABASE_URL hoặc SUPABASE_SERVICE_KEY. "
        "Tạo file .env theo hướng dẫn Phần 7.2."
    )

supabase: Client = create_client(_url, _key)
