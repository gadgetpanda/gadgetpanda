# Soft license

Honor-system entitlements for Gadget Panda (not DRM). MIT source can remove checks; signed keys + device bind package features for makers who opt in.

## Quick use

```bash
# Portal: signup → create key → pick features (see license-portal/)
gadgetpanda license activate gp_live_…
gadgetpanda license status
gadgetpanda license logout
```

Python:

```python
from gadgetpanda.license import init, require

init("gp_live_…")          # or GADGETPANDA_LICENSE_KEY
require("drone.stick")     # raises FeatureDenied if missing
```

## Soft defaults

| Mode | Behavior |
|------|----------|
| No key | Features open |
| Key activated | Only listed features |
| `GADGETPANDA_LICENSE_REQUIRED=1` | Deny until key |
| `GADGETPANDA_LICENSE_BYPASS=1` | All features (CI / forks) |

## Device bind

- Seed stored in `~/.gadgetpanda/license.json`
- One machine until `gadgetpanda license logout` or portal **Logout device**
- Offline: last signed token verified with embedded Ed25519 public key until `exp` (key TTL = 30 days)

## Portal

- Production: https://lib.gadgetpanda.app (also `https://gadgetpanda-license.kasetai-co.workers.dev`)
- Override: `GADGETPANDA_LICENSE_URL`
- Cloudflare Worker + D1: [`license-portal/`](../license-portal/README.md)
