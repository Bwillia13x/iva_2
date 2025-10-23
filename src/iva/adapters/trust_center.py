import asyncio, socket, ssl
from urllib.parse import urlparse
from datetime import datetime
import httpx
from ..models.sources import AdapterFinding, Citation

async def check_security_txt(base_url: str):
    url = base_url.rstrip("/") + "/.well-known/security.txt"
    async with httpx.AsyncClient() as client:
        r = await client.get(url, follow_redirects=True)
        if r.status_code == 200 and "Contact:" in r.text:
            return True, url
    return False, url

def tls_expiry(domain: str):
    ctx = ssl.create_default_context()
    with socket.create_connection((domain, 443), timeout=5) as sock:
        with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
            cert = ssock.getpeercert()
            return cert.get("notAfter","")

async def check_trust_center(base_url: str) -> list[AdapterFinding]:
    findings = []
    has_sec, sec_url = await check_security_txt(base_url)
    findings.append(AdapterFinding(
        key="security_txt",
        value=str(has_sec),
        status="confirmed" if has_sec else "not_found",
        citations=[Citation(source="security.txt", url=sec_url, query="", accessed_at=datetime.utcnow())]
    ))
    domain = urlparse(base_url).hostname or base_url
    exp = tls_expiry(domain)
    findings.append(AdapterFinding(
        key="tls_cert_expiry",
        value=str(exp),
        status="confirmed" if exp else "unknown",
        citations=[Citation(source="TLS", url=base_url, query="", accessed_at=datetime.utcnow())]
    ))
    return findings
