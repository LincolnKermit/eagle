import time

import httpx

from .base import Finding, Result, Source


class PhoneInfoSource(Source):
    name = "phone_info"
    description = "Validation, pays, opérateur, fuseau horaire."
    input_types = ("phone",)

    async def lookup(self, target: str, client: httpx.AsyncClient) -> Result:
        start = time.monotonic()
        result = Result(source=self.name, target=target, found=False)
        try:
            import phonenumbers
            from phonenumbers import carrier, geocoder, timezone

            num = phonenumbers.parse(target, None)
            if not phonenumbers.is_valid_number(num):
                result.error = "Numéro invalide ou format non reconnu (essayez +33...)."
            else:
                country = geocoder.description_for_number(num, "fr")
                op = carrier.name_for_number(num, "fr")
                tz = timezone.time_zones_for_number(num)
                fmt_intl = phonenumbers.format_number(
                    num, phonenumbers.PhoneNumberFormat.INTERNATIONAL
                )
                fmt_e164 = phonenumbers.format_number(
                    num, phonenumbers.PhoneNumberFormat.E164
                )
                line_type = phonenumbers.number_type(num)
                line_names = {
                    0: "FIXED_LINE", 1: "MOBILE", 2: "FIXED_LINE_OR_MOBILE",
                    3: "TOLL_FREE", 4: "PREMIUM_RATE", 5: "SHARED_COST",
                    6: "VOIP", 7: "PERSONAL_NUMBER", 8: "PAGER",
                    9: "UAN", 10: "UNKNOWN", 27: "EMERGENCY",
                }
                result.found = True
                result.findings.append(Finding(label="Pays", value=country or "(inconnu)"))
                result.findings.append(Finding(label="Opérateur", value=op or "(inconnu)"))
                result.findings.append(Finding(label="Type", value=line_names.get(line_type, str(line_type))))
                result.findings.append(Finding(label="Fuseaux", value=", ".join(tz)))
                result.findings.append(Finding(label="Format international", value=fmt_intl))
                result.findings.append(Finding(label="Format E.164", value=fmt_e164))
        except ImportError:
            result.error = "phonenumbers non installé."
        except Exception as e:
            result.error = str(e)
        result.elapsed_ms = int((time.monotonic() - start) * 1000)
        return result
