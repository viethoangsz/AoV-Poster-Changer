#!/usr/bin/env python3
"""
AoV Poster Changer – Local proxy server
Serves index.html + proxies Pinterest search, removebg, and image CORS.
"""
import gzip
import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from io import BytesIO

# ── Pinterest credentials (hardcoded) ────────────────────────────────────────
PINTEREST_SESSION = (
    "TWc9PSZ1SUhVTTZmU3prL3gvdmFBMWE3OUZuWERuQTlYbDR6cGxpN3BONXpNakZrd00wN1BPY2FFcCtLT2J1WXZGdWdoaHlrOE02TnpOTHp2M0duN3hmMUdaYisya29KY2ptOU9ZdnNJdVQvK3NSRE82VGNkZzNpUDAxM1F1SEdSbFdrTEI2NFFzbnNzbmxvRUk3Wjd6ZE53NGhSZDBjRGF2YTBZNkpQWFg3U0VUMTFWWllJdjVTOHpUSXBHTXNGYnpmTEFNTHJ6YTEvaUxuR0R0UjkyaXdiWG0rREg0bHFORGE2T0prN0ltUnpWb2Yyb012OXQzZHUwOFN1RTZyQW5MSm5MN3haSXlxbXZnM2dJMnlHdW8xWUp6Ty9qM2RzVWR3eW9JV01sRHVEc1hROVdSN2hwQjliQ3RrSXFRRHF1K2FDVXBGeHAwUnExSGlzM2dnRWIwSHBaeU9lb0c2dkg3aXpndyt1YVZyNzhWNEE3OVliWmtLUUdIaGxKeEJBYzA2U2pJL3c3SFF4MmlsQ0R0YkNBSjZWTFVsS21JTmNFZjNBSVYvZkpsOWZRNVpReWUrRW9Xc29Pa0l6SG9TdWVPZ3ptN0swdGxhcWlrUm1nQ1NJejNFbUtVSkkrdkRDemt2MnNQNWhOeGF0YlFObVRLanE1R3UvTWNIWmFCUkVhc2lGcWQxYWdvTVMzS1lBNW9DZS8zMG5PNGFJbkM4Qk94YWQ1Y2FNVnRscVBMZE92ZU5PZnVhbEJuL01vRlVPUUFMT3pkcVo2UTB5Wm1rZVl3ejRRUmxXdWFKRjZZMlI2dE8rb0Q3U2xNdzRpb2h3em1VSXlWUllpbmg4RDJMeU1oUUlyRmYxMDZsZW13VTQ0VlVPWW55cWM4ZjNYV0ZNSDVvZzFBYTB2RXhZUVluNTZsRndOYlFFcElqK204U2RNUG5YOUZzbldVQzU1OEVrSk80cW55WGFzYU5zckJNdk0zbDhacUVkMWFLNWVST0Q3azE5TTVYVERBait5Y0w5cS9zVnJtRTg5K2M2LysydnFCQ1pUZEtPOGpabURWUy82Y3ZZUVNqWEtPdjQwaERxVmtETHpCUlZkbTQwa3lZaU9rdnVBQjdFNVBpb1VkY2c1bEtjYTVyNnNEcWJYK2FjbWtrc3prRXN6T2Y3N0VhYjZQQ01zMDdoaHp0Qjg2NkxuNXdKN3B2Wk91SzY0NENxRldvUzZObGJlT09nclRxekp5S0ExcEVPN1Nnbmc3RFgzZEtpaWJPRDJmeHdKMTg2SHRWQWU5SCtqOWViNWVFQlJoVGxNd1FLNjlVemNyU3VqT1d3NzhoekJreW5qaWJMa2xxZDlDTEtLbUVIVWtMM1luWjZmSUhCVjN3NUhvVXhrVHA4QndtTjBRbXphZ0lMdytsRXFSdlBHMmo4dkxXeE9OVHJsM3FDTTZ6cWQ5NXc1U2pjUHZvc2lQajE3TEhlZzViZDJFaVk4dEhaSzBNRm5OaHg4b2o5TUl1NGhvTmE2bE0rMlpHVTFDeXVqeWlwYjRiMU1Fd3RvNGNPK253WmxaN0hZNUNkTi9oUk1WeGU3OTBOM0JGMEgreUYwbTdzdTE4Rk5tUGJya1VrYUtGQ1BEcmU1ZkppRWZtTmo1cEZHekpnZ0JiMHRYcC9RcnB1M2RnWVlOOFNZTDY3SlJmN3FydlRuRHdmUDVnb29aWFlOV2U1MG5aS093Uzl0Q2h4Nk00QWlrZGtBWFN1S1hMTTFVK24wSzRpSVpVYTVWKzltbE5VMjhtMm9GQjVEN0xsSkFUbE8mQllBSUhUMlNYODdvcGFGVVlqaHpMMXFYdHhFPQ=="
)
PINTEREST_CSRF = "34da91b881248b605349483453d6727c"
REMOVEBG_API   = "https://lavender-api-website.onrender.com/api/removebg"

