import logging
import os
import requests
import azure.functions as func
import json
from requests_toolbelt.multipart.decoder import MultipartDecoder

TOKEN_URL = "https://login.microsoftonline.com/botframework.com/oauth2/v2.0/token"
def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        ctype = req.headers.get('Content-Type', '')
        body = req.get_body()

        # 1) multipart/form-data 인지 확인
        if 'multipart/form-data' in ctype:
            # multipart 파싱
            decoder = MultipartDecoder(body, ctype)

            file_text = None
            filename = None

            for part in decoder.parts:
                # Content-Disposition 헤더에서 form 필드명/파일명 확인
                cd = part.headers.get(b'Content-Disposition', b'').decode('utf-8', errors='ignore')
                # 예: form-data; name="file"; filename="something.json"
                if 'filename=' in cd:
                    # 파일 파트
                    # 파일명 추출
                    for token in cd.split(';'):
                        token = token.strip()
                        if token.startswith('filename='):
                            filename = token.split('=', 1)[1].strip('"')
                            break

                    # 바이트 → 문자열
                    payload_bytes = part.content
                    try:
                        # JSON 파일은 보통 UTF-8
                        file_text = payload_bytes.decode('utf-8')
                    except UnicodeDecodeError:
                        return func.HttpResponse("Invalid text encoding (expect UTF-8).", status_code=400)

            # 여기서 data를 원하는 형태로 사용/가공

            result = {
                "text": file_text
             }

            return func.HttpResponse(json.dumps(result, ensure_ascii=False), mimetype="application/json", status_code=200)

        # 2) 그냥 application/json 본문으로 오는 경우도 지원(옵션)
        elif 'application/json' in ctype:
            try:
                data = req.get_json()
            except ValueError:
                return func.HttpResponse("Invalid JSON body.", status_code=400)

            return func.HttpResponse(json.dumps({"type": "json-body", "keys": list(data.keys()) if isinstance(data, dict) else None}, ensure_ascii=False),
                                     mimetype="application/json", status_code=200)

        else:
            return func.HttpResponse("Use multipart/form-data with a JSON file (field name arbitrary).", status_code=415)

    except Exception as ex:
        return func.HttpResponse(f"Server error: {ex}", status_code=500)

def get_bot_token(app_id, secret):
    form = {
        "grant_type": "client_credentials",
        "client_id": app_id,
        "client_secret": secret,
        "scope": "https://api.botframework.com/.default"
    }
    r = requests.post(TOKEN_URL, data=form)
    r.raise_for_status()
    return r.json()["access_token"]

def json_escape(s: str) -> str:
    """간단한 JSON 문자열 이스케이프"""
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'