import asyncio
import time

import httpx

from .base import Finding, Result, Source


class DomainInfoSource(Source):
    name = "domain_info"
    description = "WHOIS + résolution DNS (A, MX, NS, TXT)."
    input_types = ("domain",)

    async def lookup(self, target: str, client: httpx.AsyncClient) -> Result:
        start = time.monotonic()
        result = Result(source=self.name, target=target, found=False)

        try:
            import whois as whois_lib  # type: ignore

            def _whois():
                try:
                    return whois_lib.whois(target)
                except Exception:
                    return None

            w = await asyncio.to_thread(_whois)
            if w:
                if getattr(w, "registrar", None):
                    result.findings.append(Finding(label="Registrar", value=str(w.registrar)))
                if getattr(w, "creation_date", None):
                    cd = w.creation_date if not isinstance(w.creation_date, list) else w.creation_date[0]
                    result.findings.append(Finding(label="Created", value=str(cd)))
                if getattr(w, "expiration_date", None):
                    ed = w.expiration_date if not isinstance(w.expiration_date, list) else w.expiration_date[0]
                    result.findings.append(Finding(label="Expires", value=str(ed)))
                if getattr(w, "name_servers", None):
                    ns = w.name_servers if isinstance(w.name_servers, list) else [w.name_servers]
                    result.findings.append(Finding(
                        label="Name Servers",
                        value=", ".join(str(x) for x in ns if x),
                    ))
                emails = getattr(w, "emails", None)
                if emails:
                    em = emails if isinstance(emails, list) else [emails]
                    result.findings.append(Finding(label="WHOIS emails", value=", ".join(em)))
        except ImportError:
            pass
        except Exception:
            pass

        try:
            import dns.resolver  # type: ignore

            for rtype in ("A", "AAAA", "MX", "NS", "TXT"):
                try:
                    answers = await asyncio.to_thread(
                        lambda rt=rtype: dns.resolver.resolve(target, rt, lifetime=5)
                    )
                    vals = [str(a).strip('"') for a in answers]
                    if vals:
                        extra = {}
                        if rtype == "A" and vals:
                            primary_ip = vals[0]
                            try:
                                r_ip = await client.get(f"http://ip-api.com/json/{primary_ip}", timeout=3)
                                if r_ip.status_code == 200:
                                    ip_data = r_ip.json()
                                    if ip_data.get("status") == "success":
                                        extra["ip"] = primary_ip
                                        extra["city"] = ip_data.get("city")
                                        extra["country"] = ip_data.get("country")
                                        extra["location"] = f"{ip_data.get('city')}, {ip_data.get('country')}"
                                        extra["latitude"] = ip_data.get("lat")
                                        extra["longitude"] = ip_data.get("lon")
                                        extra["isp"] = ip_data.get("isp")
                            except Exception:
                                pass
                        result.findings.append(
                            Finding(label=f"DNS {rtype}", value=" | ".join(vals[:8]), extra=extra)
                        )
                except Exception:
                    continue
        except ImportError:
            pass

        result.found = bool(result.findings)
        result.elapsed_ms = int((time.monotonic() - start) * 1000)
        return result


class CrtShSource(Source):
    name = "crt_sh"
    description = "Énumération de sous-domaines via Certificate Transparency logs."
    input_types = ("domain",)

    async def lookup(self, target: str, client: httpx.AsyncClient) -> Result:
        start = time.monotonic()
        result = Result(source=self.name, target=target, found=False)
        try:
            r = await client.get(
                "https://crt.sh/",
                params={"q": f"%.{target}", "output": "json"},
                timeout=25,
            )
            if r.status_code == 200 and r.text.strip():
                seen: set[str] = set()
                for entry in r.json()[:300]:
                    name = entry.get("name_value", "")
                    for sub in name.splitlines():
                        sub = sub.strip().lower().lstrip("*.")
                        if sub and target in sub and sub not in seen:
                            seen.add(sub)
                for sub in sorted(seen)[:60]:
                    result.findings.append(
                        Finding(label=sub, value="found in CT logs", url=f"https://{sub}")
                    )
                result.found = bool(result.findings)
        except Exception as e:
            result.error = str(e)
        result.elapsed_ms = int((time.monotonic() - start) * 1000)
        return result