_ssl = ssl.create_default_context()
_ssl.check_hostname = False
_ssl.verify_mode = ssl.CERT_NONE


class Handler(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    # ── CORS pre-flight ──────────────────────────────────────────────────────
    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    # ── POST router ──────────────────────────────────────────────────────────
    def do_POST(self):
        if self.path == "/api/pinterest/search":
            self._pinterest_search()
        elif self.path == "/api/removebg":
            self._removebg()
        elif self.path == "/api/satoru/upscale":
            self._satoru_upscale()
        elif self.path == "/api/aov":
            self._aov_proxy()
        else:
            self.send_error(404)

    def do_PUT(self):
        if self.path == "/api/cos-upload":
            self._cos_proxy()
        else:
            self.send_error(404)

    # ── AoV API proxy (POST → kgvn-api.mobagarena.com) ──────────────────────
    def _aov_proxy(self):
        length = int(self.headers.get("Content-Length") or 0)
        body   = self.rfile.read(length)
        try:
            meta   = json.loads(body)
            target = meta["url"]
            hdrs   = meta.get("headers", {})
            payload= meta.get("body", None)
        except Exception:
            self._json({"error": "Bad request"}, 400); return

        if "kgvn-api.mobagarena.com" not in target:
            self._json({"error": "Forbidden target"}, 403); return

        req_body = json.dumps(payload).encode() if payload is not None else b"{}"
        req_hdrs = {k: v for k, v in hdrs.items()}
        req_hdrs["Content-Length"] = str(len(req_body))
        req_hdrs.setdefault("Content-Type", "application/json")

        req = urllib.request.Request(target, data=req_body, headers=req_hdrs, method="POST")
        try:
            with urllib.request.urlopen(req, context=_ssl, timeout=30) as r:
                raw = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self._cors()
            self.end_headers()
            self.wfile.write(raw)
        except urllib.error.HTTPError as e:
            err = e.read()
            self.send_response(e.code)
            self.send_header("Content-Type", "application/json")
            self._cors()
            self.end_headers()
            self.wfile.write(err or json.dumps({"error": f"HTTP {e.code}"}).encode())
        except Exception as e:
            self._json({"error": str(e)}, 502)

    # ── Tencent COS upload proxy (PUT) ───────────────────────────────────────
    def _cos_proxy(self):
        import http.client
        length = int(self.headers.get("Content-Length") or 0)
        body   = self.rfile.read(length)
        target = self.headers.get("X-Cos-Target", "")
        if not target or "myqcloud.com" not in target:
            self._json({"error": "Missing or forbidden X-Cos-Target"}, 400); return

        parsed = urllib.parse.urlparse(target)
        host   = parsed.netloc
        path   = parsed.path + (f"?{parsed.query}" if parsed.query else "")

        # Only forward headers that COS signature covers — do NOT include Host
        # (http.client sets Host automatically from the connection)
        fwd_hdrs = {"Content-Length": str(len(body))}
        for h in ["Authorization", "x-cos-security-token", "x-cos-forbid-overwrite",
                   "Content-Type", "Origin", "Referer"]:
            v = self.headers.get(h)
            if v:
                fwd_hdrs[h] = v

        try:
            conn = http.client.HTTPSConnection(host, timeout=60, context=_ssl)
            conn.request("PUT", path, body=body, headers=fwd_hdrs)
            resp = conn.getresponse()
            resp_body = resp.read()
            conn.close()
            if resp.status in (200, 204):
                self.send_response(200)
                self._cors()
                self.end_headers()
            else:
                self.send_response(resp.status)
                self.send_header("Content-Type", "text/xml")
                self.send_header("Content-Length", str(len(resp_body)))
                self._cors()
                self.end_headers()
                self.wfile.write(resp_body)
        except Exception as e:
            self._json({"error": str(e)}, 502)

    # ── Satoru lamnet upscale proxy ──────────────────────────────────────────
    def _satoru_upscale(self):
        import os, uuid, time
        # Parse image bytes from multipart sent by browser
        length = int(self.headers.get("Content-Length") or 0)
        body   = self.rfile.read(length)
        ct     = self.headers.get("Content-Type") or ""

        # Extract raw image bytes from multipart (find the binary part after double CRLF)
        img_bytes = body
        if "multipart" in ct:
            marker = b"\r\n\r\n"
            idx = body.find(marker)
            if idx != -1:
                raw = body[idx + 4:]
                bound_str = ""
                for part in ct.split(";"):
                    part = part.strip()
                    if part.startswith("boundary="):
                        bound_str = part[9:].strip('"')
                if bound_str:
                    trailer = f"\r\n--{bound_str}".encode()
                    end_idx = raw.rfind(trailer)
                    if end_idx != -1:
                        raw = raw[:end_idx]
                img_bytes = raw

        # Save to a temp file served publicly under /tmp-img/
        tmp_dir = os.path.join(os.path.dirname(__file__), "_tmp_img")
        os.makedirs(tmp_dir, exist_ok=True)
        fname   = uuid.uuid4().hex + ".png"
        fpath   = os.path.join(tmp_dir, fname)
        with open(fpath, "wb") as f:
            f.write(img_bytes)

        domain  = os.environ.get("REPLIT_DEV_DOMAIN", "localhost:5000")
        pub_url = f"https://{domain}/tmp-img/{fname}"

        def _is_real_image(data: bytes) -> bool:
            """Return True if data looks like a real image (not HTML)."""
            if len(data) < 500:
                return False
            head = data[:16]
            # JPEG, PNG, GIF, WEBP, BMP
            return (head[:2] == b'\xff\xd8' or
                    head[:4] == b'\x89PNG' or
                    head[:4] == b'GIF8' or
                    head[8:12] == b'WEBP' or
                    head[:2] == b'BM')

        def _pillow_upscale(src: bytes) -> bytes:
            """Fallback: 2× LANCZOS upscale using Pillow."""
            from PIL import Image
            from io import BytesIO
            img = Image.open(BytesIO(src))
            w, h = img.size
            up = img.resize((w * 2, h * 2), Image.LANCZOS)
            out = BytesIO()
            fmt = "JPEG" if img.format == "JPEG" else "PNG"
            up.save(out, format=fmt, quality=92)
            return out.getvalue(), ("image/jpeg" if fmt == "JPEG" else "image/png")

        try:
            # ── Step 1: call Satoru API ──────────────────────────────────────
            result_data = None
            result_ct   = "image/jpeg"
            satoru_ok   = False

            try:
                api_body = json.dumps({"url": pub_url}).encode()
                api_req  = urllib.request.Request(
                    "https://api.satoru.click/api/lamnet",
                    data=api_body,
                    headers={
                        "Content-Type":   "application/json",
                        "Content-Length": str(len(api_body)),
                        "User-Agent":     "Mozilla/5.0",
                        "Accept":         "application/json",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(api_req, context=_ssl, timeout=90) as r:
                    api_resp = json.loads(r.read())

                enhanced_url = (api_resp.get("enhancedImageUrl") or
                                api_resp.get("result_url") or "") if api_resp.get("success") else ""

                # ── Step 2: download result with retries ─────────────────────
                if enhanced_url:
                    for attempt in range(4):
                        if attempt > 0:
                            time.sleep(2)
                        try:
                            dl_req = urllib.request.Request(
                                enhanced_url,
                                headers={
                                    "User-Agent": "Mozilla/5.0",
                                    "Accept":     "image/jpeg,image/*,*/*",
                                    "Referer":    "https://api.satoru.click/",
                                },
                            )
                            with urllib.request.urlopen(dl_req, context=_ssl, timeout=30) as r2:
                                candidate  = r2.read()
                                candidate_ct = r2.headers.get("Content-Type", "image/jpeg")
                            if _is_real_image(candidate):
                                result_data = candidate
                                result_ct   = candidate_ct
                                satoru_ok   = True
                                break
                        except Exception:
                            pass
            except Exception:
                pass  # Satoru API itself failed → fall through to Pillow

            # ── Step 3: Pillow fallback if Satoru didn't deliver ─────────────
            if not satoru_ok:
                result_data, result_ct = _pillow_upscale(img_bytes)

            self.send_response(200)
            self.send_header("Content-Type", result_ct)
            self.send_header("Content-Length", str(len(result_data)))
            self._cors()
            self.end_headers()
            self.wfile.write(result_data)

        except urllib.error.HTTPError as e:
            err_body = e.read()
            self.send_response(e.code)
            self.send_header("Content-Type", "application/json")
            self._cors()
            self.end_headers()
            self.wfile.write(err_body if err_body else
                             json.dumps({"error": f"Upscale HTTP {e.code}"}).encode())
        except Exception as e:
            self._json({"success": False, "error": f"Upscale lỗi: {e}"}, 502)
        finally:
            try:
                os.remove(fpath)
            except Exception:
                pass

    # ── image proxy (GET /api/proxy-image?url=...) ──────────────────────────
    def do_GET(self):
        if self.path.startswith("/api/removebg"):
            qs = urllib.parse.urlparse(self.path).query
            params = dict(urllib.parse.parse_qsl(qs))
            img_url = params.get("url", "")
            if not img_url:
                self.send_error(400, "Missing url param"); return
            target = f"{REMOVEBG_API}?url={urllib.parse.quote(img_url, safe='')}"
            req = urllib.request.Request(target, headers={"User-Agent": "Mozilla/5.0"})
            try:
                with urllib.request.urlopen(req, context=_ssl, timeout=60) as r:
                    resp_data = r.read()
                    resp_ct   = r.headers.get("Content-Type", "application/json")
                self.send_response(200)
                self.send_header("Content-Type", resp_ct)
                self.send_header("Content-Length", str(len(resp_data)))
                self._cors()
                self.end_headers()
                self.wfile.write(resp_data)
            except urllib.error.HTTPError as e:
                err_body = e.read()
                self.send_response(e.code)
                self.send_header("Content-Type", "application/json")
                self._cors()
                self.end_headers()
                self.wfile.write(err_body)
            except Exception as e:
                self._json({"success": False, "error": str(e)}, 502)
        elif self.path.startswith("/tmp-img/"):
            import os
            fname   = self.path[len("/tmp-img/"):]
            tmp_dir = os.path.join(os.path.dirname(__file__), "_tmp_img")
            fpath   = os.path.join(tmp_dir, fname)
            if not os.path.isfile(fpath):
                self.send_error(404, "Not found"); return
            with open(fpath, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(data)))
            self._cors()
            self.end_headers()
            self.wfile.write(data)
        elif self.path.startswith("/api/proxy-image"):
            qs = urllib.parse.urlparse(self.path).query
            params = dict(urllib.parse.parse_qsl(qs))
            img_url = params.get("url", "")
            if not img_url:
                self.send_error(400, "Missing url param"); return
            try:
                req = urllib.request.Request(
                    img_url,
                    headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.pinterest.com/"},
                )
                with urllib.request.urlopen(req, context=_ssl, timeout=20) as r:
                    data = r.read()
                    ct   = r.headers.get("Content-Type", "image/jpeg")
                self.send_response(200)
                self.send_header("Content-Type", ct)
                self.send_header("Content-Length", str(len(data)))
                self._cors()
                self.end_headers()
                self.wfile.write(data)
            except Exception as e:
                self.send_error(502, str(e))
        else:
            super().do_GET()


    # ── Pinterest search ─────────────────────────────────────────────────────
    def _pinterest_search(self):
        body = self._read_body()
        try:
            params = json.loads(body)
        except Exception:
            self._json({"success": False, "error": "Bad JSON"}, 400); return

        q     = (params.get("q") or "").strip()
        limit = min(int(params.get("limit") or 18), 50)
        if not q:
            self._json({"success": False, "error": "Missing q"}, 400); return

        cookie   = f"_pinterest_sess={PINTEREST_SESSION}; _auth=1; csrftoken={PINTEREST_CSRF}"
        post_data = urllib.parse.urlencode({
            "source_url": f"/search/pins/?q={urllib.parse.quote(q)}&rs=typed",
            "data": json.dumps({
                "options": {"query": q, "scope": "pins", "rs": "typed", "redux_normalize_feed": True},
                "context": {},
            }),
        }).encode()

        req = urllib.request.Request(
            "https://www.pinterest.com/resource/BaseSearchResource/get/",
            data=post_data,
            headers={
                "accept":                 "application/json, text/javascript, */*, q=0.01",
                "content-type":           "application/x-www-form-urlencoded",
                "x-requested-with":       "XMLHttpRequest",
                "x-pinterest-appstate":   "active",
                "x-csrftoken":            PINTEREST_CSRF,
                "user-agent":             "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
                "referer":                "https://www.pinterest.com/",
                "origin":                 "https://www.pinterest.com",
                "cookie":                 cookie,
                "accept-encoding":        "gzip",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, context=_ssl, timeout=25) as r:
                raw = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
                data = json.loads(raw)
        except urllib.error.HTTPError as e:
            self._json({"success": False, "error": f"Pinterest HTTP {e.code}"}, 502); return
        except Exception as e:
            self._json({"success": False, "error": str(e)}, 502); return

        results = data.get("resource_response", {}).get("data", {}).get("results", [])
        pins = []
        for pin in results[:limit]:
            imgs = pin.get("images") or {}
            pins.append({
                "id":            pin.get("id"),
                "title":         pin.get("title") or "",
                "description":   pin.get("description") or "",
                "pin_url":       f"https://www.pinterest.com/pin/{pin.get('id')}/",
                "dominant_color":pin.get("dominant_color") or "",
                "images": {
                    "thumb":    (imgs.get("236x") or {}).get("url"),
                    "medium":   (imgs.get("474x") or {}).get("url"),
                    "large":    (imgs.get("736x") or {}).get("url"),
                    "original": (imgs.get("orig") or {}).get("url"),
                },
            })
        self._json({"success": True, "data": {"query": q, "total": len(pins), "pins": pins}})

    # ── removebg proxy ───────────────────────────────────────────────────────
    def _removebg(self):
        length = int(self.headers.get("Content-Length") or 0)
        body   = self.rfile.read(length)
        ct     = self.headers.get("Content-Type") or "application/octet-stream"

        req = urllib.request.Request(
            REMOVEBG_API,
            data=body,
            headers={"Content-Type": ct, "Content-Length": str(len(body))},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, context=_ssl, timeout=60) as r:
                resp_data = r.read()
                resp_ct   = r.headers.get("Content-Type", "application/json")
            self.send_response(200)
            self.send_header("Content-Type", resp_ct)
            self.send_header("Content-Length", str(len(resp_data)))
            self._cors()
            self.end_headers()
            self.wfile.write(resp_data)
        except urllib.error.HTTPError as e:
            err_body = e.read()
            self.send_response(e.code)
            self.send_header("Content-Type", "application/json")
            self._cors()
            self.end_headers()
            self.wfile.write(err_body)
        except Exception as e:
            self._json({"success": False, "error": str(e)}, 500)

    # ── helpers ──────────────────────────────────────────────────────────────
    def _read_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(length)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass  # silent


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"AoV Poster Changer server → http://0.0.0.0:{port}")
    server.serve_forever()
