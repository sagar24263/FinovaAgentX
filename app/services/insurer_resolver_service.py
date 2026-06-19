from typing import List, Optional, Tuple

from app.config.env import BOT_HEADER_TOKEN, INVESTMENT_API_BASE_URL
from app.utils.api_client import make_sync_get_request
from app.utils.fuzzy_matcher import fuzzy_score
from app.utils.logger import get_logger

logger = get_logger("insurer_resolver_service")

_INSURER_MASTER_URL = f"{INVESTMENT_API_BASE_URL}/bot/GetInsurerMaster"
_MATCH_THRESHOLD    = 60.0


def _bot_headers() -> dict:
    return {
        "Authorization": BOT_HEADER_TOKEN or "",
        "Source": "pbhome",
        "Content-Type": "application/json",
    }


class InsurerResolverService:
    """Resolves an insurer name to (insurer_name, insurer_id) via the master API.

    The master list is fetched once and cached for the lifetime of the instance.
    Use a single shared instance (created at app startup or route module level).
    """

    def __init__(self) -> None:
        self._master: Optional[list] = None

    def _load_master(self) -> list:
        if self._master is not None:
            return self._master

        logger.info(f"Fetching insurer master from {_INSURER_MASTER_URL}")
        response = make_sync_get_request(_INSURER_MASTER_URL, headers=_bot_headers())

        if "error" in response:
            logger.error(f"Insurer master fetch failed: {response['error']}")
            self._master = []
            return self._master

        if response.get("HasError", True):
            logger.error("GetInsurerMaster returned HasError=true")
            self._master = []
            return self._master

        insurers = response.get("ReturnValue", [])
        if not isinstance(insurers, list):
            logger.error("GetInsurerMaster ReturnValue is not a list")
            self._master = []
            return self._master

        self._master = insurers
        logger.info(f"Insurer master loaded: {len(self._master)} entries")
        return self._master

    def resolve(self, product_name: str) -> Tuple[str, Optional[int]]:
        """Match *product_name* against the insurer master.

        Fund names embed the insurer name as a leading prefix, e.g.
        "Axis Max Life BSE 500 Index Fund" → insurer "Axis Max Life Insurance".
        Matching the full fund name against a short insurer name produces a poor
        score due to the extra fund-specific tokens.  To compensate, we score
        both the full name and all leading N-word slices (N = 2 … 5) and take
        the highest result across all queries.

        Returns (insurer_name, insurer_id) of the best match above threshold,
        or ("", None) when no match is found.
        """
        if not product_name or not product_name.strip():
            return "", None

        insurers = self._load_master()
        if not insurers:
            return "", None

        words  = product_name.strip().split()
        # Queries: full name + leading 2-, 3-, 4-, 5-word prefixes (deduplicated)
        queries: List[str] = list(dict.fromkeys(
            [product_name.strip()]
            + [" ".join(words[:n]) for n in range(2, min(6, len(words) + 1))]
        ))

        best_score  = 0.0
        best_name   = ""
        best_id: Optional[int] = None

        for insurer in insurers:
            if not isinstance(insurer, dict):
                continue
            candidate_name = insurer.get("InsurerName", "")
            if not candidate_name:
                continue

            score = max(fuzzy_score(q, candidate_name) for q in queries)
            if score > best_score:
                best_score = score
                best_name  = candidate_name
                best_id    = insurer.get("InsurerID")

        if best_score >= _MATCH_THRESHOLD:
            logger.info(
                f"Insurer resolved: '{product_name}' -> '{best_name}' "
                f"(id={best_id}, score={best_score:.1f})"
            )
            return best_name, best_id

        logger.warning(
            f"No insurer match for '{product_name}' "
            f"(best score={best_score:.1f} < threshold={_MATCH_THRESHOLD})"
        )
        return "", None
