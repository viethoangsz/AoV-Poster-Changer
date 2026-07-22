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
from http.server import HTTPServer, SimpleHTTPRequestHandler
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
        elif self.path == "/api/pollinations/upscale":
            self._pollinations_upscale()
        else:
            self.send_error(404)

    # ── Pollinations upscale proxy ───────────────────────────────────────────
    def _pollinations_upscale(self):
        length = int(self.headers.get("Content-Length") or 0)
        body   = self.rfile.read(length)
        ct     = self.headers.get("Content-Type") or "application/octet-stream"
        req = urllib.request.Request(
            "https://image.pollinations.ai/models/upscale",
            data=body,
            headers={"Content-Type": ct, "Content-Length": str(len(body))},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, context=_ssl, timeout=120) as r:
                resp_data = r.read()
                resp_ct   = r.headers.get("Content-Type", "image/png")
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
            self.wfile.write(err_body if err_body else
                             json.dumps({"error": f"Pollinations HTTP {e.code}"}).encode())
        except Exception as e:
            self._json({"success": False, "error": str(e)}, 502)

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
    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"AoV Poster Changer server → http://0.0.0.0:{port}")
    server.serve_forever()
